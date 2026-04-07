package com.fibaai.soplens.ui

import android.content.Context
import androidx.compose.animation.*
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fibaai.soplens.ml.SOPClassifier
import com.fibaai.soplens.ui.theme.*

@Composable
fun ActionSearchScreen(
    viewModel: ActionViewModel,
    classifier: SOPClassifier,
    context: Context,
    onPickVideo: () -> Unit
) {
    val focusManager = LocalFocusManager.current

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 16.dp, bottom = 100.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // ── Header with logo ──
        item {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // App logo
                Surface(
                    modifier = Modifier.size(44.dp),
                    shape = RoundedCornerShape(12.dp),
                    color = Primary
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text("FI", fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, color = Color.White)
                    }
                }
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("FIBA", fontSize = 24.sp, fontWeight = FontWeight.ExtraBold, color = OnSurface)
                        Text("AI", fontSize = 24.sp, fontWeight = FontWeight.ExtraBold, color = Accent)
                    }
                    Text(
                        "Find it by Action",
                        fontSize = 12.sp,
                        color = OnSurfaceMuted,
                        fontWeight = FontWeight.Medium
                    )
                }
                Spacer(Modifier.weight(1f))
                // Edge badge
                Surface(
                    shape = RoundedCornerShape(20.dp),
                    color = Success.copy(alpha = 0.1f),
                    border = BorderStroke(1.dp, Success.copy(alpha = 0.3f))
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(6.dp)
                                .clip(CircleShape)
                                .background(Success)
                        )
                        Text("Edge", fontSize = 10.sp, color = Success, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }

        // ── Description card ──
        item {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                color = Surface,
                border = BorderStroke(1.dp, SurfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        "🔍 Action Search",
                        fontSize = 17.sp,
                        fontWeight = FontWeight.Bold,
                        color = OnSurface
                    )
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "Upload a video and search for specific assembly actions. The on-device AI classifier identifies all 7 assembly tasks and shows matching frames.",
                        fontSize = 12.sp,
                        color = OnSurfaceMuted,
                        lineHeight = 18.sp
                    )
                }
            }
        }

        // ── Video picker ──
        item {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                color = Surface,
                border = BorderStroke(1.dp, SurfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("1. Select Video", fontWeight = FontWeight.SemiBold, fontSize = 14.sp, color = Primary)
                    Spacer(Modifier.height(10.dp))
                    if (viewModel.videoUri != null) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Icon(Icons.Filled.VideoFile, null, tint = Accent, modifier = Modifier.size(20.dp))
                            Text(viewModel.videoName, fontSize = 13.sp, color = OnSurface, modifier = Modifier.weight(1f))
                            TextButton(onClick = onPickVideo) {
                                Text("Change", fontSize = 12.sp, color = Primary)
                            }
                        }
                    } else {
                        OutlinedButton(
                            onClick = onPickVideo,
                            modifier = Modifier.fillMaxWidth().height(64.dp),
                            shape = RoundedCornerShape(10.dp),
                            border = BorderStroke(1.dp, SurfaceVariant)
                        ) {
                            Icon(Icons.Outlined.VideoLibrary, null, modifier = Modifier.size(24.dp), tint = OnSurfaceMuted)
                            Spacer(Modifier.width(8.dp))
                            Text("Select assembly video", color = OnSurfaceMuted, fontSize = 13.sp)
                        }
                    }
                }
            }
        }

        // ── Query input ──
        item {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp),
                color = Surface,
                border = BorderStroke(1.dp, SurfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("2. Search Action", fontWeight = FontWeight.SemiBold, fontSize = 14.sp, color = Primary)
                    Spacer(Modifier.height(10.dp))
                    OutlinedTextField(
                        value = viewModel.query,
                        onValueChange = { viewModel.query = it },
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("e.g. screwing, inflate valve, cable…", color = OnSurfaceMuted, fontSize = 13.sp) },
                        leadingIcon = { Icon(Icons.Outlined.Search, null, tint = OnSurfaceMuted) },
                        singleLine = true,
                        shape = RoundedCornerShape(10.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Primary,
                            unfocusedBorderColor = SurfaceVariant,
                            cursorColor = Primary,
                            focusedTextColor = OnSurface,
                            unfocusedTextColor = OnSurface
                        ),
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                        keyboardActions = KeyboardActions(onSearch = {
                            focusManager.clearFocus()
                            viewModel.searchActions(classifier, context)
                        })
                    )
                    Spacer(Modifier.height(6.dp))
                    // Quick action chips
                    Row(
                        modifier = Modifier.horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf("spring", "screw", "inflate", "cable", "plastic").forEach { chip ->
                            FilterChip(
                                selected = viewModel.query.lowercase() == chip,
                                onClick = { viewModel.query = chip },
                                label = { Text(chip, fontSize = 11.sp) },
                                colors = FilterChipDefaults.filterChipColors(
                                    containerColor = SurfaceVariant,
                                    labelColor = OnSurfaceMuted,
                                    selectedContainerColor = Primary.copy(alpha = 0.2f),
                                    selectedLabelColor = Primary
                                ),
                                border = FilterChipDefaults.filterChipBorder(
                                    borderColor = Color.Transparent,
                                    enabled = true,
                                    selected = viewModel.query.lowercase() == chip
                                ),
                                modifier = Modifier.height(28.dp)
                            )
                        }
                    }
                }
            }
        }

        // ── Search button ──
        item {
            Button(
                onClick = {
                    focusManager.clearFocus()
                    viewModel.searchActions(classifier, context)
                },
                modifier = Modifier.fillMaxWidth().height(52.dp),
                enabled = viewModel.videoUri != null && viewModel.query.isNotBlank() && !viewModel.isProcessing,
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Primary,
                    disabledContainerColor = SurfaceVariant
                )
            ) {
                if (viewModel.isProcessing) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), color = Color.White, strokeWidth = 2.dp)
                    Spacer(Modifier.width(8.dp))
                    Text(viewModel.statusMessage, fontWeight = FontWeight.Bold)
                } else {
                    Icon(Icons.Filled.Search, null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("Search Actions", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                }
            }
        }

        // ── Progress ──
        if (viewModel.isProcessing) {
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    color = Surface
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        LinearProgressIndicator(
                            progress = { viewModel.progress / 100f },
                            modifier = Modifier.fillMaxWidth().height(5.dp).clip(RoundedCornerShape(3.dp)),
                            color = Primary,
                            trackColor = SurfaceVariant
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "${viewModel.statusMessage} · ${viewModel.progress}%",
                            fontSize = 11.sp,
                            color = OnSurfaceMuted,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }
            }
        }

        // ── Error ──
        viewModel.errorMessage?.let { err ->
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(10.dp),
                    color = Error.copy(alpha = 0.1f),
                    border = BorderStroke(1.dp, Error.copy(alpha = 0.3f))
                ) {
                    Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Warning, null, tint = Error, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(8.dp))
                        Text(err, fontSize = 12.sp, color = Error)
                    }
                }
            }
        }

        // ── Results ──
        viewModel.result?.let { res ->
            // Summary
            item {
                val matchColor = if (res.matchedActions.isNotEmpty()) Success else Warning
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp),
                    color = matchColor.copy(alpha = 0.08f),
                    border = BorderStroke(1.dp, matchColor.copy(alpha = 0.3f))
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Text(
                            if (res.matchedActions.isNotEmpty()) "🎯" else "⚠️",
                            fontSize = 24.sp
                        )
                        Column {
                            Text(
                                if (res.matchedActions.isNotEmpty())
                                    "${res.matchedActions.size} frame(s) matched \"${res.query}\""
                                else
                                    "No frames matched \"${res.query}\"",
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                                color = matchColor
                            )
                            Text(
                                "Analyzed ${res.totalFrames} frames · on-device inference",
                                fontSize = 11.sp,
                                color = OnSurfaceMuted
                            )
                        }
                    }
                }
            }

            // Matched frames
            if (res.matchedActions.isNotEmpty()) {
                item {
                    Text(
                        "Matched Frames",
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp,
                        color = OnSurface,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
                items(res.matchedActions) { action ->
                    ActionFrameCard(action, isMatch = true)
                }
            }

            // All detected actions summary
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp),
                    color = Surface,
                    border = BorderStroke(1.dp, SurfaceVariant)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            "All Detected Actions",
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 14.sp,
                            color = OnSurface
                        )
                        Spacer(Modifier.height(10.dp))
                        // Count per task
                        val taskCounts = res.allActions.groupingBy { it.taskName }.eachCount()
                        taskCounts.entries.sortedByDescending { it.value }.forEach { (name, count) ->
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text("•", color = Primary, fontSize = 14.sp)
                                Spacer(Modifier.width(8.dp))
                                Text(name, fontSize = 12.sp, color = OnSurface, modifier = Modifier.weight(1f))
                                Text("$count frames", fontSize = 11.sp, color = OnSurfaceMuted)
                            }
                        }
                        Spacer(Modifier.height(12.dp))
                        OutlinedButton(
                            onClick = { viewModel.reset() },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(8.dp),
                            border = BorderStroke(1.dp, Primary)
                        ) {
                            Text("New Search", color = Primary, fontWeight = FontWeight.SemiBold)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ActionFrameCard(action: DetectedAction, isMatch: Boolean = false) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        color = Surface,
        border = BorderStroke(1.dp, if (isMatch) Success.copy(alpha = 0.3f) else SurfaceVariant)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Thumbnail
            action.thumbnail?.let { bmp ->
                Image(
                    bitmap = bmp.asImageBitmap(),
                    contentDescription = "Frame",
                    modifier = Modifier
                        .width(100.dp)
                        .height(72.dp)
                        .clip(RoundedCornerShape(8.dp))
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    action.taskName,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 13.sp,
                    color = OnSurface
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    "Time: ${formatTime(action.timeMs)}",
                    fontSize = 11.sp,
                    color = OnSurfaceMuted
                )
                // Confidence bar
                Spacer(Modifier.height(6.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    LinearProgressIndicator(
                        progress = { action.confidence },
                        modifier = Modifier.weight(1f).height(4.dp).clip(RoundedCornerShape(2.dp)),
                        color = if (action.confidence > 0.8f) Success else if (action.confidence > 0.5f) Warning else Error,
                        trackColor = SurfaceVariant
                    )
                    Spacer(Modifier.width(6.dp))
                    Text("${(action.confidence * 100).toInt()}%", fontSize = 10.sp, color = OnSurfaceMuted)
                }
            }
        }
    }
}

private fun formatTime(ms: Long): String {
    val totalSec = ms / 1000
    val min = totalSec / 60
    val sec = totalSec % 60
    return "%d:%02d".format(min, sec)
}
