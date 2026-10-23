package com.hexvish.omnidownloader.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Headphones
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.hexvish.omnidownloader.ui.model.MediaTab
import com.hexvish.omnidownloader.ui.theme.*

@Composable
fun FormatPillsSection(
    activeTab: MediaTab,
    onTabChange: (MediaTab) -> Unit,
    selectedAudioCodec: String,
    onAudioCodecChange: (String) -> Unit,
    selectedBitrate: String,
    onBitrateChange: (String) -> Unit,
    selectedVideoCodec: String,
    onVideoCodecChange: (String) -> Unit,
    selectedResolution: String,
    onResolutionChange: (String) -> Unit,
    onStartDownload: () -> Unit,
    isPlaylist: Boolean,
    modifier: Modifier = Modifier
) {
    val audioCodecs = listOf("MP3", "M4A", "FLAC", "WAV")
    val bitrates = listOf("320", "256", "192", "128")
    val videoCodecs = listOf("MP4", "MKV", "WEBM")
    val resolutions = listOf("1080p", "720p", "480p", "360p")

    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Audio vs Video Tab Switcher
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
                .background(Color(0xFF0F172A))
                .border(1.dp, GlassBorder, RoundedCornerShape(14.dp))
                .padding(4.dp)
        ) {
            Box(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(10.dp))
                    .background(
                        if (activeTab == MediaTab.AUDIO) Brush.horizontalGradient(
                            listOf(CyanPrimary, VioletPrimary)
                        ) else SolidColor(Color.Transparent)
                    )
                    .clickable { onTabChange(MediaTab.AUDIO) }
                    .padding(vertical = 10.dp),
                contentAlignment = Alignment.Center
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Headphones,
                        contentDescription = null,
                        tint = if (activeTab == MediaTab.AUDIO) Color.White else TextSecondary,
                        modifier = Modifier.size(16.dp)
                    )
                    Text(
                        text = "Audio (Music)",
                        fontSize = 13.sp,
                        fontWeight = if (activeTab == MediaTab.AUDIO) FontWeight.Bold else FontWeight.Medium,
                        color = if (activeTab == MediaTab.AUDIO) Color.White else TextSecondary
                    )
                }
            }

            Box(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(10.dp))
                    .background(
                        if (activeTab == MediaTab.VIDEO) Brush.horizontalGradient(
                            listOf(CyanPrimary, VioletPrimary)
                        ) else SolidColor(Color.Transparent)
                    )
                    .clickable { onTabChange(MediaTab.VIDEO) }
                    .padding(vertical = 10.dp),
                contentAlignment = Alignment.Center
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Videocam,
                        contentDescription = null,
                        tint = if (activeTab == MediaTab.VIDEO) Color.White else TextSecondary,
                        modifier = Modifier.size(16.dp)
                    )
                    Text(
                        text = "Video",
                        fontSize = 13.sp,
                        fontWeight = if (activeTab == MediaTab.VIDEO) FontWeight.Bold else FontWeight.Medium,
                        color = if (activeTab == MediaTab.VIDEO) Color.White else TextSecondary
                    )
                }
            }
        }

        if (activeTab == MediaTab.AUDIO) {
            // Audio Codecs
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "AUDIO FORMAT",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                    color = CyanAccent
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    audioCodecs.forEach { codec ->
                        FormatPill(
                            label = codec,
                            isSelected = selectedAudioCodec.equals(codec, ignoreCase = true),
                            onClick = { onAudioCodecChange(codec) },
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }

            // Bitrates
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "BITRATE QUALITY",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                    color = CyanAccent
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    bitrates.forEach { br ->
                        val label = when (br) {
                            "320" -> "320 kbps"
                            "256" -> "256 kbps"
                            "192" -> "192 kbps"
                            else -> "128 kbps"
                        }
                        FormatPill(
                            label = label,
                            isSelected = selectedBitrate == br,
                            onClick = { onBitrateChange(br) },
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }
        } else {
            // Video Codecs
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "CONTAINER FORMAT",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                    color = CyanAccent
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    videoCodecs.forEach { codec ->
                        FormatPill(
                            label = codec,
                            isSelected = selectedVideoCodec.equals(codec, ignoreCase = true),
                            onClick = { onVideoCodecChange(codec) },
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }

            // Resolutions
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "RESOLUTION",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                    color = CyanAccent
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    resolutions.forEach { res ->
                        FormatPill(
                            label = res,
                            isSelected = selectedResolution == res,
                            onClick = { onResolutionChange(res) },
                            modifier = Modifier.weight(1f)
                        )
                    }
                }
            }
        }

        // Start Download Button
        Button(
            onClick = onStartDownload,
            modifier = Modifier
                .fillMaxWidth()
                .height(50.dp)
                .clip(RoundedCornerShape(16.dp)),
            colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
            contentPadding = PaddingValues()
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.horizontalGradient(listOf(CyanPrimary, VioletPrimary))
                    ),
                contentAlignment = Alignment.Center
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Download,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(20.dp)
                    )
                    Text(
                        text = if (isPlaylist) "Download Playlist (Zip)" else "Download Now",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                }
            }
        }
    }
}

@Composable
fun FormatPill(
    label: String,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(10.dp))
            .background(
                if (isSelected) Color(0x3038BDF8) else Color(0xFF1E293B)
            )
            .border(
                1.dp,
                if (isSelected) CyanAccent else Color(0x2038BDF8),
                RoundedCornerShape(10.dp)
            )
            .clickable { onClick() }
            .padding(vertical = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            fontSize = 12.sp,
            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
            color = if (isSelected) CyanAccent else TextSecondary
        )
    }
}
