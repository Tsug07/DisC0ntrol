"""
Main dashboard window.

Displays a responsive grid of bot cards with a toolbar for actions.
Handles bot discovery, system tray integration, and window state persistence.
"""

import logging
import threading
from pathlib import Path
import customtkinter as ctk

from core.bot_scanner import BotScanner
from core.bot_controller import BotController
from ui.bot_card import BotCard
from ui.log_viewer import LogViewer
from ui.add_bot_dialog import AddBotDialog
from ui.settings_dialog import SettingsDialog

# Max lines to keep in the internal log panel
_INTERNAL_LOG_MAX_LINES = 200

logger = logging.getLogger(__name__)

# Layout constants
CARD_PAD = 10


class Dashboard(ctk.CTk):
    """Main application window — the DisC0ntrol dashboard."""

    def __init__(self, config_path: str):
        super().__init__()

        self.scanner = BotScanner(config_path)
        self.controller = BotController()

        self._bot_cards: list[BotCard] = []
        self._bots: list[dict] = []
        self._log_viewers: dict[str, LogViewer] = {}
        self._scanning = False

        # Apply saved settings
        settings = self.scanner.config.get("settings", {})
        theme = settings.get("theme", "dark")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        self._setup_window()
        self._build_ui()

        # Initial scan (startup sequence runs after scan completes)
        self.after(200, lambda: self._refresh_bots(on_done=self._startup_sequence))

        # Auto-restart watcher
        if settings.get("auto_restart", False):
            self._start_auto_restart_watcher(settings.get("restart_interval_hours", 24))

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_window(self):
        self.title("DisC0ntrol - Bot Dashboard")
        self.geometry("850x700")
        self.minsize(500, 400)

        # Set window icon
        ico_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "favicon.ico"
        if ico_path.is_file():
            try:
                self.iconbitmap(str(ico_path))
            except Exception:
                pass

        # Try to restore window position from config
        win = self.scanner.config.get("window", {})
        if win.get("geometry"):
            try:
                self.geometry(win["geometry"])
            except Exception:
                pass

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Toolbar ──
        toolbar = ctk.CTkFrame(self, height=50, corner_radius=0, fg_color=("gray88", "gray18"))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_columnconfigure(2, weight=1)

        # Logo / title
        ctk.CTkLabel(
            toolbar,
            text="DisC0ntrol",
            font=("Segoe UI Black", 22),
            text_color=("#2c3e50", "#ecf0f1"),
        ).grid(row=0, column=0, padx=(16, 8), pady=10)

        # Bot count badge
        self._count_label = ctk.CTkLabel(
            toolbar,
            text="0 bots",
            font=("Segoe UI", 12),
            text_color=("gray50", "gray60"),
        )
        self._count_label.grid(row=0, column=1, padx=4)

        # Spacer
        ctk.CTkLabel(toolbar, text="").grid(row=0, column=2)

        # Toolbar buttons
        btn_style = dict(height=34, corner_radius=8, font=("Segoe UI", 12))

        ctk.CTkButton(
            toolbar,
            text="\u21bb  Atualizar",
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=self._refresh_bots,
            width=110,
            **btn_style,
        ).grid(row=0, column=3, padx=4, pady=10)

        ctk.CTkButton(
            toolbar,
            text="+  Adicionar",
            fg_color="#27ae60",
            hover_color="#219a52",
            command=self._open_add_dialog,
            width=110,
            **btn_style,
        ).grid(row=0, column=4, padx=4, pady=10)

        ctk.CTkButton(
            toolbar,
            text="\u2699  Config",
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=self._open_settings,
            width=90,
            **btn_style,
        ).grid(row=0, column=5, padx=4, pady=10)

        self._log_toggle_btn = ctk.CTkButton(
            toolbar,
            text="\u25b6 Log",
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=self._toggle_internal_log,
            width=70,
            **btn_style,
        )
        self._log_toggle_btn.grid(row=0, column=6, padx=(4, 16), pady=10)

        # ── Scrollable bot grid ──
        self._scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self._scroll_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)

        # ── Internal log panel (hidden by default) ──
        self._log_panel = ctk.CTkFrame(self, fg_color=("gray95", "gray10"), corner_radius=0)
        self._log_textbox = ctk.CTkTextbox(
            self._log_panel,
            height=150,
            font=("Consolas", 10),
            fg_color=("gray95", "gray10"),
            text_color=("gray30", "gray70"),
            corner_radius=0,
            state="disabled",
            wrap="word",
        )
        self._log_textbox.pack(fill="both", expand=True, padx=4, pady=4)
        self._log_panel_visible = False

        # Hook into Python logging to capture DisC0ntrol logs
        self._setup_log_handler()

        # ── Status bar ──
        self._statusbar = ctk.CTkLabel(
            self,
            text="Pronto",
            font=("Consolas", 10),
            text_color=("gray50", "gray60"),
            anchor="w",
            height=24,
        )
        self._statusbar.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 4))

        # ── Empty state ──
        self._empty_label = ctk.CTkLabel(
            self._scroll_frame,
            text="Nenhum bot encontrado.\n\nClique em \"+ Adicionar\" para registrar um diretorio\nou adicionar um bot individualmente.",
            font=("Segoe UI", 14),
            text_color=("gray50", "gray55"),
            justify="center",
        )

    # ------------------------------------------------------------------
    # Bot management
    # ------------------------------------------------------------------

    def _refresh_bots(self, on_done=None):
        """Re-scan directories in a background thread to avoid UI freeze."""
        if self._scanning:
            logger.debug("Scan already in progress, skipping.")
            return
        self._scanning = True
        self._set_status("Escaneando bots...")
        self._count_label.configure(text="...")

        # Destroy existing cards
        for card in self._bot_cards:
            card.destroy()
        self._bot_cards.clear()

        def _scan_worker():
            bots = self.scanner.scan_all()
            try:
                self.after(0, lambda: self._on_scan_done(bots, on_done))
            except RuntimeError:
                pass  # Window was closed during scan

        threading.Thread(target=_scan_worker, daemon=True).start()

    def _on_scan_done(self, bots: list[dict], on_done=None):
        """Handle scan results on the main thread."""
        try:
            # Clean orphan lock files before displaying status
            logger.info("Cleaning orphan locks...")
            self.controller.cleanup_orphans(bots)

            self._bots = bots
            self._count_label.configure(text=f"{len(self._bots)} bot(s)")

            if not self._bots:
                self._empty_label.pack(pady=60)
                self._set_status("Nenhum bot encontrado.")
            else:
                self._empty_label.pack_forget()
                logger.info("Building %d card(s)...", len(self._bots))
                self._build_card_grid()
                logger.info("Cards built successfully.")
                self._set_status(f"{len(self._bots)} bot(s) carregado(s).")

            if on_done:
                on_done()
        except Exception:
            logger.exception("Error in _on_scan_done")
        finally:
            self._scanning = False

    def _build_card_grid(self):
        """Create bot cards in a single-column vertical layout."""
        self._scroll_frame.grid_columnconfigure(0, weight=1)

        for idx, bot in enumerate(self._bots):
            card = BotCard(
                self._scroll_frame,
                bot_info=bot,
                controller=self.controller,
                on_expand_log=self._open_log_viewer,
                on_remove=self._remove_bot,
            )
            card.grid(row=idx, column=0, padx=CARD_PAD, pady=CARD_PAD, sticky="ew")
            self._bot_cards.append(card)

    def _remove_bot(self, bot_info: dict):
        """Remove a bot from the registered list and refresh."""
        self.scanner.remove_bot(bot_info["directory"])
        self._refresh_bots()

    def _startup_sequence(self):
        """Clean orphans, then auto-start bots after a 2-second delay."""
        if self._bots:
            self.controller.cleanup_orphans(self._bots)

        settings = self.scanner.config.get("settings", {})
        if settings.get("auto_start_bots", False) and self._bots:
            logger.info("Auto-start scheduled in 2 seconds...")
            self.after(2000, self._auto_start_all)

    def _auto_start_all(self):
        """Start all discovered bots that aren't already running."""
        count = 0
        def worker():
            nonlocal count
            for bot in self._bots:
                if not self.controller.is_running(bot):
                    ok, msg = self.controller.start(bot)
                    if ok:
                        count += 1
                        logger.info("Auto-started %s", bot["name"])
            try:
                self.after(0, lambda: self._set_status(
                    f"{count} bot(s) iniciado(s) automaticamente."
                ))
            except RuntimeError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    def _open_add_dialog(self):
        AddBotDialog(self, self.scanner, on_done=self._refresh_bots)

    def _open_settings(self):
        SettingsDialog(self, self.scanner, on_save=self._on_settings_saved)

    def _open_log_viewer(self, bot_info: dict, log_reader):
        """Open or focus an expanded log viewer for a bot."""
        key = bot_info["directory"]

        # Reuse existing viewer if still open
        if key in self._log_viewers:
            try:
                self._log_viewers[key].focus_force()
                return
            except Exception:
                del self._log_viewers[key]

        viewer = LogViewer(self, bot_info, log_reader)
        self._log_viewers[key] = viewer

    def _on_settings_saved(self, settings: dict):
        """Handle settings changes."""
        self._set_status("Configuracoes salvas.")

    # ------------------------------------------------------------------
    # Auto-restart watcher
    # ------------------------------------------------------------------

    def _start_auto_restart_watcher(self, interval_hours: int):
        """Periodically check for crashed bots and restart them."""
        interval_ms = max(30_000, int(interval_hours * 3600 * 1000))

        def check():
            for bot in self._bots:
                if not self.controller.is_running(bot):
                    logger.info("Auto-restarting %s", bot["name"])
                    self.controller.start(bot)
            self.after(interval_ms, check)

        self.after(interval_ms, check)

    # ------------------------------------------------------------------
    # System tray (lazy import)
    # ------------------------------------------------------------------

    def setup_tray(self):
        """Initialize system tray icon. Call after mainloop is running."""
        try:
            import pystray
            from PIL import Image, ImageDraw

            def create_icon():
                # Use the project logo if available, otherwise generate one
                logo_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "android-chrome-192x192.png"
                if logo_path.is_file():
                    return Image.open(logo_path).resize((64, 64))
                img = Image.new("RGB", (64, 64), "#2c3e50")
                draw = ImageDraw.Draw(img)
                draw.ellipse([12, 12, 52, 52], fill="#27ae60")
                draw.text((22, 20), "D", fill="white")
                return img

            def on_show(icon, item):
                self.after(0, self._show_from_tray)

            def on_quit(icon, item):
                self.after(0, self._quit)

            # Build menu items dynamically (callable for live status updates)
            def get_menu_items():
                items = [pystray.MenuItem("Abrir DisC0ntrol", on_show, default=True)]
                items.append(pystray.Menu.SEPARATOR)
                for bot in self._bots:
                    status = "Online" if self.controller.is_running(bot) else "Offline"
                    items.append(
                        pystray.MenuItem(
                            f"{bot['name']}: {status}", lambda *a: None, enabled=False
                        )
                    )
                items.append(pystray.Menu.SEPARATOR)
                items.append(pystray.MenuItem("Sair", on_quit))
                return items

            self._tray_icon = pystray.Icon(
                "DisC0ntrol",
                create_icon(),
                "DisC0ntrol",
                menu=pystray.Menu(get_menu_items),
            )

            threading.Thread(target=self._tray_icon.run, daemon=True).start()
            self._has_tray = True

        except ImportError:
            logger.warning("pystray/Pillow not installed — tray disabled")
            self._has_tray = False

    def minimize_to_tray(self):
        """Hide window and show tray icon."""
        if getattr(self, "_has_tray", False):
            self.withdraw()

    def _show_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    # ------------------------------------------------------------------
    # Internal log panel
    # ------------------------------------------------------------------

    def _setup_log_handler(self):
        """Attach a logging handler that feeds into the UI log panel."""
        handler = _UILogHandler(self)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
        logging.getLogger().addHandler(handler)

    def _append_internal_log(self, text: str):
        """Append a log line to the internal log panel (called from main thread)."""
        self._log_textbox.configure(state="normal")
        self._log_textbox.insert("end", text + "\n")
        # Trim excess lines
        content = self._log_textbox.get("1.0", "end").splitlines()
        total = len(content) - 1
        if total > _INTERNAL_LOG_MAX_LINES:
            excess = total - _INTERNAL_LOG_MAX_LINES
            self._log_textbox.delete("1.0", f"{excess + 1}.0")
        self._log_textbox.see("end")
        self._log_textbox.configure(state="disabled")

    def _toggle_internal_log(self):
        """Show/hide the internal log panel."""
        if self._log_panel_visible:
            self._log_panel.grid_forget()
            self._log_panel_visible = False
            self._log_toggle_btn.configure(text="\u25b6 Log")
        else:
            self._log_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
            self.grid_rowconfigure(2, weight=0)
            self._log_panel_visible = True
            self._log_toggle_btn.configure(text="\u25bc Log")

    # ------------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------------

    def _set_status(self, text: str):
        self._statusbar.configure(text=text)

    def _on_close(self):
        """Handle window close (X button) — minimize to tray if available."""
        # Save window geometry before hiding
        try:
            self.scanner.config["window"] = {"geometry": self.geometry()}
            self.scanner.save_config()
        except Exception:
            pass

        if getattr(self, "_has_tray", False):
            self.withdraw()  # Hide window, keep running in tray
        else:
            self._quit()  # No tray available, actually quit

    def _quit(self):
        """Fully exit the application (called from tray 'Sair')."""
        # Save window geometry
        try:
            if self.winfo_viewable():
                self.scanner.config["window"] = {"geometry": self.geometry()}
                self.scanner.save_config()
        except Exception:
            pass

        # Stop all running bots
        if self._bots:
            logger.info("Stopping all bots before exit...")
            self.controller.stop_all(self._bots)

        # Stop tray icon
        if getattr(self, "_has_tray", False):
            try:
                self._tray_icon.stop()
            except Exception:
                pass

        # Destroy cards (stops log readers)
        for card in self._bot_cards:
            try:
                card.destroy()
            except Exception:
                pass

        self.destroy()


class _UILogHandler(logging.Handler):
    """Logging handler that forwards records to the Dashboard log panel."""

    def __init__(self, dashboard: Dashboard):
        super().__init__()
        self._dashboard = dashboard

    def emit(self, record):
        try:
            msg = self.format(record)
            self._dashboard.after(0, self._dashboard._append_internal_log, msg)
        except RuntimeError:
            pass  # Window destroyed
