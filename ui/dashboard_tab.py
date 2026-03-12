"""
ui/dashboard_tab.py — Dashboard tab: download path, item cards, add/delete/sync.
"""

import threading
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.github_api import (
    parse_repo_url, get_repo_name, clone_repo,
    download_release_by_pattern, delete_local,
)


class ItemCard(ctk.CTkFrame):
    """A single item card in the dashboard."""

    def __init__(self, parent, item: dict, app, on_delete, on_refresh):
        super().__init__(parent, corner_radius=8)
        self.item = item
        self.app = app
        self.on_delete = on_delete
        self.on_refresh = on_refresh
        self._build()

    def _build(self):
        self.configure(border_width=1, border_color="gray30")

        # Main content frame with padding
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=12, pady=8)

        # ── Row 1: Type icon + Name + Action button ──────────
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x")

        is_release = self.item.get("type") == "release"
        icon = "📦" if is_release else "📂"
        action_text = "Download" if is_release else "Clone"

        ctk.CTkLabel(
            row1, text=f"{icon}  {self.item.get('name', 'Unnamed')}",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        # Action button
        self.action_btn = ctk.CTkButton(
            row1, text=f"{action_text}  ▶", width=110, height=30,
            command=self._do_action,
        )
        self.action_btn.pack(side="right")

        # ── Row 2: URL / Pattern ─────────────────────────────
        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill="x", pady=(4, 0))

        url_text = self.item.get("url", "")
        if is_release and self.item.get("asset_pattern"):
            try:
                owner, repo = parse_repo_url(url_text)
                url_text = f"{owner}/{repo}  →  {self.item['asset_pattern']}"
            except ValueError:
                pass

        ctk.CTkLabel(
            row2, text=url_text,
            font=ctk.CTkFont(size=12),
            text_color="gray55",
        ).pack(side="left")

        # ── Row 3: Token dropdown + Status + Delete ──────────
        row3 = ctk.CTkFrame(content, fg_color="transparent")
        row3.pack(fill="x", pady=(6, 0))

        # Token dropdown
        ctk.CTkLabel(row3, text="Token:", font=ctk.CTkFont(size=12)).pack(side="left")
        token_options = ["None (Public)"] + [
            t.get("label", "Unnamed") for t in self.app.tokens
        ]
        current_token_label = "None (Public)"
        if self.item.get("token_id"):
            for t in self.app.tokens:
                if t.get("id") == self.item["token_id"]:
                    current_token_label = t.get("label", "Unnamed")
                    break

        self.token_dropdown = ctk.CTkOptionMenu(
            row3, values=token_options, width=160, height=26,
            command=self._on_token_change,
            font=ctk.CTkFont(size=12),
        )
        self.token_dropdown.set(current_token_label)
        self.token_dropdown.pack(side="left", padx=(5, 15))

        # Status
        self.status_label = ctk.CTkLabel(
            row3, text=self._get_status_text(),
            font=ctk.CTkFont(size=12),
            text_color=self._get_status_color(),
        )
        self.status_label.pack(side="left")

        # Delete button
        ctk.CTkButton(
            row3, text="🗑  Del", width=60, height=26,
            fg_color="transparent", hover_color="#8B0000",
            border_width=1, border_color="gray40",
            font=ctk.CTkFont(size=12),
            command=self._delete,
        ).pack(side="right")

    def _get_status_text(self) -> str:
        """Determine item status."""
        download_path = self.app.config_data.get("download_path", "")
        if not download_path:
            return "⚠ No path set"

        dest = Path(download_path) / self.item.get("subfolder", self.item.get("name", ""))
        if self.item.get("type") == "release":
            # For releases, check if any matching file exists
            if dest.is_dir() and any(dest.iterdir()):
                return "✅ Downloaded"
            return "⬇  Not downloaded"
        else:
            if (dest / ".git").exists():
                return "✅ Cloned"
            return "⬇  Not cloned"

    def _get_status_color(self) -> str:
        text = self._get_status_text()
        if "✅" in text:
            return "#2ecc71"
        elif "⬇" in text:
            return "#f39c12"
        return "#e74c3c"

    def _get_selected_token(self) -> str | None:
        """Get the actual token value from the selected dropdown item."""
        selected = self.token_dropdown.get()
        if selected == "None (Public)":
            return None
        for t in self.app.tokens:
            if t.get("label") == selected:
                return t.get("token")
        return None

    def _on_token_change(self, selected: str):
        """Update item's token_id when dropdown changes."""
        if selected == "None (Public)":
            self.item["token_id"] = None
        else:
            for t in self.app.tokens:
                if t.get("label") == selected:
                    self.item["token_id"] = t.get("id")
                    break

    def _do_action(self):
        """Clone repo or download release in background thread."""
        download_path = self.app.config_data.get("download_path", "")
        if not download_path:
            messagebox.showwarning("No Path", "Set a download path in Settings first.")
            return

        token = self._get_selected_token()
        self.action_btn.configure(state="disabled", text="Working...")
        self.app.set_status(f"Processing {self.item.get('name')}...", "gray50")

        def _work():
            try:
                if self.item.get("type") == "release":
                    result = self._download_release(download_path, token)
                else:
                    result = self._clone_repo(download_path, token)

                def _done():
                    self.action_btn.configure(state="normal",
                        text="Download  ▶" if self.item.get("type") == "release" else "Clone  ▶")
                    self.status_label.configure(
                        text=self._get_status_text(),
                        text_color=self._get_status_color(),
                    )
                    if result:
                        self.app.set_status(f"✓ {self.item.get('name')} done", "#2ecc71")
                    else:
                        self.app.set_status(f"✗ {self.item.get('name')} failed", "#e74c3c")

                self.after(0, _done)
            except Exception as e:
                def _err():
                    self.action_btn.configure(state="normal",
                        text="Download  ▶" if self.item.get("type") == "release" else "Clone  ▶")
                    self.app.set_status(f"✗ Error: {str(e)[:50]}", "#e74c3c")
                self.after(0, _err)

        threading.Thread(target=_work, daemon=True).start()

    def _clone_repo(self, download_path: str, token: str | None) -> bool:
        url = self.item.get("url", "")
        subfolder = self.item.get("subfolder") or self.item.get("name", "repo")
        dest = Path(download_path) / subfolder
        return clone_repo(url, dest, token)

    def _download_release(self, download_path: str, token: str | None) -> bool:
        url = self.item.get("url", "")
        pattern = self.item.get("asset_pattern", "")
        subfolder = self.item.get("subfolder") or self.item.get("name", "release")
        dest_dir = Path(download_path) / subfolder

        try:
            owner, repo = parse_repo_url(url)
        except ValueError:
            return False

        result = download_release_by_pattern(owner, repo, pattern, dest_dir, token)
        return result is not None

    def _delete(self):
        """Delete this item + local files."""
        name = self.item.get("name", "this item")
        if not messagebox.askyesno("Delete Item", f"Delete '{name}' and its local files?"):
            return

        # Delete local files
        download_path = self.app.config_data.get("download_path", "")
        if download_path:
            subfolder = self.item.get("subfolder") or self.item.get("name", "")
            local_path = Path(download_path) / subfolder
            delete_local(local_path)

        # Delete from Supabase
        if self.app.supabase_client and self.item.get("id"):
            self.app.supabase_client.delete_item(self.item["id"])

        # Remove from app state
        self.app.items = [i for i in self.app.items if i.get("id") != self.item.get("id")]
        self.on_delete()


