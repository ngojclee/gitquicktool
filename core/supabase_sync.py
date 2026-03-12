"""
core/supabase_sync.py — Supabase CRUD for items, tokens, and settings.
"""

from typing import Optional
from supabase import create_client, Client


class SupabaseSync:
    """Manages sync between local state and Supabase."""

    TABLE_ITEMS = "LuxeClaw_gitquicktool_items"
    TABLE_TOKENS = "LuxeClaw_gitquicktool_tokens"
    TABLE_SETTINGS = "LuxeClaw_gitquicktool_settings"

    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    # ── Connection Test ──────────────────────────────────────

    def test_connection(self) -> tuple[bool, str]:
        """Test Supabase connection. Returns (success, message)."""
        try:
            result = self.client.table(self.TABLE_SETTINGS).select("id").limit(1).execute()
            return True, "Connected"
        except Exception as e:
            return False, str(e)

    # ── Items CRUD ───────────────────────────────────────────

    def get_items(self) -> list[dict]:
        """Fetch all items from Supabase."""
        try:
            result = self.client.table(self.TABLE_ITEMS) \
                .select("*") \
                .order("sort_order") \
                .execute()
            return result.data or []
        except Exception:
            return []

    def upsert_item(self, item: dict) -> Optional[dict]:
        """Insert or update a single item."""
        try:
            result = self.client.table(self.TABLE_ITEMS) \
                .upsert(item, on_conflict="id") \
                .execute()
            return result.data[0] if result.data else None
        except Exception:
            return None

    def upsert_items(self, items: list[dict]) -> list[dict]:
        """Bulk upsert items."""
        try:
            result = self.client.table(self.TABLE_ITEMS) \
                .upsert(items, on_conflict="id") \
                .execute()
            return result.data or []
        except Exception:
            return []

    def delete_item(self, item_id: str) -> bool:
        """Delete item by ID."""
        try:
            self.client.table(self.TABLE_ITEMS) \
                .delete() \
                .eq("id", item_id) \
                .execute()
            return True
        except Exception:
            return False

    # ── Tokens CRUD ──────────────────────────────────────────

    def get_tokens(self) -> list[dict]:
        """Fetch all GitHub tokens."""
        try:
            result = self.client.table(self.TABLE_TOKENS) \
                .select("*") \
                .order("created_at") \
                .execute()
            return result.data or []
        except Exception:
            return []

    def upsert_token(self, token_data: dict) -> Optional[dict]:
        """Insert or update a single token."""
        try:
            result = self.client.table(self.TABLE_TOKENS) \
                .upsert(token_data, on_conflict="id") \
                .execute()
            return result.data[0] if result.data else None
        except Exception:
            return None

    def delete_token(self, token_id: str) -> bool:
        """Delete token by ID."""
        try:
            self.client.table(self.TABLE_TOKENS) \
                .delete() \
                .eq("id", token_id) \
                .execute()
            return True
        except Exception:
            return False

    # ── Settings CRUD ────────────────────────────────────────

    def get_settings(self) -> dict:
        """Fetch all settings as key-value dict."""
        try:
            result = self.client.table(self.TABLE_SETTINGS) \
                .select("*") \
                .execute()
            return {row["key"]: row["value"] for row in (result.data or [])}
        except Exception:
            return {}

    def set_setting(self, key: str, value: str) -> bool:
        """Set a single setting."""
        try:
            self.client.table(self.TABLE_SETTINGS) \
                .upsert({"key": key, "value": value}, on_conflict="key") \
                .execute()
            return True
        except Exception:
            return False

    # ── Full Sync ────────────────────────────────────────────

    def sync_down(self) -> dict:
        """Pull all data from Supabase."""
        return {
            "items": self.get_items(),
            "tokens": self.get_tokens(),
            "settings": self.get_settings(),
        }

    def sync_up(self, items: list[dict], tokens: list[dict]) -> bool:
        """Push items and tokens to Supabase."""
        try:
            if items:
                self.upsert_items(items)
            if tokens:
                for t in tokens:
                    self.upsert_token(t)
            return True
        except Exception:
            return False
