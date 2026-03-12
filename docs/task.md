# GitQuickTool — Task Tracker

## Phase 1: Core Engine ✅
- [x] `core/config.py` — Local config, machine ID, paths
- [x] `core/vault.py` — AES-256 encryption for local secrets
- [x] `core/github_api.py` — Clone, pull, releases, smart asset matching
- [x] `core/supabase_sync.py` — CRUD for items, tokens, settings

## Phase 2: GUI ✅
- [x] `ui/app.py` — Main window, dark theme, tabs
- [x] `ui/dashboard_tab.py` — Item cards, download path, add/delete/sync
- [x] `ui/settings_tab.py` — Supabase config, token manager, cloud sync
- [x] Add New dialog with auto-name from URL
- [x] Token dropdown per item
- [x] Status detection (cloned / not cloned / downloaded)

## Phase 3: CLI ✅
- [x] `cli/commands.py` — config, list, sync, tokens commands
- [x] `main.py` — auto-detect GUI/CLI mode

## Phase 4: Packaging
- [ ] PyInstaller config for Windows .exe
- [ ] PyInstaller config for Linux binary
- [ ] GitHub release

## Pending
- [ ] Supabase tables creation (need user's Supabase project)
- [ ] TUI mode (rich/textual for terminal GUI)
- [ ] First real test with user's repos
