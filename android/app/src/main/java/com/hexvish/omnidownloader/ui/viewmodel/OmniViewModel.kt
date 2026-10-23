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

    private val _selectedAudioCodec = MutableStateFlow("MP3")
    val selectedAudioCodec: StateFlow<String> = _selectedAudioCodec.asStateFlow()

    private val _selectedBitrate = MutableStateFlow("320")
    val selectedBitrate: StateFlow<String> = _selectedBitrate.asStateFlow()

    private val _selectedVideoCodec = MutableStateFlow("MP4")
    val selectedVideoCodec: StateFlow<String> = _selectedVideoCodec.asStateFlow()

    private val _selectedResolution = MutableStateFlow("1080p")
    val selectedResolution: StateFlow<String> = _selectedResolution.asStateFlow()

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

    fun onAudioCodecChange(codec: String) {
        _selectedAudioCodec.value = codec
    }

    fun onBitrateChange(bitrate: String) {
        _selectedBitrate.value = bitrate
    }

    fun onVideoCodecChange(codec: String) {
        _selectedVideoCodec.value = codec
    }

    fun onResolutionChange(res: String) {
        _selectedResolution.value = res
    }

    fun toggleTrack(trackIndex: Int) {
        OmniDownloadController.toggleTrackSelection(trackIndex)
    }

    fun toggleAllTracks(selectAll: Boolean) {
        OmniDownloadController.toggleAllTracks(selectAll)
    }

    fun startDownload(context: Context) {
        val type = if (_activeTab.value == MediaTab.AUDIO) "audio" else "video"
        val codec = if (_activeTab.value == MediaTab.AUDIO) _selectedAudioCodec.value else _selectedVideoCodec.value
        val bitrate = _selectedBitrate.value
        val resolution = _selectedResolution.value

        OmniDownloadController.startDownload(
            context = context,
            url = _url.value,
            downloadType = type,
            codec = codec,
            bitrate = bitrate,
            resolution = resolution
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
