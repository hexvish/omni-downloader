package com.hexvish.omnidownloader

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class OmniApplication : Application() {

    companion object {
        const val DOWNLOAD_CHANNEL_ID = "omni_download_channel"
    }

    override fun onCreate() {
        super.onCreate()

        // Initialize Chaquopy Python Runtime
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }


        // Create notification channel for Foreground Service
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                DOWNLOAD_CHANNEL_ID,
                "Omni Downloads",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Foreground downloads progress and notifications"
                setShowBadge(false)
            }

            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }
}
