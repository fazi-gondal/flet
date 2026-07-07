package com.example.flet_media_scanner

import android.content.Context
import android.media.MediaScannerConnection
import android.util.Log
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.MethodChannel.MethodCallHandler
import io.flutter.plugin.common.MethodChannel.Result

/**
 * FletMediaScannerPlugin
 *
 * Wraps Android's MediaScannerConnection.scanFile() so that newly downloaded
 * media files are immediately visible in the Gallery / Photos app without the
 * user having to open a File Manager to trigger an index refresh.
 */
class FletMediaScannerPlugin : FlutterPlugin, MethodCallHandler {

    private lateinit var channel: MethodChannel
    private lateinit var context: Context

    companion object {
        private const val TAG = "FletMediaScanner"
        private const val CHANNEL = "flet_media_scanner/scan"
    }

    // ── FlutterPlugin lifecycle ──────────────────────────────────────────────

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        context = binding.applicationContext
        channel = MethodChannel(binding.binaryMessenger, CHANNEL)
        channel.setMethodCallHandler(this)
        Log.d(TAG, "onAttachedToEngine: channel registered")
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        channel.setMethodCallHandler(null)
        Log.d(TAG, "onDetachedFromEngine")
    }

    // ── MethodChannel handler ────────────────────────────────────────────────

    override fun onMethodCall(call: MethodCall, result: Result) {
        Log.d(TAG, "onMethodCall: method=${call.method}")

        when (call.method) {
            "scanFile" -> {
                val path = call.argument<String>("path")
                Log.d(TAG, "scanFile: path=$path")

                if (path.isNullOrBlank()) {
                    result.error("INVALID_ARGUMENT", "path must not be null or empty", null)
                    return
                }

                try {
                    // MediaScannerConnection.scanFile() is the official Android API to
                    // notify the MediaStore that a new file exists. This is exactly what
                    // the File Manager does when it "refreshes" the media index.
                    // The callback is invoked on the main thread.
                    MediaScannerConnection.scanFile(
                        context,
                        arrayOf(path),
                        null  // mimeType: null → let Android detect it from extension
                    ) { scannedPath, uri ->
                        Log.d(TAG, "scanFile complete: path=$scannedPath uri=$uri")
                        if (uri != null) {
                            result.success("scanned")
                        } else {
                            // uri being null usually means the file wasn't found or
                            // isn't in a publicly accessible location. Still a "soft"
                            // failure — don't crash.
                            Log.w(TAG, "scanFile: uri is null for path=$scannedPath")
                            result.success("failed")
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "scanFile: exception: ${e.message}", e)
                    result.error("SCAN_ERROR", e.message, e.toString())
                }
            }

            else -> {
                Log.w(TAG, "onMethodCall: notImplemented for method=${call.method}")
                result.notImplemented()
            }
        }
    }
}
