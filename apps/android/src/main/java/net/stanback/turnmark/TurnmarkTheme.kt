package net.stanback.turnmark

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.*

val LocalTurnmarkColors = staticCompositionLocalOf { TurnmarkTokens.light }

@Composable fun TurnmarkTheme(dark: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    val c = if (dark) TurnmarkTokens.dark else TurnmarkTokens.light
    val base = if (dark) darkColorScheme() else lightColorScheme()
    val scheme = base.copy(
        primary = c.accent, onPrimary = if (dark) c.onAction else c.surface,
        primaryContainer = c.selectedSurface, onPrimaryContainer = c.text,
        secondary = c.accent, onSecondary = if (dark) c.onAction else c.surface,
        secondaryContainer = c.selectedSurface, onSecondaryContainer = c.text,
        tertiary = c.accent, onTertiary = if (dark) c.onAction else c.surface,
        tertiaryContainer = c.selectedSurface, onTertiaryContainer = c.text,
        background = c.canvas, onBackground = c.text, surface = c.surface, onSurface = c.text,
        surfaceVariant = c.surfaceRaised, onSurfaceVariant = c.textMuted,
        surfaceContainer = c.surface, surfaceContainerLow = c.surface,
        surfaceContainerLowest = c.canvas, surfaceContainerHigh = c.surfaceRaised,
        surfaceContainerHighest = c.surfaceRaised,
        outline = c.borderControl, outlineVariant = c.borderSubtle, error = c.error,
    )
    CompositionLocalProvider(LocalTurnmarkColors provides c) { MaterialTheme(colorScheme = scheme, content = content) }
}
