package net.stanback.turnmark

import androidx.compose.foundation.layout.*
import androidx.compose.material3.adaptive.collectFoldingFeaturesAsState
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.positionInWindow
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.window.layout.FoldingFeature

// Bounds are reported in window pixels. Convert relative to this content area,
// which may already be inset for navigation, system bars or a neighboring pane.
@Composable fun AdaptiveWorkspace(
    modifier: Modifier = Modifier, name: String,
    primary: @Composable () -> Unit, supporting: @Composable (tabletop: Boolean) -> Unit,
    compact: @Composable () -> Unit,
    onPaneChange: () -> Unit = {},
) {
    val folds by collectFoldingFeaturesAsState()
    val density = LocalDensity.current
    var origin by remember { mutableStateOf(Offset.Zero) }
    BoxWithConstraints(modifier.fillMaxSize().onGloballyPositioned { origin = it.positionInWindow() }) {
        val fold = folds.firstOrNull { it.isSeparating || it.occlusionType == FoldingFeature.OcclusionType.FULL }
        val horizontal = fold?.orientation == FoldingFeature.Orientation.HORIZONTAL
        val before = fold?.let { with(density) {
            (if (horizontal) it.bounds.top - origin.y else it.bounds.left - origin.x).toDp()
        } }
        val after = fold?.let { with(density) {
            (if (horizontal) it.bounds.bottom - origin.y else it.bounds.right - origin.x).toDp()
        } }
        val extent = if (horizontal) maxHeight else maxWidth
        val usableFold = before != null && after != null && before > 0.dp && after < extent
        val expanded = usableFold || (maxWidth >= 700.dp && maxHeight >= 400.dp && density.fontScale < 1.5f)
        val arrangement = if (!expanded) "compact" else if (usableFold && horizontal) "tabletop" else "expanded"
        // Capture the caller's focus before movable content is reattached.
        LaunchedEffect(arrangement) { withFrameNanos { }; onPaneChange() }
        if (!expanded) Box(Modifier.fillMaxSize().testTag("$name-compact")) { compact() }
        else if (usableFold && horizontal) {
            Column(Modifier.fillMaxSize().testTag("$name-tabletop")) {
                Box(Modifier.fillMaxWidth().height((before!! - 12.dp).coerceAtLeast(0.dp))) { supporting(true) }
                Spacer(Modifier.height((after!! - before + 24.dp).coerceAtLeast(24.dp)))
                Box(Modifier.fillMaxWidth().weight(1f)) { primary() }
            }
        } else {
            Row(Modifier.fillMaxSize().testTag("$name-expanded")) {
                val first = if (usableFold) Modifier.width((before!! - 12.dp).coerceAtLeast(0.dp)) else Modifier.weight(1f)
                Box(first.fillMaxHeight()) { primary() }
                Spacer(Modifier.width(if (usableFold) (after!! - before!! + 24.dp).coerceAtLeast(24.dp) else 0.dp))
                Box(Modifier.weight(1f).fillMaxHeight()) { supporting(false) }
            }
        }
    }
}
