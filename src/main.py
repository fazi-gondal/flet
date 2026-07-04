"""
main.py — App entry point and navigation router.
Imports of heavy modules (flet_video, yt-dlp, requests) are kept out of
this file so the Python interpreter has very little to load before the
splash screen can appear.
"""

import os
import threading
import flet as ft
import flet_permission_handler as fph

from downloader import (
    detect_platform, load_metadata, save_metadata,
    resolve_short_url, run_download, preload_heavy_modules, scan_android_media,
)
from library  import build_library_view

ANDROID_STORAGE_ROOT = "/storage/emulated/0"


async def main(page: ft.Page):
    # ── Basic page setup (fast — no heavy work yet) ────────────────────────
    page.title   = "Vidsaver"
    page.padding = 0
    page.spacing = 0
    page.safe_area = True
    page.appbar = ft.AppBar(
        title=ft.Text("Vidsaver", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.Colors.BLUE_700,
    )
    page.vertical_alignment   = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # ── Platform & storage ────────────────────────────────────────────────
    is_android = os.path.exists(ANDROID_STORAGE_ROOT)

    if is_android:
        download_dir = os.path.join(ANDROID_STORAGE_ROOT, "Movies", "VidSaver")
    else:
        try:
            sp = ft.StoragePaths(page)
            download_dir = await sp.get_downloads_directory() or "./downloads"
        except Exception:
            download_dir = (
                os.path.join(os.environ['USERPROFILE'], 'Downloads')
                if 'USERPROFILE' in os.environ else "./downloads"
            )

    os.makedirs(download_dir, exist_ok=True)
    metadata_path = os.path.join(download_dir, '.metadata.json')

    def scan_existing_downloads():
        if not is_android:
            return
        try:
            video_paths = [
                os.path.join(download_dir, file_name)
                for file_name in os.listdir(download_dir)
                if file_name.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))
            ]
            scan_android_media(video_paths)
        except Exception:
            pass

    # ── Permission handler ─────────────────────────────────────────────────
    permission_handler = fph.PermissionHandler()
    page.services.append(permission_handler)

    async def has_storage_access() -> bool:
        if not is_android:
            return True
        try:
            status = await permission_handler.get_status(fph.Permission.MANAGE_EXTERNAL_STORAGE)
            return status == fph.PermissionStatus.GRANTED
        except Exception:
            return False

    # ── Home view controls ─────────────────────────────────────────────────
    _VIDEO_DOMAINS = (
        'tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com',
        'instagram.com', 'youtube.com', 'youtu.be',
        'twitter.com', 'x.com', 'facebook.com', 'fb.com',
    )

    def _is_video_url(text: str) -> bool:
        if not text:
            return False
        t = text.strip()
        return t.startswith(('http://', 'https://')) and any(d in t for d in _VIDEO_DOMAINS)

    url_input = ft.TextField(
        label="Paste video link",
        border_radius=12,
        filled=True,
        prefix_icon=ft.Icons.LINK,
    )
    status_text  = ft.Text(value="", color=ft.Colors.BLUE_GREY, size=12)
    progress_bar = ft.ProgressBar(
        height=4, value=0.0, visible=False,
        color=ft.Colors.BLUE, bgcolor=ft.Colors.BLUE_100, border_radius=4,
    )

    # ── Clipboard auto-paste ────────────────────────────────────────────
    async def _try_paste_clipboard():
        """Read clipboard and paste into url_input if it looks like a video link."""
        try:
            clip = await ft.Clipboard().get()
            if clip and _is_video_url(clip) and clip.strip() != (url_input.value or '').strip():
                url_input.value = clip.strip()
                page.update()
        except Exception:
            pass

    async def _on_url_focus(e):
        """Auto-paste on field focus (user taps the input)."""
        if not url_input.value:
            await _try_paste_clipboard()

    url_input.on_focus = _on_url_focus

    async def _on_app_lifecycle(e):
        """Auto-paste when app resumes from background (user copied from another app)."""
        if e.state == ft.AppLifecycleState.RESUME:
            await _try_paste_clipboard()

    page.on_app_lifecycle_state_change = _on_app_lifecycle

    # ── Storage permission helpers ──────────────────────────────────────────
    async def request_storage_access() -> bool:
        """Show the system permission dialog and return True if granted."""
        if not is_android:
            return True
        try:
            await permission_handler.request(fph.Permission.MANAGE_EXTERNAL_STORAGE)
        except Exception:
            pass
        return await has_storage_access()

    # ── Download logic ─────────────────────────────────────────────────────
    def _on_progress(value):
        progress_bar.value = value

    def _on_status(msg):
        status_text.value = msg

    def _on_finish():
        progress_bar.visible = False
        refresh_downloads_list()
        page.update()

    def _on_error(msg):
        status_text.value = f"Error: {msg}"

    def _start_download(url: str):
        base_dir    = os.path.dirname(os.path.abspath(__file__))
        cookie_path = os.path.join(base_dir, 'cookies.txt')
        threading.Thread(
            target=run_download,
            args=(url, download_dir, cookie_path, metadata_path,
                  _on_status, _on_progress, _on_finish, _on_error, page),
            daemon=True,
        ).start()

    async def on_download_click(e):
        if not url_input.value:
            status_text.value = "Please enter a valid URL!"
            page.update()
            return
        # Auto-request permission if not yet granted — no button step needed
        if not await has_storage_access():
            status_text.value = "Requesting storage permission…"
            page.update()
            granted = await request_storage_access()
            if not granted:
                status_text.value = (
                    "Storage permission denied. Enable 'All files access' "
                    "for this app in Android Settings, then try again."
                )
                page.update()
                return
        progress_bar.value   = None   # indeterminate animation — shows immediately
        progress_bar.visible = True
        status_text.value    = "Fetching video…"
        page.update()
        _start_download(url_input.value)

    url_input.on_submit = on_download_click

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

    home_view = ft.Container(
        content=ft.Column(
            controls=[url_input, download_btn, progress_bar, status_text],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        padding=ft.Padding(left=24, right=24, top=24, bottom=24),
        expand=True,
    )

    # ── Player view ────────────────────────────────────────────────────────
    player_view = None
    video_control = None
    player_title = None
    close_btn = None

    async def close_player(e):
        # Pause BEFORE swapping view — the control must still be in the tree
        # when pause() is invoked, otherwise Flet raises "Control not registered".
        try:
            if video_control:
                await video_control.pause()
        except Exception:
            pass
        main_container.content   = library_view
        main_container.alignment = None
        page.update()

    def ensure_player_view():
        nonlocal player_view, video_control, player_title, close_btn
        if player_view is None:
            from player import build_player_view

            player_view, video_control, player_title, close_btn = build_player_view()
            close_btn.on_click = close_player

    def play_video(file_name: str):
        ensure_player_view()
        from player import make_video_media

        player_title.value      = file_name
        video_control.playlist  = [make_video_media(os.path.join(download_dir, file_name))]
        main_container.content  = player_view
        main_container.alignment = None
        page.update()
        video_control.update()

    # ── Library view ───────────────────────────────────────────────────────
    def delete_file(file_name: str):
        def close_dialog(e):
            confirm_delete_dialog.open = False
            page.update()

        def confirm_delete(e):
            confirm_delete_dialog.open = False
            delete_confirmed_file(file_name)

        confirm_delete_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete video?"),
            content=ft.Text(f"Are you sure you want to delete \"{file_name}\"?"),
            actions=[
                ft.TextButton("No", on_click=close_dialog),
                ft.TextButton("OK", on_click=confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(confirm_delete_dialog)
        confirm_delete_dialog.open = True
        page.update()

    def delete_confirmed_file(file_name: str):
        full_path = os.path.join(download_dir, file_name)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                page.overlay.append(
                    ft.SnackBar(ft.Text(f"Deleted: {file_name}"), open=True)
                )
            else:
                page.overlay.append(
                    ft.SnackBar(ft.Text("File already removed."), open=True)
                )
            refresh_downloads_list()
        except Exception as ex:
            page.overlay.append(
                ft.SnackBar(ft.Text(f"Permission Error: {ex}"), open=True)
            )
        page.update()

    library_view, _list_view, refresh_downloads_list = build_library_view(
        download_dir=download_dir,
        metadata_path=metadata_path,
        on_play=play_video,
        on_delete=delete_file,
        page=page,
    )

    # ── Navigation router ──────────────────────────────────────────────────
    main_container = ft.Container(content=home_view, expand=True)

    async def on_navigation_change(e):
        idx = e.control.selected_index
        if idx == 0:
            main_container.content   = home_view
            main_container.alignment = None
            page.update()
            try:
                if video_control:
                    await video_control.pause()
            except Exception:
                pass
        elif idx == 1:
            refresh_downloads_list()
            main_container.content   = library_view
            main_container.alignment = None
            page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_navigation_change,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME,     label="Home"),
            ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Downloads"),
        ],
    )

    page.add(ft.SafeArea(content=main_container, expand=True))

    # ── Post-render background tasks ───────────────────────────────────────
    async def on_start():
        # Pre-warm yt-dlp & requests in background so first download is instant
        threading.Thread(target=preload_heavy_modules, daemon=True).start()
        threading.Thread(target=scan_existing_downloads, daemon=True).start()

    page.run_task(on_start)


ft.run(main)
