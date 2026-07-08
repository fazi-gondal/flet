"""
downloader.py - Download logic, URL resolution, platform detection, and
metadata helpers. The module has no direct Flet UI dependencies except shared
color constants used by the library view.
"""

from datetime import datetime
import json
import os
import re
import sys
import time

import flet as ft

PLATFORM_COLOR = {
    "TikTok": ft.Colors.PINK_900,
    "Instagram": ft.Colors.PURPLE_700,
    "YouTube": ft.Colors.RED_700,
    "Twitter/X": ft.Colors.BLUE_GREY_800,
    "Facebook": ft.Colors.BLUE_800,
    "Video": ft.Colors.BLUE_700,
}
PLATFORM_CHIP_COLOR = {
    "TikTok": ft.Colors.PINK_100,
    "Instagram": ft.Colors.PURPLE_100,
    "YouTube": ft.Colors.RED_100,
    "Twitter/X": ft.Colors.BLUE_GREY_100,
    "Facebook": ft.Colors.BLUE_100,
    "Video": ft.Colors.BLUE_100,
}

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".3gp")


def detect_platform(url: str) -> str:
    u = url.lower()
    if "tiktok.com" in u:
        return "TikTok"
    if "instagram.com" in u:
        return "Instagram"
    if "youtube.com" in u or "youtu.be" in u:
        return "YouTube"
    if "twitter.com" in u or "x.com" in u:
        return "Twitter/X"
    if "facebook.com" in u or "fb.com" in u:
        return "Facebook"
    return "Video"


def clean_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[mGKH]", "", text)


def load_metadata(metadata_path: str) -> dict:
    try:
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_metadata(metadata_path: str, meta: dict):
    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def resolve_short_url(url: str) -> str:
    """Follow redirects for short TikTok links. Lazy-imports requests."""
    if "tiktok.com" in url:
        import requests

        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            return response.url
        except Exception:
            pass
    return url


def preload_heavy_modules():
    """Kept for compatibility; downloads import network packages on demand."""
    return


def mark_files_recent(paths: list[str]) -> None:
    """Make Android media pickers sort newly downloaded files as recent."""
    now = time.time()
    for path in paths:
        if path and os.path.isfile(path):
            try:
                os.utime(path, (now, now))
            except Exception:
                pass


def collect_downloaded_paths(info) -> list[str]:
    """Return final downloaded file paths from yt-dlp info dictionaries."""
    paths = []

    def add_from(item):
        if not isinstance(item, dict):
            return
        for download in item.get("requested_downloads") or []:
            path = download.get("filepath") or download.get("filename")
            if path:
                paths.append(path)
        for key in ("filepath", "_filename", "filename"):
            path = item.get(key)
            if path:
                paths.append(path)
        for entry in item.get("entries") or []:
            add_from(entry)

    add_from(info)
    return paths


def run_download(
    url: str,
    target_dir: str,
    cookie_path: str,
    metadata_path: str,
    on_status,
    on_progress,
    on_finish,
    on_error,
    page,
    schedule_media_scan_later=None,
):
    """
    Execute a yt-dlp download synchronously in a worker thread.

    Returns staged video data for the async app layer to publish through
    MediaStore. The metadata_path, on_finish, and schedule_media_scan_later
    arguments are retained for call-site compatibility.
    """
    del metadata_path, on_finish, schedule_media_scan_later

    if not os.path.exists(cookie_path):
        on_status("Error: 'cookies.txt' file missing!")
        return None

    downloaded_paths = []

    def _hook(d):
        if d["status"] == "downloading":
            raw = d.get("_percent_str", "0%")
            pct_str = clean_ansi(raw).replace("%", "").strip()
            try:
                on_progress(float(pct_str) / 100.0)
            except ValueError:
                pass
            on_status(f"Downloading: {raw.strip()}")
            page.update()
        elif d["status"] == "finished":
            filename = d.get("filename")
            if filename:
                downloaded_paths.append(filename)
            on_progress(1.0)
            on_status("Preparing file...")
            page.update()

    os.makedirs(target_dir, exist_ok=True)

    ydl_opts = {
        "outtmpl": os.path.join(target_dir, "%(title).80s [%(id)s].%(ext)s"),
        "progress_hooks": [_hook],
        "cookiefile": cookie_path,
        "updatetime": False,
        "format": "b[ext=mp4]/b",
        "writesubtitles": False,
        "writeautomaticsub": False,
        "writethumbnail": False,
        "noplaylist": True,
        "sleep_interval": 0,
        "max_sleep_interval": 0,
        "socket_timeout": 15,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 4,
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
        },
    }

    before = {
        f: os.path.getmtime(os.path.join(target_dir, f))
        for f in os.listdir(target_dir)
        if f.lower().endswith(VIDEO_EXTENSIONS)
    }

    try:
        if "yt_dlp" not in sys.modules:
            on_status("Preparing downloader (first run only)...")
            page.update()

        from yt_dlp import YoutubeDL

        on_status("Analyzing video...")
        page.update()
        with YoutubeDL(ydl_opts) as ydl:
            on_status("Downloading video...")
            page.update()
            info = ydl.extract_info(url, download=True)
            downloaded_paths.extend(collect_downloaded_paths(info))

        after = {
            f: os.path.getmtime(os.path.join(target_dir, f))
            for f in os.listdir(target_dir)
            if f.lower().endswith(VIDEO_EXTENSIONS)
        }
        new_files = set(after) - set(before)
        updated_files = {
            f for f, mtime in after.items()
            if f in before and mtime > before[f]
        }
        detected_paths = [
            path
            for path in downloaded_paths
            if path and os.path.exists(path) and path.lower().endswith(VIDEO_EXTENSIONS)
        ]
        detected_files = {os.path.basename(path) for path in detected_paths}
        saved_files = sorted(new_files | updated_files | detected_files)

        if not saved_files:
            on_error(
                "No video file was saved. Instagram may require fresh cookies, "
                "login access, or the link may not contain a downloadable video."
            )
            return None

        staged_paths = [os.path.join(target_dir, fname) for fname in saved_files]
        mark_files_recent(staged_paths)
        on_status("Publishing video to Gallery...")
        return {
            "paths": staged_paths,
            "platform": detect_platform(url),
            "url": url,
            "date": datetime.now().strftime("%d %b %Y"),
        }
    except Exception as exc:
        on_error(str(exc))
        return None
