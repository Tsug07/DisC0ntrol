"""
DisC0ntrol — Discord Bot Dashboard
Entry point for the application.
"""

import sys
import os
import logging
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Config file location
CONFIG_PATH = PROJECT_ROOT / "config.json"

# Logging setup
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "discontrol.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("DisC0ntrol")


LOCK_FILE = PROJECT_ROOT / "discontrol.lock"


def _acquire_single_instance():
    """Ensure only one instance of DisC0ntrol is running."""
    import psutil

    if LOCK_FILE.is_file():
        try:
            old_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
            proc = psutil.Process(old_pid)
            if "python" in proc.name().lower():
                # Already running — bring focus hint via file and exit
                logger.warning("DisC0ntrol já está rodando (PID %d). Encerrando.", old_pid)
                print(f"DisC0ntrol já está em execução (PID {old_pid}).")
                sys.exit(0)
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError, OSError):
            pass  # Stale lock file — safe to proceed

    # Write current PID
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")

    import atexit
    atexit.register(lambda: LOCK_FILE.unlink(missing_ok=True))


def main():
    _acquire_single_instance()
    logger.info("Starting DisC0ntrol...")

    from ui.dashboard import Dashboard
    from ui.splash_screen import SplashScreen

    app = Dashboard(config_path=str(CONFIG_PATH))

    # Hide dashboard while splash is visible
    app.withdraw()

    splash = SplashScreen(app)

    def _on_splash_done():
        """Show the main window after splash closes."""
        app.deiconify()
        app.after(500, app.setup_tray)

        settings = app.scanner.config.get("settings", {})
        if settings.get("start_minimized", False):
            app.after(1000, app.minimize_to_tray)

    # When splash is destroyed, show the dashboard
    splash.bind("<Destroy>", lambda e: _on_splash_done() if e.widget is splash else None)

    app.mainloop()

    logger.info("DisC0ntrol closed.")


if __name__ == "__main__":
    main()
