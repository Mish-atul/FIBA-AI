package com.fibaai.soplens

import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.fibaai.soplens.ml.SOPClassifier
import com.fibaai.soplens.ui.ActionSearchScreen
import com.fibaai.soplens.ui.SOPScreen
import com.fibaai.soplens.ui.SOPViewModel
import com.fibaai.soplens.ui.ActionViewModel
import com.fibaai.soplens.ui.theme.*

class MainActivity : ComponentActivity() {

    private lateinit var classifier: SOPClassifier

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        classifier = SOPClassifier(applicationContext)

        setContent {
            SOPLensTheme {
                val sopVm: SOPViewModel = viewModel()
                val actionVm: ActionViewModel = viewModel()
                var selectedTab by remember { mutableIntStateOf(0) }

                // Video picker for SOP
                val sopVideoPicker = rememberLauncherForActivityResult(
                    ActivityResultContracts.GetContent()
                ) { uri: Uri? ->
                    uri?.let { sopVm.setVideo(it, getFileName(it) ?: "video.mp4") }
                }

                // Video picker for Action Search
                val actionVideoPicker = rememberLauncherForActivityResult(
                    ActivityResultContracts.GetContent()
                ) { uri: Uri? ->
                    uri?.let { actionVm.setVideo(it, getFileName(it) ?: "video.mp4") }
                }

                Scaffold(
                    containerColor = Background,
                    bottomBar = {
                        NavigationBar(
                            containerColor = Surface,
                            contentColor = OnSurface,
                            tonalElevation = 0.dp
                        ) {
                            BottomNavItem(
                                selected = selectedTab == 0,
                                onClick = { selectedTab = 0 },
                                icon = Icons.Outlined.Search,
                                selectedIcon = Icons.Filled.Search,
                                label = "Action Search"
                            )
                            BottomNavItem(
                                selected = selectedTab == 1,
                                onClick = { selectedTab = 1 },
                                icon = Icons.Outlined.Shield,
                                selectedIcon = Icons.Filled.Shield,
                                label = "SOP Compliance"
                            )
                        }
                    }
                ) { padding ->
                    Box(modifier = Modifier.padding(padding)) {
                        AnimatedContent(
                            targetState = selectedTab,
                            transitionSpec = {
                                fadeIn() togetherWith fadeOut()
                            },
                            label = "tab"
                        ) { tab ->
                            when (tab) {
                                0 -> ActionSearchScreen(
                                    viewModel = actionVm,
                                    classifier = classifier,
                                    context = applicationContext,
                                    onPickVideo = { actionVideoPicker.launch("video/*") }
                                )
                                1 -> SOPScreen(
                                    viewModel = sopVm,
                                    onPickVideo = { sopVideoPicker.launch("video/*") },
                                    onProcess = { sopVm.processVideo(classifier, applicationContext) }
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::classifier.isInitialized) classifier.close()
    }

    private fun getFileName(uri: Uri): String? {
        val cursor = contentResolver.query(uri, null, null, null, null)
        return cursor?.use {
            if (it.moveToFirst()) {
                val idx = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (idx >= 0) it.getString(idx) else null
            } else null
        }
    }
}

@Composable
fun RowScope.BottomNavItem(
    selected: Boolean,
    onClick: () -> Unit,
    icon: ImageVector,
    selectedIcon: ImageVector,
    label: String
) {
    NavigationBarItem(
        selected = selected,
        onClick = onClick,
        icon = {
            Icon(
                if (selected) selectedIcon else icon,
                contentDescription = label,
                modifier = Modifier.size(22.dp)
            )
        },
        label = { Text(label, style = MaterialTheme.typography.labelSmall) },
        colors = NavigationBarItemDefaults.colors(
            selectedIconColor = Primary,
            selectedTextColor = Primary,
            unselectedIconColor = OnSurfaceMuted,
            unselectedTextColor = OnSurfaceMuted,
            indicatorColor = Primary.copy(alpha = 0.12f)
        )
    )
}
