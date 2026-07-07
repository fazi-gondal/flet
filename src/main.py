"""
main.py — Vidsaver app entry point.
Refactored to use Flet's module-level declarative component architecture.
"""

import os
import asyncio
import flet as ft

ANDROID_STORAGE_ROOT = "/storage/emulated/0"
VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".3gp")

VIDEO_DOMAINS = (
    "tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
    "instagram.com", "youtube.com", "youtu.be",
    "twitter.com", "x.com", "facebook.com", "fb.com",
)


def is_video_url(text: str) -> bool:
    if not text:
        return False
    value = text.strip()
    return value.startswith(("http://", "https://")) and any(
        domain in value for domain in VIDEO_DOMAINS
    )


def ensure_storage_paths(page: ft.Page):
    if getattr(page, "_download_dir", None):
        return page._download_dir, page._metadata_path

    is_android = os.path.exists(ANDROID_STORAGE_ROOT)
    if is_android:
        download_dir = os.path.join(ANDROID_STORAGE_ROOT, "Download", "VidSaver")
    else:
        download_dir = (
            os.path.join(os.environ["USERPROFILE"], "Downloads")
            if "USERPROFILE" in os.environ else "./downloads"
        )

    os.makedirs(download_dir, exist_ok=True)
    metadata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata.json")
    
    page._download_dir = download_dir
    page._metadata_path = metadata_path
    return download_dir, metadata_path


def ensure_permission_handler(page: ft.Page):
    if not os.path.exists(ANDROID_STORAGE_ROOT):
        return None, None
    
    if not hasattr(page, "_permission_handler"):
        import flet_permission_handler as fph
        handler = fph.PermissionHandler()
        page.services.append(handler)
        page._permission_handler = handler
        page._permission_module = fph
        page.update()
        
    return page._permission_handler, page._permission_module


def ensure_media_scanner(page: ft.Page):
    """Initialize MediaScanner extension on Android only. Idempotent."""
    if hasattr(page, "_media_scanner"):
        return page._media_scanner

    # Only initialize on Android — on other platforms page.platform may be
    # ANDROID in a release build even on desktop if the check happens too early,
    # so we use ANDROID_STORAGE_ROOT existence as a reliable guard.
    if not os.path.exists(ANDROID_STORAGE_ROOT):
        page._media_scanner = None
        return None

    try:
        from flet_media_scanner import MediaScanner
        scanner = MediaScanner()
        page.services.append(scanner)
        page._media_scanner = scanner
        page.update()
        print("[VidSaver] MediaScanner extension initialized")
    except Exception as e:
        print(f"[VidSaver] MediaScanner init failed: {e}")
        page._media_scanner = None

    return page._media_scanner



async def has_storage_access(page: ft.Page) -> bool:
    if not os.path.exists(ANDROID_STORAGE_ROOT):
        return True
    handler, fph = ensure_permission_handler(page)
    try:
        status = await handler.get_status(fph.Permission.MANAGE_EXTERNAL_STORAGE)
        return status == fph.PermissionStatus.GRANTED
    except Exception:
        return False


async def request_storage_access(page: ft.Page) -> bool:
    if not os.path.exists(ANDROID_STORAGE_ROOT):
        return True
    handler, fph = ensure_permission_handler(page)
    try:
        await handler.request(fph.Permission.MANAGE_EXTERNAL_STORAGE)
    except Exception:
        pass
    return await has_storage_access(page)


async def scan_existing_downloads(page: ft.Page):
    """Scan all existing downloaded videos into Android MediaStore on startup."""
    if not os.path.exists(ANDROID_STORAGE_ROOT):
        return
    try:
        directory, _ = ensure_storage_paths(page)
        paths = [
            os.path.join(directory, name)
            for name in os.listdir(directory)
            if name.lower().endswith(VIDEO_EXTENSIONS)
        ]
        if not paths:
            return

        print(f"[VidSaver] scan_existing_downloads: scanning {len(paths)} files")
        scanner = getattr(page, "_media_scanner", None)
        if scanner:
            for path in paths:
                try:
                    result = await scanner.scan_media(path)
                    print(f"[VidSaver] scan_existing: {path} -> {result}")
                except Exception as e:
                    print(f"[VidSaver] scan_existing error: {path}: {e}")
        else:
            print("[VidSaver] scan_existing_downloads: no scanner available")
    except Exception as e:
        print(f"[VidSaver] scan_existing_downloads error: {e}")


