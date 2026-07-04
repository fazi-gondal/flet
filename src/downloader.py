"""
downloader.py — All download logic, URL resolution, platform detection
and metadata helpers. No direct Flet UI dependencies; everything is
communicated back to the UI via callback functions.
"""

import os
import re
import json
import sys
import mimetypes
import subprocess
from datetime import datetime
from urllib.parse import quote

# ── Platform colour maps (used by library.py for card styling) ─────────────
import flet as ft

PLATFORM_COLOR = {
    'TikTok':    ft.Colors.PINK_900,
    'Instagram': ft.Colors.PURPLE_700,
    'YouTube':   ft.Colors.RED_700,
    'Twitter/X': ft.Colors.BLUE_GREY_800,
    'Facebook':  ft.Colors.BLUE_800,
    'Video':     ft.Colors.BLUE_700,
}
PLATFORM_CHIP_COLOR = {
    'TikTok':    ft.Colors.PINK_100,
    'Instagram': ft.Colors.PURPLE_100,
    'YouTube':   ft.Colors.RED_100,
    'Twitter/X': ft.Colors.BLUE_GREY_100,
    'Facebook':  ft.Colors.BLUE_100,
    'Video':     ft.Colors.BLUE_100,
}


def detect_platform(url: str) -> str:
    u = url.lower()
    if 'tiktok.com' in u:                      return 'TikTok'
    if 'instagram.com' in u:                   return 'Instagram'
    if 'youtube.com' in u or 'youtu.be' in u: return 'YouTube'
    if 'twitter.com' in u or 'x.com' in u:    return 'Twitter/X'
    if 'facebook.com' in u or 'fb.com' in u:  return 'Facebook'
    return 'Video'


def clean_ansi(text: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*[mGKH]', '', text)


def load_metadata(metadata_path: str) -> dict:
    try:
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_metadata(metadata_path: str, meta: dict):
    try:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def resolve_short_url(url: str) -> str:
    """Follow redirects for short TikTok links. Lazy-imports requests."""
    if 'tiktok.com' in url:
        import requests  # lazy — not needed at startup
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            }
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
            return response.url
        except Exception:
            pass
    return url


def preload_heavy_modules():
    """Import yt-dlp and requests in a background thread so first download is instant."""
    try:
        import requests       # noqa
        from yt_dlp import YoutubeDL  # noqa
    except Exception:
        pass


def scan_android_media(paths: list[str]) -> bool:
    """
    Ask Android to index newly saved media files so they appear in Gallery
    and video player apps without waiting for a device-wide media scan.
    """
    paths = [path for path in paths if path and os.path.exists(path)]
    if not paths or not os.path.exists("/storage/emulated/0"):
        return False

    try:
        from jnius import autoclass

        activity_thread = autoclass("android.app.ActivityThread")
        context = activity_thread.currentApplication().getApplicationContext()

        media_scanner = autoclass("android.media.MediaScannerConnection")
        mime_types = [
            mimetypes.guess_type(path)[0] or "video/*"
            for path in paths
        ]
        media_scanner.scanFile(context, paths, mime_types, None)
        return True
    except Exception:
        pass

    try:
        from jnius import autoclass

        activity_thread = autoclass("android.app.ActivityThread")
        context = activity_thread.currentApplication().getApplicationContext()
        intent = autoclass("android.content.Intent")
        uri = autoclass("android.net.Uri")
        java_file = autoclass("java.io.File")

        for path in paths:
            context.sendBroadcast(
                intent(
                    intent.ACTION_MEDIA_SCANNER_SCAN_FILE,
                    uri.fromFile(java_file(path)),
                )
            )
        return True
    except Exception:
        pass

    try:
        for path in paths:
            subprocess.run(
                [
                    "/system/bin/am",
                    "broadcast",
                    "-a",
                    "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                    "-d",
                    f"file://{quote(path)}",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        return True
    except Exception:
        return False


def run_download(url: str, target_dir: str, cookie_path: str,
                 metadata_path: str,
                 on_status,   # callable(str)
                 on_progress, # callable(float)
                 on_finish,   # callable()
                 on_error,    # callable(str)
                 page):
    """
    Execute a yt-dlp download synchronously (run this in a daemon thread).
    All UI feedback goes through the on_* callbacks.

    NOTE: We do NOT call resolve_short_url() here — yt-dlp follows HTTP
    redirects internally.  Calling it manually just adds an extra network
    round-trip before yt-dlp makes the same trip itself.
    """
    if not os.path.exists(cookie_path):
        on_status("Error: 'cookies.txt' file missing!")
        on_finish()
        return

    def _hook(d):
        if d['status'] == 'downloading':
            raw = d.get('_percent_str', '0%')
            pct_str = clean_ansi(raw).replace('%', '').strip()
            try:
                on_progress(float(pct_str) / 100.0)
            except ValueError:
                pass
            on_status(f"Downloading: {raw.strip()}")
            page.update()
        elif d['status'] == 'finished':
            on_progress(1.0)
            on_status("Saving file…")
            page.update()

    ydl_opts = {
        'outtmpl':    os.path.join(target_dir, '%(title)s.%(ext)s'),
        'progress_hooks': [_hook],
        'cookiefile': cookie_path,

        # Simpler format string resolves faster (fewer format comparisons)
        'format': 'b[ext=mp4]/b',

        # Skip things we don't need — each one saves a network request
        'writesubtitles':    False,
        'writeautomaticsub': False,
        'writethumbnail':    False,
        'noplaylist':        True,   # don't scan for playlists

        # No artificial delays between requests
        'sleep_interval':     0,
        'max_sleep_interval': 0,

        'socket_timeout':               15,   # detect failures faster
        'retries':                       5,
        'fragment_retries':              5,
        'concurrent_fragment_downloads': 4,   # parallel chunks

        'quiet':       True,
        'no_warnings': True,

        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;'
                'q=0.9,image/avif,image/webp,*/*;q=0.8'
            ),
            'Accept-Language': 'en-US,en;q=0.5',
        },
    }

    video_exts = ('.mp4', '.mkv', '.mov', '.avi')
    before = (
        set(f for f in os.listdir(target_dir) if f.lower().endswith(video_exts))
        if os.path.exists(target_dir) else set()
    )

    try:
        if 'yt_dlp' not in sys.modules:
            on_status("Preparing downloader (first run only)…")
            page.update()

        from yt_dlp import YoutubeDL  # lazy — instant if pre-warmed
        on_status("Analyzing video…")   # info-extraction phase: no hooks fire yet
        page.update()
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Persist metadata for newly created files
        after = set(f for f in os.listdir(target_dir) if f.lower().endswith(video_exts))
        new_files = after - before
        if new_files:
            meta = load_metadata(metadata_path)
            platform = detect_platform(url)
            date_str = datetime.now().strftime('%d %b %Y')
            for fname in new_files:
                meta[fname] = {'platform': platform, 'url': url, 'date': date_str}
            save_metadata(metadata_path, meta)

            new_paths = [os.path.join(target_dir, fname) for fname in new_files]
            if scan_android_media(new_paths):
                on_status("Video saved and added to Gallery.")
            else:
                on_status("Video saved successfully.")
        else:
            on_status("Video saved successfully.")

    except Exception as exc:
        on_error(str(exc))
    finally:
        on_finish()
