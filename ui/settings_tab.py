"""
ui/settings_tab.py — Settings tab: Supabase connection, Token Manager, Download Path, Sync.
"""

import threading
import uuid
import customtkinter as ctk
from tkinter import filedialog, messagebox


class SettingsTab:
    """Settings tab with Supabase config, Token Manager, and Sync."""

    def __init__(self, parent: ctk.CTkFrame, app):
        self.parent = parent
        self.app = app
        self._build()

    def _build(self):
        # Scrollable container
        scroll = ctk.CTkScrollableFrame(self.parent, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Supabase Connection ──────────────────────────────
        sec1 = self._section(scroll, "Supabase Connection")

        row1 = ctk.CTkFrame(sec1, fg_color="transparent")
        row1.pack(fill="x", pady=2)
        ctk.CTkLabel(row1, text="URL:", width=60, anchor="w").pack(side="left")
        self.url_entry = ctk.CTkEntry(row1, placeholder_text="https://xxx.supabase.co")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))

        row2 = ctk.CTkFrame(sec1, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        ctk.CTkLabel(row2, text="Token:", width=60, anchor="w").pack(side="left")
        self.token_entry = ctk.CTkEntry(row2, placeholder_text="eyJhbGci...", show="*")
        self.token_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))

        btn_row = ctk.CTkFrame(sec1, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8, 0))
        self.test_btn = ctk.CTkButton(
            btn_row, text="Test Connection", width=140,
            command=self._test_connection,
        )
        self.test_btn.pack(side="left")
        self.test_status = ctk.CTkLabel(btn_row, text="", font=ctk.CTkFont(size=12))
        self.test_status.pack(side="left", padx=10)

        save_btn = ctk.CTkButton(
            btn_row, text="Save & Connect", width=140,
            fg_color="#2d8659", hover_color="#236b47",
            command=self._save_supabase,
        )
        save_btn.pack(side="right")

        # ── Token Manager ────────────────────────────────────
        sec2 = self._section(scroll, "GitHub Token Manager")

        self.tokens_frame = ctk.CTkFrame(sec2, fg_color="transparent")
        self.tokens_frame.pack(fill="x", pady=2)

        add_row = ctk.CTkFrame(sec2, fg_color="transparent")
        add_row.pack(fill="x", pady=(8, 0))
        self.new_label_entry = ctk.CTkEntry(add_row, placeholder_text="Label (e.g., Main PAT)", width=180)
        self.new_label_entry.pack(side="left")
        self.new_token_entry = ctk.CTkEntry(add_row, placeholder_text="ghp_xxxx...", show="*", width=280)
        self.new_token_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        ctk.CTkButton(
            add_row, text="+ Add", width=70,
            command=self._add_token,
        ).pack(side="left", padx=(5, 0))

        # ── Download Path ────────────────────────────────────
        sec3 = self._section(scroll, "Download Path")

        path_row = ctk.CTkFrame(sec3, fg_color="transparent")
        path_row.pack(fill="x", pady=2)
        self.path_entry = ctk.CTkEntry(path_row, placeholder_text="D:\\Tools\\")
        self.path_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            path_row, text="Browse", width=80,
            command=self._browse_path,
        ).pack(side="left", padx=(5, 0))

        # ── Sync ─────────────────────────────────────────────
        sec4 = self._section(scroll, "Cloud Sync")

        sync_row = ctk.CTkFrame(sec4, fg_color="transparent")
        sync_row.pack(fill="x", pady=2)
        ctk.CTkButton(
            sync_row, text="↑  Sync to Cloud", width=160,
            command=self._sync_up,
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            sync_row, text="↓  Sync from Cloud", width=160,
            command=self._sync_down,
        ).pack(side="left")
        self.sync_status = ctk.CTkLabel(sync_row, text="", font=ctk.CTkFont(size=12))
        self.sync_status.pack(side="left", padx=15)

        # ── Machine Info ─────────────────────────────────────
        sec5 = self._section(scroll, "Machine Info")
        ctk.CTkLabel(
            sec5, text=f"Machine ID: {self.app.config_data.get('machine_id', 'N/A')}",
            font=ctk.CTkFont(size=12), text_color="gray60",
        ).pack(anchor="w")

        # ── Load values ──────────────────────────────────────
        self._load_values()

    def _section(self, parent, title: str) -> ctk.CTkFrame:
        """Create a labeled section frame."""
        lbl = ctk.CTkLabel(
            parent, text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl.pack(anchor="w", padx=5, pady=(15, 5))

        frame = ctk.CTkFrame(parent, corner_radius=8)
        frame.pack(fill="x", padx=5, pady=(0, 5))
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        return inner

    def _load_values(self):
        """Populate fields from config."""
        cfg = self.app.config_data
        if cfg.get("supabase_url"):
            self.url_entry.insert(0, cfg["supabase_url"])
        if cfg.get("supabase_token"):
            self.token_entry.insert(0, cfg["supabase_token"])
        if cfg.get("download_path"):
            self.path_entry.insert(0, cfg["download_path"])

        self._refresh_token_list()

    def _refresh_token_list(self):
        """Redraw the token list."""
        for w in self.tokens_frame.winfo_children():
            w.destroy()

        if not self.app.tokens:
            ctk.CTkLabel(
                self.tokens_frame, text="No tokens configured yet.",
                text_color="gray50",
            ).pack(anchor="w")
            return

        for token_data in self.app.tokens:
            row = ctk.CTkFrame(self.tokens_frame, corner_radius=6, height=36)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            label = token_data.get("label", "Unnamed")
            value = token_data.get("token", "")
            masked = value[:4] + "•" * 12 + value[-4:] if len(value) > 8 else "•" * 16

            ctk.CTkLabel(row, text=label, font=ctk.CTkFont(weight="bold"), width=140).pack(
                side="left", padx=(10, 5), pady=4,
            )
            ctk.CTkLabel(row, text=masked, text_color="gray50", font=ctk.CTkFont(size=12)).pack(
                side="left", padx=5, pady=4,
            )
            del_btn = ctk.CTkButton(
                row, text="🗑", width=30, height=24,
                fg_color="transparent", hover_color="#8B0000",
                command=lambda tid=token_data.get("id"): self._delete_token(tid),
            )
            del_btn.pack(side="right", padx=5, pady=4)

    # ── Actions ──────────────────────────────────────────────

    def _test_connection(self):
        """Test Supabase connection."""
        url = self.url_entry.get().strip()
        key = self.token_entry.get().strip()
        if not url or not key:
            self.test_status.configure(text="✗ Enter URL and token", text_color="#e74c3c")
            return

        self.test_status.configure(text="Testing...", text_color="gray50")
        self.test_btn.configure(state="disabled")

        def _test():
            try:
                from core.supabase_sync import SupabaseSync
                sync = SupabaseSync(url, key)
                ok, msg = sync.test_connection()
                self.parent.after(0, lambda: self._show_test_result(ok, msg, sync))
            except Exception as e:
                self.parent.after(0, lambda: self._show_test_result(False, str(e), None))

        threading.Thread(target=_test, daemon=True).start()

    def _show_test_result(self, ok: bool, msg: str, sync):
        self.test_btn.configure(state="normal")
        if ok:
            self.test_status.configure(text="✓ Connected", text_color="#2ecc71")
            self.app.supabase_client = sync
            self.app.set_status("Supabase connected", "#2ecc71")
        else:
            self.test_status.configure(text=f"✗ {msg[:50]}", text_color="#e74c3c")

    def _save_supabase(self):
        """Save Supabase credentials and connect."""
        url = self.url_entry.get().strip()
        key = self.token_entry.get().strip()
        path = self.path_entry.get().strip()

        self.app.config_data["supabase_url"] = url
        self.app.config_data["supabase_token"] = key
        if path:
            self.app.config_data["download_path"] = path
        self.app.config_data["first_run"] = False
        self.app.save_app_config()

        # Auto-connect and sync down
        self._test_connection()
        self.app.set_status("Saved", "#2ecc71")

    def _browse_path(self):
        """Open folder picker for download path."""
        folder = filedialog.askdirectory(title="Select Download Folder")
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            self.app.config_data["download_path"] = folder
            self.app.save_app_config()

    def _add_token(self):
        """Add a new GitHub token."""
        label = self.new_label_entry.get().strip()
        value = self.new_token_entry.get().strip()
        if not label or not value:
            messagebox.showwarning("Add Token", "Enter both label and token value.")
            return

        token_data = {
            "id": str(uuid.uuid4()),
            "label": label,
            "token": value,
        }
        self.app.tokens.append(token_data)

        # Sync to Supabase if connected
        if self.app.supabase_client:
            self.app.supabase_client.upsert_token(token_data)

        self.new_label_entry.delete(0, "end")
        self.new_token_entry.delete(0, "end")
        self._refresh_token_list()
        # Notify dashboard to refresh dropdowns
        self.app.dashboard_tab.refresh_items()

    def _delete_token(self, token_id: str):
        """Delete a token by ID."""
        if not messagebox.askyesno("Delete Token", "Remove this token?"):
            return

        self.app.tokens = [t for t in self.app.tokens if t.get("id") != token_id]
        if self.app.supabase_client:
            self.app.supabase_client.delete_token(token_id)
        self._refresh_token_list()
        self.app.dashboard_tab.refresh_items()

    def _sync_up(self):
        """Push all items and tokens to Supabase."""
        if not self.app.supabase_client:
            self.sync_status.configure(text="✗ Not connected", text_color="#e74c3c")
            return

        self.sync_status.configure(text="Syncing up...", text_color="gray50")

        def _do():
            try:
                ok = self.app.supabase_client.sync_up(self.app.items, self.app.tokens)
                msg = "✓ Synced to cloud" if ok else "✗ Sync failed"
                color = "#2ecc71" if ok else "#e74c3c"
                self.parent.after(0, lambda: self.sync_status.configure(text=msg, text_color=color))
            except Exception as e:
                self.parent.after(0, lambda: self.sync_status.configure(
                    text=f"✗ {str(e)[:40]}", text_color="#e74c3c"
                ))

        threading.Thread(target=_do, daemon=True).start()

    def _sync_down(self):
        """Pull all data from Supabase."""
        if not self.app.supabase_client:
            self.sync_status.configure(text="✗ Not connected", text_color="#e74c3c")
            return

        self.sync_status.configure(text="Syncing down...", text_color="gray50")

        def _do():
            try:
                data = self.app.supabase_client.sync_down()
                self.app.items = data.get("items", [])
                self.app.tokens = data.get("tokens", [])
                settings = data.get("settings", {})
                if settings.get("download_path"):
                    self.app.config_data["download_path"] = settings["download_path"]

                def _update_ui():
                    self._refresh_token_list()
                    self.app.dashboard_tab.refresh_items()
                    if settings.get("download_path"):
                        self.path_entry.delete(0, "end")
                        self.path_entry.insert(0, settings["download_path"])
                    self.sync_status.configure(text="✓ Synced from cloud", text_color="#2ecc71")
                    self.app.set_status(
                        f"Synced: {len(self.app.items)} items, {len(self.app.tokens)} tokens",
                        "#2ecc71"
                    )

                self.parent.after(0, _update_ui)
            except Exception as e:
                self.parent.after(0, lambda: self.sync_status.configure(
                    text=f"✗ {str(e)[:40]}", text_color="#e74c3c"
                ))

        threading.Thread(target=_do, daemon=True).start()
