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
import time
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

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v', '.3gp')


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
    """Kept for compatibility; downloads import network packages on demand."""
    return


def get_android_context():
    """
    Retrieve the Android Context/Activity. 
    First looks at Serious Python environment configurations,
    then common Python-to-Android framework classes, and falls back to ActivityThread.
    """
    import os
    try:
        import jnius
        jnius.attach_thread()  # Ensure the background thread is attached to JVM
        from jnius import autoclass
    except ImportError:
        return None

    context = None
    
    # 1. Try to get context via serious_python activity holder class (environment variable)
    host_class = os.environ.get("MAIN_ACTIVITY_HOST_CLASS_NAME")
    if host_class:
        try:
            PythonActivity = autoclass(host_class)
            context = PythonActivity.mActivity
        except Exception:
            pass

    # 2. Try common hardcoded class names
    if not context:
        for name in (
            "com.flet.serious_python.PythonActivity",
            "com.flet.serious_python_android.PythonActivity",
            "org.kivy.android.PythonActivity",
            "org.renpy.android.PythonActivity"
        ):
            try:
                PythonActivity = autoclass(name)
                context = PythonActivity.mActivity
                if context:
                    break
            except Exception:
                pass

    # 3. Fallback to ActivityThread
    if not context:
        try:
            activity_thread = autoclass("android.app.ActivityThread")
            app = activity_thread.currentApplication()
            if app:
                context = app.getApplicationContext()
        except Exception:
            pass

    return context


def log_scan_attempt(message: str):
    """Write scan logs to a local file in Download/VidSaver/ directory for easy mobile debugging."""
    try:
        log_dir = "/storage/emulated/0/Download/VidSaver"
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "media_scan_log.txt")
        from datetime import datetime
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


_cmd_media_supported = None


