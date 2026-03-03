"""
Bot autodiscovery module.

Scans registered directories for bot folders and identifies:
- Main script (Python file importing discord)
- .env config files
- Lock files (PID tracking)
- Log directories

Detection works with any folder name — not limited to Bot_*/ pattern.
A directory is considered a bot if it contains a .py file that imports discord.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Known bot color mapping (can be extended via config)
DEFAULT_BOT_COLORS = {
    "gerson": "#27ae60",
    "bip": "#ff8c00",
    "rebecca": "#0076ff",
}

# Directories to skip during scan (not bots)
_SKIP_DIRS = {
    "venv", "env", ".venv", ".env", "__pycache__", "node_modules",
    ".git", ".svn", "logs", "backups", "backup", "config", "assets",
    "scripts", "docs", "tests", "test", ".idea", ".vscode",
}


def discover_bot_info(bot_dir: Path) -> Optional[dict]:
    """Analyze a directory and extract bot metadata.

    Works with any folder name — not limited to Bot_*/ pattern.
    A directory is considered a bot if it contains a .py file that imports discord.

    Returns a dict with bot info or None if not a valid bot directory.
    """
    if not bot_dir.is_dir():
        return None

    dir_name = bot_dir.name
    # Extract bot name: Bot_Gerson -> Gerson, Disbot -> Disbot, Mionions -> Mionions
    match = re.match(r"^Bot_(.+)$", dir_name, re.IGNORECASE)
    bot_name = match.group(1) if match else dir_name
    bot_key = bot_name.lower()

    info = {
        "name": bot_name,
        "directory": str(bot_dir),
        "script": None,
        "env_file": None,
        "lock_file": None,
        "log_file": None,
        "color": DEFAULT_BOT_COLORS.get(bot_key, "#7289da"),
    }

    # Find main script: look for .py files that import discord
    info["script"] = _find_main_script(bot_dir, bot_key)

    # Find .env file
    info["env_file"] = _find_env_file(bot_dir)

    # Find lock file
    info["lock_file"] = _find_lock_file(bot_dir, bot_key)

    # Find log file
    info["log_file"] = _find_log_file(bot_dir)

    if info["script"] is None:
        logger.warning("No Discord bot script found in %s", bot_dir)
        return None

    return info


def _find_main_script(bot_dir: Path, bot_key: str) -> Optional[str]:
    """Find the main bot script by checking for discord imports."""
    # Priority 1: file named <bot_key>_bot.py
    expected_name = f"{bot_key}_bot.py"
    expected_path = bot_dir / expected_name
    if expected_path.is_file() and _has_discord_import(expected_path):
        return str(expected_path)

    # Priority 2: any .py file with discord import (not bot_manager.py)
    candidates = []
    for py_file in bot_dir.glob("*.py"):
        if py_file.name == "bot_manager.py":
            continue
        if py_file.name.startswith("__"):
            continue
        if _has_discord_import(py_file):
            candidates.append(py_file)

    if candidates:
        # Prefer files with 'bot' in name
        for c in candidates:
            if "bot" in c.stem.lower():
                return str(c)
        return str(candidates[0])

    return None


def _has_discord_import(filepath: Path) -> bool:
    """Check if a Python file imports discord."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        return bool(
            re.search(r"^\s*(import\s+discord|from\s+discord)", content, re.MULTILINE)
        )
    except OSError:
        return False


def _find_env_file(bot_dir: Path) -> Optional[str]:
    """Find .env file in bot directory or config/ subdirectory."""
    for candidate in [
        bot_dir / ".env",
        bot_dir / "config" / ".env",
        bot_dir / "config.env",
    ]:
        if candidate.is_file():
            return str(candidate)
    return None


def _find_lock_file(bot_dir: Path, bot_key: str) -> Optional[str]:
    """Find or determine the lock file path for PID tracking."""
    # Check for existing lock files
    expected = bot_dir / f"{bot_key}_bot.lock"
    if expected.exists():
        return str(expected)

    # Check for any .lock file
    for lock in bot_dir.glob("*.lock"):
        return str(lock)

    # Return the expected path even if it doesn't exist yet
    return str(expected)


