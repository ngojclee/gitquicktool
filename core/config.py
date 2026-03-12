"""
core/config.py — Local configuration management.
Handles config.json for Supabase credentials, download path, machine ID.
"""

import json
import os
import platform
import uuid
from pathlib import Path


def get_app_dir() -> Path:
    """Return the app directory (same folder as the executable/script)."""
    # When frozen (PyInstaller), use exe directory
    if getattr(os.sys, 'frozen', False):
        return Path(os.sys.executable).parent
    return Path(__file__).resolve().parent.parent


def get_machine_id() -> str:
    """Generate a stable machine identifier."""
    node = uuid.getnode()
    hostname = platform.node()
    return f"{hostname}-{node:012x}"


CONFIG_FILE = get_app_dir() / "config.json"

DEFAULT_CONFIG = {
    "supabase_url": "",
    "supabase_token": "",      # encrypted locally via vault
    "download_path": "",
    "machine_id": get_machine_id(),
    "first_run": True,
}


def load_config() -> dict:
    """Load config from disk. Returns defaults if file missing."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults for any new keys
            merged = {**DEFAULT_CONFIG, **data}
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    """Save config to disk."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_default_download_path() -> str:
    """Return a sensible default download path for the current OS."""
    if platform.system() == "Windows":
        return str(Path.home() / "GitQuickTool")
    return str(Path.home() / "gitquicktool")
