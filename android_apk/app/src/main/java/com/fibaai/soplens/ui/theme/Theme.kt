package com.fibaai.soplens.ui.theme

import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val Primary = Color(0xFF6C63FF)
val PrimaryDark = Color(0xFF4F46E5)
val Accent = Color(0xFF22D3EE)
val Background = Color(0xFF0F172A)
val Surface = Color(0xFF1E293B)
val SurfaceVariant = Color(0xFF334155)
val OnSurface = Color(0xFFE2E8F0)
val OnSurfaceMuted = Color(0xFF94A3B8)
val Success = Color(0xFF10B981)
val Error = Color(0xFFEF4444)
val Warning = Color(0xFFFBBF24)

private val DarkColorScheme = darkColorScheme(
    primary = Primary,
    secondary = Accent,
    tertiary = PrimaryDark,
    background = Background,
    surface = Surface,
    surfaceVariant = SurfaceVariant,
    onBackground = OnSurface,
    onSurface = OnSurface,
    onPrimary = Color.White,
    error = Error,
)

@Composable
fun SOPLensTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        content = content
    )
}
