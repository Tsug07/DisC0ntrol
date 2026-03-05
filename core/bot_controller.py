"""
Bot process controller.

Manages starting, stopping, and restarting bot processes via subprocess.
Tracks PIDs through lock files and uses psutil for process verification.
"""

import os
import sys
import signal
import subprocess
import logging
import time
import threading
from pathlib import Path
from typing import Optional

import psutil

logger = logging.getLogger(__name__)


class BotController:
    """Controls bot processes (start/stop/restart) and monitors their status."""

    def __init__(self):
        self._processes: dict[str, subprocess.Popen] = {}

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_running(self, bot_info: dict) -> bool:
        """Check if a bot is currently running by verifying its PID."""
        pid = self.read_pid(bot_info)
        if pid is not None and self._pid_alive(pid):
            return True

        # Fallback: check tracked subprocess (for bots without lock files)
        proc = self._processes.get(bot_info.get("directory"))
        if proc is not None and proc.poll() is None:
            return True

        return False

    @staticmethod
    def read_pid(bot_info: dict) -> Optional[int]:
        """Read PID from the bot's lock file."""
        lock_path = bot_info.get("lock_file")
        if not lock_path:
            return None
        lock = Path(lock_path)
        if not lock.is_file():
            return None
        try:
            content = lock.read_text(encoding="utf-8").strip()
            return int(content)
        except (ValueError, OSError):
            return None

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        """Check if a PID corresponds to a running Python process."""
        try:
            proc = psutil.Process(pid)
            if proc.status() == psutil.STATUS_ZOMBIE:
                return False
            # Verify it's a Python process
            name = proc.name().lower()
            return "python" in name
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

    @staticmethod
    def get_process_info(bot_info: dict) -> Optional[dict]:
        """Get detailed process info for a running bot."""
        pid = BotController.read_pid(bot_info)
        if pid is None:
            return None
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                return {
                    "pid": pid,
                    "status": proc.status(),
                    "cpu_percent": proc.cpu_percent(interval=None),
                    "memory_mb": round(proc.memory_info().rss / (1024 * 1024), 1),
                    "create_time": proc.create_time(),
                    "uptime_seconds": time.time() - proc.create_time(),
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    # ------------------------------------------------------------------
    # Process control
    # ------------------------------------------------------------------

    def start(self, bot_info: dict) -> tuple[bool, str]:
        """Start a bot process.

        Returns (success, message).
        """
        if self.is_running(bot_info):
            return False, f"{bot_info['name']} já está rodando."

        script = bot_info.get("script")
        if not script or not Path(script).is_file():
            return False, f"Script não encontrado: {script}"

        bot_dir = bot_info.get("directory", str(Path(script).parent))

        # Build environment with bot's .env if available
        env = os.environ.copy()
        env_file = bot_info.get("env_file")
        if env_file and Path(env_file).is_file():
            env.update(_parse_env_file(Path(env_file)))

        try:
            # Use the same Python interpreter that runs DisC0ntrol
            python_exe = sys.executable

            # Redirect stderr to a crash log for debugging
            logs_dir = Path(bot_dir) / "logs"
            logs_dir.mkdir(exist_ok=True)
            stderr_path = logs_dir / "stderr.log"
            stderr_file = open(stderr_path, "a", encoding="utf-8")

            # Remove stale lock file before starting so the bot
            # doesn't think it's already running
            lock_path = bot_info.get("lock_file")
            if lock_path and Path(lock_path).is_file():
                try:
                    Path(lock_path).unlink()
                except OSError:
                    pass

            proc = subprocess.Popen(
                [python_exe, script],
                cwd=bot_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=stderr_file,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            # Let the bot create its own lock file.
            # Store the PID in memory for tracking.
            self._processes[bot_info["directory"]] = proc

            # Schedule fallback lock file creation after 10s
            # (gives bot time to create its own lock file first)
            def _deferred_lock(bi=bot_info, p=proc):
                time.sleep(10)
                if p.poll() is None:  # Still running
                    self._ensure_lock_file(bi, p.pid)

            threading.Thread(target=_deferred_lock, daemon=True).start()

            logger.info("Started %s (PID %d)", bot_info["name"], proc.pid)
            return True, f"{bot_info['name']} iniciado (PID {proc.pid})."

        except OSError as e:
            logger.error("Failed to start %s: %s", bot_info["name"], e)
            return False, f"Erro ao iniciar {bot_info['name']}: {e}"

    def stop(self, bot_info: dict) -> tuple[bool, str]:
        """Stop a bot process gracefully, then force-kill if needed.

        Returns (success, message).
        """
        pid = self.read_pid(bot_info)

        # Fallback: get PID from tracked subprocess
        if (pid is None or not self._pid_alive(pid)):
            proc = self._processes.get(bot_info.get("directory"))
            if proc is not None and proc.poll() is None:
                pid = proc.pid
            else:
                self._cleanup_lock(bot_info)
                self._processes.pop(bot_info.get("directory"), None)
                return False, f"{bot_info['name']} não está rodando."

        try:
            proc = psutil.Process(pid)

            # Graceful termination
            proc.terminate()

            try:
                proc.wait(timeout=5)
            except psutil.TimeoutExpired:
                # Force kill
                logger.warning("Force killing %s (PID %d)", bot_info["name"], pid)
                proc.kill()
                proc.wait(timeout=3)

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning("Error stopping %s: %s", bot_info["name"], e)

        # Clean up lock file
        self._cleanup_lock(bot_info)

        # Remove from tracked processes
        self._processes.pop(bot_info["directory"], None)

        logger.info("Stopped %s (PID %d)", bot_info["name"], pid)
        return True, f"{bot_info['name']} parado."

    def restart(self, bot_info: dict) -> tuple[bool, str]:
        """Restart a bot (stop then start).

        Returns (success, message).
        """
        if self.is_running(bot_info):
            ok, msg = self.stop(bot_info)
            if not ok:
                return False, f"Falha ao parar: {msg}"
            # Brief pause to ensure port/resource release
            time.sleep(1)

        return self.start(bot_info)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_lock_file(bot_info: dict, pid: int):
        """Create a lock file if the bot didn't create one itself."""
        lock_path = bot_info.get("lock_file")
        if not lock_path:
            return
        lock = Path(lock_path)
        if not lock.is_file():
            try:
                lock.parent.mkdir(parents=True, exist_ok=True)
                lock.write_text(str(pid), encoding="utf-8")
                logger.info("Created fallback lock file for %s (PID %d)", bot_info.get("name"), pid)
            except OSError:
                pass

    @staticmethod
    def _cleanup_lock(bot_info: dict):
        """Remove the lock file for a stopped bot."""
        lock_path = bot_info.get("lock_file")
        if lock_path:
            lock = Path(lock_path)
            if lock.is_file():
                try:
                    lock.unlink()
                except OSError:
                    pass

    def cleanup_orphans(self, bots: list[dict]):
        """Check all known bots for orphan lock files (PID not running) and clean up."""
        for bot in bots:
            pid = self.read_pid(bot)
            if pid is not None and not self._pid_alive(pid):
                logger.info(
                    "Cleaning orphan lock for %s (stale PID %d)", bot["name"], pid
                )
                self._cleanup_lock(bot)

    def stop_all(self, bots: list[dict]):
        """Stop all running bots."""
        for bot in bots:
            if self.is_running(bot):
                self.stop(bot)


def _parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a .env file into a dict, ignoring comments and empty lines."""
    result = {}
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("\"'")
                if key:
                    result[key] = value
    except OSError:
        pass
    return result
