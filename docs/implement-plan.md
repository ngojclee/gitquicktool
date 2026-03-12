# GitQuickTool — Kế Hoạch Triển Khai

> Công cụ đa nền tảng giúp triển khai nhanh script, repo, và release từ GitHub.
> Cấu hình đồng bộ qua Supabase — máy mới chỉ cần nhập URL + token là xong.

---

## Tổng Quan

**Vấn đề**: Mỗi lần setup máy mới phải clone repo, tải release, cấu hình token thủ công.

**Giải pháp**: App portable duy nhất — nhập Supabase creds → đồng bộ hết → bấm nút tải.

**Ngôn ngữ**: Python 3.10+
**GUI**: `customtkinter` (modern, dark theme, cross-platform)
**TUI**: `rich` / `textual` (giao diện terminal cho Linux headless, có thể thêm sau)
**CLI**: `argparse` (lệnh dòng, không cần GUI)
**UI**: Toàn bộ tiếng Anh
**Ưu tiên**: GUI + Windows trước

---

## Cấu Trúc Thư Mục

```
gitquicktool/
├── main.py                   # Entry point (auto-detect GUI/CLI/TUI)
├── pyproject.toml             # Version 0.1.0.0
├── requirements.txt
├── docs/
│   └── implement-plan.md
│
├── core/
│   ├── __init__.py
│   ├── config.py              # Local config, paths, constants
│   ├── github_api.py          # GitHub API: clone, pull, releases, download
│   ├── supabase_sync.py       # Supabase CRUD for items + tokens + settings
│   ├── vault.py               # AES-256 encrypt for local secrets
│   └── downloader.py          # Download engine with progress
│
├── ui/
│   ├── __init__.py
│   ├── app.py                 # Main window, tabs
│   ├── dashboard_tab.py       # Item cards + download path
│   └── settings_tab.py        # Supabase creds, token manager, preferences
│
├── cli/
│   ├── __init__.py
│   └── commands.py            # CLI commands: sync, pull, list, add, remove
│
├── tests/
│   ├── test_github_api.py
│   └── test_vault.py
│
└── assets/
    └── icon.png
```

---

## Supabase Schema

### Bảng: `quicktool_tokens`

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | uuid (PK) | Tự tạo |
| `label` | text | Tên hiển thị (vd: "Main GitHub PAT", "Company Token") |
| `token` | text | GitHub PAT |
| `created_at` | timestamptz | Tự tạo |
| `updated_at` | timestamptz | Tự tạo |

### Bảng: `quicktool_items`

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | uuid (PK) | Tự tạo |
| `name` | text | Tên hiển thị (tự lấy từ URL hoặc tự đặt) |
| `description` | text | Mô tả ngắn (tuỳ chọn) |
| `type` | text | `repo` hoặc `release` |
| `url` | text | GitHub repo URL |
| `asset_pattern` | text | Cho release: glob pattern (vd: `luxeclaw-proxy-*.xpi`) |
| `token_id` | uuid (FK) | Token nào dùng cho item này (nullable = public) |
| `subfolder` | text | Tên thư mục con (mặc định = tên repo) |
| `enabled` | bool | Có bao gồm khi Sync All |
| `sort_order` | int | Thứ tự hiển thị |
| `created_at` | timestamptz | Tự tạo |
| `updated_at` | timestamptz | Tự tạo |

### Bảng: `quicktool_settings`

| Cột | Kiểu | Mô tả |
|-----|------|-------|
| `id` | uuid (PK) | Tự tạo |
| `key` | text (unique) | Setting key (vd: "download_path") |
| `value` | text | Setting value |
| `updated_at` | timestamptz | Tự tạo |

---

## Multi-Token Management

- Tab **Settings** có phần **Token Manager**:
  - Danh sách token với Label + masked value
  - Nút [+ Add Token] → nhập label + token
  - Nút [Delete] từng token
  - Tất cả đồng bộ lên Supabase
