package com.hexvish.omnidownloader.util

import android.app.DownloadManager
import android.content.ContentValues
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.webkit.MimeTypeMap
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File
import java.io.FileInputStream

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
            else -> MimeTypeMap.getSingleton().getMimeTypeFromExtension(extension) ?: "*/*"
        }
    }

    /**
     * Saves downloaded file to Android public MediaStore (Music or Movies)
     * so it appears instantly in Samsung Music, YouTube Music, Google Files, and Gallery.
     */
    fun saveToPublicStorage(context: Context, sourceFile: File): Uri? {
        if (!sourceFile.exists()) return null

        val filename = sourceFile.name
        val mimeType = getMimeType(sourceFile)
        val isAudio = mimeType.startsWith("audio")

        val collectionUri: Uri = if (isAudio) {
            MediaStore.Audio.Media.EXTERNAL_CONTENT_URI
        } else {
            MediaStore.Video.Media.EXTERNAL_CONTENT_URI
        }

        val relativePath = if (isAudio) {
            "${Environment.DIRECTORY_MUSIC}/Omni Downloader"
        } else {
            "${Environment.DIRECTORY_MOVIES}/Omni Downloader"
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
     * Launches the default system audio/video player to play the downloaded file immediately.
     */
    fun openFile(context: Context, uri: Uri, mimeType: String) {
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, mimeType)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        try {
            context.startActivity(Intent.createChooser(intent, "Play with").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            })
        } catch (e: Exception) {
            Toast.makeText(context, "No media player found to play this file.", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Opens the Music/Omni Downloader or Movies/Omni Downloader folder in the file manager.
     */
    fun openFolder(context: Context, isAudio: Boolean) {
        val subDir = if (isAudio) "Music/Omni Downloader" else "Movies/Omni Downloader"

        // Attempt 1: Open directory via DocumentsUI
        val intent = Intent(Intent.ACTION_VIEW).apply {
            val uri = Uri.parse("content://com.android.externalstorage.documents/document/primary:${Uri.encode(subDir)}")
            setDataAndType(uri, "vnd.android.document/directory")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        try {
            context.startActivity(intent)
        } catch (e1: Exception) {
            // Attempt 2: Open system Downloads or Files view
            try {
                val fallback = Intent(DownloadManager.ACTION_VIEW_DOWNLOADS).apply {
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(fallback)
            } catch (e2: Exception) {
                Toast.makeText(context, "Saved to Internal Storage > $subDir", Toast.LENGTH_LONG).show()
            }
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
            Toast.makeText(context, "Unable to share file.", Toast.LENGTH_SHORT).show()
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