class DashboardTab:
    """Dashboard tab with download path, item cards, and bulk actions."""

    def __init__(self, parent: ctk.CTkFrame, app):
        self.parent = parent
        self.app = app
        self._build()

    def _build(self):
        # ── Download Path Row ────────────────────────────────
        path_frame = ctk.CTkFrame(self.parent, corner_radius=8)
        path_frame.pack(fill="x", padx=5, pady=(5, 5))

        inner_path = ctk.CTkFrame(path_frame, fg_color="transparent")
        inner_path.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            inner_path, text="Download Path:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        self.path_entry = ctk.CTkEntry(inner_path, width=400)
        self.path_entry.pack(side="left", padx=(10, 5), fill="x", expand=True)
        if self.app.config_data.get("download_path"):
            self.path_entry.insert(0, self.app.config_data["download_path"])

        ctk.CTkButton(
            inner_path, text="Browse", width=75,
            command=self._browse_path,
        ).pack(side="left")

        # ── Items Scroll Area ────────────────────────────────
        self.items_scroll = ctk.CTkScrollableFrame(self.parent, corner_radius=0)
        self.items_scroll.pack(fill="both", expand=True, padx=5, pady=0)

        # Empty state
        self.empty_label = ctk.CTkLabel(
            self.items_scroll,
            text="No items yet. Click '+ Add New' to get started.",
            text_color="gray50",
            font=ctk.CTkFont(size=14),
        )

        # ── Bottom Buttons ───────────────────────────────────
        bottom = ctk.CTkFrame(self.parent, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=8)

        ctk.CTkButton(
            bottom, text="+  Add New", width=120,
            command=self._add_new,
        ).pack(side="left")

        ctk.CTkButton(
            bottom, text="↻  Sync All", width=120,
            fg_color="#2d8659", hover_color="#236b47",
            command=self._sync_all,
        ).pack(side="right")

        # Initial render
        self.refresh_items()

    def refresh_items(self):
        """Redraw all item cards."""
        for w in self.items_scroll.winfo_children():
            w.destroy()

        if not self.app.items:
            self.empty_label = ctk.CTkLabel(
                self.items_scroll,
                text="No items yet. Click '+ Add New' to get started.",
                text_color="gray50",
                font=ctk.CTkFont(size=14),
            )
            self.empty_label.pack(pady=40)
            return

        for item in self.app.items:
            card = ItemCard(
                self.items_scroll, item, self.app,
                on_delete=self.refresh_items,
                on_refresh=self.refresh_items,
            )
            card.pack(fill="x", pady=4)

    def _browse_path(self):
        folder = filedialog.askdirectory(title="Select Download Folder")
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            self.app.config_data["download_path"] = folder
            self.app.save_app_config()

    def _add_new(self):
        """Dialog to add a new item."""
        dialog = AddItemDialog(self.parent, self.app)
        self.parent.wait_window(dialog)
        if dialog.result:
            self.app.items.append(dialog.result)
            if self.app.supabase_client:
                self.app.supabase_client.upsert_item(dialog.result)
            self.refresh_items()

    def _sync_all(self):
        """Clone/download all enabled items."""
        download_path = self.app.config_data.get("download_path", "")
        if not download_path:
            messagebox.showwarning("No Path", "Set a download path first.")
            return

        enabled = [i for i in self.app.items if i.get("enabled", True)]
        if not enabled:
            self.app.set_status("Nothing to sync", "gray50")
            return

        self.app.set_status(f"Syncing {len(enabled)} items...", "gray50")

        def _work():
            done = 0
            for item in enabled:
                try:
                    token = None
                    if item.get("token_id"):
                        for t in self.app.tokens:
                            if t.get("id") == item["token_id"]:
                                token = t.get("token")
                                break

                    subfolder = item.get("subfolder") or item.get("name", "")
                    dest = Path(download_path) / subfolder

                    if item.get("type") == "release":
                        owner, repo = parse_repo_url(item.get("url", ""))
                        download_release_by_pattern(
                            owner, repo, item.get("asset_pattern", ""),
                            dest, token
                        )
                    else:
                        clone_repo(item.get("url", ""), dest, token)
                    done += 1
                except Exception:
                    pass

            def _done():
                self.app.set_status(f"✓ Synced {done}/{len(enabled)} items", "#2ecc71")
                self.refresh_items()

            self.parent.after(0, _done)

        threading.Thread(target=_work, daemon=True).start()


