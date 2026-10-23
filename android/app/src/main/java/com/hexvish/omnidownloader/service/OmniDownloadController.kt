package com.hexvish.omnidownloader.service

import android.content.Context
import android.content.Intent
import android.net.Uri
import com.chaquo.python.Python
import com.hexvish.omnidownloader.ui.model.DownloadProgress
import com.hexvish.omnidownloader.ui.model.DownloadState
import com.hexvish.omnidownloader.ui.model.MediaMetadata
import com.hexvish.omnidownloader.ui.model.TrackItem
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

object OmniDownloadController {

    private val scope = CoroutineScope(Dispatchers.Main)

    private val _downloadState = MutableStateFlow(DownloadState.IDLE)
    val downloadState: StateFlow<DownloadState> = _downloadState.asStateFlow()

    private val _metadata = MutableStateFlow<MediaMetadata?>(null)
    val metadata: StateFlow<MediaMetadata?> = _metadata.asStateFlow()

    private val _progress = MutableStateFlow(DownloadProgress())
    val progress: StateFlow<DownloadProgress> = _progress.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _completedFile = MutableStateFlow<File?>(null)
    val completedFile: StateFlow<File?> = _completedFile.asStateFlow()

    private val _publicUri = MutableStateFlow<Uri?>(null)
    val publicUri: StateFlow<Uri?> = _publicUri.asStateFlow()

    fun fetchMetadata(url: String) {
        if (url.isBlank()) return

        _downloadState.value = DownloadState.FETCHING_METADATA
        _errorMessage.value = null
        _metadata.value = null
        _completedFile.value = null
        _publicUri.value = null

        scope.launch {
            try {
                val jsonResult = withContext(Dispatchers.IO) {
                    val py = Python.getInstance()
                    val engine = py.getModule("omni_engine")
                    engine.callAttr("extract_media_info", url.trim()).toString()
                }

                val obj = JSONObject(jsonResult)
                if (obj.optString("status") == "success") {
                    val isPlaylist = obj.optBoolean("is_playlist", false)
                    val title = obj.optString("title", "Unknown Title")
                    val uploader = obj.optString("uploader", "")
                    val thumbnail = obj.optString("thumbnail", "")

                    if (isPlaylist) {
                        val tracksArray = obj.optJSONArray("tracks")
                        val trackList = mutableListOf<TrackItem>()
                        if (tracksArray != null) {
                            for (i in 0 until tracksArray.length()) {
                                val tObj = tracksArray.getJSONObject(i)
                                trackList.add(
                                    TrackItem(
                                        index = tObj.optInt("index", i + 1),
                                        title = tObj.optString("title", "Track ${i + 1}"),
                                        url = tObj.optString("url", ""),
                                        duration = tObj.optLong("duration", 0L),
                                        durationStr = tObj.optString("duration_str", ""),
                                        uploader = tObj.optString("uploader", ""),
                                        isSelected = true
                                    )
                                )
                            }
                        }
                        _metadata.value = MediaMetadata(
                            title = title,
                            uploader = uploader,
                            thumbnail = thumbnail,
                            durationStr = "",
                            duration = 0L,
                            viewCount = 0L,
                            isPlaylist = true,
                            totalTracks = trackList.size,
                            tracks = trackList
                        )
                    } else {
                        _metadata.value = MediaMetadata(
                            title = title,
                            uploader = uploader,
                            thumbnail = thumbnail,
                            durationStr = obj.optString("duration_str", ""),
                            duration = obj.optLong("duration", 0L),
                            viewCount = obj.optLong("view_count", 0L),
                            isPlaylist = false
                        )
                    }
                    _downloadState.value = DownloadState.READY_TO_DOWNLOAD
                } else {
                    _errorMessage.value = obj.optString("message", "Unable to extract media metadata.")
                    _downloadState.value = DownloadState.ERROR
                }
            } catch (e: Exception) {
                _errorMessage.value = e.localizedMessage ?: "Network or extraction error"
                _downloadState.value = DownloadState.ERROR
            }
        }
    }

    fun toggleTrackSelection(trackIndex: Int) {
        val current = _metadata.value ?: return
        if (!current.isPlaylist) return

        val updatedTracks = current.tracks.map {
            if (it.index == trackIndex) it.copy(isSelected = !it.isSelected) else it
        }
        _metadata.value = current.copy(tracks = updatedTracks)
    }

