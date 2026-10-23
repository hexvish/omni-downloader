package com.hexvish.omnidownloader

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.hexvish.omnidownloader.ui.components.*
import com.hexvish.omnidownloader.ui.model.DownloadState
import com.hexvish.omnidownloader.ui.model.MediaTab
import com.hexvish.omnidownloader.ui.theme.*
import com.hexvish.omnidownloader.ui.viewmodel.OmniViewModel
import com.hexvish.omnidownloader.util.MediaStoreHelper
import java.util.regex.Pattern

class MainActivity : ComponentActivity() {

    private val viewModel: OmniViewModel by viewModels()

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* Permission granted or denied */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Request notification permission on Android 13+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        // Handle shared URL from YouTube, Spotify, TikTok, etc.
        handleIncomingIntent(intent)

        setContent {
            OmniDownloaderTheme {
                OmniMainScreen(viewModel = viewModel)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIncomingIntent(intent)
    }

    private fun handleIncomingIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT)
            if (!sharedText.isNullOrBlank()) {
                val extractedUrl = extractUrl(sharedText)
                if (extractedUrl != null) {
                    viewModel.onUrlChange(extractedUrl)
                    viewModel.fetchMetadata()
                }
            }
        }
    }

    private fun extractUrl(text: String): String? {
        val pattern = Pattern.compile("https?://[\\w\\d:#@%/;$()~_?\\+-=\\\\\\.&]+")
        val matcher = pattern.matcher(text)
        return if (matcher.find()) matcher.group(0) else null
    }
}

@Composable
fun OmniMainScreen(
    viewModel: OmniViewModel
) {
    val context = LocalContext.current
    val url by viewModel.url.collectAsState()
    val activeTab by viewModel.activeTab.collectAsState()
    val audioCodec by viewModel.selectedAudioCodec.collectAsState()
    val bitrate by viewModel.selectedBitrate.collectAsState()
    val videoCodec by viewModel.selectedVideoCodec.collectAsState()
    val resolution by viewModel.selectedResolution.collectAsState()

    val downloadState by viewModel.downloadState.collectAsState()
    val metadata by viewModel.metadata.collectAsState()
    val progress by viewModel.progress.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()
    val completedFile by viewModel.completedFile.collectAsState()
    val publicUri by viewModel.publicUri.collectAsState()

    val scrollState = rememberScrollState()

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = BgDark
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .statusBarsPadding()
                .navigationBarsPadding()
                .padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OmniTopBar()

            UrlInputField(
                url = url,
                onUrlChange = { viewModel.onUrlChange(it) },
                onFetch = { viewModel.fetchMetadata() },
                isLoading = downloadState == DownloadState.FETCHING_METADATA
            )

            // Error Banner
            if (errorMessage != null && downloadState == DownloadState.ERROR) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 20.dp)
                        .clip(RoundedCornerShape(14.dp))
                        .background(Color(0x30EF4444))
                        .border(1.dp, Color(0x60EF4444), RoundedCornerShape(14.dp))
                        .padding(14.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.ErrorOutline,
                            contentDescription = null,
                            tint = ErrorRed,
                            modifier = Modifier.size(20.dp)
                        )
                        Text(
                            text = errorMessage ?: "Extraction error",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color.White
                        )
                    }
                }
            }

            // Media Preview Card
            metadata?.let { meta ->
                MediaPreviewCard(metadata = meta)

                // Playlist Selector if playlist
                if (meta.isPlaylist && meta.tracks.isNotEmpty()) {
                    PlaylistSelector(
                        tracks = meta.tracks,
                        onToggleTrack = { viewModel.toggleTrack(it) },
                        onToggleAll = { viewModel.toggleAllTracks(it) },
                        onDownloadTrack = { viewModel.downloadSingleTrack(context, it) }
                    )
                }

                // Format & Bitrate Controls (also visible on ERROR so user can change settings & retry)
                if (downloadState == DownloadState.READY_TO_DOWNLOAD || downloadState == DownloadState.ERROR) {
                    FormatPillsSection(
                        activeTab = activeTab,
                        onTabChange = { viewModel.onTabChange(it) },
                        selectedAudioCodec = audioCodec,
                        onAudioCodecChange = { viewModel.onAudioCodecChange(it) },
                        selectedBitrate = bitrate,
                        onBitrateChange = { viewModel.onBitrateChange(it) },
                        selectedVideoCodec = videoCodec,
                        onVideoCodecChange = { viewModel.onVideoCodecChange(it) },
                        selectedResolution = resolution,
                        onResolutionChange = { viewModel.onResolutionChange(it) },
                        onStartDownload = { viewModel.startDownload(context) },
                        isPlaylist = meta.isPlaylist,
                        selectedCount = meta.tracks.count { it.isSelected }
                    )
                }
            }

            // Downloading Progress Card
            if (downloadState == DownloadState.DOWNLOADING) {
                DownloadProgressCard(
                    title = metadata?.title ?: "Downloading...",
                    progress = progress,
                    onCancel = { viewModel.cancelDownload(context) }
                )
            }

            // Completed Card
            if (downloadState == DownloadState.COMPLETED && completedFile != null) {
                val file = completedFile!!
                val targetUri = publicUri ?: MediaStoreHelper.getFileUri(context, file)
                val mimeType = MediaStoreHelper.getMimeType(file)

                CompletedCard(
                    file = file,
                    onPlay = { MediaStoreHelper.openFile(context, targetUri, mimeType) },
                    onShowInFolder = { MediaStoreHelper.openFolder(context, isAudio = activeTab == MediaTab.AUDIO) },
                    onShare = { MediaStoreHelper.shareFile(context, targetUri, mimeType, file.name) },
                    onDownloadAnother = { viewModel.reset() }
                )
            }
        }
    }
}
