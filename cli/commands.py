"""
cli/commands.py — CLI interface for GitQuickTool.
"""

import argparse
import json
import sys

from core.config import load_config, save_config, get_default_download_path


def run_cli():
    parser = argparse.ArgumentParser(
        prog="gitquicktool",
        description="GitQuickTool — Quick deploy repos & releases from GitHub",
    )
    sub = parser.add_subparsers(dest="command")

    # config
    cfg_parser = sub.add_parser("config", help="Configure Supabase connection")
    cfg_parser.add_argument("--url", help="Supabase URL")
    cfg_parser.add_argument("--token", help="Supabase anon/service token")
    cfg_parser.add_argument("--path", help="Download path")

    # list
    sub.add_parser("list", help="List configured items")

    # sync
    sub.add_parser("sync", help="Sync all enabled items")

    # tokens
    tok_parser = sub.add_parser("tokens", help="Manage GitHub tokens")
    tok_parser.add_argument("action", nargs="?", default="list",
                            choices=["list", "add", "remove"])

    args = parser.parse_args()

    if args.command == "config":
        _cmd_config(args)
    elif args.command == "list":
        _cmd_list()
    elif args.command == "sync":
        _cmd_sync()
    elif args.command == "tokens":
        _cmd_tokens(args)
    else:
        parser.print_help()


def _cmd_config(args):
    cfg = load_config()
    changed = False
    if args.url:
        cfg["supabase_url"] = args.url
        changed = True
    if args.token:
        cfg["supabase_token"] = args.token
        changed = True
    if args.path:
        cfg["download_path"] = args.path
        changed = True

    if changed:
        cfg["first_run"] = False
        save_config(cfg)
        print("Config saved.")
    else:
        print(f"Supabase URL:   {cfg.get('supabase_url', '(not set)')}")
        print(f"Download Path:  {cfg.get('download_path', '(not set)')}")
        print(f"Machine ID:     {cfg.get('machine_id', 'N/A')}")


def _cmd_list():
    cfg = load_config()
    if not cfg.get("supabase_url") or not cfg.get("supabase_token"):
        print("Not configured. Run: gitquicktool config --url <url> --token <token>")
        return

    from core.supabase_sync import SupabaseSync
    sync = SupabaseSync(cfg["supabase_url"], cfg["supabase_token"])
    items = sync.get_items()

    if not items:
        print("No items configured.")
        return

    for i, item in enumerate(items, 1):
        icon = "📦" if item.get("type") == "release" else "📂"
        name = item.get("name", "Unnamed")
        url = item.get("url", "")
        print(f"  {i}. {icon} {name}")
        print(f"     URL: {url}")
        if item.get("asset_pattern"):
            print(f"     Pattern: {item['asset_pattern']}")
        print()


def _cmd_sync():
    from pathlib import Path
    cfg = load_config()
    if not cfg.get("supabase_url") or not cfg.get("supabase_token"):
        print("Not configured. Run: gitquicktool config --url <url> --token <token>")
        return

    download_path = cfg.get("download_path") or get_default_download_path()

    from core.supabase_sync import SupabaseSync
    from core.github_api import clone_repo, download_release_by_pattern, parse_repo_url

    sync = SupabaseSync(cfg["supabase_url"], cfg["supabase_token"])
    data = sync.sync_down()
    items = data.get("items", [])
    tokens = data.get("tokens", [])

    enabled = [i for i in items if i.get("enabled", True)]
    print(f"Syncing {len(enabled)} items to {download_path}...\n")

    for item in enabled:
        name = item.get("name", "Unnamed")
        print(f"  → {name}...", end=" ", flush=True)

        token = None
        if item.get("token_id"):
            for t in tokens:
                if t.get("id") == item["token_id"]:
                    token = t.get("token")
                    break

        try:
            subfolder = item.get("subfolder") or name
            dest = Path(download_path) / subfolder

            if item.get("type") == "release":
                owner, repo = parse_repo_url(item.get("url", ""))
                result = download_release_by_pattern(
                    owner, repo, item.get("asset_pattern", ""), dest, token
                )
                print("✓ Downloaded" if result else "✗ No matching release")
            else:
                ok = clone_repo(item.get("url", ""), dest, token)
                print("✓ Done" if ok else "✗ Failed")
        except Exception as e:
            print(f"✗ Error: {e}")

    print("\nSync complete.")


def _cmd_tokens(args):
    cfg = load_config()
    if not cfg.get("supabase_url") or not cfg.get("supabase_token"):
        print("Not configured.")
        return

    from core.supabase_sync import SupabaseSync
    sync = SupabaseSync(cfg["supabase_url"], cfg["supabase_token"])

    if args.action == "list":
        tokens = sync.get_tokens()
        if not tokens:
            print("No tokens configured.")
            return
        for t in tokens:
            val = t.get("token", "")
            masked = val[:4] + "•" * 8 + val[-4:] if len(val) > 8 else "•" * 16
            print(f"  {t.get('label', 'Unnamed'):20s}  {masked}")

    elif args.action == "add":
        import uuid
        label = input("Label: ").strip()
        token = input("Token: ").strip()
        if label and token:
            sync.upsert_token({"id": str(uuid.uuid4()), "label": label, "token": token})
            print(f"Token '{label}' added.")
        else:
            print("Cancelled.")

    elif args.action == "remove":
        tokens = sync.get_tokens()
        for i, t in enumerate(tokens, 1):
            print(f"  {i}. {t.get('label', 'Unnamed')}")
        choice = input("Delete # (0 to cancel): ").strip()
        if choice.isdigit() and 0 < int(choice) <= len(tokens):
            t = tokens[int(choice) - 1]
            sync.delete_token(t["id"])
            print(f"Deleted '{t.get('label')}'.")
