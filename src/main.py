"""
main.py - Vidsaver app entry point.
"""

import asyncio
import os
import tempfile

import flet as ft

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".3gp")

VIDEO_DOMAINS = (
    "tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
    "twitter.com",
    "x.com",
    "facebook.com",
    "fb.com",
)


def is_android_page(page: ft.Page) -> bool:
    platform = getattr(page, "platform", None)
    platform_value = getattr(platform, "value", platform)
    return platform == ft.PagePlatform.ANDROID or platform_value == "android"


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

    app_dir = os.path.dirname(os.path.abspath(__file__))
    metadata_path = os.path.join(app_dir, "metadata.json")
    if is_android_page(page):
        download_dir = os.path.join(tempfile.gettempdir(), "vidsaver-staging")
    else:
        download_dir = (
            os.path.join(os.environ["USERPROFILE"], "Downloads", "VidSaver")
            if "USERPROFILE" in os.environ
            else "./downloads"
        )

    os.makedirs(download_dir, exist_ok=True)
    page._download_dir = download_dir
    page._metadata_path = metadata_path
    return download_dir, metadata_path


def ensure_media_scanner(page: ft.Page):
    """Initialize the local media service on Android only."""
    if hasattr(page, "_media_scanner"):
        return page._media_scanner

    if not is_android_page(page):
        page._media_scanner = None
        page._media_scanner_error = ""
        return None

    try:
        from flet_media_scanner import MediaScanner

        scanner = MediaScanner()
        page.services.append(scanner)
        page._media_scanner = scanner
        page._media_scanner_error = ""
        page.update()
        print("[VidSaver] MediaStore service initialized")
    except Exception as e:
        page._media_scanner_error = str(e)
        print(f"[VidSaver] MediaStore service init failed: {e}")
        page._media_scanner = None

    return page._media_scanner


async def publish_download_result(page: ft.Page, download_result: dict, metadata_path: str):
    """Publish staged downloads to MediaStore on Android and update metadata."""
    from downloader import load_metadata, save_metadata

    if not download_result or not download_result.get("paths"):
        return False, "No video file was saved."

    meta = load_metadata(metadata_path)
    published = 0
    last_error = ""

    for path in download_result["paths"]:
        file_name = os.path.basename(path)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        entry = {
            "platform": download_result["platform"],
            "url": download_result["url"],
            "date": download_result["date"],
            "source_path": path,
            "size": size,
        }

        android = is_android_page(page)
        scanner = ensure_media_scanner(page) if android else None
        if android and scanner is None:
            init_error = getattr(page, "_media_scanner_error", "")
            last_error = (
                f"MediaStore service is not available: {init_error}"
                if init_error
                else "MediaStore service is not available."
            )
            continue

        if scanner is not None:
            result = await scanner.save_video(path, file_name=file_name, album="Vidsaver")
            if not result.success:
                last_error = result.error or "MediaStore save failed."
                continue

            display_name = result.display_name or file_name
            entry.update(
                {
                    "content_uri": result.content_uri,
                    "display_name": display_name,
                    "mime_type": result.mime_type,
                    "relative_path": result.relative_path,
                    "size": result.size or size,
                }
            )
            meta[display_name] = entry
        else:
            meta[file_name] = entry

        published += 1

    if published:
        save_metadata(metadata_path, meta)
        return True, ""
    return False, last_error or "Unable to publish video to Gallery."


