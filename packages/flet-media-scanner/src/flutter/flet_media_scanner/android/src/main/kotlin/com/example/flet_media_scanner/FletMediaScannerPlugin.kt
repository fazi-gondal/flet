package com.example.flet_media_scanner

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.MethodChannel.MethodCallHandler
import io.flutter.plugin.common.MethodChannel.Result
import java.io.File
import java.io.FileInputStream
import java.net.URLConnection

class FletMediaScannerPlugin : FlutterPlugin, MethodCallHandler {
    private lateinit var channel: MethodChannel
    private lateinit var context: Context

    companion object {
        private const val TAG = "FletMediaScanner"
        private const val CHANNEL = "flet_media_scanner/scan"
    }

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

    override fun onMethodCall(call: MethodCall, result: Result) {
        when (call.method) {
            "saveVideo" -> saveVideo(call, result)
            else -> result.notImplemented()
        }
    }

    private fun saveVideo(call: MethodCall, result: Result) {
        val path = call.argument<String>("path")
        val requestedFileName = call.argument<String>("fileName")
        val album = call.argument<String>("album")
            ?.trim()
            ?.trim('/')
            ?.takeIf { it.isNotBlank() }
            ?: "Vidsaver"

        if (path.isNullOrBlank()) {
            result.error("INVALID_ARGUMENT", "path must not be null or empty", null)
            return
        }

        val source = File(path)
        if (!source.isFile) {
            result.error("FILE_NOT_FOUND", "source file does not exist: $path", null)
            return
        }

        val displayName = requestedFileName
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?: source.name
        val mimeType = URLConnection.guessContentTypeFromName(displayName) ?: "video/mp4"
        val relativePath = "${Environment.DIRECTORY_MOVIES}/$album"
        val resolver = context.contentResolver
        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        } else {
            MediaStore.Video.Media.EXTERNAL_CONTENT_URI
        }

        var uri: Uri? = null
        try {
            val values = ContentValues().apply {
                put(MediaStore.Video.Media.DISPLAY_NAME, displayName)
                put(MediaStore.Video.Media.MIME_TYPE, mimeType)
                put(MediaStore.Video.Media.DATE_ADDED, System.currentTimeMillis() / 1000)
                put(MediaStore.Video.Media.DATE_MODIFIED, source.lastModified() / 1000)
                put(MediaStore.Video.Media.SIZE, source.length())
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(MediaStore.Video.Media.RELATIVE_PATH, relativePath)
                    put(MediaStore.Video.Media.IS_PENDING, 1)
                }
            }

            uri = resolver.insert(collection, values)
                ?: throw IllegalStateException("MediaStore insert returned null")

            resolver.openOutputStream(uri)?.use { output ->
                FileInputStream(source).use { input ->
                    input.copyTo(output)
                }
            } ?: throw IllegalStateException("Unable to open MediaStore output stream")

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val publishedValues = ContentValues().apply {
                    put(MediaStore.Video.Media.IS_PENDING, 0)
                    put(MediaStore.Video.Media.SIZE, source.length())
                }
                resolver.update(uri, publishedValues, null, null)
            }

            result.success(
                mapOf(
                    "success" to true,
                    "content_uri" to uri.toString(),
                    "display_name" to displayName,
                    "mime_type" to mimeType,
                    "relative_path" to relativePath,
                    "source_path" to path,
                    "size" to source.length(),
                )
            )
        } catch (e: Exception) {
            Log.e(TAG, "saveVideo: exception: ${e.message}", e)
            uri?.let {
                try {
                    resolver.delete(it, null, null)
                } catch (deleteError: Exception) {
                    Log.w(TAG, "saveVideo: failed to delete incomplete item: $deleteError")
                }
            }
            result.error("SAVE_ERROR", e.message, e.toString())
        }
    }
}
