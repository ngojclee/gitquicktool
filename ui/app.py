"""
ui/app.py — Main application window using customtkinter.
Dark theme, tabbed interface: Dashboard | Settings.
"""

import os
import sys
from pathlib import Path

import customtkinter as ctk
from ui.dashboard_tab import DashboardTab
from ui.settings_tab import SettingsTab
from core.config import load_config, save_config, get_default_download_path


class App(ctk.CTk):
    """Main application window."""

    APP_TITLE = "GitQuickTool"
    APP_VERSION = "0.1.0.0"
    WINDOW_WIDTH = 960
    WINDOW_HEIGHT = 680

    def __init__(self):
        super().__init__()

        # ── Window Setup ─────────────────────────────────────
        self.title(f"{self.APP_TITLE} v{self.APP_VERSION}")
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.minsize(800, 550)

        # Icon
        icon_path = self._get_icon_path()
        if icon_path:
            self.iconbitmap(icon_path)

        # Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Cleanup previous update files
        try:
            from core.updater import cleanup_update
            cleanup_update()
        except Exception:
            pass

        # ── State ────────────────────────────────────────────
        self.config_data = load_config()
        self.supabase_client = None  # SupabaseSync instance
        self.tokens = []             # List of token dicts from Supabase
        self.items = []              # List of item dicts from Supabase

        # Set default download path if empty
        if not self.config_data.get("download_path"):
            self.config_data["download_path"] = get_default_download_path()

        # ── Layout ───────────────────────────────────────────
        self._build_ui()

        # ── Protocol ─────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        """Build the main UI layout."""
        # Top bar
        top = ctk.CTkFrame(self, height=40, corner_radius=0)
        top.pack(fill="x", padx=0, pady=0)
        top.pack_propagate(False)

        title_label = ctk.CTkLabel(
            top, text=f"  {self.APP_TITLE}",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        title_label.pack(side="left", padx=10, pady=5)

        version_label = ctk.CTkLabel(
            top, text=f"v{self.APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        version_label.pack(side="left", padx=0, pady=5)

        # Status label (right side of top bar)
        self.status_label = ctk.CTkLabel(
            top, text="",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self.status_label.pack(side="right", padx=15, pady=5)

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.tabview.add("Dashboard")
        self.tabview.add("Settings")

        # Build tabs
        self.dashboard_tab = DashboardTab(
            self.tabview.tab("Dashboard"), self
        )
        self.settings_tab = SettingsTab(
            self.tabview.tab("Settings"), self
        )

    def set_status(self, text: str, color: str = "gray50"):
        """Update the status label in the top bar."""
        self.status_label.configure(text=text, text_color=color)

    def update_download_path(self, new_path: str, source: str = ""):
        """
        Centralized download path update — keeps Dashboard and Settings in sync.
        source: 'dashboard' or 'settings' to avoid infinite loop.
        """
        self.config_data["download_path"] = new_path
        self.save_app_config()

        # Sync the other tab's path entry
        if source != "dashboard" and hasattr(self, 'dashboard_tab'):
            try:
                self.dashboard_tab.path_entry.delete(0, "end")
                self.dashboard_tab.path_entry.insert(0, new_path)
            except Exception:
                pass
        if source != "settings" and hasattr(self, 'settings_tab'):
            try:
                self.settings_tab.path_entry.delete(0, "end")
                self.settings_tab.path_entry.insert(0, new_path)
            except Exception:
                pass

    def save_app_config(self):
        """Save current config to disk."""
        save_config(self.config_data)

    def _get_icon_path(self) -> str | None:
        """Find icon.ico — works for both dev and frozen (PyInstaller) mode."""
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
        else:
            base = Path(__file__).parent.parent

        ico = base / "assets" / "icon.ico"
        if ico.exists():
            return str(ico)
        return None

    def _on_close(self):
        """Handle window close."""
        self.save_app_config()
        self.destroy()


def run_gui():
    """Entry point for GUI mode."""
    app = App()
    app.mainloop()
