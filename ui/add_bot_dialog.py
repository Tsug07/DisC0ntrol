"""
Add bot dialog.

Allows users to:
1. Register an entire directory for auto-scanning (Bot_*/ folders)
2. Add a single bot by selecting its script file
"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path


class AddBotDialog(ctk.CTkToplevel):
    """Dialog for adding bots or bot directories."""

    def __init__(self, master, scanner, on_done=None, **kwargs):
        super().__init__(master, **kwargs)

        self.scanner = scanner
        self.on_done = on_done

        self.title("DisC0ntrol - Adicionar Bot")
        self.geometry("520x560")
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
            text="Adicionar Bots",
            font=("Segoe UI Semibold", 20),
        ).grid(row=0, column=0, pady=(20, 10))

        # ── Option 1: Register directory ──
        dir_frame = ctk.CTkFrame(self, corner_radius=10)
        dir_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        dir_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dir_frame,
            text="\U0001f4c1  Registrar Diretorio",
            font=("Segoe UI Semibold", 14),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 2))

        ctk.CTkLabel(
            dir_frame,
            text="Escaneia automaticamente pastas Bot_*/ no diretorio selecionado.",
            font=("Segoe UI", 11),
            text_color=("gray50", "gray60"),
            anchor="w",
            wraplength=440,
        ).grid(row=1, column=0, sticky="w", padx=15, pady=(0, 4))

        self._dir_path_var = ctk.StringVar()
        dir_input = ctk.CTkFrame(dir_frame, fg_color="transparent")
        dir_input.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 12))
        dir_input.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(
            dir_input,
            textvariable=self._dir_path_var,
            placeholder_text="C:\\caminho\\para\\DisBot_Canella",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            dir_input,
            text="Escolher...",
            width=90,
            command=self._browse_directory,
        ).grid(row=0, column=1)

        ctk.CTkButton(
            dir_frame,
            text="Registrar Diretorio",
            fg_color="#27ae60",
            hover_color="#219a52",
            command=self._add_directory,
        ).grid(row=3, column=0, padx=15, pady=(0, 12))

        # ── Separator ──
        ctk.CTkLabel(
            self,
            text="- ou -",
            font=("Segoe UI", 12),
            text_color=("gray50", "gray60"),
        ).grid(row=2, column=0, pady=4)

        # ── Option 2: Add single bot ──
        bot_frame = ctk.CTkFrame(self, corner_radius=10)
        bot_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=8)
        bot_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            bot_frame,
            text="\U0001f916  Adicionar Bot Individual",
            font=("Segoe UI Semibold", 14),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 2))

        ctk.CTkLabel(
            bot_frame,
            text="Selecione o script principal (.py) do bot Discord.",
            font=("Segoe UI", 11),
            text_color=("gray50", "gray60"),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=15, pady=(0, 4))

        self._script_path_var = ctk.StringVar()
        script_input = ctk.CTkFrame(bot_frame, fg_color="transparent")
        script_input.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 4))
        script_input.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(
            script_input,
            textvariable=self._script_path_var,
            placeholder_text="C:\\caminho\\Bot_Meu\\meu_bot.py",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            script_input,
            text="Escolher...",
            width=90,
            command=self._browse_script,
        ).grid(row=0, column=1)

        # Bot name and color
        meta_frame = ctk.CTkFrame(bot_frame, fg_color="transparent")
        meta_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 4))
        meta_frame.grid_columnconfigure(0, weight=1)
        meta_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(meta_frame, text="Nome:", font=("Segoe UI", 11)).grid(
            row=0, column=0, sticky="w"
        )
        self._bot_name_var = ctk.StringVar()
        ctk.CTkEntry(
            meta_frame,
            textvariable=self._bot_name_var,
            placeholder_text="(auto-detectar)",
        ).grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(meta_frame, text="Cor:", font=("Segoe UI", 11)).grid(
            row=0, column=1, sticky="w"
        )
        self._bot_color_var = ctk.StringVar(value="#7289da")
        ctk.CTkEntry(
            meta_frame,
            textvariable=self._bot_color_var,
            placeholder_text="#7289da",
        ).grid(row=1, column=1, sticky="ew")

        ctk.CTkButton(
            bot_frame,
            text="Adicionar Bot",
            fg_color="#2980b9",
            hover_color="#2471a3",
            command=self._add_bot,
        ).grid(row=4, column=0, padx=15, pady=(8, 12))

        # ── Status ──
        self._status_label = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI", 11),
            text_color=("gray50", "gray60"),
        )
        self._status_label.grid(row=4, column=0, pady=(4, 12))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_directory(self):
        path = filedialog.askdirectory(title="Selecione o diretorio dos bots")
        if path:
            self._dir_path_var.set(path)

    def _browse_script(self):
        path = filedialog.askopenfilename(
            title="Selecione o script do bot",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if path:
            self._script_path_var.set(path)
            # Auto-fill name from parent folder
            parent = Path(path).parent.name
            if parent.startswith("Bot_"):
                self._bot_name_var.set(parent.replace("Bot_", ""))

    def _add_directory(self):
        path = self._dir_path_var.get().strip()
        if not path:
            self._show_status("Selecione um diretorio.", "#c0392b")
            return
        if not Path(path).is_dir():
            self._show_status("Diretorio nao encontrado.", "#c0392b")
            return

        count = self.scanner.add_directory(path)
        self._show_status(
            f"Diretorio registrado! {count} bot(s) encontrado(s).", "#27ae60"
        )
        if self.on_done:
            self.on_done()

    def _add_bot(self):
        script = self._script_path_var.get().strip()
        if not script:
            self._show_status("Selecione o script do bot.", "#c0392b")
            return
        if not Path(script).is_file():
            self._show_status("Arquivo nao encontrado.", "#c0392b")
            return

        name = self._bot_name_var.get().strip()
        color = self._bot_color_var.get().strip() or "#7289da"

        info = self.scanner.add_bot_manually(script, name, color)
        if info:
            self._show_status(f"Bot '{info['name']}' adicionado!", "#27ae60")
            if self.on_done:
                self.on_done()
        else:
            self._show_status("Falha ao adicionar bot.", "#c0392b")

    def _show_status(self, text: str, color: str):
        self._status_label.configure(text=text, text_color=color)
