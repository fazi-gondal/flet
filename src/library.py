"""
library.py - Declarative downloads library view.
"""

import asyncio
import os

import flet as ft

from downloader import PLATFORM_CHIP_COLOR, PLATFORM_COLOR, load_metadata, save_metadata

VIDEO_EXTENSIONS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".3gp")


@ft.component
def VideoCard(file_name: str, meta: dict, on_play, on_delete):
    """Styled card component representing one saved video."""
    info = meta.get(file_name, {})
    platform = info.get("platform", "Video")
    date_str = info.get("date", "")
    thumb_color = PLATFORM_COLOR.get(platform, ft.Colors.BLUE_700)
    chip_color = PLATFORM_CHIP_COLOR.get(platform, ft.Colors.BLUE_100)
    source_path = info.get("source_path") or info.get("file_path") or ""

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

    chip = ft.Container(
        content=ft.Text(platform, size=10, weight=ft.FontWeight.W_600, color=thumb_color),
        bgcolor=chip_color,
        border_radius=20,
        padding=ft.Padding(left=8, right=8, top=3, bottom=3),
    )

    size = info.get("size") or 0
    if not size and source_path:
        try:
            size = os.path.getsize(source_path)
        except Exception:
            size = 0
    size_str = f"{size / (1024 * 1024):.1f} MB" if size else ""
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

    return ft.Card(
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
                        on_click=lambda e, fn=file_name: on_delete(fn),
                    ),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=12, right=4, top=10, bottom=10),
            on_click=lambda e, fn=file_name: on_play(fn),
            ink=True,
        ),
        margin=ft.Margin(left=8, right=8, top=4, bottom=4),
    )


@ft.component
def LibraryView(
    download_dir: str,
    metadata_path: str,
    on_play,
    initial_scroll=0,
    on_scroll_change=None,
    refresh_trigger=0,
):
    """
    Declarative component for the downloads library.

    Android MediaStore saves are listed from app metadata, not by scanning a
    public directory.
    """
    files, set_files = ft.use_state([])
    meta, set_meta = ft.use_state({})
    deleting_file, set_deleting_file = ft.use_state(None)
    list_ref = ft.use_ref()

    def sort_key(item, loaded_meta):
        info = loaded_meta.get(item, {})
        source_path = info.get("source_path") or info.get("file_path") or ""
        try:
            return os.path.getmtime(source_path)
        except Exception:
            return 0

    def load_data():
        loaded_meta = load_metadata(metadata_path)
        valid_files = [
            name
            for name in loaded_meta
            if name.lower().endswith(VIDEO_EXTENSIONS)
        ]
        set_meta(loaded_meta)
        valid_files.sort(key=lambda item: sort_key(item, loaded_meta), reverse=True)
        set_files(valid_files)

    ft.use_effect(load_data, dependencies=[refresh_trigger])

    async def restore_scroll():
        if initial_scroll > 0 and list_ref.current:
            await asyncio.sleep(0.05)
            try:
                await list_ref.current.scroll_to(offset=initial_scroll, duration=0)
                list_ref.current.update()
            except Exception:
                pass

    ft.use_effect(restore_scroll, dependencies=[files])

    def confirm_delete(e):
        file_name = deleting_file
        set_deleting_file(None)
        loaded_meta = load_metadata(metadata_path)
        info = loaded_meta.pop(file_name, {})
        source_path = info.get("source_path") or info.get("file_path") or ""
        try:
            if source_path and os.path.exists(source_path):
                os.remove(source_path)
        except Exception:
            pass
        save_metadata(metadata_path, loaded_meta)
        load_data()

    ft.use_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete video?"),
            content=ft.Text(f'Are you sure you want to delete "{deleting_file}"?'),
            actions=[
                ft.TextButton("No", on_click=lambda _: set_deleting_file(None)),
                ft.TextButton("OK", on_click=confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        if deleting_file
        else None
    )

    list_controls = []
    if not files:
        list_controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            ft.Icons.VIDEO_LIBRARY_OUTLINED,
                            size=48,
                            color=ft.Colors.GREY_400,
                        ),
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
            list_controls.append(
                VideoCard(
                    file_name=file_name,
                    meta=meta,
                    on_play=on_play,
                    on_delete=set_deleting_file,
                )
            )

    return ft.Column(
        controls=[
            ft.ListView(
                ref=list_ref,
                controls=list_controls,
                expand=True,
                spacing=0,
                padding=0,
                on_scroll=lambda e: on_scroll_change(e.pixels) if on_scroll_change else None,
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )
