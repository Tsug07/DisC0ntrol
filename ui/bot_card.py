"""
Bot card widget.

A compact card displaying bot info, status, controls, and a mini log view.
Each card represents one discovered/registered bot.
"""

import os
import time
import threading
import customtkinter as ctk

from core.bot_controller import BotController
from core.log_reader import LogReader

# Mini-log: max visible lines
MINI_LOG_LINES = 8


class BotCard(ctk.CTkFrame):
    """Card widget for a single bot with status, controls, and mini-log."""

    def __init__(
        self,
        master,
        bot_info: dict,
        controller: BotController,
        on_expand_log=None,
        on_remove=None,
        **kwargs,
    ):
        self.bot_info = bot_info
        self.controller = controller
        self.on_expand_log = on_expand_log
        self.on_remove = on_remove

        bot_color = bot_info.get("color", "#7289da")

        super().__init__(
            master,
            corner_radius=12,
            border_width=2,
            border_color=bot_color,
            fg_color=("gray92", "gray17"),
            **kwargs,
        )

        self._bot_color = bot_color
        self._is_running = False
        self._log_reader = None
        self._status_poll_id = None

        self._build_ui()
        self._setup_log_reader()
        self._poll_status()

    def _build_ui(self):
        """Construct the card layout."""
        self.grid_columnconfigure(0, weight=1)

        # ── Row 0: Header (color accent + name + status) ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        header.grid_columnconfigure(1, weight=1)

        # Color dot
        self._dot = ctk.CTkLabel(
            header, text="\u25cf", font=("Segoe UI", 22), text_color=self._bot_color
        )
        self._dot.grid(row=0, column=0, padx=(0, 6))

        # Bot name
        ctk.CTkLabel(
            header,
            text=self.bot_info["name"],
            font=("Segoe UI Semibold", 16),
            anchor="w",
        ).grid(row=0, column=1, sticky="w")

        # Status badge
        self._status_label = ctk.CTkLabel(
            header,
            text="Offline",
            font=("Segoe UI", 12),
            corner_radius=6,
            fg_color=("gray80", "gray30"),
            text_color=("gray40", "gray70"),
            width=70,
            height=24,
        )
        self._status_label.grid(row=0, column=2, padx=(6, 0))

        # ── Row 1: Process info ──
        self._info_label = ctk.CTkLabel(
            self,
            text="",
            font=("Consolas", 11),
            text_color=("gray50", "gray60"),
            anchor="w",
        )
        self._info_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 2))

        # ── Row 2: Control buttons ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=4)

        btn_style = dict(height=30, corner_radius=8, font=("Segoe UI", 12))

        self._start_btn = ctk.CTkButton(
            btn_frame,
            text="\u25b6  Start",
            fg_color="#27ae60",
            hover_color="#219a52",
            command=self._on_start,
            **btn_style,
        )
        self._start_btn.pack(side="left", padx=(0, 4))

        self._stop_btn = ctk.CTkButton(
            btn_frame,
            text="\u25a0  Stop",
            fg_color="#c0392b",
            hover_color="#a93226",
            command=self._on_stop,
            **btn_style,
        )
        self._stop_btn.pack(side="left", padx=4)

        self._restart_btn = ctk.CTkButton(
            btn_frame,
            text="\u21bb  Restart",
            fg_color="#2980b9",
            hover_color="#2471a3",
            command=self._on_restart,
            **btn_style,
        )
        self._restart_btn.pack(side="left", padx=4)

        # Open log file in OS default editor
        ctk.CTkButton(
            btn_frame,
            text="\U0001f4c4 Log",
            width=60,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=self._open_log_file,
            **btn_style,
        ).pack(side="right", padx=(4, 0))

        # Expand log button (in-app viewer)
        ctk.CTkButton(
            btn_frame,
            text="\u2197",
            width=30,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=self._on_expand,
            **{k: v for k, v in btn_style.items() if k != "font"},
            font=("Segoe UI", 14),
        ).pack(side="right", padx=(4, 0))

        # Remove button
        if self.on_remove:
            ctk.CTkButton(
                btn_frame,
                text="\u2715",
                width=30,
                fg_color=("gray75", "gray30"),
                hover_color=("#c0392b", "#c0392b"),
                command=lambda: self.on_remove(self.bot_info),
                **{k: v for k, v in btn_style.items() if k != "font"},
                font=("Segoe UI", 14),
            ).pack(side="right", padx=(4, 0))

        # ── Row 3: Mini log ──
        self._log_text = ctk.CTkTextbox(
            self,
            height=120,
            font=("Consolas", 10),
            fg_color=("gray95", "gray10"),
            corner_radius=8,
            state="disabled",
            wrap="word",
        )
        self._log_text.grid(row=3, column=0, sticky="ew", padx=10, pady=(4, 10))

    # ------------------------------------------------------------------
    # Log reader
    # ------------------------------------------------------------------

    def _setup_log_reader(self):
        """Initialize log reader for this bot."""
        log_path = self.bot_info.get("log_file")
        if not log_path:
            return

        self._log_reader = LogReader(
            log_path, on_new_lines=self._on_new_log_lines
        )
        self._log_reader.start_watching()

        # Show initial tail content
        initial = self._log_reader.lines
        if initial:
            self._append_log_lines(initial[-MINI_LOG_LINES:])

    def _on_new_log_lines(self, lines: list[str]):
        """Callback from log reader thread — schedule UI update."""
        try:
            self.after(0, self._append_log_lines, lines)
        except RuntimeError:
            pass

    def _append_log_lines(self, lines: list[str]):
        """Append lines to the mini-log textbox."""
        self._log_text.configure(state="normal")
        for line in lines:
            self._log_text.insert("end", line + "\n")
        # Trim to keep only the most recent MINI_LOG_LINES lines
        content = self._log_text.get("1.0", "end").splitlines()
        # Subtract 1 because get("1.0", "end") adds a trailing empty line
        total = len(content) - 1
        if total > MINI_LOG_LINES:
            excess = total - MINI_LOG_LINES
            self._log_text.delete("1.0", f"{excess + 1}.0")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Status polling
    # ------------------------------------------------------------------

    def _poll_status(self):
        """Periodically check bot status and update UI."""
        running = self.controller.is_running(self.bot_info)

        if running != self._is_running:
            self._is_running = running
            self._update_status_ui(running)

        if running:
            info = self.controller.get_process_info(self.bot_info)
            if info:
                uptime = self._format_uptime(info["uptime_seconds"])
                self._info_label.configure(
                    text=f"PID {info['pid']}  |  CPU {info['cpu_percent']:.0f}%  |  RAM {info['memory_mb']} MB  |  Up {uptime}"
                )
            else:
                self._info_label.configure(text="")
        else:
            self._info_label.configure(text="")

        self._status_poll_id = self.after(3000, self._poll_status)

    def _update_status_ui(self, running: bool):
        """Update visual indicators based on bot status."""
        if running:
            self._status_label.configure(
                text="Online",
                fg_color=("#d5f5e3", "#1a3a2a"),
                text_color="#27ae60",
            )
            self._start_btn.configure(state="disabled")
            self._stop_btn.configure(state="normal")
            self._restart_btn.configure(state="normal")
            self.configure(border_color=self._bot_color)
        else:
            self._status_label.configure(
                text="Offline",
                fg_color=("gray80", "gray30"),
                text_color=("gray40", "gray70"),
            )
            self._start_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")
            self._restart_btn.configure(state="disabled")
            self.configure(border_color=("gray70", "gray35"))

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        s = int(seconds)
        if s < 60:
            return f"{s}s"
        if s < 3600:
            return f"{s // 60}m {s % 60}s"
        h = s // 3600
        m = (s % 3600) // 60
        return f"{h}h {m}m"

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_start(self):
        self._run_in_thread(lambda: self.controller.start(self.bot_info))

    def _on_stop(self):
        self._run_in_thread(lambda: self.controller.stop(self.bot_info))

    def _on_restart(self):
        self._run_in_thread(lambda: self.controller.restart(self.bot_info))

    def _run_in_thread(self, func):
        """Run a controller action in a background thread to avoid blocking UI."""
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="disabled")
        self._restart_btn.configure(state="disabled")

        def worker():
            ok, msg = func()
            try:
                self.after(0, self._force_status_refresh)
            except RuntimeError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _force_status_refresh(self, retries=3):
        """Force update status and buttons, retrying briefly for lock file creation."""
        running = self.controller.is_running(self.bot_info)
        if not running and retries > 0:
            # Bot may not have created its lock file yet — retry shortly
            self.after(1500, lambda: self._force_status_refresh(retries - 1))
            return
        self._is_running = running
        self._update_status_ui(running)

    def _open_log_file(self):
        """Open the log file in the OS default application."""
        log_path = self.bot_info.get("log_file")
        if log_path and os.path.isfile(log_path):
            os.startfile(log_path)

    def _on_expand(self):
        if self.on_expand_log:
            self.on_expand_log(self.bot_info, self._log_reader)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def destroy(self):
        if self._status_poll_id:
            self.after_cancel(self._status_poll_id)
        if self._log_reader:
            self._log_reader.stop_watching()
        super().destroy()
