import flet as ft
from typing import Optional, Any
import os

_ANDROID_STORAGE_ROOT = "/storage/emulated/0"


@ft.control("MediaScanner")
class MediaScanner(ft.Service):
    """
    A Flet Service that triggers Android's native MediaScannerConnection
    via a native Kotlin plugin (FletMediaScannerPlugin).

    Add to page.services once at startup. Then call scan_media(path) from
    anywhere — it is safe to call from async context on the main event loop.
    """
    on_scanned: Optional[ft.EventHandler[Any]] = None

    def _is_android(self) -> bool:
        """
        Detect Android reliably using filesystem, not page.platform.
        page.platform can be wrong before the Flutter engine fully initialises.
        """
        return os.path.exists(_ANDROID_STORAGE_ROOT)

    async def scan_media(self, file_path: str) -> bool:
        """
        Scan a single media file so it appears immediately in Gallery/Photos.
        Returns True if the native scanner reported success.
        """
        if not self._is_android():
            return False
        if not file_path or not os.path.exists(file_path):
            print(f"[MediaScanner] scan_media: file does not exist: {file_path}")
            return False
        try:
            result = await self._invoke_method(
                "scan_media",
                {"path": file_path},
                timeout=15.0,
            )
            success = result == "true"
            print(f"[MediaScanner] scan_media: {file_path} -> result={result} success={success}")
            return success
        except Exception as e:
            print(f"[MediaScanner] scan_media error: {file_path}: {e}")
            return False
