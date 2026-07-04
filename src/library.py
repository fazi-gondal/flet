"""
library.py — Downloads library view: list view + card builder.
Receives callbacks for play / delete so it has no knowledge of
the player or router.
"""

import os
import flet as ft
from downloader import PLATFORM_COLOR, PLATFORM_CHIP_COLOR, load_metadata


def build_video_card(file_name: str, download_dir: str, meta: dict,
                     on_play, on_delete) -> ft.Card:
    """Return a styled Card for one video file."""
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


def build_library_view(download_dir: str, metadata_path: str,
                        on_play, on_delete, page: ft.Page):
    """
    Return (library_column, list_view, refresh_fn).
    refresh_fn() re-populates the list from disk and calls page.update().
    """
    list_view = ft.ListView(expand=True, spacing=0, padding=0)

    def refresh():
        list_view.controls.clear()
        meta = load_metadata(metadata_path)
        try:
            files = [
                f for f in os.listdir(download_dir)
                if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))
            ]
            files.sort(
                key=lambda x: os.path.getmtime(os.path.join(download_dir, x)),
                reverse=True,
            )

            if not files:
                list_view.controls.append(
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
                    list_view.controls.append(
                        build_video_card(file_name, download_dir, meta, on_play, on_delete)
                    )
        except Exception as exc:
            list_view.controls.append(
                ft.Text(f"Failed to index files: {exc}", color=ft.Colors.RED)
            )

        page.update()

    library_col = ft.Column(
        controls=[list_view],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
    )

    return library_col, list_view, refresh
