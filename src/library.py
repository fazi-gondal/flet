"""
library.py — Declarative downloads library view.
"""

import os
import asyncio
import flet as ft
from downloader import PLATFORM_COLOR, PLATFORM_CHIP_COLOR, load_metadata

VIDEO_EXTENSIONS = ('.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v', '.3gp')


@ft.component
def VideoCard(file_name: str, download_dir: str, meta: dict, on_play, on_delete):
    """
    Styled Card component representing one downloaded video.
    """
    info        = meta.get(file_name, {})
    platform    = info.get('platform', 'Video')
    date_str    = info.get('date', '')
    thumb_color = PLATFORM_COLOR.get(platform, ft.Colors.BLUE_700)
    chip_color  = PLATFORM_CHIP_COLOR.get(platform, ft.Colors.BLUE_100)

    # ── Thumbnail placeholder ────────────────────────────────────────────────
    thumb = ft.Container(
        width=72, height=72,
        bgcolor=thumb_color,
        border_radius=8,
        content=ft.Icon(
            ft.Icons.PLAY_CIRCLE_FILL_ROUNDED,
            color=ft.Colors.with_opacity(0.85, ft.Colors.WHITE),
            size=32,
        ),
        alignment=ft.Alignment(0, 0),
    )

    # ── Platform chip ────────────────────────────────────────────────────────
    chip = ft.Container(
        content=ft.Text(platform, size=10, weight=ft.FontWeight.W_600, color=thumb_color),
        bgcolor=chip_color,
        border_radius=20,
        padding=ft.Padding(left=8, right=8, top=3, bottom=3),
    )

    # ── File size ────────────────────────────────────────────────────────────
    try:
        size_mb  = os.path.getsize(os.path.join(download_dir, file_name)) / (1024 * 1024)
        size_str = f"{size_mb:.1f} MB"
    except Exception:
        size_str = ""

    name_without_ext = os.path.splitext(file_name)[0]

    info_col = ft.Column(
        controls=[
            ft.Text(
                name_without_ext,
                size=13, weight=ft.FontWeight.W_600,
                max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
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
def LibraryView(download_dir: str, metadata_path: str, on_play, initial_scroll=0, on_scroll_change=None, refresh_trigger=0):
    """
    Declarative component for the Downloads library.
    Automatically maintains scroll position and handles items dynamically.
    """
    files, set_files = ft.use_state([])
    meta, set_meta = ft.use_state({})
    
    # State for delete confirmation dialog
    deleting_file, set_deleting_file = ft.use_state(None)
    
    list_ref = ft.use_ref()

    def load_data():
        loaded_meta = load_metadata(metadata_path)
        set_meta(loaded_meta)
        try:
            loaded_files = [
                f for f in os.listdir(download_dir)
                if f.lower().endswith(VIDEO_EXTENSIONS)
            ]
            loaded_files.sort(
                key=lambda x: os.path.getmtime(os.path.join(download_dir, x)),
                reverse=True,
            )
            set_files(loaded_files)
        except Exception:
            pass

    # Run load_data on mount and whenever refresh_trigger increments
    ft.use_effect(load_data, dependencies=[refresh_trigger])

    # Restore scroll position once data loads
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
        
        full_path = os.path.join(download_dir, file_name)
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
            load_data()
        except Exception:
            pass

    # Render Dialog Portal declaratively
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
        ) if deleting_file else None
    )

    list_controls = []
    if not files:
        list_controls.append(
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
            list_controls.append(
                VideoCard(
                    file_name=file_name,
                    download_dir=download_dir,
                    meta=meta,
                    on_play=on_play,
                    on_delete=set_deleting_file
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
