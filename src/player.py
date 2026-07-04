"""
player.py — Full-screen video player view builder.
flet_video is imported here so main.py doesn't need it at startup,
keeping the initial import chain lean.
"""

import flet as ft
import flet_video as ftv


def build_player_view():
    """
    Build and return the player view plus the controls that main.py needs
    to wire up callbacks and drive playback.

    Returns:
        (player_view, video_control, title_text, close_btn)
    """
    video_control = ftv.Video(expand=True, autoplay=True)

    title_text = ft.Text(
        value="",
        weight=ft.FontWeight.BOLD,
        size=16,
        expand=True,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )

    close_btn = ft.IconButton(
        icon=ft.Icons.CLOSE,
        icon_color=ft.Colors.RED,
        # on_click is wired by main.py after the view is built
    )

    player_view = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        title_text,   # expand=True keeps close_btn always visible
                        close_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                # NOTE: No border_radius — rounded corners clip the flet_video
                # controls overlay (progress bar, seek time) at the bottom edge.
                ft.Container(
                    content=video_control,
                    expand=True,
                    bgcolor=ft.Colors.BLACK,
                ),
            ],
            expand=True,
        ),
        padding=ft.Padding(left=10, right=10, top=8, bottom=0),
        expand=True,
    )

    return player_view, video_control, title_text, close_btn


def make_video_media(full_path: str):
    """Wrap a file path in a VideoMedia object."""
    return ftv.VideoMedia(full_path)
