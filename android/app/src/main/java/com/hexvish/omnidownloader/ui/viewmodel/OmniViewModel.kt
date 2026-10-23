package com.hexvish.omnidownloader.ui.viewmodel

import android.content.Context
import androidx.lifecycle.ViewModel
import com.hexvish.omnidownloader.service.OmniDownloadController
import com.hexvish.omnidownloader.ui.model.MediaTab
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class OmniViewModel : ViewModel() {

    private val _url = MutableStateFlow("")
    val url: StateFlow<String> = _url.asStateFlow()

    private val _activeTab = MutableStateFlow(MediaTab.AUDIO)
    val activeTab: StateFlow<MediaTab> = _activeTab.asStateFlow()

    val downloadState = OmniDownloadController.downloadState
    val metadata = OmniDownloadController.metadata
    val progress = OmniDownloadController.progress
    val errorMessage = OmniDownloadController.errorMessage
    val completedFile = OmniDownloadController.completedFile
    val publicUri = OmniDownloadController.publicUri

    fun onUrlChange(newUrl: String) {
        _url.value = newUrl
    }

    fun fetchMetadata() {
        OmniDownloadController.fetchMetadata(_url.value)
    }

    fun onTabChange(tab: MediaTab) {
        _activeTab.value = tab
    }

    fun toggleTrack(trackIndex: Int) {
        OmniDownloadController.toggleTrackSelection(trackIndex)
    }

    fun toggleAllTracks(selectAll: Boolean) {
        OmniDownloadController.toggleAllTracks(selectAll)
    }

    fun startDownload(context: Context) {
        val type = if (_activeTab.value == MediaTab.AUDIO) "audio" else "video"
        OmniDownloadController.startDownload(
            context = context,
            url = _url.value,
            downloadType = type
        )
    }

    fun downloadSingleTrack(context: Context, track: com.hexvish.omnidownloader.ui.model.TrackItem) {
        val type = if (_activeTab.value == MediaTab.AUDIO) "audio" else "video"
        OmniDownloadController.startSingleTrackDownload(
            context = context,
            track = track,
            downloadType = type
        )
    }

    fun cancelDownload(context: Context) {
        OmniDownloadController.cancelDownload(context)
    }

    fun reset() {
        _url.value = ""
        OmniDownloadController.reset()
    }
}
