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


def main():
    logger.info("Starting DisC0ntrol...")

    from ui.dashboard import Dashboard

    app = Dashboard(config_path=str(CONFIG_PATH))

    # Setup system tray after window is shown
    app.after(1000, app.setup_tray)

    # Handle start minimized
    settings = app.scanner.config.get("settings", {})
    if settings.get("start_minimized", False):
        app.after(1500, app.minimize_to_tray)

    app.mainloop()

    logger.info("DisC0ntrol closed.")


if __name__ == "__main__":
    main()
