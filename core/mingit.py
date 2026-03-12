"""
core/mingit.py — Auto-download MinGit (portable git) if git is not installed.
Downloads from git-for-windows releases on GitHub.
"""

import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path

import requests

# MinGit release info
MINGIT_VERSION = "2.47.1"
MINGIT_TAG = f"v{MINGIT_VERSION}.windows.1"
MINGIT_FILENAME = f"MinGit-{MINGIT_VERSION}-64-bit.zip"
MINGIT_URL = (
    f"https://github.com/git-for-windows/git/releases/download/"
    f"{MINGIT_TAG}/{MINGIT_FILENAME}"
)


def get_mingit_dir() -> Path:
    """Get the directory where MinGit should be installed."""
    # Store alongside the executable or in app directory
    if getattr(os.sys, 'frozen', False):
        # Running as PyInstaller exe
        base = Path(os.sys.executable).parent
    else:
        base = Path(__file__).parent.parent

    return base / "mingit"


def get_mingit_exe() -> Path | None:
    """Get the path to MinGit's git.exe if it exists."""
    mingit_dir = get_mingit_dir()
    git_exe = mingit_dir / "cmd" / "git.exe"
    if git_exe.exists():
        return git_exe
    return None


def is_git_available() -> bool:
    """Check if git is available on the system (PATH or MinGit)."""
    # Check MinGit first
    if get_mingit_exe():
        return True

    # Check system PATH
    return shutil.which("git") is not None


def get_git_executable() -> str:
    """Get the git executable path. Prefers MinGit over system git."""
    mingit_exe = get_mingit_exe()
    if mingit_exe:
        return str(mingit_exe)

    system_git = shutil.which("git")
    if system_git:
        return system_git

    return "git"  # Fallback, will fail if not found


def download_mingit(progress_callback=None) -> bool:
    """
    Download and extract MinGit.
    progress_callback(percent: int, message: str) — optional progress updates.
    Returns True on success.
    """
    if platform.system() != "Windows":
        if progress_callback:
            progress_callback(0, "MinGit is Windows-only. Install git via package manager.")
        return False

    mingit_dir = get_mingit_dir()
    zip_path = mingit_dir.parent / MINGIT_FILENAME

    try:
        # Download
        if progress_callback:
            progress_callback(0, f"Downloading MinGit {MINGIT_VERSION}...")

        resp = requests.get(MINGIT_URL, stream=True, timeout=60)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total and progress_callback:
                    pct = int(downloaded / total * 80)  # 0-80% for download
                    progress_callback(pct, f"Downloading... {downloaded // 1024 // 1024}MB")

        # Extract
        if progress_callback:
            progress_callback(85, "Extracting MinGit...")

        mingit_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(mingit_dir)

        # Verify
        git_exe = mingit_dir / "cmd" / "git.exe"
        if not git_exe.exists():
            if progress_callback:
                progress_callback(0, "Extraction failed — git.exe not found")
            return False

        # Test
        if progress_callback:
            progress_callback(95, "Verifying...")

        result = subprocess.run(
            [str(git_exe), "--version"],
            capture_output=True, text=True, timeout=10,
        )
        version = result.stdout.strip()

        if progress_callback:
            progress_callback(100, f"✓ {version}")

        return True

    except Exception as e:
        if progress_callback:
            progress_callback(0, f"✗ Download failed: {str(e)[:60]}")
        return False

    finally:
        # Cleanup zip
        try:
            if zip_path.exists():
                zip_path.unlink()
        except OSError:
            pass


def check_and_offer_mingit() -> tuple[bool, str]:
    """
    Check if git is available. Returns (available, message).
    If not available, message suggests downloading MinGit.
    """
    if is_git_available():
        git_exe = get_git_executable()
        try:
            result = subprocess.run(
                [git_exe, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            return True, result.stdout.strip()
        except Exception:
            return True, "git found"

    return False, "Git not found. Click 'Install MinGit' to download a portable git."