@ft.component
def HomeView(
    status_text_val: str,
    progress_val: float | None,
    progress_visible: bool,
    download_disabled: bool,
    on_download_click,
    page: ft.Page,
):
    """Declarative home view component for downloading videos."""
    url, set_url = ft.use_state("")

    async def try_paste_clipboard():
        try:
            clip = await ft.Clipboard().get()
            if clip and is_video_url(clip) and clip.strip() != url.strip():
                set_url(clip.strip())
        except Exception:
            pass

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
                    "Vidsaver made with love by Fazi Gondal",
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
    """Root declarative App component."""
    active_tab, set_active_tab = ft.use_state(0)
    playing_file, set_playing_file = ft.use_state(None)

    status_text, set_status_text = ft.use_state("")
    progress_val, set_progress_val = ft.use_state(None)
    progress_visible, set_progress_visible = ft.use_state(False)
    download_disabled, set_download_disabled = ft.use_state(False)
    download_completed, set_download_completed = ft.use_state(False)

    refresh_trigger, set_refresh_trigger = ft.use_state(0)
    scroll_offset, set_scroll_offset = ft.use_state(0)

    def sync_page_ui():
        if page.appbar:
            page.appbar.visible = not playing_file

        if playing_file:
            page.navigation_bar = None
        else:
            page.navigation_bar = ft.NavigationBar(
                bgcolor=ft.Colors.WHITE_10,
                selected_index=active_tab,
                on_change=lambda e: set_active_tab(e.control.selected_index),
                destinations=[
                    ft.NavigationBarDestination(icon=ft.Icons.HOME_FILLED, label="Home"),
                    ft.NavigationBarDestination(
                        icon=ft.Icons.FILE_DOWNLOAD_ROUNDED,
                        label="Downloads",
                    ),
                ],
            )
        page.update()

    ft.use_effect(sync_page_ui, dependencies=[playing_file, active_tab])

    def set_download_busy(message: str):
        set_download_completed(False)
        set_progress_val(None)
        set_progress_visible(True)
        set_download_disabled(True)
        set_status_text(message)

    def finish_download(is_done: bool):
        set_progress_visible(False)
        set_download_disabled(False)
        set_refresh_trigger(lambda prev: prev + 1)
        if is_done:
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

    def start_download(url: str):
        if not url:
            set_status_text("Please enter a valid URL!")
            return

        if not is_video_url(url):
            set_status_text("Not a recognized or supported video link.")
            return

        async def download_flow():
            set_download_busy("Fetching video...")

            directory, metadata = ensure_storage_paths(page)
            cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")
            from downloader import run_download

            had_error = [False]

            def on_status(message):
                if message.startswith("Downloading:"):
                    page.loop.call_soon_threadsafe(lambda: set_status_text("Downloading video..."))
                else:
                    page.loop.call_soon_threadsafe(lambda: set_status_text(message))

            def on_progress(value):
                page.loop.call_soon_threadsafe(lambda: set_progress_val(value))

            def on_error(message):
                had_error[0] = True
                page.loop.call_soon_threadsafe(lambda: set_download_completed(False))
                page.loop.call_soon_threadsafe(lambda: set_status_text(f"Error: {message}"))

            def on_finish():
                pass

            class DummyPage:
                def update(self):
                    pass

            download_result = await asyncio.to_thread(
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
                None,
            )

            is_done = False
            if download_result and not had_error[0]:
                try:
                    ok, error = await publish_download_result(page, download_result, metadata)
                except Exception as exc:
                    ok, error = False, str(exc)
                if ok:
                    set_download_completed(True)
                    set_status_text("Video saved to Gallery.")
                    is_done = True
                else:
                    set_download_completed(False)
                    set_status_text(f"Error: {error}")

            finish_download(is_done)

        asyncio.create_task(download_flow())

    if playing_file:
        from downloader import load_metadata
        from player import PlayerView

        _, metadata = ensure_storage_paths(page)
        info = load_metadata(metadata).get(playing_file, {})
        playable_path = (
            info.get("source_path")
            or info.get("file_path")
            or info.get("content_uri")
            or playing_file
        )
        content_view = PlayerView(
            file_path=playable_path,
            on_close=lambda e: set_playing_file(None),
        )
    elif active_tab == 0:
        content_view = HomeView(
            status_text_val=status_text,
            progress_val=progress_val,
            progress_visible=progress_visible,
            download_disabled=download_disabled,
            on_download_click=start_download,
            page=page,
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
            refresh_trigger=refresh_trigger,
        )

    return ft.SafeArea(content=content_view, expand=True)


async def main(page: ft.Page):
    page._event_loop = asyncio.get_running_loop()
    ensure_storage_paths(page)
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
