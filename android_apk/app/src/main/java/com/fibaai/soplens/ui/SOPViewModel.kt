package com.fibaai.soplens.ui

import android.graphics.Bitmap
import android.net.Uri
import androidx.compose.runtime.*
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.fibaai.soplens.ml.SOPClassifier
import com.fibaai.soplens.ml.SOPResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/** Manages video selection, processing state, and results. */
class SOPViewModel : ViewModel() {

    var videoUri by mutableStateOf<Uri?>(null)
        private set
    var videoName by mutableStateOf("")
        private set
    var isProcessing by mutableStateOf(false)
        private set
    var progress by mutableIntStateOf(0)
        private set
    var statusMessage by mutableStateOf("")
        private set
    var result by mutableStateOf<SOPResult?>(null)
        private set
    var errorMessage by mutableStateOf<String?>(null)
        private set

    fun setVideo(uri: Uri, name: String) {
        videoUri = uri
        videoName = name
        result = null
        errorMessage = null
    }

    fun processVideo(classifier: SOPClassifier, context: android.content.Context) {
        val uri = videoUri ?: return
        isProcessing = true
        progress = 0
        statusMessage = "Starting…"
        result = null
        errorMessage = null

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val sopResult = classifier.processVideo(context, uri) { pct, msg ->
                    progress = pct
                    statusMessage = msg
                }
                result = sopResult
            } catch (e: Exception) {
                errorMessage = e.message ?: "Processing failed"
            } finally {
                isProcessing = false
            }
        }
    }

    fun reset() {
        videoUri = null
        videoName = ""
        isProcessing = false
        progress = 0
        statusMessage = ""
        result = null
        errorMessage = null
    }
}
