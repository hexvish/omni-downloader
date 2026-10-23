package com.hexvish.omnidownloader.util

import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.webkit.MimeTypeMap
import androidx.core.content.FileProvider
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream

object MediaStoreHelper {

    fun getMimeType(file: File): String {
        val extension = file.extension.lowercase()
        return when (extension) {
            "mp3" -> "audio/mpeg"
            "m4a" -> "audio/mp4"
            "flac" -> "audio/flac"
            "wav" -> "audio/wav"
            "opus" -> "audio/opus"
            "mp4" -> "video/mp4"
            "mkv" -> "video/x-matroska"
            "webm" -> "video/webm"
            "zip" -> "application/zip"
            else -> MimeTypeMap.getSingleton().getMimeTypeFromExtension(extension) ?: "*/*"
        }
    }

    /**
     * Saves downloaded file to Android public MediaStore (Music, Movies, or Downloads)
     * so it appears instantly in Samsung Music, YouTube Music, Google Files, and Gallery.
     */
    fun saveToPublicStorage(context: Context, sourceFile: File): Uri? {
        if (!sourceFile.exists()) return null

        val filename = sourceFile.name
        val mimeType = getMimeType(sourceFile)
        val isAudio = mimeType.startsWith("audio")
        val isVideo = mimeType.startsWith("video")

        val collectionUri: Uri = when {
            isAudio -> MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
            isVideo -> MediaStore.Video.Media.EXTERNAL_CONTENT_URI
            else -> {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    MediaStore.Downloads.EXTERNAL_CONTENT_URI
                } else {
                    MediaStore.Files.getContentUri("external")
                }
            }
        }

        val relativePath = when {
            isAudio -> "${Environment.DIRECTORY_MUSIC}/Omni Downloader"
            isVideo -> "${Environment.DIRECTORY_MOVIES}/Omni Downloader"
            else -> "${Environment.DIRECTORY_DOWNLOADS}/Omni Downloader"
        }

        val contentValues = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, filename)
            put(MediaStore.MediaColumns.MIME_TYPE, mimeType)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.MediaColumns.RELATIVE_PATH, relativePath)
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
        }

        val resolver = context.contentResolver
        val itemUri = resolver.insert(collectionUri, contentValues) ?: return null

        try {
            resolver.openOutputStream(itemUri)?.use { out ->
                FileInputStream(sourceFile).use { input ->
                    input.copyTo(out)
                }
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                contentValues.clear()
                contentValues.put(MediaStore.MediaColumns.IS_PENDING, 0)
                resolver.update(itemUri, contentValues, null, null)
            }
            return itemUri
        } catch (e: Exception) {
            e.printStackTrace()
            return null
        }
    }

    /**
     * Saves a source file into a user-selected destination URI (via SAF CreateDocument picker).
     */
    fun copyToUri(context: Context, sourceFile: File, destinationUri: Uri): Boolean {
        return try {
            context.contentResolver.openOutputStream(destinationUri)?.use { outStream ->
                FileInputStream(sourceFile).use { inStream ->
                    inStream.copyTo(outStream)
                }
            }
            true
        } catch (e: Exception) {
            e.printStackTrace()
            false
        }
    }

    /**
     * Launches the default system audio/video player to play the downloaded file immediately.
     */
    fun openFile(context: Context, uri: Uri, mimeType: String) {
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, mimeType)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        try {
            context.startActivity(Intent.createChooser(intent, "Open with").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            })
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    /**
     * Launches the system share sheet (WhatsApp, Telegram, Drive, etc.).
     */
    fun shareFile(context: Context, uri: Uri, mimeType: String, title: String) {
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = mimeType
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_SUBJECT, title)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            context.startActivity(Intent.createChooser(intent, "Share media via").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            })
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    /**
     * Obtains a secure content URI using FileProvider.
     */
    fun getFileUri(context: Context, file: File): Uri {
        return try {
            FileProvider.getUriForFile(context, "com.hexvish.omnidownloader.fileprovider", file)
        } catch (e: Exception) {
            Uri.fromFile(file)
        }
    }
}

