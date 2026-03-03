"""
Real-time log reader (tail -f style).

Reads log files from the end and watches for new content,
providing callbacks when new lines arrive.
"""

import os
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Maximum number of lines to keep in buffer
MAX_BUFFER_LINES = 500
# How many lines to read initially (tail)
INITIAL_TAIL_LINES = 100
# Poll interval in seconds
POLL_INTERVAL = 1.0


class LogReader:
    """Watches a log file and emits new lines via callback."""

    def __init__(
        self,
        log_path: str,
        on_new_lines: Optional[Callable[[list[str]], None]] = None,
        max_lines: int = MAX_BUFFER_LINES,
    ):
        self.log_path = Path(log_path)
        self.on_new_lines = on_new_lines
        self.max_lines = max_lines

        self._buffer: list[str] = []
        self._file_pos: int = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def lines(self) -> list[str]:
        """Get current buffer contents (thread-safe copy)."""
        with self._lock:
            return list(self._buffer)

    def read_tail(self, n_lines: int = INITIAL_TAIL_LINES) -> list[str]:
        """Read the last N lines from the log file."""
        if not self.log_path.is_file():
            return []

        try:
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                # Seek to end
                f.seek(0, os.SEEK_END)
                file_size = f.tell()

                if file_size == 0:
                    return []

                # Read backwards to find n_lines
                lines = []
                chunk_size = 4096
                pos = file_size

                while pos > 0 and len(lines) <= n_lines:
                    read_size = min(chunk_size, pos)
                    pos -= read_size
                    f.seek(pos)
                    chunk = f.read(read_size)
                    lines = chunk.splitlines() + lines

                # Keep only last n_lines
                result = lines[-n_lines:] if len(lines) > n_lines else lines

                # Update position to end of file
                self._file_pos = file_size

                with self._lock:
                    self._buffer = result[-self.max_lines:]

                return result

        except OSError as e:
            logger.error("Error reading log %s: %s", self.log_path, e)
            return []

    def start_watching(self):
        """Start watching the log file in a background thread."""
        if self._running:
            return

        # Initial read
        self.read_tail()

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop_watching(self):
        """Stop the background watcher."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    def _watch_loop(self):
        """Background loop that polls for new log content."""
        while self._running:
            try:
                self._check_for_new_lines()
            except Exception as e:
                logger.error("Log watch error for %s: %s", self.log_path, e)
            time.sleep(POLL_INTERVAL)

    def _check_for_new_lines(self):
        """Read any new lines appended since last check."""
        if not self.log_path.is_file():
            return

        try:
            current_size = self.log_path.stat().st_size
        except OSError:
            return

        # File was truncated or rotated
        if current_size < self._file_pos:
            self._file_pos = 0

        if current_size <= self._file_pos:
            return

        try:
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._file_pos)
                new_content = f.read()
                self._file_pos = f.tell()

            if not new_content:
                return

            new_lines = new_content.splitlines()
            if not new_lines:
                return

            with self._lock:
                self._buffer.extend(new_lines)
                # Trim buffer
                if len(self._buffer) > self.max_lines:
                    self._buffer = self._buffer[-self.max_lines:]

            # Notify callback
            if self.on_new_lines:
                self.on_new_lines(new_lines)

        except OSError as e:
            logger.error("Error reading new lines from %s: %s", self.log_path, e)

    def clear(self):
        """Clear the internal buffer."""
        with self._lock:
            self._buffer.clear()
