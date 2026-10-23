package com.hexvish.omnidownloader.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Headphones
import androidx.compose.material.icons.filled.HighQuality
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
    onStartDownload: () -> Unit,
    isPlaylist: Boolean,
    selectedCount: Int = 0,
    isDownloading: Boolean = false,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
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
                        text = "Video (Movies)",
                        fontSize = 13.sp,
                        fontWeight = if (activeTab == MediaTab.VIDEO) FontWeight.Bold else FontWeight.Medium,
                        color = if (activeTab == MediaTab.VIDEO) Color.White else TextSecondary
                    )
                }
            }
        }

        // Quality Info Card
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(14.dp))
                .background(Color(0xFF0F172A))
                .border(1.dp, GlassBorder, RoundedCornerShape(14.dp))
                .padding(14.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(38.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .background(Color(0x2038BDF8)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = if (activeTab == MediaTab.AUDIO) Icons.Default.Headphones else Icons.Default.HighQuality,
                        contentDescription = null,
                        tint = CyanAccent,
                        modifier = Modifier.size(20.dp)
                    )
                }

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = if (activeTab == MediaTab.AUDIO) "ORIGINAL MASTER AUDIO" else "HIGHEST RESOLUTION VIDEO",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = if (activeTab == MediaTab.AUDIO)
                            "Source quality • Saved to Music"
                        else
                            "Best quality with audio • Saved to Movies",
                        fontSize = 11.sp,
                        color = TextMuted
                    )
                }

                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(Color(0x3010B981))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = "Native",
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF34D399)
                    )
                }
            }
        }

        val isEnabled = !isDownloading && (if (isPlaylist) selectedCount > 0 else true)
        val buttonText = if (isDownloading) {
            "Downloading in progress..."
        } else if (isPlaylist) {
            when {
                selectedCount == 1 -> if (activeTab == MediaTab.AUDIO) "Download 1 Track" else "Download 1 Video"
                selectedCount > 1 -> if (activeTab == MediaTab.AUDIO) "Download Selected ($selectedCount Tracks)" else "Download Selected ($selectedCount Videos)"
                else -> "Select Items to Download"
            }
        } else {
            if (activeTab == MediaTab.AUDIO) "Download Audio (Best Quality)" else "Download Video (Best Quality)"
        }

        // Start Download Button
        Button(
            onClick = onStartDownload,
            enabled = isEnabled,
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp)
                .clip(RoundedCornerShape(16.dp)),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color.Transparent,
                disabledContainerColor = Color(0x2038BDF8)
            ),
            contentPadding = PaddingValues()
        ) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        if (isEnabled) {
                            Brush.horizontalGradient(listOf(CyanPrimary, VioletPrimary))
                        } else {
                            SolidColor(Color(0x2038BDF8))
                        }
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
                        tint = if (isEnabled) Color.White else TextMuted,
                        modifier = Modifier.size(20.dp)
                    )
                    Text(
                        text = buttonText,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (isEnabled) Color.White else TextMuted
                    )
                }
            }
        }
    }
}
