"""
App entry point.

Keep startup lean: render the Home view before touching storage,
permissions, downloads, the library, or video playback.
"""

import os
import threading

import flet as ft


ANDROID_STORAGE_ROOT = "/storage/emulated/0"
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".3gp")


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
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    is_android = os.path.exists(ANDROID_STORAGE_ROOT)
    download_dir = None
    metadata_path = None
    permission_handler = None
    permission_module = None
    library_view = None
    refresh_downloads_list = None
    player_view = None
    video_control = None
    player_title = None
    close_btn = None

    video_domains = (
        "tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
        "instagram.com", "youtube.com", "youtu.be",
        "twitter.com", "x.com", "facebook.com", "fb.com",
    )

    def is_video_url(text: str) -> bool:
        if not text:
            return False
        value = text.strip()
        return value.startswith(("http://", "https://")) and any(
            domain in value for domain in video_domains
        )

    def ensure_storage_paths():
        nonlocal download_dir, metadata_path
        if download_dir:
            return download_dir, metadata_path

        if is_android:
            download_dir = os.path.join(ANDROID_STORAGE_ROOT, "Movies", "VidSaver")
        else:
            download_dir = (
                os.path.join(os.environ["USERPROFILE"], "Downloads")
                if "USERPROFILE" in os.environ else "./downloads"
            )

        os.makedirs(download_dir, exist_ok=True)
        metadata_path = os.path.join(download_dir, ".metadata.json")
        return download_dir, metadata_path

    def ensure_permission_handler():
        nonlocal permission_handler, permission_module
        if not is_android:
            return None, None
        if permission_handler is None:
            import flet_permission_handler as fph

            permission_module = fph
            permission_handler = fph.PermissionHandler()
            page.services.append(permission_handler)
            page.update()
        return permission_handler, permission_module

    async def has_storage_access() -> bool:
        if not is_android:
            return True
        handler, fph = ensure_permission_handler()
        try:
            status = await handler.get_status(fph.Permission.MANAGE_EXTERNAL_STORAGE)
            return status == fph.PermissionStatus.GRANTED
        except Exception:
            return False

    async def request_storage_access() -> bool:
        if not is_android:
            return True
        handler, fph = ensure_permission_handler()
        try:
            await handler.request(fph.Permission.MANAGE_EXTERNAL_STORAGE)
        except Exception:
            pass
        return await has_storage_access()

    def scan_existing_downloads():
        if not is_android:
            return
        try:
            directory, _ = ensure_storage_paths()
            paths = [
                os.path.join(directory, name)
                for name in os.listdir(directory)
                if name.lower().endswith(VIDEO_EXTENSIONS)
            ]
            from downloader import scan_android_media

            scan_android_media(paths)
        except Exception:
            pass

    url_input = ft.TextField(
        label="Paste video link",
        border_radius=12,
        filled=True,
        prefix_icon=ft.Icons.LINK,
    )
    status_text = ft.Text(value="", color=ft.Colors.BLUE_GREY, size=12)
    progress_bar = ft.ProgressBar(
        height=4,
        value=None,
        visible=False,
        color=ft.Colors.BLUE,
        bgcolor=ft.Colors.BLUE_100,
        border_radius=4,
    )

    async def try_paste_clipboard():
        try:
            clip = await ft.Clipboard().get()
            if clip and is_video_url(clip) and clip.strip() != (url_input.value or "").strip():
                url_input.value = clip.strip()
                page.update()
        except Exception:
            pass

    async def on_url_focus(e):
        if not url_input.value:
            await try_paste_clipboard()

    async def on_app_lifecycle(e):
        if e.state == ft.AppLifecycleState.RESUME:
            await try_paste_clipboard()

    def set_download_busy(message: str):
        progress_bar.value = None
        progress_bar.visible = True
        status_text.value = message
        page.update()

    def on_progress(value):
        progress_bar.value = value

    def on_status(message):
        if message.startswith("Downloading:"):
            status_text.value = f"Downloading video... {int((progress_bar.value or 0) * 100)}%"
        else:
            status_text.value = message

    def on_finish():
        progress_bar.visible = False
        if refresh_downloads_list:
            refresh_downloads_list()
        page.update()

    def on_error(message):
        status_text.value = f"Error: {message}"

    def start_download(url: str):
        directory, metadata = ensure_storage_paths()
        cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
        from downloader import run_download

        threading.Thread(
            target=run_download,
            args=(
                url,
                directory,
                cookie_path,
                metadata,
                on_status,
                on_progress,
                on_finish,
                on_error,
                page,
            ),
            daemon=True,
        ).start()

    async def on_download_click(e):
        url = (url_input.value or "").strip()
        if not url:
            status_text.value = "Please enter a valid URL!"
            page.update()
            return

        if not await has_storage_access():
            status_text.value = "Requesting storage permission..."
            page.update()
            granted = await request_storage_access()
            if not granted:
                status_text.value = (
                    "Storage permission denied. Enable 'All files access' "
                    "for this app in Android Settings, then try again."
                )
                page.update()
                return

        set_download_busy("Fetching video...")
        start_download(url)

    download_btn = ft.Button(
        "Download",
        icon=ft.Icons.DOWNLOAD_ROUNDED,
        height=40,
        on_click=on_download_click,
        style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
    )

    url_input.on_focus = on_url_focus
    url_input.on_submit = on_download_click
    page.on_app_lifecycle_state_change = on_app_lifecycle

    home_view = ft.Container(
        content=ft.Column(
            controls=[url_input, download_btn, progress_bar, status_text],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        ),
        padding=ft.Padding(left=24, right=24, top=24, bottom=24),
        expand=True,
    )

    main_container = ft.Container(content=home_view, expand=True)

    def ensure_library_view():
        nonlocal library_view, refresh_downloads_list
        if library_view is None:
            directory, metadata = ensure_storage_paths()
            from library import build_library_view

            library_view, _, refresh_downloads_list = build_library_view(
                download_dir=directory,
                metadata_path=metadata,
                on_play=play_video,
                on_delete=delete_file,
                page=page,
            )
        return library_view

    async def close_player(e):
        try:
            if video_control:
                await video_control.pause()
        except Exception:
            pass
        main_container.content = ensure_library_view()
        main_container.alignment = None
        page.update()

    def ensure_player_view():
        nonlocal player_view, video_control, player_title, close_btn
        if player_view is None:
            from player import build_player_view

            player_view, video_control, player_title, close_btn = build_player_view()
            close_btn.on_click = close_player

    def play_video(file_name: str):
        nonlocal player_title, video_control, player_view
        ensure_player_view()
        directory, _ = ensure_storage_paths()
        from player import make_video_media

        player_title.value = file_name
        video_control.playlist = [make_video_media(os.path.join(directory, file_name))]
        main_container.content = player_view
        main_container.alignment = None
        page.update()
        video_control.update()

    def delete_file(file_name: str):
        def close_dialog(e):
            confirm_dialog.open = False
            page.update()

        def confirm_delete(e):
            confirm_dialog.open = False
            delete_confirmed_file(file_name)

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete video?"),
            content=ft.Text(f'Are you sure you want to delete "{file_name}"?'),
            actions=[
                ft.TextButton("No", on_click=close_dialog),
                ft.TextButton("OK", on_click=confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(confirm_dialog)
        confirm_dialog.open = True
        page.update()

    def delete_confirmed_file(file_name: str):
        directory, _ = ensure_storage_paths()
        full_path = os.path.join(directory, file_name)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
                page.overlay.append(ft.SnackBar(ft.Text(f"Deleted: {file_name}"), open=True))
            else:
                page.overlay.append(ft.SnackBar(ft.Text("File already removed."), open=True))
            if refresh_downloads_list:
                refresh_downloads_list()
        except Exception as ex:
            page.overlay.append(ft.SnackBar(ft.Text(f"Permission Error: {ex}"), open=True))
        page.update()

    async def on_navigation_change(e):
        idx = e.control.selected_index
        if idx == 0:
            main_container.content = home_view
            main_container.alignment = None
            page.update()
            try:
                if video_control:
                    await video_control.pause()
            except Exception:
                pass
        elif idx == 1:
            view = ensure_library_view()
            if refresh_downloads_list:
                refresh_downloads_list()
            main_container.content = view
            main_container.alignment = None
            page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_navigation_change,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
            ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Downloads"),
        ],
    )

    page.add(ft.SafeArea(content=main_container, expand=True))

    async def on_start():
        threading.Thread(target=scan_existing_downloads, daemon=True).start()

    page.run_task(on_start)


ft.run(main)