class AddItemDialog(ctk.CTkToplevel):
    """Dialog for adding a new repo or release item."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.result = None

        self.title("Add New Item")
        self.geometry("520x380")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._build()

    def _build(self):
        pad = {"padx": 15, "pady": (8, 0)}

        # Type selection
        ctk.CTkLabel(self, text="Type:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", **pad)
        self.type_var = ctk.StringVar(value="repo")
        type_frame = ctk.CTkFrame(self, fg_color="transparent")
        type_frame.pack(anchor="w", padx=15, pady=2)
        ctk.CTkRadioButton(type_frame, text="📂  Repository (git clone)", variable=self.type_var,
                           value="repo", command=self._on_type_change).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(type_frame, text="📦  Release Asset (download)", variable=self.type_var,
                           value="release", command=self._on_type_change).pack(side="left")

        # URL
        ctk.CTkLabel(self, text="GitHub URL:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", **pad)
        self.url_entry = ctk.CTkEntry(self, placeholder_text="https://github.com/owner/repo")
        self.url_entry.pack(fill="x", padx=15, pady=2)
        self.url_entry.bind("<FocusOut>", self._auto_fill_name)
        self.url_entry.bind("<Return>", self._auto_fill_name)

        # Asset pattern container (release only — hidden by default)
        self.pattern_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.pattern_frame, text="Asset Pattern:", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=0, pady=(4, 0))
        self.pattern_entry = ctk.CTkEntry(self.pattern_frame, placeholder_text="luxeclaw-proxy-*.xpi")
        self.pattern_entry.pack(fill="x", pady=2)

        # Name
        ctk.CTkLabel(self, text="Name:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", **pad)
        self.name_entry = ctk.CTkEntry(self, placeholder_text="Auto-detected from URL")
        self.name_entry.pack(fill="x", padx=15, pady=2)

        # Description
        ctk.CTkLabel(self, text="Description (optional):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", **pad)
        self.desc_entry = ctk.CTkEntry(self, placeholder_text="Short description")
        self.desc_entry.pack(fill="x", padx=15, pady=2)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(20, 15))
        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            command=self.destroy,
        ).pack(side="left")
        ctk.CTkButton(
            btn_frame, text="Add Item", width=120,
            fg_color="#2d8659", hover_color="#236b47",
            command=self._submit,
        ).pack(side="right")

        self._on_type_change()

    def _on_type_change(self):
        """Show/hide pattern field based on type."""
        if self.type_var.get() == "release":
            self.pattern_frame.pack(fill="x", padx=15, pady=(4, 0), after=self.url_entry)
        else:
            self.pattern_frame.pack_forget()

    def _auto_fill_name(self, _event=None):
        """Auto-detect name from URL if name field is empty."""
        if self.name_entry.get().strip():
            return
        url = self.url_entry.get().strip()
        if url:
            try:
                name = get_repo_name(url)
                self.name_entry.delete(0, "end")
                self.name_entry.insert(0, name)
            except ValueError:
                pass

    def _submit(self):
        url = self.url_entry.get().strip()
        name = self.name_entry.get().strip()
        item_type = self.type_var.get()

        if not url:
            messagebox.showwarning("Missing URL", "Enter a GitHub URL.")
            return

        if not name:
            try:
                name = get_repo_name(url)
            except ValueError:
                messagebox.showwarning("Invalid URL", "Cannot parse the URL.")
                return

        self.result = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": self.desc_entry.get().strip(),
            "type": item_type,
            "url": url,
            "asset_pattern": self.pattern_entry.get().strip() if item_type == "release" else "",
            "token_id": None,
            "subfolder": name,
            "enabled": True,
            "sort_order": len(self.app.items),
        }
        self.destroy()
