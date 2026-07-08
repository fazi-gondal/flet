# MediaStore Save With `media_scanner` Fallback

## Current Approach

Vidsaver targets Android 13+ with a permissionless media save flow:

1. `yt-dlp` downloads videos into app-private staging storage.
2. The local `flet-media-scanner` service publishes finished videos through Android `MediaStore.Video.Media`.
3. Android places the public copy under `Movies/Vidsaver`.
4. The app stores returned metadata, including `content_uri`, in `src/metadata.json`.

This replaces the older direct public-folder write plus scan approach.

## Extension API

The local extension package remains named `flet-media-scanner` for now.

```python
scanner = fms.MediaScanner()
page.services.append(scanner)

result = await scanner.save_video(
    file_path="/private/staging/video.mp4",
    file_name="video.mp4",
    album="Vidsaver",
)
```

`scan_media(path)` remains available only for legacy files that already exist in
public storage and need Gallery indexing. New downloads should not call it.

## Permissions

The normal download flow needs no storage or media permission dialogs.

```toml
[tool.flet.android.permission]
"android.permission.INTERNET" = true
```

Do not add broad storage permissions for the core flow. Add Android's video
read media permission only if the app later needs to browse or import videos
created by other apps.

## Removed Workarounds

The app no longer uses:

- PyJNIus
- shell `cmd media scan`
- Android media scan broadcasts
- `MediaScannerConnection.scanFile()` for new downloads
- broad storage permission requests
