# Vidsaver

Vidsaver is a Flet-based video downloader for saving videos from supported social/video platforms to the device. It uses `yt-dlp` for download handling and provides a simple mobile/desktop UI for pasting a link, downloading, viewing saved videos, and deleting downloads.

**Download TikTok and Instagram reels without watermark in Full HD**

## Features

- Download videos from common video URLs supported by `yt-dlp`.
- Android downloads are saved to:
  ```text
  /storage/emulated/0/Movies/VidSaver
  ```
- Saved Android videos are scanned so they can appear in Gallery and video player apps.
- Downloads list with video metadata, file size, platform chip, play action, and delete confirmation.
- Built-in video playback with `flet-video`.
- Android APK release builds target `arm64-v8a`.
- GitHub Releases attach:
  ```text
  Vidsaver-vX.Y.Z-Windows.zip
  Vidsaver-vX.Y.Z-Android-arm64-v8a.apk
  ```
### Mobile Demo

![Demo](/src/assets/demo.jpg)

### Windows Demo

![Demo](/src/assets/demo1.png)
![Demo](/src/assets/demo2.png)
![Demo](/src/assets/demo3.png)

## Tech Stack

- Python 3.10+
- Flet
- flet-video
- flet-permission-handler
- yt-dlp
- requests
- uv

## Project Structure

```text
.
|-- .github/workflows/
|   |-- all-builds.yml
|   `-- generate-android-keystore.yml
|-- src/
|   |-- assets/
|   |   |-- icon.png
|   |   `-- splash_android.png
|   |-- cookies.txt
|   |-- downloader.py
|   |-- library.py
|   |-- main.py
|   `-- player.py
|-- pyproject.toml
`-- README.md
```

## Run Locally

Install dependencies and run the app:

```bash
uv run flet run
```

Run as a web app:

```bash
uv run flet run --web
```

## Android Permissions

The app requests storage access on Android so downloads can be saved to the public Movies folder:

```toml
"android.permission.MANAGE_EXTERNAL_STORAGE" = true
"android.permission.READ_EXTERNAL_STORAGE" = true
"android.permission.WRITE_EXTERNAL_STORAGE" = true
"android.permission.INTERNET" = true
```

If permission is denied, enable "All files access" for Vidsaver in Android Settings.

## Build Locally

Android arm64 APK:

```bash
uv run flet build apk --split-per-abi --arch arm64-v8a --yes --verbose
```

Windows:

```bash
uv run flet build windows --yes --verbose
```

## GitHub Release Workflow

The main release workflow is:

```text
.github/workflows/all-builds.yml
```

It runs only when a version tag is pushed:

```bash
git tag v1.1.8
git push origin v1.1.8
```

Normal pushes to `main` do not run the heavy release build.

The workflow builds:

- Windows
- Android APK, `arm64-v8a` only

The release job refuses to publish an Android APK unless the APK filename contains:

```text
arm64-v8a
```

This prevents accidentally uploading a mislabeled `armeabi-v7a` APK.

## Android Signing

Stable Android signing is required if users should install new APK versions over old ones without uninstalling.

The release workflow expects these GitHub Actions secrets:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_PASSWORD
ANDROID_KEY_ALIAS
```

The workflow decodes the keystore and signs the APK with:

```bash
--android-signing-key-store upload-keystore.jks
--android-signing-key-store-password "$ANDROID_KEYSTORE_PASSWORD"
--android-signing-key-password "$ANDROID_KEY_PASSWORD"
--android-signing-key-alias "$ANDROID_KEY_ALIAS"
```

If these secrets are missing, Android release builds fail intentionally instead of publishing a debug-signed APK.

## Generate Android Keystore In GitHub

If you do not have Java, Android Studio, or Android tooling locally, use the manual workflow:

```text
.github/workflows/generate-android-keystore.yml
```

Steps:

1. Open GitHub Actions.
2. Run `Generate Android Keystore Secret`.
3. Keep the default alias as `vidsaver`, or enter another alias.
4. Download the `android-keystore-github-secrets` artifact.
5. Copy each value from `android-keystore-github-secrets.txt` into GitHub repository secrets:
   ```text
   ANDROID_KEYSTORE_BASE64
   ANDROID_KEYSTORE_PASSWORD
   ANDROID_KEY_PASSWORD
   ANDROID_KEY_ALIAS
   ```
6. Delete the artifact after copying the values. The workflow sets artifact retention to 1 day.

After this one-time setup, future release APKs are signed automatically with the same key.

## Install And Update Notes

- Install the `Android-arm64-v8a.apk` asset on arm64 Android devices.
- If an older version was installed from a wrong ABI, split APK, or different signing key, Android may show an install/package mismatch error.
- In that case, uninstall the old app once, then install the new signed APK.
- After stable signing is configured, future APKs should install over previous versions normally.

## Download Behavior

When a link is submitted:

1. The app shows an active progress bar immediately.
2. `yt-dlp` analyzes the URL.
3. When download progress is available, the progress bar shows percentage.
4. On Android, the saved file is scanned so Gallery/video players can detect it.

Fast downloads may finish before much percentage progress is visible.

## Cookies

`src/cookies.txt` is used by `yt-dlp` for sites that require cookies. Keep it updated if a platform starts blocking downloads or requires login/session data.

## Troubleshooting

### `ModuleNotFoundError: certifi`

Make sure the APK was built after `certifi`, `charset-normalizer`, `idna`, and `urllib3` were added to `pyproject.toml`.

### APK Installs As 32-bit

Use the release asset named:

```text
Vidsaver-vX.Y.Z-Android-arm64-v8a.apk
```

The workflow now fails if it cannot find an actual `arm64-v8a` APK.

### New Version Will Not Install Over Old Version

This is usually caused by a different signing key or a previous wrong ABI/split install. Configure stable signing secrets and uninstall the older build once if necessary.

### Video Does Not Appear In Gallery

The app saves to `Movies/VidSaver` and asks Android to scan the new file. Some Gallery apps may still take a short time to refresh their cache.

## Useful Links

- [Flet documentation](https://flet.dev/docs/)
- [Flet Android packaging](https://flet.dev/docs/publish/android/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