def _find_log_file(bot_dir: Path) -> Optional[str]:
    """Find the log file for the bot."""
    # Check logs/ subdirectory
    logs_dir = bot_dir / "logs"
    if logs_dir.is_dir():
        for log_file in sorted(logs_dir.glob("*.log"), key=os.path.getmtime, reverse=True):
            return str(log_file)

    # Check root directory
    for log_file in sorted(bot_dir.glob("*.log"), key=os.path.getmtime, reverse=True):
        return str(log_file)

    # Return expected path
    logs_dir.mkdir(exist_ok=True)
    return str(logs_dir / "bot_logs.log")


class BotScanner:
    """Scans directories to discover Discord bots."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if self.config_path.is_file():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load config: %s", e)
        return {
            "bot_directories": [],
            "registered_bots": [],
            "settings": {
                "auto_restart": False,
                "restart_interval_hours": 24,
                "start_minimized": False,
                "theme": "dark",
            },
        }

    def save_config(self):
        """Persist current config to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.config, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def scan_all(self) -> list[dict]:
        """Scan all registered directories and return discovered bots."""
        discovered = []
        seen_dirs = set()

        # Include manually registered bots
        for bot in self.config.get("registered_bots", []):
            bot_dir = Path(bot.get("directory", ""))
            if bot_dir.is_dir() and str(bot_dir) not in seen_dirs:
                seen_dirs.add(str(bot_dir))
                info = discover_bot_info(bot_dir)
                if info:
                    # Preserve manual overrides
                    info["color"] = bot.get("color", info["color"])
                    discovered.append(info)

        # Scan registered directories
        for directory in self.config.get("bot_directories", []):
            dir_path = Path(directory)
            if not dir_path.is_dir():
                logger.warning("Directory not found: %s", directory)
                continue

            # First, scan subdirectories for bots
            found_in_subdirs = False
            for entry in sorted(dir_path.iterdir()):
                if not entry.is_dir():
                    continue
                # Skip common non-bot directories
                if entry.name.startswith(".") or entry.name in _SKIP_DIRS:
                    continue
                if str(entry) not in seen_dirs:
                    info = discover_bot_info(entry)
                    if info:
                        seen_dirs.add(str(entry))
                        discovered.append(info)
                        found_in_subdirs = True

            # If no bots found in subdirs, check if the directory itself is a bot
            if not found_in_subdirs and str(dir_path) not in seen_dirs:
                info = discover_bot_info(dir_path)
                if info:
                    seen_dirs.add(str(dir_path))
                    discovered.append(info)

        logger.info("Discovered %d bot(s)", len(discovered))
        return discovered

    def add_directory(self, directory: str) -> int:
        """Register a directory for scanning. Returns number of bots found."""
        directory = str(Path(directory).resolve())
        if directory not in self.config["bot_directories"]:
            self.config["bot_directories"].append(directory)
            self.save_config()

        # Quick scan to report count
        count = 0
        dir_path = Path(directory)
        if dir_path.is_dir():
            # Check if directory itself is a bot
            if discover_bot_info(dir_path):
                return 1
            # Scan subdirectories
            for entry in dir_path.iterdir():
                if entry.is_dir() and not entry.name.startswith(".") and entry.name not in _SKIP_DIRS:
                    if discover_bot_info(entry):
                        count += 1
        return count

    def add_bot_manually(self, script_path: str, name: str = "", color: str = "#7289da") -> Optional[dict]:
        """Register a single bot by its script path."""
        script = Path(script_path).resolve()
        if not script.is_file():
            return None

        bot_dir = script.parent
        bot_name = name or bot_dir.name.replace("Bot_", "")

        info = {
            "name": bot_name,
            "directory": str(bot_dir),
            "script": str(script),
            "env_file": _find_env_file(bot_dir),
            "lock_file": _find_lock_file(bot_dir, bot_name.lower()),
            "log_file": _find_log_file(bot_dir),
            "color": color,
        }

        # Add to registered bots if not already there
        existing = [b for b in self.config["registered_bots"] if b.get("directory") == str(bot_dir)]
        if not existing:
            self.config["registered_bots"].append(info)
            self.save_config()

        return info

    def remove_directory(self, directory: str):
        """Unregister a directory."""
        directory = str(Path(directory).resolve())
        if directory in self.config["bot_directories"]:
            self.config["bot_directories"].remove(directory)
            self.save_config()

    def remove_bot(self, bot_directory: str):
        """Remove a manually registered bot."""
        self.config["registered_bots"] = [
            b for b in self.config["registered_bots"]
            if b.get("directory") != bot_directory
        ]
        self.save_config()