- Trên **Dashboard**, mỗi item card có dropdown chọn token (hoặc "None — Public")
- Khi clone/download → dùng token được gán cho item đó

---

## Smart Release Detection

**Vấn đề**: Một repo (vd: `win-toolbox`) có releases cho nhiều app khác nhau:
```
luxeclaw-proxy-v1.1.0.0    → luxeclaw-proxy-1.1.0.0.xpi
container-inspector-v1.1.0  → container-inspector-1.1.0.3.xpi
```

**Giải pháp**: Dùng `asset_pattern` (glob) để match chính xác file cần tải:

1. Gọi API: `GET /repos/{owner}/{repo}/releases` (lấy tất cả releases)
2. Duyệt từng release → kiểm tra `assets[]` → match `asset_pattern`
3. Lấy release **mới nhất** có asset match → download asset đó
4. Bỏ qua releases của app khác (vì asset name không match pattern)

**Ví dụ**:
```
Item: LuxeClaw Proxy XPI
Repo: ngojclee/win-toolbox
Pattern: luxeclaw-proxy-*.xpi

→ Tìm thấy release "luxeclaw-proxy-v1.2.0.0" có asset "luxeclaw-proxy-1.2.0.0.xpi"
→ Bỏ qua release "container-inspector-v1.1.0" (không match pattern)
→ Download "luxeclaw-proxy-1.2.0.0.xpi" → đè file cũ
```

---

## Các Giai Đoạn Triển Khai

### Giai đoạn 1 — Core Engine

#### [NEW] `core/config.py`
- File config local: `<app_dir>/config.json`
- Lưu: Supabase URL, token (mã hoá AES), download path, machine ID
- Đường dẫn đa nền tảng

#### [NEW] `core/vault.py`
- AES-256-CBC cho secrets local (pattern từ LuxeClaw Deployer)
- Key = hostname + hardware salt
- Encrypt/decrypt Supabase token khi lưu local

#### [NEW] `core/github_api.py`
- `clone_repo(url, dest, token)` — git clone / git pull
- `get_releases(owner, repo, token)` — lấy tất cả releases
- `find_latest_asset(releases, pattern)` — tìm release mới nhất có asset match pattern
- `download_asset(url, dest, token)` — tải file với progress
- `parse_repo_url(url)` → `(owner, repo_name)` tự tách từ URL

#### [NEW] `core/supabase_sync.py`
- CRUD cho `quicktool_items`, `quicktool_tokens`, `quicktool_settings`
- `sync_down()` / `sync_up()` cho tất cả bảng

#### [NEW] `core/downloader.py`
- Download engine thống nhất với progress callback
- Hỗ trợ git clone/pull + HTTP download
- Retry on failure

---

### Giai đoạn 2 — GUI (customtkinter, Windows first)

#### [NEW] `ui/app.py`
- Cửa sổ chính 900×650, dark theme
- 2 tab: **Dashboard** | **Settings**
- First-run wizard: nhập Supabase URL + token

#### [NEW] `ui/dashboard_tab.py`
- Download path input (Browse button)
- Scrollable item cards:
  - Name + description
  - Type icon (📂 repo / 📦 release)
  - URL (editable)
  - Token dropdown (None / labeled tokens)
  - Status indicator
  - [Clone/Download] [Delete] buttons
- [+ Add New] → paste URL → auto-detect name
- [Sync All] button
- Delete = xoá local files + xoá khỏi list

#### [NEW] `ui/settings_tab.py`
- Supabase connection (URL + token + [Test])
- **Token Manager**: list tokens with label, [Add] [Delete]
- Download path + Browse
- [Sync to Cloud] / [Sync from Cloud]

---

### Giai đoạn 3 — CLI Mode

