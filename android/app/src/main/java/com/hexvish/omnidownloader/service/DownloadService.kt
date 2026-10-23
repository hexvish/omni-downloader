package com.hexvish.omnidownloader.service

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.chaquo.python.Python
import com.hexvish.omnidownloader.MainActivity
import com.hexvish.omnidownloader.OmniApplication
import com.hexvish.omnidownloader.util.MediaStoreHelper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

class DownloadService : Service() {

    companion object {
        const val ACTION_START_DOWNLOAD = "com.hexvish.omnidownloader.START_DOWNLOAD"
        const val ACTION_CANCEL_DOWNLOAD = "com.hexvish.omnidownloader.CANCEL_DOWNLOAD"

        const val EXTRA_URL = "extra_url"
        const val EXTRA_TYPE = "extra_type"
        const val EXTRA_CODEC = "extra_codec"
        const val EXTRA_BITRATE = "extra_bitrate"
        const val EXTRA_RESOLUTION = "extra_resolution"
        const val EXTRA_IS_PLAYLIST = "extra_is_playlist"
        const val EXTRA_TITLE = "extra_title"
        const val EXTRA_SELECTED_INDICES = "extra_selected_indices"

        private const val NOTIFICATION_ID = 1001
        private const val COMPLETED_NOTIFICATION_ID = 1002
    }

    private var downloadJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.Main)
    private lateinit var notificationManager: NotificationManager

    override fun onCreate() {
        super.onCreate()
        notificationManager = getSystemService(NotificationManager::class.java)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START_DOWNLOAD -> {
                val url = intent.getStringExtra(EXTRA_URL) ?: ""
                val type = intent.getStringExtra(EXTRA_TYPE) ?: "audio"
                val codec = intent.getStringExtra(EXTRA_CODEC) ?: "mp3"
                val bitrate = intent.getStringExtra(EXTRA_BITRATE) ?: "320"
                val resolution = intent.getStringExtra(EXTRA_RESOLUTION) ?: "1080p"
                val isPlaylist = intent.getBooleanExtra(EXTRA_IS_PLAYLIST, false)
                val title = intent.getStringExtra(EXTRA_TITLE) ?: "Omni Download"
                val selectedIndices = intent.getIntArrayExtra(EXTRA_SELECTED_INDICES) ?: intArrayOf()

                startForegroundWithNotification(title)
                startDownloadTask(url, type, codec, bitrate, resolution, isPlaylist, title, selectedIndices)
            }
            ACTION_CANCEL_DOWNLOAD -> {
                downloadJob?.cancel()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
        return START_NOT_STICKY
    }

    private fun startForegroundWithNotification(title: String) {
        val notification = buildOngoingNotification(title, 0, "", "Preparing download...")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun buildOngoingNotification(
        title: String,
        progress: Int,
        speed: String,
        status: String
    ): Notification {
        val openAppIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val openPendingIntent = PendingIntent.getActivity(
            this, 0, openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val cancelIntent = Intent(this, DownloadService::class.java).apply {
            action = ACTION_CANCEL_DOWNLOAD
        }
        val cancelPendingIntent = PendingIntent.getService(
            this, 1, cancelIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val textContent = if (speed.isNotBlank()) "$progress% • $speed • $status" else "$progress% • $status"

        return NotificationCompat.Builder(this, OmniApplication.DOWNLOAD_CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(textContent)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentIntent(openPendingIntent)
            .setProgress(100, progress, false)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Cancel", cancelPendingIntent)
            .build()
    }

    private fun startDownloadTask(
        url: String,
        type: String,
        codec: String,
        bitrate: String,
        resolution: String,
        isPlaylist: Boolean,
        title: String,
        selectedIndices: IntArray
    ) {
        downloadJob?.cancel()
        downloadJob = scope.launch {
            try {
                val outputDir = File(cacheDir, "omni_downloads").apply { mkdirs() }

                val listener = object : Any() {
                    // Chaquopy calls these methods dynamically
                    fun onProgress(percentage: Double, speed: String, statusText: String) {
                        val pctFloat = percentage.toFloat()
                        OmniDownloadController.updateProgress(pctFloat, speed, statusText)

                        val notif = buildOngoingNotification(title, pctFloat.toInt(), speed, statusText)
                        notificationManager.notify(NOTIFICATION_ID, notif)
                    }

                    fun onCompleted(filePath: String) {
                        // Handled upon return
                    }

                    fun onError(errorMessage: String) {
                        OmniDownloadController.onDownloadError(errorMessage)
                    }
                }

                val downloadedFilePath = withContext(Dispatchers.IO) {
                    val py = Python.getInstance()
                    val engine = py.getModule("omni_engine")
                    
                    val pySelectedIndices = if (selectedIndices.isNotEmpty()) {
                        selectedIndices.toList()
                    } else {
                        null
                    }

                    engine.callAttr(
                        "run_download",
                        url,
                        type,
                        codec,
                        bitrate,
                        resolution,
                        isPlaylist,
                        outputDir.absolutePath,
                        listener,
                        pySelectedIndices
                    ).toString()
                }

                val downloadedFile = File(downloadedFilePath)
                if (downloadedFile.exists()) {
                    // Copy to Android Public MediaStore
                    val publicUri = MediaStoreHelper.saveToPublicStorage(this@DownloadService, downloadedFile)
                    OmniDownloadController.onDownloadCompleted(downloadedFile, publicUri)
                    showCompletionNotification(downloadedFile, title)
                } else {
                    OmniDownloadController.onDownloadError("Downloaded file could not be verified on disk.")
                }

            } catch (e: Exception) {
                OmniDownloadController.onDownloadError(e.localizedMessage ?: "Download failed.")
            } finally {
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
            }
        }
    }

    private fun showCompletionNotification(file: File, title: String) {
        val openAppIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 2, openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val completionNotif = NotificationCompat.Builder(this, OmniApplication.DOWNLOAD_CHANNEL_ID)
            .setContentTitle("Download Complete: $title")
            .setContentText(file.name)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(COMPLETED_NOTIFICATION_ID, completionNotif)
    }

    override fun onDestroy() {
        downloadJob?.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