def scan_android_media(paths: list[str]) -> bool:
    """
    Ask Android to index newly saved media files so they appear in Gallery.
    Uses subprocess commands only — safe to call from any thread (no JNI needed).
    subprocess.run creates a new OS process so thread attachment is irrelevant.
    """
    global _cmd_media_supported

    file_paths = [path for path in paths if path and os.path.isfile(path)]
    if not file_paths or not os.path.exists("/storage/emulated/0"):
        return False

    scanned = False

    for path in file_paths:
        uri = f"file://{path}"
        fname = os.path.basename(path)

        # Method 1: cmd media scan (Android 9+ / API 28+)
        if _cmd_media_supported is not False:
            try:
                result = subprocess.run(
                    ["/system/bin/cmd", "media", "scan", uri],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    timeout=8,
                )
                stderr_text = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
                if result.returncode == 0:
                    scanned = True
                    _cmd_media_supported = True
                    log_scan_attempt(f"bg-cmd-scan OK: {fname}")
                    continue
                else:
                    log_scan_attempt(f"bg-cmd-scan failed (code {result.returncode}) for {fname}: {stderr_text.strip()}")
                    if "Can't find service" in stderr_text or "not found" in stderr_text:
                        _cmd_media_supported = False
            except Exception as e:
                log_scan_attempt(f"bg-cmd-scan error for {fname}: {e}")
                _cmd_media_supported = False

        # Method 2: am broadcast with new media provider package (Android 10+)
        try:
            result = subprocess.run(
                [
                    "/system/bin/am", "broadcast",
                    "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                    "-d", uri,
                    "-p", "com.android.providers.media.module",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if result.returncode == 0:
                scanned = True
                continue
        except Exception:
            pass

        # Method 3: am broadcast without package filter (Android 5-9)
        try:
            result = subprocess.run(
                [
                    "/system/bin/am", "broadcast",
                    "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                    "-d", uri,
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            scanned = scanned or result.returncode == 0
        except Exception:
            pass

    return scanned



def register_android_media_store(paths: list[str]) -> bool:
    """
    Insert saved videos into Android MediaStore directly. This mirrors the
    refresh File Manager triggers when it notices a new public media file.
    """
    file_paths = [path for path in paths if path and os.path.isfile(path)]
    if not file_paths or not os.path.exists("/storage/emulated/0"):
        return False

    context = get_android_context()
    if not context:
        return False

    try:
        from jnius import autoclass
        resolver = context.getContentResolver()
        content_values = autoclass("android.content.ContentValues")
        media_store_video = autoclass("android.provider.MediaStore$Video$Media")
        build_version = autoclass("android.os.Build$VERSION")

        registered = False
        now = int(time.time())
        now_ms = now * 1000
        for path in file_paths:
            try:
                values = content_values()
                name = os.path.basename(path)
                title, _ = os.path.splitext(name)
                mime_type = mimetypes.guess_type(path)[0] or "video/mp4"
                modified = int(os.path.getmtime(path))
                size = int(os.path.getsize(path))

                values.put("_data", path)
                values.put("_display_name", name)
                values.put("title", title)
                values.put("mime_type", mime_type)
                values.put("date_added", now)
                values.put("date_modified", modified)
                values.put("datetaken", now_ms)
                values.put("_size", size)
                if build_version.SDK_INT >= 29:
                    values.put("relative_path", "Download/VidSaver/")
                    values.put("is_pending", 0)

                uri = resolver.insert(media_store_video.EXTERNAL_CONTENT_URI, values)
                registered = registered or uri is not None
            except Exception:
                pass

        return registered
    except Exception:
        return False


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
        for download in item.get('requested_downloads') or []:
            path = download.get('filepath') or download.get('filename')
            if path:
                paths.append(path)
        for key in ('filepath', '_filename', 'filename'):
            path = item.get(key)
            if path:
                paths.append(path)
        for entry in item.get('entries') or []:
            add_from(entry)

    add_from(info)
    return paths


def run_download(url: str, target_dir: str, cookie_path: str,
                 metadata_path: str,
                 on_status,   # callable(str)
                 on_progress, # callable(float)
                 on_finish,   # callable()
                 on_error,    # callable(str)
                 page,
                 schedule_media_scan_later=None):
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

    downloaded_paths = []

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
            filename = d.get('filename')
            if filename:
                downloaded_paths.append(filename)
            on_progress(1.0)
            on_status("Saving file…")
            page.update()

    ydl_opts = {
        'outtmpl':    os.path.join(target_dir, '%(title).80s [%(id)s].%(ext)s'),
        'progress_hooks': [_hook],
        'cookiefile': cookie_path,

        # Keep downloaded videos sorted as new/recent media on Android. yt-dlp
        # can otherwise preserve old server timestamps from the source file.
        'updatetime': False,

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

    before = {}
    if os.path.exists(target_dir):
        before = {
            f: os.path.getmtime(os.path.join(target_dir, f))
            for f in os.listdir(target_dir)
            if f.lower().endswith(VIDEO_EXTENSIONS)
        }

    try:
        if 'yt_dlp' not in sys.modules:
            on_status("Preparing downloader (first run only)…")
            page.update()

        from yt_dlp import YoutubeDL  # lazy — instant if pre-warmed
        on_status("Analyzing video…")   # info-extraction phase: no hooks fire yet
        page.update()
        with YoutubeDL(ydl_opts) as ydl:
            on_status("Downloading video...")
            page.update()
            info = ydl.extract_info(url, download=True)
            downloaded_paths.extend(collect_downloaded_paths(info))

        # Persist metadata for newly created files
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
            path for path in downloaded_paths
            if path and os.path.exists(path) and path.lower().endswith(VIDEO_EXTENSIONS)
        ]
        detected_files = {os.path.basename(path) for path in detected_paths}
        saved_files = sorted(new_files | updated_files | detected_files)

        if saved_files:
            meta = load_metadata(metadata_path)
            platform = detect_platform(url)
            date_str = datetime.now().strftime('%d %b %Y')
            for fname in saved_files:
                meta[fname] = {'platform': platform, 'url': url, 'date': date_str}
            save_metadata(metadata_path, meta)

            new_paths = [os.path.join(target_dir, fname) for fname in saved_files]
            mark_files_recent(new_paths)
            media_registered = register_android_media_store(new_paths)
            scan_started = scan_android_media(new_paths)
            if schedule_media_scan_later:
                schedule_media_scan_later(new_paths)
            if media_registered or scan_started:
                on_status("Video saved and added to Gallery.")
            else:
                on_status("Video saved. Gallery may update shortly.")
        else:
            on_error(
                "No video file was saved. Instagram may require fresh cookies, "
                "login access, or the link may not contain a downloadable video."
            )

    except Exception as exc:
        on_error(str(exc))
    finally:
        on_finish()
