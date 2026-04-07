package com.fibaai.soplens.ml

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Color
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.util.Log
import java.nio.FloatBuffer
import kotlin.math.exp

/**
 * On-device SOP classifier using ONNX Runtime.
 *
 * Architecture: YOLOv8n-cls fine-tuned on HATREC assembly dataset.
 * Input:  [1, 3, 224, 224] float tensor (RGB, normalized 0-1)
 * Output: [1, 7] float tensor (logits for 7 assembly tasks)
 *
 * Runs 100% on-device — no network needed.
 */
class SOPClassifier(context: Context) {

    companion object {
        private const val TAG = "SOPClassifier"
        private const val MODEL_FILE = "sop_classifier.onnx"
        private const val IMG_SIZE = 224
        private const val NUM_CLASSES = 7
        private const val WINDOW_SIZE = 5 // Majority vote window

        val TASK_NAMES = arrayOf(
            "Assembling the spring",
            "Placing white plastic part",
            "Screwing-1",
            "Inflating the valve",
            "Placing black plastic part",
            "Screwing-2",
            "Fixing the cable"
        )
    }

    private val env: OrtEnvironment = OrtEnvironment.getEnvironment()
    private val session: OrtSession

    init {
        val modelBytes = context.assets.open(MODEL_FILE).readBytes()
        val opts = OrtSession.SessionOptions().apply {
            setIntraOpNumThreads(2)
        }
        session = env.createSession(modelBytes, opts)
        Log.i(TAG, "Loaded ONNX model: $MODEL_FILE (${modelBytes.size / 1024} KB)")
    }

    /** Classify a single bitmap frame. Returns (taskId, confidence). */
    fun classifyFrame(bitmap: Bitmap): Pair<Int, Float> {
        val resized = Bitmap.createScaledBitmap(bitmap, IMG_SIZE, IMG_SIZE, true)
        val inputBuffer = FloatBuffer.allocate(3 * IMG_SIZE * IMG_SIZE)

        // Convert bitmap to CHW float tensor (RGB, 0-1 normalized)
        for (y in 0 until IMG_SIZE) {
            for (x in 0 until IMG_SIZE) {
                val pixel = resized.getPixel(x, y)
                val r = Color.red(pixel) / 255.0f
                val g = Color.green(pixel) / 255.0f
                val b = Color.blue(pixel) / 255.0f
                inputBuffer.put(y * IMG_SIZE + x, r)                               // R channel
                inputBuffer.put(IMG_SIZE * IMG_SIZE + y * IMG_SIZE + x, g)          // G channel
                inputBuffer.put(2 * IMG_SIZE * IMG_SIZE + y * IMG_SIZE + x, b)      // B channel
            }
        }
        inputBuffer.rewind()

        val shape = longArrayOf(1, 3, IMG_SIZE.toLong(), IMG_SIZE.toLong())
        val inputTensor = OnnxTensor.createTensor(env, inputBuffer, shape)

        val results = session.run(mapOf("images" to inputTensor))
        val output = (results[0].value as Array<FloatArray>)[0]

        inputTensor.close()
        results.close()

        if (resized != bitmap) resized.recycle()

        // Softmax
        val probs = softmax(output)
        val maxIdx = probs.indices.maxByOrNull { probs[it] } ?: 0
        return Pair(maxIdx, probs[maxIdx])
    }

    /**
     * Process a full video: extract frames, classify each, apply majority vote,
     * detect task transitions, and validate SOP sequence.
     *
     * @return SOPResult with pass/fail and step-by-step details
     */
    fun processVideo(
        context: Context,
        videoUri: Uri,
        onProgress: (Int, String) -> Unit
    ): SOPResult {
        val startTime = System.currentTimeMillis()

        onProgress(5, "Opening video…")
        val retriever = MediaMetadataRetriever()
        retriever.setDataSource(context, videoUri)

        val durationMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLong() ?: 0
        val fps = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_CAPTURE_FRAMERATE)?.toFloat() ?: 30f
        val totalFrames = ((durationMs / 1000.0) * fps).toInt().coerceAtLeast(1)

        // Sample frames evenly (aim for ~2 fps for efficiency)
        val sampleRate = (fps / 2.0).toInt().coerceAtLeast(1)
        val frameTimes = mutableListOf<Long>()
        val stepUs = (1_000_000.0 / fps * sampleRate).toLong()
        var timeUs = 0L
        while (timeUs < durationMs * 1000) {
            frameTimes.add(timeUs)
            timeUs += stepUs
        }

        onProgress(10, "Extracting & classifying ${frameTimes.size} frames…")

        // Classify each sampled frame
        val predictions = mutableListOf<Int>()
        val confidences = mutableListOf<Float>()
        val keyframes = mutableMapOf<Int, Bitmap>() // taskId -> representative frame

