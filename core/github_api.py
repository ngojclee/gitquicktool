"""
core/github_api.py — GitHub API interactions.
Handles repo cloning, release fetching, and asset downloading.
"""

import fnmatch
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse

import requests


def parse_repo_url(url: str) -> tuple[str, str]:
    """
    Extract (owner, repo) from a GitHub URL.
    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
      - github.com/owner/repo
      - owner/repo
    """
    url = url.strip().rstrip("/")

    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]

    # Try parsing as URL
    parsed = urlparse(url)
    if parsed.netloc:
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]

    # Try as owner/repo shorthand
    parts = url.strip("/").split("/")
    if len(parts) == 2:
        return parts[0], parts[1]

    raise ValueError(f"Cannot parse GitHub URL: {url}")


def get_repo_name(url: str) -> str:
    """Extract just the repo name from a URL."""
    _, repo = parse_repo_url(url)
    return repo


def _auth_headers(token: Optional[str] = None) -> dict:
    """Build authorization headers for GitHub API."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _git_with_token(url: str, token: Optional[str] = None) -> str:
    """Inject token into git clone URL for private repos."""
    if not token:
        return url
    parsed = urlparse(url)
    if parsed.scheme in ("https", "http"):
        return f"{parsed.scheme}://x-access-token:{token}@{parsed.netloc}{parsed.path}"
    return url


# ── Repo Operations ──────────────────────────────────────────

def clone_repo(
    url: str,
    dest: str | Path,
    token: Optional[str] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Clone a repo to dest. If already exists, do git pull instead.
    Returns True on success.
    """
    dest = Path(dest)
    auth_url = _git_with_token(url, token)

    if (dest / ".git").exists():
        # Already cloned — pull
        if progress_cb:
            progress_cb("Pulling latest changes...")
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(dest),
            capture_output=True, text=True, timeout=120,
        )
        if progress_cb:
            progress_cb(result.stdout.strip() or "Pull complete")
        return result.returncode == 0

    # Fresh clone
    dest.parent.mkdir(parents=True, exist_ok=True)
    if progress_cb:
        progress_cb(f"Cloning to {dest.name}...")

    result = subprocess.run(
        ["git", "clone", "--depth", "1", auth_url, str(dest)],
        capture_output=True, text=True, timeout=300,
    )
    if progress_cb:
        progress_cb("Clone complete" if result.returncode == 0 else result.stderr.strip())
    return result.returncode == 0


# ── Release Operations ───────────────────────────────────────

def get_releases(
    owner: str, repo: str,
    token: Optional[str] = None,
    per_page: int = 30,
) -> list[dict]:
    """Fetch releases from GitHub API (most recent first)."""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    headers = _auth_headers(token)
    params = {"per_page": per_page}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def find_latest_asset(
    releases: list[dict],
    pattern: str,
) -> Optional[dict]:
    """
    Find the most recent release that has an asset matching the glob pattern.
    Returns dict with keys: release_tag, asset_name, asset_url, asset_size, release_date.
    """
    for release in releases:
        for asset in release.get("assets", []):
            if fnmatch.fnmatch(asset["name"], pattern):
                return {
                    "release_tag": release["tag_name"],
                    "release_name": release.get("name", release["tag_name"]),
                    "release_date": release["published_at"],
                    "asset_name": asset["name"],
                    "asset_url": asset["browser_download_url"],
                    "asset_api_url": asset["url"],
                    "asset_size": asset["size"],
                }
    return None


def download_asset(
    asset_url: str,
    dest: str | Path,
    token: Optional[str] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> bool:
    """
    Download a release asset to dest path.
    progress_cb(downloaded_bytes, total_bytes) called periodically.
    Returns True on success.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    headers = _auth_headers(token)
    headers["Accept"] = "application/octet-stream"

    resp = requests.get(asset_url, headers=headers, stream=True, timeout=60)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            downloaded += len(chunk)
            if progress_cb and total > 0:
                progress_cb(downloaded, total)

    return True


def download_release_by_pattern(
    owner: str, repo: str,
    pattern: str,
    dest_dir: str | Path,
    token: Optional[str] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
) -> Optional[dict]:
    """
    High-level: find latest release matching pattern, download it.
    Returns asset info dict or None if no match.
    """
    releases = get_releases(owner, repo, token)
    asset_info = find_latest_asset(releases, pattern)
    if not asset_info:
        return None

    dest_dir = Path(dest_dir)
    dest_file = dest_dir / asset_info["asset_name"]

    # Use API URL for private repos, browser URL for public
    url = asset_info["asset_api_url"] if token else asset_info["asset_url"]
    download_asset(url, dest_file, token=token, progress_cb=progress_cb)

    asset_info["local_path"] = str(dest_file)
    return asset_info


def delete_local(path: str | Path) -> bool:
    """Delete a local file or directory."""
    path = Path(path)
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        return True
    elif path.is_file():
        path.unlink(missing_ok=True)
        return True
    return False
