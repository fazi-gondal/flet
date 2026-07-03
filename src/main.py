import os
import re
import json
import threading
from datetime import datetime
import flet as ft
import flet_video as ftv  # Dedicated video playback extension
import flet_permission_handler as fph  # Separate extension package — not part of core flet

ANDROID_STORAGE_ROOT = "/storage/emulated/0"


async def main(page: ft.Page):
    page.title = "Vidsaver"
    page.padding = 0
    page.spacing = 0
    page.safe_area = True
    page.appbar = ft.AppBar(
        title=ft.Text("Vidsaver", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.Colors.BLUE_700,
    )
    is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    page_max_height = page.height or 0

    async def handle_page_resize(e):
        nonlocal page_max_height
        if page.height and page.height > page_max_height:
            page_max_height = page.height
        # Keyboard closed → page height returns to max. Nothing to do here now.
        pass

    page.on_resize = handle_page_resize

    is_android = os.path.exists(ANDROID_STORAGE_ROOT)

    # ------------------ ANDROID STORAGE PERMISSION ------------------
    # Since this app is sideloaded (not on Play Store), MANAGE_EXTERNAL_STORAGE
    # ("All files access") is the simplest reliable option — it bypasses scoped
    # storage entirely, so the existing raw-path yt-dlp write below just works.
    # It must also be declared in pyproject.toml:
    #   [tool.flet.android.permission]
    #   "android.permission.MANAGE_EXTERNAL_STORAGE" = true
    permission_handler = fph.PermissionHandler()
    page.services.append(permission_handler)  # PermissionHandler is a Service, not an overlay control

    async def has_storage_access() -> bool:
        if not is_android:
            return True
        try:
            status = await permission_handler.get_status(fph.Permission.MANAGE_EXTERNAL_STORAGE)
        except Exception:
            return False
        return status == fph.PermissionStatus.GRANTED

    async def request_storage_access(e=None):
        if not is_android:
            return
        # This routes to the special system settings screen ("Allow management
        # of all files") — the toggle has to be flipped manually by the user,
        # there's no silent/instant grant for this particular permission.
        try:
            await permission_handler.request(fph.Permission.MANAGE_EXTERNAL_STORAGE)
        except Exception:
            pass
        if await has_storage_access():
            grant_access_btn.visible = False
            status_text.value = "Storage access granted. Ready to download!"
        else:
            status_text.value = (
                "Enable 'Allow management of all files' for this app in the "
                "settings screen that just opened, then come back here."
            )
        page.update()

    # 📂 PERMANENT DYNAMIC PATH EVALUATION:
    if is_android:
        # Movies/ is one of the standard public directories Android's MediaProvider
        # actively watches and indexes into the Video collection — files saved here
        # show up in Gallery apps and video players automatically. Download/ isn't
        # consistently indexed the same way across OEM skins.
        download_dir = os.path.join(ANDROID_STORAGE_ROOT, "Movies", "VidSaver")
    else:
        try:
            sp = ft.StoragePaths(page)
            download_dir = await sp.get_downloads_directory() or "./downloads"
        except Exception:
            download_dir = os.path.join(os.environ['USERPROFILE'], 'Downloads') if 'USERPROFILE' in os.environ else "./downloads"

    if not os.path.exists(download_dir):
        os.makedirs(download_dir, exist_ok=True)

    # ------------------ TAB 1: DOWNLOADER UI ELEMENTS ------------------
    url_input = ft.TextField(
        label="Paste video link",
        border_radius=12,
        filled=True,
        prefix_icon=ft.Icons.LINK,
    )
    status_text = ft.Text(value="", color=ft.Colors.BLUE_GREY, size=12)
    progress_bar = ft.ProgressBar(height=4, value=0.0, visible=False, color=ft.Colors.BLUE, bgcolor=ft.Colors.BLUE_100, border_radius=4)

    def clean_ansi(text):
        return re.sub(r'\x1b\[[0-9;]*[mGKH]', '', text)

    def ytdl_hook(d):
        if d['status'] == 'downloading':
            raw_percent = d.get('_percent_str', '0%')
            clean_percent = clean_ansi(raw_percent).replace('%', '').strip()
            try:
                float_val = float(clean_percent) / 100.0
                progress_bar.value = float_val
            except ValueError:
                pass
            status_text.value = f"Downloading: {raw_percent.strip()}"
            page.update()
        elif d['status'] == 'finished':
            progress_bar.value = 1.0
            status_text.value = "Saving file..."
            page.update()

    def resolve_short_url(url):
        if "tiktok.com" in url:
            import requests  # lazy import — only loaded when resolving a URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            try:
                response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
                return response.url
            except Exception:
                return url
        return url

    # ── Platform detection & metadata helpers ─────────────────────────────────
    metadata_path = os.path.join(download_dir, '.metadata.json')

    def detect_platform(url: str) -> str:
        u = url.lower()
        if 'tiktok.com' in u:                      return 'TikTok'
        if 'instagram.com' in u:                   return 'Instagram'
        if 'youtube.com' in u or 'youtu.be' in u: return 'YouTube'
        if 'twitter.com' in u or 'x.com' in u:    return 'Twitter/X'
        if 'facebook.com' in u or 'fb.com' in u:  return 'Facebook'
        return 'Video'

    _PLATFORM_COLOR = {
        'TikTok':    ft.Colors.PINK_900,
        'Instagram': ft.Colors.PURPLE_700,
        'YouTube':   ft.Colors.RED_700,
        'Twitter/X': ft.Colors.BLUE_GREY_800,
        'Facebook':  ft.Colors.BLUE_800,
        'Video':     ft.Colors.BLUE_700,
    }
    _PLATFORM_CHIP_COLOR = {
        'TikTok':    ft.Colors.PINK_100,
        'Instagram': ft.Colors.PURPLE_100,
        'YouTube':   ft.Colors.RED_100,
        'Twitter/X': ft.Colors.BLUE_GREY_100,
        'Facebook':  ft.Colors.BLUE_100,
        'Video':     ft.Colors.BLUE_100,
    }

    def load_metadata() -> dict:
        try:
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_metadata(meta: dict):
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def download_video(url, target_dir):
        final_url = resolve_short_url(url)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cookie_path = os.path.join(base_dir, 'cookies.txt')

        if not os.path.exists(cookie_path):
            status_text.value = "Error: 'cookies.txt' file missing!"
            progress_bar.visible = False
            page.update()
            return

        ydl_opts = {
            'outtmpl': os.path.join(target_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [ytdl_hook],
            'cookiefile': cookie_path,
            'format': 'best[ext=mp4]/best',
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
        }

        # Snapshot dir before so we can detect the new file afterwards
        video_exts = ('.mp4', '.mkv', '.mov', '.avi')
        before = set(
            f for f in os.listdir(target_dir)
            if f.lower().endswith(video_exts)
        ) if os.path.exists(target_dir) else set()

        try:
            import sys
            if 'yt_dlp' not in sys.modules:
                # First run: yt-dlp not yet cached. Tell the user we're loading.
                status_text.value = "Preparing downloader (first run only)..."
                page.update()
            from yt_dlp import YoutubeDL  # lazy — instant if pre-warmed
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([final_url])

            # Save platform metadata for every newly created file
            after = set(
                f for f in os.listdir(target_dir)
                if f.lower().endswith(video_exts)
            )
            new_files = after - before
            if new_files:
                meta = load_metadata()
                platform = detect_platform(url)
                date_str = datetime.now().strftime('%d %b %Y')
                for fname in new_files:
                    meta[fname] = {'platform': platform, 'url': url, 'date': date_str}
                save_metadata(meta)

            status_text.value = "Success! Video saved successfully."
            refresh_downloads_list()
        except Exception as e:
            status_text.value = f"Network Timeout / Blocked.\n{str(e)}"
        finally:
            progress_bar.visible = False
            page.update()

    async def on_download_click(e):
        if not url_input.value:
            status_text.value = "Please enter a valid URL!"
            page.update()
            return

        if not await has_storage_access():
            grant_access_btn.visible = True
            status_text.value = "Storage access needed — tap 'Grant Storage Access' first."
            page.update()
            return

        progress_bar.value = 0.0
        progress_bar.visible = True
        status_text.value = "Unwrapping short-link and connecting..."
        page.update()

        threading.Thread(target=download_video, args=(url_input.value, download_dir), daemon=True).start()

    download_btn = ft.Button(
        "Download",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        height=40,
        on_click=on_download_click,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_700,
            color=ft.Colors.WHITE,
        ),
    )

    async def on_url_submit(e):
        await on_download_click(e)

    url_input.on_submit = on_url_submit
    grant_access_btn = ft.OutlinedButton(
        "Grant Storage Access",
        on_click=request_storage_access,
        visible=False,
        icon=ft.Icons.FOLDER_OPEN,
        expand=True,
    )

    # ── HOME VIEW ─────────────────────────────────────────────────────────────
    # Flat layout — no card, just the input form centred on the screen.
    home_view = ft.Container(
        content=ft.Column(
            controls=[
                url_input,
                download_btn,
                grant_access_btn,
                progress_bar,
                status_text,
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        padding=ft.Padding(left=24, right=24, top=24, bottom=24),
        expand=True,
    )
    # ------------------ TAB 2: DOWNLOADS STORAGE LISTVIEW ------------------
    downloads_list_view = ft.ListView(expand=True, spacing=10, padding=20)
    
    # 🌟 FIXED: Create player control inside a permanent main widget tree node
    video_player_control = ftv.Video(expand=True, autoplay=True)
    player_title = ft.Text(
        value="",
        weight=ft.FontWeight.BOLD,
        size=16,
        expand=True,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    async def close_player(e):
        # IMPORTANT: pause() MUST be called while video_player_control is still
        # in the widget tree. If we call page.update() first (swapping the content),
        # Flet deregisters the control and the pause() invoke-method response comes
        # back to an unknown control ID → RuntimeError "Control with ID X is not registered".
        try:
            await video_player_control.pause()
        except Exception:
            pass
        # Now it's safe to swap the view — the control is paused and any pending
        # round-trips have completed before we remove it from the tree.
        main_container.content = library_view
        main_container.alignment = None  # library also relies on an expand=True chain
        page.update()

    # NOTE: on_complete is intentionally NOT set here.
    # Setting on_complete = close_player caused the player view to auto-close
    # the moment a new playlist was assigned, because media_kit fires the
    # "complete" event when the previous session ends during playlist replacement.
    # The user closes the player manually with the ✕ button.

    # 🌟 FIXED: Created an explicit Full-Screen Player interface view layout
    player_view = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        player_title,                    # expand=True truncates long titles
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            on_click=close_player,
                            icon_color=ft.Colors.RED,
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # No border_radius here — rounded corners clip the flet_video
                # controls overlay (progress bar, seek time) at the bottom edge.
                ft.Container(
                    content=video_player_control,
                    expand=True,
                    bgcolor=ft.Colors.BLACK,
                )
            ],
            expand=True
        ),
        padding=ft.Padding(left=10, right=10, top=8, bottom=0),
        expand=True
    )

    def play_video(file_name):
        full_path = os.path.join(download_dir, file_name)
        player_title.value = file_name
        
        # Link the file to the playlist
        video_player_control.playlist = [ftv.VideoMedia(full_path)]
        
        # 🌟 FIXED: Dynamically inject the full player screen over the container context node
        main_container.content = player_view
        # IMPORTANT: main_container.alignment=CENTER (used to center the Home card)
        # wraps its child in an Align widget, which gives the child *loose*
        # constraints and collapses any expand=True chain underneath it to
        # zero size. That's why the video was blank but audio still played.
        # Clear it whenever we're not showing the Home view.
        main_container.alignment = None
        page.update()
        video_player_control.update()

    def delete_file(file_name):
        full_path = os.path.join(download_dir, file_name)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                page.overlay.append(ft.SnackBar(ft.Text(f"Deleted from device: {file_name}"), open=True))
            else:
                page.overlay.append(ft.SnackBar(ft.Text("File already removed from device."), open=True))
            refresh_downloads_list()
        except Exception as ex:
            page.overlay.append(ft.SnackBar(ft.Text(f"Permission Error: {str(ex)}"), open=True))
            page.update()

    def refresh_downloads_list():
        downloads_list_view.controls.clear()
        meta = load_metadata()
        try:
            files = [
                f for f in os.listdir(download_dir)
                if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))
            ]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)

            if not files:
                downloads_list_view.controls.append(
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(ft.Icons.VIDEO_LIBRARY_OUTLINED, size=48, color=ft.Colors.GREY_400),
                                ft.Text("No downloads yet", color=ft.Colors.GREY, size=14),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                        alignment=ft.Alignment(0, 0),
                        expand=True,
                        padding=40,
                    )
                )
            else:
                for file_name in files:
                    info      = meta.get(file_name, {})
                    platform  = info.get('platform', 'Video')
                    date_str  = info.get('date', '')
                    thumb_color = _PLATFORM_COLOR.get(platform, ft.Colors.BLUE_700)
                    chip_color  = _PLATFORM_CHIP_COLOR.get(platform, ft.Colors.BLUE_100)

                    # ── Thumbnail placeholder ─────────────────────────────────
                    thumb = ft.Container(
                        width=72,
                        height=72,
                        bgcolor=thumb_color,
                        border_radius=8,
                        content=ft.Icon(
                            ft.Icons.PLAY_CIRCLE_FILL_ROUNDED,
                            color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
                            size=32,
                        ),
                        alignment=ft.Alignment(0, 0),
                    )

                    # ── Platform chip ─────────────────────────────────────────
                    chip = ft.Container(
                        content=ft.Text(
                            platform,
                            size=10,
                            weight=ft.FontWeight.W_600,
                            color=thumb_color,
                        ),
                        bgcolor=chip_color,
                        border_radius=20,
                        padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                    )

                    # ── File size ─────────────────────────────────────────────
                    try:
                        size_mb = os.path.getsize(os.path.join(download_dir, file_name)) / (1024 * 1024)
                        size_str = f"{size_mb:.1f} MB"
                    except Exception:
                        size_str = ""

                    # ── Info column ───────────────────────────────────────────
                    name_without_ext = os.path.splitext(file_name)[0]
                    info_col = ft.Column(
                        controls=[
                            ft.Text(
                                name_without_ext,
                                size=13,
                                weight=ft.FontWeight.W_600,
                                max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Row(
                                controls=[
                                    chip,
                                    ft.Text(size_str, size=11, color=ft.Colors.GREY_500),
                                    ft.Text(date_str, size=11, color=ft.Colors.GREY_500),
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    )

                    card = ft.Card(
                        elevation=2,
                        content=ft.Container(
                            content=ft.Row(
                                controls=[
                                    thumb,
                                    info_col,
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=ft.Colors.RED_400,
                                        tooltip="Delete",
                                        on_click=lambda e, fn=file_name: delete_file(fn),
                                    ),
                                ],
                                spacing=12,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            padding=ft.Padding(left=12, right=4, top=10, bottom=10),
                            on_click=lambda e, fn=file_name: play_video(fn),
                            ink=True,
                        ),
                        margin=ft.Margin(left=8, right=8, top=4, bottom=4),
                    )
                    downloads_list_view.controls.append(card)

        except Exception as e:
            downloads_list_view.controls.append(
                ft.Text(f"Failed to index files: {str(e)}", color=ft.Colors.RED)
            )

        page.update()

    library_view = ft.Column(
        controls=[
            downloads_list_view
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True
    )

    # ------------------ CORE APPLICATION ROUTER SETUP ------------------
    main_container = ft.Container(
        content=home_view,
        expand=True,
    )

    async def on_navigation_change(e):
        selected_index = e.control.selected_index
        if selected_index == 0:
            main_container.content = home_view
            main_container.alignment = None
            page.update()
            try:
                await video_player_control.pause()
            except Exception:
                pass
        elif selected_index == 1:
            refresh_downloads_list()
            main_container.content = library_view
            main_container.alignment = None
            page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_navigation_change,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
            ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Downloads"),
        ]
    )

    page.add(ft.SafeArea(content=main_container, expand=True))

    # Check storage permission AFTER the UI is visible so the user sees
    # the home screen immediately on startup (not a blank screen).
    async def check_permission_on_start():
        # Pre-warm heavy modules in a background thread so first download is instant.
        # Python caches imports in sys.modules; once loaded here they cost nothing
        # when download_video calls them later.
        def _preload():
            try:
                import requests  # noqa
                from yt_dlp import YoutubeDL  # noqa
            except Exception:
                pass
        threading.Thread(target=_preload, daemon=True).start()

        if is_android and not await has_storage_access():
            grant_access_btn.visible = True
            status_text.value = "Storage access needed — tap 'Grant Storage Access' below."
            page.update()

    page.run_task(check_permission_on_start)


ft.run(main)