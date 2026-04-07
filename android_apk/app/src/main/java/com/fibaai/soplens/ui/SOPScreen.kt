package com.fibaai.soplens.ui

import android.graphics.Bitmap
import androidx.compose.animation.*
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.fibaai.soplens.ml.SOPClassifier
import com.fibaai.soplens.ml.SOPResult
import com.fibaai.soplens.ml.StepResult
import com.fibaai.soplens.ui.theme.*

// ── SOP Compliance Screen ────────────────────────────

@Composable
fun SOPScreen(
    viewModel: SOPViewModel,
    onPickVideo: () -> Unit,
    onProcess: () -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 16.dp, bottom = 100.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Header with logo
        item {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
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
                    Text("SOP Compliance", fontSize = 12.sp, color = OnSurfaceMuted, fontWeight = FontWeight.Medium)
                }
                Spacer(Modifier.weight(1f))
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

        // Classifier badge
        item {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                color = Success.copy(alpha = 0.1f),
                border = BorderStroke(1.dp, Success.copy(alpha = 0.3f))
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Icon(Icons.Filled.Memory, contentDescription = null, tint = Success, modifier = Modifier.size(20.dp))
                    Text(
                        "On-device classifier loaded · Fully offline",
                        fontSize = 12.sp,
                        color = Success,
                        fontWeight = FontWeight.Medium
                    )
                }
            }
        }

        // SOP Timeline
        item {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                color = Surface,
                border = BorderStroke(1.dp, SurfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(Icons.Outlined.Checklist, contentDescription = null, tint = Primary, modifier = Modifier.size(20.dp))
                        Text("Standard Operating Procedure", fontWeight = FontWeight.SemiBold, color = OnSurface, fontSize = 15.sp)
                    }
                    Spacer(Modifier.height(14.dp))

                    SOPClassifier.TASK_NAMES.forEachIndexed { index, name ->
                        val stepColor = if (viewModel.result != null) {
                            val sr = viewModel.result!!.stepResults.getOrNull(index)
                            if (sr?.isCorrect == true) Success else if (sr != null) Error else Primary
                        } else Primary

                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            // Step number circle
                            Surface(
                                modifier = Modifier.size(28.dp),
                                shape = CircleShape,
                                color = stepColor
                            ) {
                                Box(contentAlignment = Alignment.Center) {
                                    Text("${index + 1}", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.White)
                                }
                            }
                            Text(name, fontSize = 13.sp, color = OnSurface, modifier = Modifier.weight(1f))

                            // Status icon
                            if (viewModel.result != null) {
                                val sr = viewModel.result!!.stepResults.getOrNull(index)
                                if (sr?.isCorrect == true) {
                                    Icon(Icons.Filled.CheckCircle, contentDescription = "Correct", tint = Success, modifier = Modifier.size(20.dp))
                                } else if (sr != null) {
                                    Icon(Icons.Filled.Cancel, contentDescription = "Wrong", tint = Error, modifier = Modifier.size(20.dp))
                                }
                            }
                        }
                        if (index < SOPClassifier.TASK_NAMES.lastIndex) {
                            Box(
                                modifier = Modifier
                                    .padding(start = 13.dp)
                                    .width(2.dp)
                                    .height(8.dp)
                                    .background(SurfaceVariant)
                            )
                        }
                    }
                }
            }
        }

        // Video picker
        item {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                color = Surface,
                border = BorderStroke(1.dp, SurfaceVariant)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    if (viewModel.videoUri != null) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Icon(Icons.Filled.VideoFile, contentDescription = null, tint = Accent, modifier = Modifier.size(20.dp))
                            Text(viewModel.videoName, fontSize = 13.sp, color = OnSurface, modifier = Modifier.weight(1f))
                            TextButton(onClick = onPickVideo) {
                                Text("Change", fontSize = 12.sp, color = Primary)
                            }
                        }
                    } else {
                        OutlinedButton(
                            onClick = onPickVideo,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(80.dp),
                            shape = RoundedCornerShape(12.dp),
                            border = BorderStroke(1.dp, SurfaceVariant),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = OnSurfaceMuted)
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Icon(Icons.Outlined.VideoLibrary, contentDescription = null, modifier = Modifier.size(28.dp))
                                Spacer(Modifier.height(4.dp))
                                Text("Select assembly video", fontSize = 13.sp)
                            }
                        }
                    }
                }
            }
        }

        // Validate button
        item {
            Button(
                onClick = onProcess,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                enabled = viewModel.videoUri != null && !viewModel.isProcessing,
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Primary,
                    disabledContainerColor = SurfaceVariant
                )
            ) {
                if (viewModel.isProcessing) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = Color.White,
                        strokeWidth = 2.dp
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(viewModel.statusMessage, fontWeight = FontWeight.Bold)
                } else {
                    Icon(Icons.Filled.Shield, contentDescription = null, modifier = Modifier.size(20.dp))
                    Spacer(Modifier.width(10.dp))
                    Text("Validate SOP Compliance", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                }
            }
        }

        // Progress bar
        if (viewModel.isProcessing) {
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    color = Surface
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(16.dp),
                                color = Primary,
                                strokeWidth = 2.dp
                            )
                            Text(viewModel.statusMessage, fontSize = 12.sp, color = OnSurface)
                        }
                        Spacer(Modifier.height(10.dp))
                        LinearProgressIndicator(
                            progress = { viewModel.progress / 100f },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(6.dp)
                                .clip(RoundedCornerShape(3.dp)),
                            color = Primary,
                            trackColor = SurfaceVariant
                        )
                        Text(
                            "${viewModel.progress}%",
                            fontSize = 11.sp,
                            color = OnSurfaceMuted,
                            textAlign = TextAlign.Center,
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(top = 6.dp)
                        )
                    }
                }
            }
        }

        // Error
        if (viewModel.errorMessage != null) {
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    color = Error.copy(alpha = 0.1f),
                    border = BorderStroke(1.dp, Error.copy(alpha = 0.3f))
                ) {
                    Row(
                        modifier = Modifier.padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Icon(Icons.Filled.Warning, contentDescription = null, tint = Error)
                        Text(viewModel.errorMessage!!, fontSize = 12.sp, color = Error, modifier = Modifier.weight(1f))
                    }
                }
            }
        }

        // Results
        val result = viewModel.result
        if (result != null) {
            // Verdict banner
            item {
                val bgColor = if (result.passed) Success.copy(alpha = 0.1f) else Error.copy(alpha = 0.1f)
                val borderColor = if (result.passed) Success else Error
                val emoji = if (result.passed) "✅" else "❌"
                val title = if (result.passed) "SOP COMPLIANCE PASSED" else "SOP VIOLATION DETECTED"

                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    color = bgColor,
                    border = BorderStroke(2.dp, borderColor)
                ) {
                    Row(
                        modifier = Modifier.padding(18.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        Text(emoji, fontSize = 28.sp)
                        Column {
                            Text(title, fontWeight = FontWeight.ExtraBold, fontSize = 15.sp, color = borderColor)
                            Text(result.summary, fontSize = 11.sp, color = OnSurfaceMuted)
                        }
                    }
                }
            }

            // Step-by-step results
            result.stepResults.forEach { step ->
                item {
                    StepResultCard(step)
                }
            }

            // Meta info
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    color = Surface,
                    border = BorderStroke(1.dp, SurfaceVariant)
                ) {
                    Column(
                        modifier = Modifier.padding(14.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Text(
                            "%.1fs · %d frames · Edge inference".format(result.processingTimeS, result.totalFrames),
                            fontSize = 11.sp,
                            color = OnSurfaceMuted
                        )
                        OutlinedButton(
                            onClick = { viewModel.reset() },
                            shape = RoundedCornerShape(8.dp),
                            border = BorderStroke(1.dp, Primary)
                        ) {
                            Text("New Validation", color = Primary, fontWeight = FontWeight.SemiBold)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StepResultCard(step: StepResult) {
    val borderColor = if (step.isCorrect) Success.copy(alpha = 0.4f) else Error.copy(alpha = 0.4f)
    val leftColor = if (step.isCorrect) Success else Error

    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        color = Surface,
        border = BorderStroke(1.dp, borderColor)
    ) {
        Row(modifier = Modifier.fillMaxWidth()) {
            // Left accent bar
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(IntrinsicSize.Max)
                    .background(leftColor)
            )
            Column(modifier = Modifier.padding(14.dp)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        if (step.isCorrect) "✅" else "❌",
                        fontSize = 16.sp
                    )
                    Text(
                        "Position ${step.position}",
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                        color = OnSurface,
                        modifier = Modifier.weight(1f)
                    )
                    Text(
                        "${(step.similarity * 100).toInt()}% match",
                        fontSize = 11.sp,
                        color = OnSurfaceMuted
                    )
                }
                Spacer(Modifier.height(4.dp))
                Text(
                    "Expected: ${step.expectedTask}",
                    fontSize = 12.sp,
                    color = OnSurfaceMuted
                )
                if (!step.isCorrect) {
                    Text(
                        "Detected: ${step.detectedTask}",
                        fontSize = 12.sp,
                        color = Error,
                        fontWeight = FontWeight.Medium
                    )
                }

                // Keyframe thumbnail
                step.keyframe?.let { bmp ->
                    Spacer(Modifier.height(8.dp))
                    Image(
                        bitmap = bmp.asImageBitmap(),
                        contentDescription = "Keyframe",
                        modifier = Modifier
                            .width(120.dp)
                            .height(80.dp)
                            .clip(RoundedCornerShape(8.dp))
                    )
                }
            }
        }
    }
}
