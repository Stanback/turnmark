package net.stanback.turnmark

import android.content.Context
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.window.layout.FoldingFeature
import androidx.window.testing.layout.FoldingFeature as TestFold
import androidx.window.testing.layout.TestWindowLayoutInfo
import androidx.window.testing.layout.WindowLayoutInfoPublisherRule
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AdaptiveLayoutTest {
    @get:Rule(order = 0) val windows = WindowLayoutInfoPublisherRule()
    @get:Rule(order = 1) val compose = createAndroidComposeRule<MainActivity>()

    @Before fun clearSavedState() {
        ApplicationProvider.getApplicationContext<Context>().getSharedPreferences("turnmark", Context.MODE_PRIVATE).edit().clear().commit()
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("tryExample").performScrollTo().performClick()
    }

    @Test fun foldedPanesAvoidTheHingeAndPreserveEntry() {
        compose.onNodeWithTag("nav-Convert").performClick()
        compose.onNodeWithTag("timeInput").performScrollTo().performClick().performTextReplacement("1:00")
        val book = TestFold(compose.activity, size = 20, state = FoldingFeature.State.HALF_OPENED,
            orientation = FoldingFeature.Orientation.VERTICAL)
        windows.overrideWindowLayoutInfo(TestWindowLayoutInfo(listOf(book)))
        compose.waitUntil(5_000) { compose.onAllNodesWithTag("converter-expanded").fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithTag("timeInput").assertTextContains("1:00").assertIsFocused()
        compose.onNodeWithTag("timeInput").performTextInput(".25")
        compose.onNodeWithTag("timeInput").performImeAction()
        val input = compose.onNodeWithTag("timeInput").fetchSemanticsNode().boundsInWindow
        val result = compose.onNodeWithTag("resultTime").fetchSemanticsNode().boundsInWindow
        assertTrue("Entry must stay before the hinge", input.right <= book.bounds.left)
        assertTrue("Complete result must stay after the hinge", result.left >= book.bounds.right)
        capture("android-book-test")

        val tabletop = TestFold(compose.activity, size = 20, state = FoldingFeature.State.HALF_OPENED,
            orientation = FoldingFeature.Orientation.HORIZONTAL)
        windows.overrideWindowLayoutInfo(TestWindowLayoutInfo(listOf(tabletop)))
        compose.waitUntil(5_000) { compose.onAllNodesWithTag("converter-tabletop").fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithTag("timeInput").assertTextContains("1:00.25")
        val top = compose.onNodeWithTag("resultTime").fetchSemanticsNode().boundsInWindow
        val bottom = compose.onNodeWithTag("timeInput").fetchSemanticsNode().boundsInWindow
        assertTrue("Result belongs above the hinge", top.bottom <= tabletop.bounds.top)
        assertTrue("Entry belongs below the hinge", bottom.top >= tabletop.bounds.bottom)
        capture("android-tabletop-test")
        windows.overrideWindowLayoutInfo(TestWindowLayoutInfo(emptyList()))
        compose.waitUntil(5_000) { compose.onAllNodesWithTag("converter-tabletop").fetchSemanticsNodes().isEmpty() }
        compose.onNodeWithTag("timeInput").assertTextContains("1:00.25")
    }

    @Test fun benchmarkSheetKeepsItsOriginalSwimAcrossPaneChanges() {
        compose.onNodeWithTag("openBenchmarks").performScrollTo().performClick()
        compose.onNodeWithTag("benchmarkOriginalTime").assertTextEquals("58.32")
        val book = TestFold(compose.activity, size = 20, state = FoldingFeature.State.HALF_OPENED, orientation = FoldingFeature.Orientation.VERTICAL)
        windows.overrideWindowLayoutInfo(TestWindowLayoutInfo(listOf(book)))
        compose.onNodeWithTag("benchmarkSummary").assertTextEquals("A standard")
        val tabletop = TestFold(compose.activity, size = 20, state = FoldingFeature.State.HALF_OPENED, orientation = FoldingFeature.Orientation.HORIZONTAL)
        windows.overrideWindowLayoutInfo(TestWindowLayoutInfo(listOf(tabletop)))
        compose.onNodeWithTag("benchmarkOriginalTime").assertTextEquals("58.32")
        compose.onNodeWithTag("closeBenchmarks").performScrollTo().performClick()
        compose.onNodeWithTag("timeInput").assertTextContains("58.32")
    }

    private fun capture(name: String) {
        if (InstrumentationRegistry.getArguments().getString("turnmarkScreenshots") != "true") return
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val bitmap = instrumentation.uiAutomation.takeScreenshot()
        try { instrumentation.targetContext.openFileOutput("$name.png", android.content.Context.MODE_PRIVATE).use {
            bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it)
        } } finally { bitmap.recycle() }
    }
}