def schedule_media_scan_later(page: ft.Page, paths: list[str]):
    """Thread-safe: schedule a media scan from a background download thread."""
    if not os.path.exists(ANDROID_STORAGE_ROOT):
        return
    if not paths:
        return

    async def _scan_with_retry():
        scanner = getattr(page, "_media_scanner", None)
        if not scanner:
            print("[VidSaver] schedule_media_scan_later: no scanner, skipping")
            return

        # Attempt 1 — immediately after download completes
        for path in paths:
            try:
                result = await scanner.scan_media(path)
                print(f"[VidSaver] scan immediate: {path} -> {result}")
            except Exception as e:
                print(f"[VidSaver] scan immediate error: {path}: {e}")

        # Attempt 2 — after 3 seconds (file system flush may be needed)
        await asyncio.sleep(3)
        for path in paths:
            try:
                result = await scanner.scan_media(path)
                print(f"[VidSaver] scan retry@3s: {path} -> {result}")
            except Exception as e:
                print(f"[VidSaver] scan retry@3s error: {path}: {e}")

    page._loop.call_soon_threadsafe(
        lambda: page._loop.create_task(_scan_with_retry())
    )


@ft.component
def HomeView(
    status_text_val: str,
    progress_val: float | None,
    progress_visible: bool,
    download_disabled: bool,
    on_download_click,
    page: ft.Page
):
    """
    Declarative home view component for downloading videos.
    Manages local URL state and clipboard sync self-containedly.
    """
    url, set_url = ft.use_state("")

    async def try_paste_clipboard():
        try:
            clip = await ft.Clipboard().get()
            if clip and is_video_url(clip):
                if clip.strip() != url.strip():
                    set_url(clip.strip())
        except Exception:
            pass

    # Clipboard sync on resume lifecycle
    def setup_lifecycle():
        def on_lifecycle(e):
            if e.state == ft.AppLifecycleState.RESUME:
                asyncio.create_task(try_paste_clipboard())

        old_handler = page.on_app_lifecycle_state_change
        page.on_app_lifecycle_state_change = on_lifecycle
        return lambda: setattr(page, "on_app_lifecycle_state_change", old_handler)

    ft.use_effect(setup_lifecycle, dependencies=[url])

    async def on_url_focus(e):
        if not url:
            await try_paste_clipboard()

    def handle_submit(e):
        if url.strip():
            on_download_click(url.strip())

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.TextField(
                    value=url,
                    on_change=lambda e: set_url(e.control.value),
                    on_focus=lambda e: asyncio.create_task(on_url_focus(e)),
                    on_submit=handle_submit,
                    label="Paste video link",
                    border_radius=12,
                    filled=True,
                    prefix_icon=ft.Icons.LINK,
                ),
                ft.Button(
                    "Download",
                    icon=ft.Icons.DOWNLOAD_ROUNDED,
                    height=40,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, color=ft.Colors.WHITE),
                    disabled=download_disabled,
                    on_click=handle_submit,
                ),
                ft.ProgressBar(
                    height=4,
                    value=progress_val,
                    visible=progress_visible,
                    color=ft.Colors.BLUE,
                    bgcolor=ft.Colors.BLUE_100,
                    border_radius=4,
                ),
                ft.Text(value=status_text_val, color=ft.Colors.BLUE_GREY, size=12),
                ft.Container(height=40),
                ft.Text(
                    "Vidsaver made with ❤️ by Fazi Gondal",
                    size=16,
                    color=ft.Colors.BLUE_GREY,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            scroll=ft.ScrollMode.ADAPTIVE,
        ),
        padding=ft.Padding(left=24, right=24, top=24, bottom=24),
        expand=True,
    )