    fun toggleAllTracks(selectAll: Boolean) {
        val current = _metadata.value ?: return
        if (!current.isPlaylist) return

        val updatedTracks = current.tracks.map { it.copy(isSelected = selectAll) }
        _metadata.value = current.copy(tracks = updatedTracks)
    }

    fun startDownload(
        context: Context,
        url: String,
        downloadType: String,
        codec: String,
        bitrate: String,
        resolution: String
    ) {
        val meta = _metadata.value
        val isPlaylist = meta?.isPlaylist ?: false
        val selectedIndices = if (isPlaylist) {
            meta?.tracks?.filter { it.isSelected }?.map { it.index }?.toIntArray() ?: intArrayOf()
        } else {
            intArrayOf()
        }

        // If user selected exactly 1 track from playlist, treat as single track download
        val effectiveUrl = if (isPlaylist && selectedIndices.size == 1) {
            meta?.tracks?.find { it.index == selectedIndices[0] }?.url ?: url
        } else {
            url
        }
        val effectiveIsPlaylist = isPlaylist && selectedIndices.size > 1

        _downloadState.value = DownloadState.DOWNLOADING
        _progress.value = DownloadProgress(0f, "", "Starting download...")
        _errorMessage.value = null
        _completedFile.value = null
        _publicUri.value = null

        val intent = Intent(context, DownloadService::class.java).apply {
            action = DownloadService.ACTION_START_DOWNLOAD
            putExtra(DownloadService.EXTRA_URL, effectiveUrl)
            putExtra(DownloadService.EXTRA_TYPE, downloadType)
            putExtra(DownloadService.EXTRA_CODEC, codec)
            putExtra(DownloadService.EXTRA_BITRATE, bitrate)
            putExtra(DownloadService.EXTRA_RESOLUTION, resolution)
            putExtra(DownloadService.EXTRA_IS_PLAYLIST, effectiveIsPlaylist)
            putExtra(DownloadService.EXTRA_TITLE, meta?.title ?: "Download")
            putExtra(DownloadService.EXTRA_SELECTED_INDICES, selectedIndices)
        }

        context.startForegroundService(intent)
    }

    fun startSingleTrackDownload(
        context: Context,
        track: TrackItem,
        downloadType: String,
        codec: String,
        bitrate: String,
        resolution: String
    ) {
        _downloadState.value = DownloadState.DOWNLOADING
        _progress.value = DownloadProgress(0f, "", "Starting download for ${track.title}...")
        _errorMessage.value = null
        _completedFile.value = null
        _publicUri.value = null

        val intent = Intent(context, DownloadService::class.java).apply {
            action = DownloadService.ACTION_START_DOWNLOAD
            putExtra(DownloadService.EXTRA_URL, track.url)
            putExtra(DownloadService.EXTRA_TYPE, downloadType)
            putExtra(DownloadService.EXTRA_CODEC, codec)
            putExtra(DownloadService.EXTRA_BITRATE, bitrate)
            putExtra(DownloadService.EXTRA_RESOLUTION, resolution)
            putExtra(DownloadService.EXTRA_IS_PLAYLIST, false)
            putExtra(DownloadService.EXTRA_TITLE, track.title)
            putExtra(DownloadService.EXTRA_SELECTED_INDICES, intArrayOf())
        }

        context.startForegroundService(intent)
    }

    fun updateProgress(percentage: Float, speed: String, statusText: String) {
        _progress.value = DownloadProgress(percentage, speed, statusText)
    }

    fun onDownloadCompleted(file: File, uri: Uri?) {
        _completedFile.value = file
        _publicUri.value = uri
        _downloadState.value = DownloadState.COMPLETED
    }

    fun onDownloadError(error: String) {
        _errorMessage.value = error
        _downloadState.value = DownloadState.ERROR
    }

    fun cancelDownload(context: Context) {
        val intent = Intent(context, DownloadService::class.java).apply {
            action = DownloadService.ACTION_CANCEL_DOWNLOAD
        }
        context.startService(intent)
        _downloadState.value = DownloadState.IDLE
        _progress.value = DownloadProgress()
    }

    fun reset() {
        _downloadState.value = DownloadState.IDLE
        _metadata.value = null
        _progress.value = DownloadProgress()
        _errorMessage.value = null
        _completedFile.value = null
        _publicUri.value = null
    }
}
