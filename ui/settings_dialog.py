"""
Settings dialog.

Configures global preferences:
- Auto-restart bots
- Restart interval
- Start minimized
- Theme selection
- Registered directories management
"""

import customtkinter as ctk


class SettingsDialog(ctk.CTkToplevel):
    """Settings/preferences window."""

    def __init__(self, master, scanner, on_save=None, **kwargs):
        super().__init__(master, **kwargs)

        self.scanner = scanner
        self.on_save = on_save
        self.settings = dict(scanner.config.get("settings", {}))

        self.title("DisC0ntrol - Configuracoes")
        self.geometry("480x520")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self.after(100, self.focus_force)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # ── Title ──
        ctk.CTkLabel(
            self,
            text="\u2699  Configuracoes",
            font=("Segoe UI Semibold", 20),
        ).grid(row=0, column=0, pady=(20, 15))

        # ── General settings ──
        gen_frame = ctk.CTkFrame(self, corner_radius=10)
        gen_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        gen_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            gen_frame,
            text="Geral",
            font=("Segoe UI Semibold", 14),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 8))

        # Auto-restart
        self._auto_restart_var = ctk.BooleanVar(
            value=self.settings.get("auto_restart", False)
        )
        ctk.CTkCheckBox(
            gen_frame,
            text="Reiniciar bots automaticamente se caírem",
            variable=self._auto_restart_var,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=15, pady=4)

        # Restart interval
        ctk.CTkLabel(
            gen_frame,
            text="Intervalo de restart (horas):",
            font=("Segoe UI", 12),
        ).grid(row=2, column=0, sticky="w", padx=15, pady=4)

        self._restart_interval_var = ctk.StringVar(
            value=str(self.settings.get("restart_interval_hours", 24))
        )
        ctk.CTkEntry(
            gen_frame,
            textvariable=self._restart_interval_var,
            width=80,
        ).grid(row=2, column=1, sticky="w", padx=15, pady=4)

        # Auto-start bots
        self._auto_start_var = ctk.BooleanVar(
            value=self.settings.get("auto_start_bots", False)
        )
        ctk.CTkCheckBox(
            gen_frame,
            text="Iniciar todos os bots ao abrir o DisC0ntrol",
            variable=self._auto_start_var,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=15, pady=4)

        # Start minimized
        self._start_minimized_var = ctk.BooleanVar(
            value=self.settings.get("start_minimized", False)
        )
        ctk.CTkCheckBox(
            gen_frame,
            text="Iniciar minimizado na bandeja",
            variable=self._start_minimized_var,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=15, pady=(4, 12))

        # ── Appearance ──
        app_frame = ctk.CTkFrame(self, corner_radius=10)
        app_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=5)
        app_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            app_frame,
            text="Aparencia",
            font=("Segoe UI Semibold", 14),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 8))

        ctk.CTkLabel(
            app_frame,
            text="Tema:",
            font=("Segoe UI", 12),
        ).grid(row=1, column=0, sticky="w", padx=15, pady=(4, 12))

        self._theme_var = ctk.StringVar(value=self.settings.get("theme", "dark"))
        ctk.CTkSegmentedButton(
            app_frame,
            values=["dark", "light", "system"],
            variable=self._theme_var,
        ).grid(row=1, column=1, sticky="w", padx=15, pady=(4, 12))

        # ── Registered directories ──
        dir_frame = ctk.CTkFrame(self, corner_radius=10)
        dir_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=5)
        dir_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dir_frame,
            text="Diretorios Registrados",
            font=("Segoe UI Semibold", 14),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 8))

        self._dir_listbox = ctk.CTkTextbox(
            dir_frame,
            height=80,
            font=("Consolas", 10),
        )
        self._dir_listbox.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 4))

        # Bind click to select a line
        self._dir_listbox._textbox.bind("<ButtonRelease-1>", self._on_dir_click)
        self._selected_dir = None
        self._refresh_dir_list()

        btn_row = ctk.CTkFrame(dir_frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 12))

        ctk.CTkButton(
            btn_row,
            text="Remover Selecionado",
            fg_color="#c0392b",
            hover_color="#a93226",
            width=150,
            height=28,
            command=self._remove_directory,
        ).pack(side="left")

        # ── Buttons ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(15, 20))
        btn_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_frame,
            text="Salvar",
            fg_color="#27ae60",
            hover_color="#219a52",
            width=120,
            command=self._save,
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_frame,
            text="Cancelar",
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            width=100,
            command=self.destroy,
        ).pack(side="right")

    def _refresh_dir_list(self):
        dirs = self.scanner.config.get("bot_directories", [])
        inner = self._dir_listbox._textbox
        inner.config(state="normal")
        inner.delete("1.0", "end")
        for d in dirs:
            inner.insert("end", d + "\n")
        inner.config(state="disabled")
        self._selected_dir = None
        inner.tag_remove("sel_line", "1.0", "end")

    def _on_dir_click(self, event=None):
        """Select the clicked line in the directory list."""
        inner = self._dir_listbox._textbox
        inner.tag_remove("sel_line", "1.0", "end")

        # Get clicked line
        line_idx = inner.index("@0,%d" % event.y).split(".")[0]
        line_text = inner.get(f"{line_idx}.0", f"{line_idx}.end").strip()

        if not line_text:
            self._selected_dir = None
            return

        self._selected_dir = line_text
        inner.tag_add("sel_line", f"{line_idx}.0", f"{line_idx}.end")
        inner.tag_config("sel_line", background="#2980b9", foreground="#ffffff")

    def _remove_directory(self):
        """Remove the selected directory from the list."""
        if not self._selected_dir:
            # Fallback: show a brief hint
            return

        dirs = self.scanner.config.get("bot_directories", [])
        # Match against registered dirs (handle trailing slashes / normalization)
        target = self._selected_dir.rstrip("\\/")
        for d in dirs:
            if d.rstrip("\\/") == target:
                self.scanner.remove_directory(d)
                break

        self._refresh_dir_list()

    def _save(self):
        try:
            interval = int(self._restart_interval_var.get())
        except ValueError:
            interval = 24

        self.settings.update({
            "auto_restart": self._auto_restart_var.get(),
            "restart_interval_hours": max(1, interval),
            "auto_start_bots": self._auto_start_var.get(),
            "start_minimized": self._start_minimized_var.get(),
            "theme": self._theme_var.get(),
        })

        self.scanner.config["settings"] = self.settings
        self.scanner.save_config()

        # Apply theme
        ctk.set_appearance_mode(self.settings["theme"])

        if self.on_save:
            self.on_save(self.settings)

        self.destroy()
