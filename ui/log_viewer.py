"""
Expanded log viewer window.

A separate top-level window showing full log output for a specific bot,
with auto-scroll, search, and clear functionality.
"""

import customtkinter as ctk
from core.log_reader import LogReader


class LogViewer(ctk.CTkToplevel):
    """Full-size log viewer window for a specific bot."""

    def __init__(self, master, bot_info: dict, log_reader: LogReader = None, **kwargs):
        super().__init__(master, **kwargs)

        self.bot_info = bot_info
        self.log_reader = log_reader
        self._auto_scroll = True

        bot_name = bot_info.get("name", "Bot")
        bot_color = bot_info.get("color", "#7289da")

        self.title(f"DisC0ntrol - Logs: {bot_name}")
        self.geometry("800x600")
        self.minsize(500, 300)

        # Set window icon color reference
        self.configure(fg_color=("gray95", "gray14"))

        self._build_ui(bot_name, bot_color)
        self._load_initial_content()

        # Register for new lines
        if self.log_reader:
            self._original_callback = self.log_reader.on_new_lines
            self.log_reader.on_new_lines = self._on_new_lines

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self, bot_name: str, bot_color: str):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ──
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text=f"\u25cf  {bot_name} Logs",
            font=("Segoe UI Semibold", 16),
            text_color=bot_color,
        ).grid(row=0, column=0, sticky="w")

        # Search
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._highlight_search())

        search_entry = ctk.CTkEntry(
            header,
            placeholder_text="Buscar nos logs...",
            textvariable=self._search_var,
            width=200,
        )
        search_entry.grid(row=0, column=1, sticky="e", padx=(10, 5))

        # Auto-scroll toggle
        self._scroll_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            header,
            text="Auto-scroll",
            variable=self._scroll_var,
            command=self._toggle_auto_scroll,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=0, column=2, padx=(5, 5))

        # Clear button
        ctk.CTkButton(
            header,
            text="Limpar",
            width=70,
            height=28,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=self._clear_log,
        ).grid(row=0, column=3, padx=(5, 0))

        # ── Log text area ──
        self._log_text = ctk.CTkTextbox(
            self,
            font=("Consolas", 11),
            fg_color=("white", "gray8"),
            corner_radius=8,
            state="disabled",
            wrap="word",
        )
        self._log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # ── Status bar ──
        self._status = ctk.CTkLabel(
            self,
            text="",
            font=("Consolas", 10),
            text_color=("gray50", "gray60"),
            anchor="w",
        )
        self._status.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))

    def _load_initial_content(self):
        """Load existing log content."""
        if not self.log_reader:
            return

        lines = self.log_reader.lines
        if lines:
            self._log_text.configure(state="normal")
            self._log_text.insert("end", "\n".join(lines) + "\n")
            self._log_text.see("end")
            self._log_text.configure(state="disabled")
            self._update_status(len(lines))

    def _on_new_lines(self, lines: list[str]):
        """Handle new log lines from the reader."""
        # Forward to original callback (bot_card mini-log)
        if self._original_callback:
            self._original_callback(lines)

        try:
            self.after(0, self._append_lines, lines)
        except RuntimeError:
            pass

    def _append_lines(self, lines: list[str]):
        self._log_text.configure(state="normal")
        for line in lines:
            self._log_text.insert("end", line + "\n")
        if self._auto_scroll:
            self._log_text.see("end")
        self._log_text.configure(state="disabled")

        total = len(self._log_text.get("1.0", "end").splitlines()) - 1
        self._update_status(total)

    def _update_status(self, line_count: int):
        log_path = self.bot_info.get("log_file", "")
        self._base_status_text = f"{line_count} linhas  |  {log_path}"
        # Only update if no active search
        if not self._search_var.get().strip():
            self._status.configure(text=self._base_status_text)

    def _toggle_auto_scroll(self):
        self._auto_scroll = self._scroll_var.get()
        if self._auto_scroll:
            self._log_text.see("end")

    def _clear_log(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")
        self._update_status(0)

    def _highlight_search(self):
        """Highlight matching text and scroll to first match."""
        # Access the internal tkinter Text widget for tag support
        inner = self._log_text._textbox

        # Remove previous highlights
        inner.tag_remove("search_hl", "1.0", "end")

        term = self._search_var.get().strip()
        if not term:
            self._status.configure(text=self._base_status_text)
            return

        # Search and highlight all occurrences
        count = 0
        start_pos = "1.0"
        first_match = None

        while True:
            pos = inner.search(term, start_pos, stopindex="end", nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(term)}c"
            inner.tag_add("search_hl", pos, end_pos)
            if first_match is None:
                first_match = pos
            start_pos = end_pos
            count += 1

        # Configure highlight style
        inner.tag_config("search_hl", background="#f39c12", foreground="#000000")

        # Scroll to first match
        if first_match:
            inner.see(first_match)

        self._status.configure(
            text=f'{count} resultado(s) para "{term}"' if count else f'Nenhum resultado para "{term}"'
        )

    def _on_close(self):
        """Restore original callback and close."""
        if self.log_reader and hasattr(self, "_original_callback"):
            self.log_reader.on_new_lines = self._original_callback
        self.destroy()
