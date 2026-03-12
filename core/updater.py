"""
core/updater.py — Self-Update via GitHub Releases.

Flow:
  1. check_update() → compare APP_VERSION vs latest release tag
  2. download_update() → download exe to <current>_update.exe
  3. apply_update() → write _update.bat, launch it, exit app
"""

import os
import sys
from pathlib import Path
from typing import Optional

import requests


GITHUB_API = "https://api.github.com"
REPO = "ngojclee/gitquicktool"
EXE_NAME = "GitQuickTool.exe"


def _parse_version(tag: str) -> tuple:
    """Parse 'v1.0.0.0' or '1.0.0.0' → (1, 0, 0, 0)."""
    v = tag.lstrip("v").strip()
    parts = v.split(".")
    return tuple(int(p) for p in parts if p.isdigit())


def check_update(current_version: str, git_token: Optional[str] = None, force: bool = False):
    """
    Check GitHub for newer release.
    Returns dict with status:
      - {"status":"update_available", ...} when a release .exe is ready.
      - {"status":"up_to_date"} when local version is latest.
      - {"status":"error", "message": "..."} on failure.
    If force=True, always returns info (even if same version).
    For public repos, git_token is optional.
    """
    try:
        headers = {"Accept": "application/vnd.github+json"}
        if git_token:
            headers["Authorization"] = f"token {git_token}"

        r = requests.get(
            f"{GITHUB_API}/repos/{REPO}/releases/latest",
            headers=headers, timeout=15
        )

        if r.status_code == 404:
            return {
                "status": "error",
                "message": "No releases found on GitHub."
            }
        if r.status_code not in (200, ):
            return {
                "status": "error",
                "message": f"GitHub API error HTTP {r.status_code}."
            }

        data = r.json()
        remote_tag = data.get("tag_name", "")
        remote_ver = _parse_version(remote_tag)
        local_ver = _parse_version(current_version)

        if not force and remote_ver <= local_ver:
            return {"status": "up_to_date"}

        # Find .exe asset
        for asset in data.get("assets", []):
            if asset["name"].lower().endswith(".exe"):
                return {
                    "status": "update_available",
                    "tag": remote_tag,
                    "name": asset["name"],
                    "download_url": asset["url"],  # API URL
                    "browser_url": asset["browser_download_url"],
                    "size": asset["size"],
                    "notes": data.get("body", ""),
                }
        return {
            "status": "error",
            "message": "New release has no .exe asset."
        }
    except requests.RequestException:
        return {
            "status": "error",
            "message": "Cannot connect to GitHub. Check network."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unknown error: {str(e)[:60]}"
        }


def download_update(download_url: str, dest_path: Path,
                    git_token: Optional[str] = None,
                    progress_fn=None,
                    expected_size: Optional[int] = None) -> bool:
    """
    Download release asset to dest_path.
    progress_fn(bytes_downloaded, total_bytes) called periodically.
    """
    try:
        headers = {"Accept": "application/octet-stream"}
        if git_token:
            headers["Authorization"] = f"token {git_token}"

        r = requests.get(download_url, headers=headers, stream=True, timeout=120)
        if r.status_code != 200:
            return False

        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")

        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress_fn:
                    progress_fn(downloaded, total)
            f.flush()
            os.fsync(f.fileno())

        # Integrity check
        if total > 0 and downloaded != total:
            tmp_path.unlink(missing_ok=True)
            return False
        if expected_size and downloaded != expected_size:
            tmp_path.unlink(missing_ok=True)
            return False

        tmp_path.replace(dest_path)
        return True
    except Exception:
        tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
        tmp_path.unlink(missing_ok=True)
        return False


def apply_update(current_exe: Path, new_exe: Path):
    """
    Write a .bat that waits for this process to exit,
    replaces the old exe with new, then auto-launches the new app.
    """
    bat = current_exe.parent / "_update.bat"
    backup_exe = current_exe.with_suffix(current_exe.suffix + ".bak")
    err_log = current_exe.parent / "_update_error.log"
    bat_content = f"""@echo off
setlocal EnableExtensions EnableDelayedExpansion
timeout /t 3 /nobreak >nul

set "APP={current_exe}"
set "NEW={new_exe}"
set "BAK={backup_exe}"
set "ERRLOG={err_log}"
set /a RETRIES=0

if not exist "%NEW%" (
    echo [%date% %time%] Missing update file: %NEW%>>"%ERRLOG%"
    goto fail
)

:wait_unlock
set /a RETRIES+=1
if exist "%BAK%" del /f /q "%BAK%" >nul 2>&1
if exist "%APP%" move /y "%APP%" "%BAK%" >nul 2>&1
if exist "%APP%" (
    if !RETRIES! GEQ 30 (
        echo [%date% %time%] Cannot unlock old exe after !RETRIES! tries>>"%ERRLOG%"
        goto fail
    )
    timeout /t 2 /nobreak >nul
    goto wait_unlock
)

move /y "%NEW%" "%APP%" >nul 2>&1
if exist "%APP%" goto launch

if exist "%BAK%" (
    move /y "%BAK%" "%APP%" >nul 2>&1
)
echo [%date% %time%] Move new exe failed, restored backup if possible>>"%ERRLOG%"
goto fail

:launch
set "_MEIPASS2="
set "_PYI_APPLICATION_HOME_DIR="
set "PYINSTALLER_RESET_ENVIRONMENT=1"
start "" /D "{current_exe.parent}" "%APP%"
goto cleanup

:fail
echo [%date% %time%] Update apply failed>>"%ERRLOG%"

:cleanup
del /f /q "%~f0"
"""
    bat.write_text(bat_content, encoding="utf-8")

    # Launch bat and exit
    os.startfile(str(bat))
    sys.exit(0)


def get_current_exe() -> Optional[Path]:
    """Get path of running .exe (only works when frozen by PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable)
    return None


def cleanup_update():
    """Remove leftover _update.bat and temp files from previous update."""
    exe = get_current_exe()
    if not exe:
        return
    d = exe.parent
    for name in ("_update.bat", f"{EXE_NAME.replace('.exe', '')}_update.exe",
                 f"{EXE_NAME.replace('.exe', '')}_update.exe.part",
                 f"{EXE_NAME}.bak"):
        f = d / name
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass
