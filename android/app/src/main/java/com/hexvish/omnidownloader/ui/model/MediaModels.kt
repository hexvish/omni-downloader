package com.hexvish.omnidownloader.ui.model

data class TrackItem(
    val index: Int,
    val title: String,
    val url: String,
    val duration: Long,
    val durationStr: String,
    val uploader: String,
    val isSelected: Boolean = true
)

data class MediaMetadata(
    val title: String,
    val uploader: String,
    val thumbnail: String,
    val durationStr: String,
    val duration: Long,
    val viewCount: Long,
    val isPlaylist: Boolean,
    val totalTracks: Int = 0,
    val tracks: List<TrackItem> = emptyList()
)

data class DownloadProgress(
    val percentage: Float = 0f,
    val speed: String = "",
    val statusText: String = ""
)

enum class DownloadState {
    IDLE,
    FETCHING_METADATA,
    READY_TO_DOWNLOAD,
    DOWNLOADING,
    COMPLETED,
    ERROR
}

enum class MediaTab {
    AUDIO,
    VIDEO
}
