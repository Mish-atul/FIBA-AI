package com.fibaai.soplens.ui

import android.content.Context
import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.net.Uri
import androidx.compose.runtime.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fibaai.soplens.ml.SOPClassifier
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Represents an action detected in a video frame.
 */
data class DetectedAction(
    val frameIndex: Int,
    val timeMs: Long,
    val taskId: Int,
    val taskName: String,
    val confidence: Float,
    val thumbnail: Bitmap?
)

/**
 * Result of an action search.
 */
data class ActionSearchResult(
    val query: String,
    val matchedActions: List<DetectedAction>,
    val allActions: List<DetectedAction>,
    val totalFrames: Int,
    val processingTimeS: Float
)

/**
 * ViewModel for the Action Search tab.
 * Processes video, classifies frames, and filters by query.
 */
class ActionViewModel : ViewModel() {

    var videoUri by mutableStateOf<Uri?>(null)
        private set
    var videoName by mutableStateOf("")
        private set
    var query by mutableStateOf("")
    var isProcessing by mutableStateOf(false)
        private set
    var progress by mutableIntStateOf(0)
        private set
    var statusMessage by mutableStateOf("")
        private set
    var result by mutableStateOf<ActionSearchResult?>(null)
        private set
    var errorMessage by mutableStateOf<String?>(null)
        private set

    // Cached results from last video processing
    private var cachedActions: List<DetectedAction>? = null
    private var cachedVideoUri: Uri? = null

    fun setVideo(uri: Uri, name: String) {
        videoUri = uri
        videoName = name
        result = null
        errorMessage = null
        // Invalidate cache if different video
        if (uri != cachedVideoUri) {
            cachedActions = null
            cachedVideoUri = null
        }
    }

    fun searchActions(classifier: SOPClassifier, context: Context) {
        val uri = videoUri ?: return
        val searchQuery = query.trim()
        if (searchQuery.isEmpty()) {
            errorMessage = "Please enter a search query"
            return
        }

        isProcessing = true
        progress = 0
        statusMessage = "Starting…"
        result = null
        errorMessage = null

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val actions: List<DetectedAction>

                // Use cached results if same video
                if (cachedActions != null && uri == cachedVideoUri) {
                    actions = cachedActions!!
                    progress = 80
                    statusMessage = "Using cached analysis…"
                } else {
                    actions = processVideoFrames(classifier, context, uri)
                    cachedActions = actions
                    cachedVideoUri = uri
                }

                statusMessage = "Searching for: $searchQuery"
                progress = 90

                // Match query against task names
                val queryLower = searchQuery.lowercase()
                val matched = actions.filter { action ->
                    action.taskName.lowercase().contains(queryLower) ||
                    matchesActionKeywords(queryLower, action.taskName)
                }

                progress = 100
                result = ActionSearchResult(
                    query = searchQuery,
                    matchedActions = matched,
                    allActions = actions,
                    totalFrames = actions.size,
                    processingTimeS = 0f // Will be set properly
                )
            } catch (e: Exception) {
                errorMessage = e.message ?: "Processing failed"
            } finally {
                isProcessing = false
            }
        }
    }

    private fun processVideoFrames(
        classifier: SOPClassifier,
        context: Context,
        uri: Uri
    ): List<DetectedAction> {
        val startTime = System.currentTimeMillis()
        statusMessage = "Opening video…"
        progress = 5

        val retriever = MediaMetadataRetriever()
        retriever.setDataSource(context, uri)

        val durationMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLong() ?: 0
        val fps = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_CAPTURE_FRAMERATE)?.toFloat() ?: 30f

        // Sample at ~2 fps
        val sampleRate = (fps / 2.0).toInt().coerceAtLeast(1)
        val stepUs = (1_000_000.0 / fps * sampleRate).toLong()
        val frameTimes = mutableListOf<Long>()
        var timeUs = 0L
        while (timeUs < durationMs * 1000) {
            frameTimes.add(timeUs)
            timeUs += stepUs
        }

        statusMessage = "Classifying ${frameTimes.size} frames…"
        progress = 10

        val actions = mutableListOf<DetectedAction>()

        for ((idx, timeUs2) in frameTimes.withIndex()) {
            val frame = retriever.getFrameAtTime(timeUs2, MediaMetadataRetriever.OPTION_CLOSEST)
            if (frame != null) {
                val (taskId, conf) = classifier.classifyFrame(frame)
                actions.add(DetectedAction(
                    frameIndex = idx,
                    timeMs = timeUs2 / 1000,
                    taskId = taskId,
                    taskName = SOPClassifier.TASK_NAMES.getOrElse(taskId) { "Unknown" },
                    confidence = conf,
                    thumbnail = Bitmap.createScaledBitmap(frame, 160, 120, true)
                ))
            }
            val pct = 10 + (idx * 70 / frameTimes.size.coerceAtLeast(1))
            if (idx % 5 == 0) {
                progress = pct.coerceAtMost(80)
                statusMessage = "Frame ${idx + 1}/${frameTimes.size}…"
            }
        }

        retriever.release()
        return actions
    }

    /**
     * Fuzzy match query keywords to action names.
     */
    private fun matchesActionKeywords(query: String, taskName: String): Boolean {
        val keywordMap = mapOf(
            "screw" to listOf("Screwing-1", "Screwing-2"),
            "spring" to listOf("Assembling the spring"),
            "assemble" to listOf("Assembling the spring"),
            "white" to listOf("Placing white plastic part"),
            "plastic" to listOf("Placing white plastic part", "Placing black plastic part"),
            "black" to listOf("Placing black plastic part"),
            "inflate" to listOf("Inflating the valve"),
            "valve" to listOf("Inflating the valve"),
            "cable" to listOf("Fixing the cable"),
            "fix" to listOf("Fixing the cable"),
            "place" to listOf("Placing white plastic part", "Placing black plastic part"),
            "wire" to listOf("Fixing the cable"),
        )

        for ((keyword, matchNames) in keywordMap) {
            if (query.contains(keyword) && matchNames.any { it == taskName }) {
                return true
            }
        }
        return false
    }

    fun reset() {
        videoUri = null
        videoName = ""
        query = ""
        isProcessing = false
        progress = 0
        statusMessage = ""
        result = null
        errorMessage = null
        cachedActions = null
        cachedVideoUri = null
    }
}