        for ((idx, timeUs2) in frameTimes.withIndex()) {
            val frame = retriever.getFrameAtTime(timeUs2, MediaMetadataRetriever.OPTION_CLOSEST)
            if (frame != null) {
                val (taskId, conf) = classifyFrame(frame)
                predictions.add(taskId)
                confidences.add(conf)

                // Save best keyframe per task
                if (!keyframes.containsKey(taskId) || conf > (confidences.getOrNull(keyframes[taskId]?.let { predictions.indexOf(taskId) } ?: 0) ?: 0f)) {
                    keyframes[taskId] = frame.copy(frame.config, false)
                }
            }

            val pct = 10 + (idx * 70 / frameTimes.size.coerceAtLeast(1))
            if (idx % 5 == 0) {
                onProgress(pct.coerceAtMost(80), "Classifying frame ${idx + 1}/${frameTimes.size}…")
            }
        }

        retriever.release()

        onProgress(85, "Analyzing task transitions…")

        // Apply sliding window majority vote
        val smoothed = majorityVote(predictions, WINDOW_SIZE)

        // Detect transitions (task changes)
        val segments = mutableListOf<TaskSegment>()
        if (smoothed.isNotEmpty()) {
            var segStart = 0
            var currentTask = smoothed[0]
            for (i in 1..smoothed.lastIndex) {
                if (smoothed[i] != currentTask) {
                    segments.add(TaskSegment(
                        taskId = currentTask,
                        startFrame = segStart * sampleRate,
                        endFrame = i * sampleRate,
                        keyframe = keyframes[currentTask]
                    ))
                    segStart = i
                    currentTask = smoothed[i]
                }
            }
            // Last segment
            segments.add(TaskSegment(
                taskId = currentTask,
                startFrame = segStart * sampleRate,
                endFrame = smoothed.size * sampleRate,
                keyframe = keyframes[currentTask]
            ))
        }

        onProgress(90, "Validating SOP sequence…")

        // Build detected order (unique tasks in order of first appearance)
        val detectedOrder = mutableListOf<Int>()
        for (seg in segments) {
            if (detectedOrder.isEmpty() || detectedOrder.last() != seg.taskId) {
                detectedOrder.add(seg.taskId)
            }
        }

        // Expected order: 0, 1, 2, 3, 4, 5, 6
        val expectedOrder = (0 until NUM_CLASSES).toList()

        // Compare step by step
        val stepResults = mutableListOf<StepResult>()
        for (i in 0 until NUM_CLASSES) {
            val expected = expectedOrder.getOrNull(i) ?: i
            val detected = detectedOrder.getOrNull(i) ?: -1
            val isCorrect = expected == detected
            val similarity = if (isCorrect) 1.0f else 0.0f
            stepResults.add(StepResult(
                position = i + 1,
                expectedStep = expected,
                expectedTask = TASK_NAMES.getOrElse(expected) { "Unknown" },
                detectedStep = detected,
                detectedTask = if (detected >= 0) TASK_NAMES.getOrElse(detected) { "Unknown" } else "Not detected",
                isCorrect = isCorrect,
                similarity = similarity,
                keyframe = if (detected >= 0) keyframes[detected] else null
            ))
        }

        val passed = detectedOrder == expectedOrder
        val processingTime = (System.currentTimeMillis() - startTime) / 1000.0f

        onProgress(100, if (passed) "✅ SOP PASSED" else "❌ SOP VIOLATION")

        return SOPResult(
            passed = passed,
            stepResults = stepResults,
            segments = segments,
            totalFrames = totalFrames,
            fps = fps,
            processingTimeS = processingTime,
            detectedOrder = detectedOrder,
            summary = if (passed) {
                "All ${NUM_CLASSES} steps performed in correct sequence"
            } else {
                val violations = stepResults.filter { !it.isCorrect }
                "${violations.size} step(s) out of sequence"
            }
        )
    }

    private fun softmax(logits: FloatArray): FloatArray {
        val maxVal = logits.max() ?: 0f
        val exps = logits.map { exp((it - maxVal).toDouble()).toFloat() }
        val sumExps = exps.sum()
        return exps.map { it / sumExps }.toFloatArray()
    }

    private fun majorityVote(predictions: List<Int>, windowSize: Int): List<Int> {
        if (predictions.isEmpty()) return emptyList()
        val half = windowSize / 2
        return predictions.indices.map { i ->
            val start = (i - half).coerceAtLeast(0)
            val end = (i + half).coerceAtMost(predictions.lastIndex)
            val window = predictions.subList(start, end + 1)
            window.groupingBy { it }.eachCount().maxByOrNull { it.value }?.key ?: predictions[i]
        }
    }

    fun close() {
        session.close()
        env.close()
    }
}

// ── Data classes ─────────────────────────────────────

data class TaskSegment(
    val taskId: Int,
    val startFrame: Int,
    val endFrame: Int,
    val keyframe: Bitmap?
)

data class StepResult(
    val position: Int,
    val expectedStep: Int,
    val expectedTask: String,
    val detectedStep: Int,
    val detectedTask: String,
    val isCorrect: Boolean,
    val similarity: Float,
    val keyframe: Bitmap?
)

data class SOPResult(
    val passed: Boolean,
    val stepResults: List<StepResult>,
    val segments: List<TaskSegment>,
    val totalFrames: Int,
    val fps: Float,
    val processingTimeS: Float,
    val detectedOrder: List<Int>,
    val summary: String
)
