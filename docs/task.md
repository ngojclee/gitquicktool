# GitQuickTool — Task Tracker

## Phase 1: Core Engine ✅
- [x] `core/config.py` — Local config, machine ID, paths
- [x] `core/vault.py` — AES-256 encryption for local secrets
- [x] `core/github_api.py` — Clone, pull, releases, smart asset matching
- [x] `core/supabase_sync.py` — CRUD for items, tokens, settings (LuxeClaw_ prefix)
- [x] `core/mingit.py` — Auto-download MinGit if git not installed

## Phase 2: GUI ✅
- [x] `ui/app.py` — Main window, dark theme, tabs, centralized path sync
- [x] `ui/dashboard_tab.py` — Item cards, download path, add/delete/sync
- [x] `ui/settings_tab.py` — Supabase config, token manager, cloud sync, MinGit install
- [x] Add New dialog with auto-name from URL
- [x] Token dropdown per item
- [x] Status detection (cloned / not cloned / downloaded)
- [x] Download path sync between Dashboard ↔ Settings

## Phase 3: CLI ✅
- [x] `cli/commands.py` — config, list, sync, tokens commands
- [x] `main.py` — auto-detect GUI/CLI mode

## Phase 4: Database ✅
- [x] `docs/sql/create_tables.sql` — Supabase schema with LuxeClaw_ prefix
- [x] RLS policies: authenticated + service_role

## Phase 5: Packaging ✅
- [x] PyInstaller build → `dist/GitQuickTool.exe` (83MB)
- [x] GitHub release v0.1.0.0 created (uploading exe)
- [x] Code pushed to https://github.com/ngojclee/gitquicktool

## Security ✅
- [x] No hardcoded credentials in source code
- [x] config.json / vault.json in .gitignore
- [x] All secrets entered at runtime by user
- [x] Safe to publish on GitHub

## Pending
- [ ] Test thực tế với repos + Supabase tables
- [ ] TUI mode (rich/textual)
- [ ] Linux build
- [ ] Repo visibility: consider making private if code should be hidden