```bash
gitquicktool sync              # Sync all enabled items
gitquicktool list              # List configured items
gitquicktool add <url>         # Add new repo/release
gitquicktool remove <name>     # Remove item
gitquicktool pull <name>       # Clone/download single item
gitquicktool config --url X    # Configure Supabase
gitquicktool tokens            # List tokens
gitquicktool tokens add        # Add token interactively
```

---

### Giai đoạn 4 — Đóng Gói

- Windows: PyInstaller → `.exe` portable
- Linux: PyInstaller → binary
- Public release trên GitHub
- Version: `0.1.0.0`

---

## UI Mockup

### Dashboard Tab
```
┌─────────────────────────────────────────────────────────────┐
│  GitQuickTool v0.1.0                        [—] [□] [×]     │
├─────────────────────────────────────────────────────────────┤
│  [Dashboard]  [Settings]                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Download Path: [D:\Tools\__________________] [Browse]      │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📂 win-toolbox                             [Clone ▶]  │  │
│  │ https://github.com/ngojclee/win-toolbox               │  │
│  │ Token: [None ▾]   Status: ✅ Up to date   [🗑 Del]   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📂 win-toolbox-private                     [Clone ▶]  │  │
│  │ https://github.com/ngojclee/win-toolbox-private       │  │
│  │ Token: [Main PAT ▾]  Status: ⬇ Not cloned  [🗑 Del]  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📦 LuxeClaw Proxy                       [Download ▶]  │  │
│  │ ngojclee/win-toolbox → luxeclaw-proxy-*.xpi           │  │
│  │ Token: [Main PAT ▾]  Status: 🔄 Update    [🗑 Del]   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  [+ Add New]                            [↻ Sync All]       │
└─────────────────────────────────────────────────────────────┘
```

### Settings Tab
```
┌─────────────────────────────────────────────────────────────┐
│  [Dashboard]  [Settings]                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ── Supabase Connection ──                                  │
│  URL:   [https://xxx.supabase.co__________]                 │
│  Token: [••••••••••••••••••••••••••••••••_]                  │
│  [Test Connection]  Status: ✅ Connected                    │
│                                                             │
│  ── Token Manager ──                                        │
│  ┌─────────────────────────────────────────┐                │
│  │ Main PAT        ghp_xxxx...xxxx  [🗑]  │                │
│  │ Company Token   ghp_yyyy...yyyy  [🗑]  │                │
│  └─────────────────────────────────────────┘                │
│  [+ Add Token]                                              │
│                                                             │
│  ── Download Path ──                                        │
│  Path: [D:\Tools\__________________] [Browse]               │
│                                                             │
│  ── Sync ──                                                 │
│  [↑ Sync to Cloud]    [↓ Sync from Cloud]                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Kế Hoạch Kiểm Tra

### Test tự động

```bash
python -m pytest tests/ -v
```

1. **`tests/test_github_api.py`**:
   - Test `parse_repo_url("https://github.com/ngojclee/win-toolbox")` → `("ngojclee", "win-toolbox")`
   - Test `find_latest_asset()` với mock releases chứa nhiều app
   - Test glob pattern matching

2. **`tests/test_vault.py`**:
   - Test encrypt/decrypt roundtrip
   - Test wrong key bị từ chối

### Kiểm tra thủ công (trên Windows)

1. Chạy `python main.py` → cửa sổ GUI hiện lên với dark theme
2. Settings tab → nhập Supabase URL + token → [Test Connection] → thấy ✅
3. Token Manager → [+ Add Token] → nhập label + token → thấy trong list
4. Dashboard → [+ Add New] → paste `https://github.com/ngojclee/win-toolbox` → tên tự điền `win-toolbox`
5. Bấm [Clone] → thấy progress → thư mục được tạo
6. Thêm release item → pattern `luxeclaw-proxy-*.xpi` → [Download] → file xuất hiện
7. [Sync to Cloud] → kiểm tra dữ liệu trên Supabase
8. Xoá app data → [Sync from Cloud] → tất cả items + tokens xuất hiện lại