@ft.component
def App(page: ft.Page):
    """
    Root declarative App component.
    """
    active_tab, set_active_tab = ft.use_state(0)
    playing_file, set_playing_file = ft.use_state(None)
    
    status_text, set_status_text = ft.use_state("")
    progress_val, set_progress_val = ft.use_state(None)
    progress_visible, set_progress_visible = ft.use_state(False)
    download_disabled, set_download_disabled = ft.use_state(False)
    download_completed, set_download_completed = ft.use_state(False)
    
    refresh_trigger, set_refresh_trigger = ft.use_state(0)
    scroll_offset, set_scroll_offset = ft.use_state(0)

    # Sync Page UI (AppBar & NavigationBar) reactively
    def sync_page_ui():
        if page.appbar:
            page.appbar.visible = not playing_file
        
        if playing_file:
            page.navigation_bar = None
        else:
            page.navigation_bar = ft.NavigationBar(
                selected_index=active_tab,
                on_change=lambda e: set_active_tab(e.control.selected_index),
                destinations=[
                    ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
                    ft.NavigationBarDestination(icon=ft.Icons.DOWNLOAD, label="Downloads"),
                ],
            )
        page.update()

    ft.use_effect(sync_page_ui, dependencies=[playing_file, active_tab])

    # Scan existing files on mount
    def on_mounted_action():
        async def run_initial_scan():
            await asyncio.sleep(3)
            await scan_existing_downloads(page)
        asyncio.create_task(run_initial_scan())
        
    ft.use_effect(on_mounted_action, dependencies=[])

    # Downloader wiring
    def set_download_busy(message: str):
        set_download_completed(False)
        set_progress_val(None)
        set_progress_visible(True)
        set_download_disabled(True)
        set_status_text(message)

    def start_download(url: str):
        if not url:
            set_status_text("Please enter a valid URL!")
            return
        
        if not is_video_url(url):
            set_status_text("Not a recognized or supported video link.")
            return

        async def download_flow():
            has_access = await has_storage_access(page)
            if not has_access:
                set_status_text("Requesting storage permission...")
                granted = await request_storage_access(page)
                if not granted:
                    set_status_text(
                        "Storage permission denied. Enable 'All files access' "
                        "for this app in Android Settings, then try again."
                    )
                    return
            
            set_download_busy("Fetching video...")
            
            directory, metadata = ensure_storage_paths(page)
            cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
            from downloader import run_download

            is_done = [False]

            def on_status(message):
                if message.startswith("Downloading:"):
                    page._loop.call_soon_threadsafe(lambda: set_status_text("Downloading video..."))
                else:
                    page._loop.call_soon_threadsafe(lambda: set_status_text(message))
                if message in (
                    "Video saved and added to Gallery.",
                    "Video saved successfully.",
                    "Video saved. Gallery may update shortly.",
                ):
                    is_done[0] = True
                    page._loop.call_soon_threadsafe(lambda: set_download_completed(True))

            def on_progress(value):
                page._loop.call_soon_threadsafe(lambda: set_progress_val(value))

            def on_error(message):
                is_done[0] = False
                page._loop.call_soon_threadsafe(lambda: set_download_completed(False))
                page._loop.call_soon_threadsafe(lambda: set_status_text(f"Error: {message}"))

            def on_finish():
                page._loop.call_soon_threadsafe(lambda: set_progress_visible(False))
                page._loop.call_soon_threadsafe(lambda: set_download_disabled(False))
                page._loop.call_soon_threadsafe(lambda: set_refresh_trigger(lambda prev: prev + 1))
                if is_done[0]:
                    def show_snackbar():
                        page.overlay.append(
                            ft.SnackBar(
                                content=ft.Text("Video download complete"),
                                open=True,
                                duration=2500,
                                behavior=ft.SnackBarBehavior.FLOATING,
                                margin=ft.Margin(left=16, top=0, right=16, bottom=10),
                            )
                        )
                        page.update()
                    page._loop.call_soon_threadsafe(show_snackbar)

            # Pass a dummy page object to prevent background thread update conflicts
            class DummyPage:
                def update(self):
                    pass

            await asyncio.to_thread(
                run_download,
                url,
                directory,
                cookie_path,
                metadata,
                on_status,
                on_progress,
                on_finish,
                on_error,
                DummyPage(),
                lambda paths: schedule_media_scan_later(page, paths),
            )

        asyncio.create_task(download_flow())

    # Select view based on state
    if playing_file:
        from player import PlayerView
        directory, _ = ensure_storage_paths(page)
        full_path = os.path.join(directory, playing_file)
        content_view = PlayerView(
            file_path=full_path,
            on_close=lambda e: set_playing_file(None)
        )
    elif active_tab == 0:
        content_view = HomeView(
            status_text_val=status_text,
            progress_val=progress_val,
            progress_visible=progress_visible,
            download_disabled=download_disabled,
            on_download_click=start_download,
            page=page
        )
    else:
        from library import LibraryView
        directory, metadata = ensure_storage_paths(page)
        content_view = LibraryView(
            download_dir=directory,
            metadata_path=metadata,
            on_play=set_playing_file,
            initial_scroll=scroll_offset,
            on_scroll_change=set_scroll_offset,
            refresh_trigger=refresh_trigger
        )

    return ft.SafeArea(content=content_view, expand=True)


async def main(page: ft.Page):
    page._loop = asyncio.get_running_loop()
    
    # Pre-initialize and cache storage paths asynchronously using Flet's StoragePaths service
    is_android = os.path.exists(ANDROID_STORAGE_ROOT)
    if is_android:
        # Save directly to the public Download directory to bypass sandbox storage
        download_dir = os.path.join(ANDROID_STORAGE_ROOT, "Download", "VidSaver")
    else:
        try:
            storage_paths = ft.StoragePaths()
            downloads_dir = await storage_paths.get_downloads_directory()
            if downloads_dir:
                download_dir = os.path.join(downloads_dir, "VidSaver")
            else:
                download_dir = "./downloads"
        except Exception:
            download_dir = (
                os.path.join(os.environ["USERPROFILE"], "Downloads")
                if "USERPROFILE" in os.environ else "./downloads"
            )

    os.makedirs(download_dir, exist_ok=True)
    metadata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata.json")
    
    # Cache on page
    page._download_dir = download_dir
    page._metadata_path = metadata_path
    
    ensure_media_scanner(page)

    page.title = "Vidsaver"
    page.padding = 0
    page.spacing = 0
    page.safe_area = True
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme = ft.Theme(
        scrollbar_theme=ft.ScrollbarTheme(
            thickness=6,
            radius=4,
            interactive=True,
        )
    )
    page.navigation_bar = None
    page.appbar = ft.AppBar(
        title=ft.Text("Vidsaver", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=ft.Colors.BLUE_700,
    )

    page.render(App, page=page)


ft.run(main)
