package net.stanback.turnmark

import android.app.Activity
import android.app.Instrumentation
import android.content.Intent
import android.net.Uri
import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.graphics.Bitmap
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import java.util.concurrent.atomic.AtomicReference
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ConverterTest {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()

    @Before fun clearSavedState() {
        ApplicationProvider.getApplicationContext<Context>().getSharedPreferences("turnmark", Context.MODE_PRIVATE).edit().clear().commit()
        SwimHistoryStore(ApplicationProvider.getApplicationContext()).use { store -> store.load().forEach { store.remove(it.id) } }
        compose.activityRule.scenario.recreate()
    }

    @Test fun conversionKeepsOriginalAndSupportsContextualDetails() {
        compose.onNodeWithTag("timeInput").performScrollTo().performClick().performTextReplacement("1:00")
        compose.onNodeWithTag("timeInput").performImeAction()
        compose.waitUntil(5_000) { compose.onAllNodesWithTag("nav-Convert").fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithTag("nav-Saved").assertDoesNotExist()
        compose.onNodeWithTag("nav-Method").assertDoesNotExist()
        compose.onNodeWithTag("inputCourse-LCM").performScrollTo().performClick()
        compose.onNodeWithTag("targetCourse-SCY").performScrollTo().performClick()
        compose.onNodeWithTag("resultTime").assertTextEquals("52.44")
        compose.onNodeWithTag("resultContext").assertTextEquals("100 yd Freestyle · SCY · Women")
        compose.onNodeWithTag("conversionDetails").performScrollTo().performClick()
        compose.onNodeWithText("Conversion details").assertExists()
        compose.onNodeWithText("100 m Freestyle · LCM · Women").assertExists()
        compose.onNodeWithText("Edition:", substring = true).performScrollTo().assertIsDisplayed()
        capture("android-details")
        compose.onNodeWithText("Done").performScrollTo().performClick()
        compose.onNodeWithTag("resultTime").performScrollTo()
        capture("android-converter-result")
        compose.onNodeWithTag("timeInput").performScrollTo()
        capture("android-converter-input")
        compose.onNodeWithTag("methodology").performScrollTo().performClick()
        compose.onNodeWithText("How comparisons work").assertExists()
        compose.onNodeWithText("Done").performScrollTo().performClick()
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText("No logged swims").assertExists()
        compose.onNodeWithTag("nav-Convert").performClick()
        compose.onNodeWithTag("timeInput").assertTextContains("1:00")
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("timeInput").assertTextContains("1:00")
    }

    @Test fun sharingUsesOriginalValuesWithoutRecordingAResult() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val captured = AtomicReference<Intent>()
        val monitor = object : Instrumentation.ActivityMonitor() {
            override fun onStartActivity(intent: Intent): Instrumentation.ActivityResult? {
                if (intent.action != Intent.ACTION_CHOOSER) return null
                captured.set(Intent(intent)); return Instrumentation.ActivityResult(Activity.RESULT_CANCELED, null)
            }
        }
        instrumentation.addMonitor(monitor)
        try {
            compose.onNodeWithTag("timeInput").performScrollTo().performTextReplacement("1:00")
            compose.onNodeWithTag("timeInput").performImeAction()
            compose.onNodeWithTag("shareSwim").performScrollTo().performClick()
            assertSharedTime(captured.get(), "1:00")
        } finally { instrumentation.removeMonitor(monitor) }
        compose.onNodeWithTag("shareSwim").performScrollTo().performClick()
        val automation = instrumentation.uiAutomation
        compose.waitUntil(5_000) { automation.rootInActiveWindow?.packageName?.toString() in listOf("android", "com.android.intentresolver") }
        capture("android-share")
        assertTrue(automation.performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK))
        compose.waitUntil(5_000) { automation.rootInActiveWindow?.packageName?.toString() == "net.stanback.turnmark" }
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText("No logged swims").assertExists()
    }

    @Test fun earlierBookmarkRemainsSeparateFromActualTimes() {
        ApplicationProvider.getApplicationContext<Context>().getSharedPreferences("turnmark", Context.MODE_PRIVATE)
            .edit().putString("saved", Draft(time = "57.25").encode()).commit()
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText("No logged swims").assertExists()
        compose.onNodeWithText("Open previous comparison").performScrollTo().performClick()
        compose.onNodeWithText("Use these inputs").performScrollTo().performClick()
        compose.onNodeWithTag("timeInput").assertTextContains("57.25")
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText("Open previous comparison").performScrollTo().performClick()
        compose.onNodeWithText("Remove previous comparison").performScrollTo().performClick()
        compose.activityRule.scenario.recreate()
        compose.onNodeWithText("Open previous comparison").assertDoesNotExist()
        compose.onNodeWithText("No logged swims").assertExists()
    }

    @Test fun actualTimeCanBeRecordedDirectlyFromMyTimes() {
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithTag("recordTime").performClick()
        compose.onNodeWithTag("confirmLog").assertIsNotEnabled()
        compose.onNodeWithTag("logTime").performTextReplacement("57.99")
        compose.onNodeWithTag("confirmLog").performClick()
        compose.onNodeWithText("57.99 · PB").assertExists()
        compose.onNodeWithTag("recordTime").performClick()
        compose.onNodeWithTag("logTime").performTextReplacement("1:00")
        compose.onNodeWithTag("confirmLog").performClick()
        compose.onNodeWithText("1:00").assertExists()
        compose.onNodeWithTag("times-Best").performClick()
        compose.onNodeWithText("57.99 · PB").assertExists()
        compose.onNodeWithText("1:00").assertDoesNotExist()
        capture("android-my-times")
    }

    @Test fun longEventAndMeetKeepRecordingAndComparisonReachable() {
        val meet = "Pacific Northwest Masters Long Course Championships"
        compose.onNodeWithTag("timeInput").performScrollTo().performTextReplacement("2:12.34")
        compose.onNodeWithTag("timeInput").performImeAction()
        compose.onNodeWithText("Stroke: Freestyle").performScrollTo().performClick()
        compose.onNodeWithText("Individual medley").performClick()
        compose.onNodeWithText("Distance: 100 yd").performScrollTo().performClick()
        compose.onNodeWithText("200 yd").performClick()
        compose.onNodeWithTag("resultTime").performScrollTo().assertIsDisplayed()
        capture("android-long-result")
        compose.onNodeWithTag("logSwim").performScrollTo().performClick()
        compose.onNodeWithTag("logMeet").performScrollTo().performTextReplacement(meet)
        capture("android-long-editor")
        compose.onNodeWithTag("confirmLog").performClick()
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText(meet, substring = true).assertExists()
        capture("android-long-meet")
        compose.onNodeWithText("2:12.34 · PB").performScrollTo().performClick()
        compose.onNodeWithText("Compare this swim").performScrollTo().assertIsDisplayed()
        capture("android-long-detail")
        compose.onNodeWithText("Compare this swim").performClick()
        compose.onNodeWithTag("timeInput").performScrollTo().assertTextContains("2:12.34")
        capture("android-long-input")
    }

    @Test fun loggingEditingComparingAndDeletingActualSwims() {
        compose.onNodeWithText("Stroke: Freestyle").performScrollTo().performClick()
        compose.onNodeWithText("Individual medley").performClick()
        compose.onNodeWithTag("unavailableConversion").assertExists()
        compose.onNodeWithTag("logSwim").performScrollTo().performClick()
        compose.onNodeWithTag("logDate").performScrollTo().performTextReplacement("2026-10-17")
        compose.onNodeWithTag("logMeet").performScrollTo().performTextReplacement("Autumn Invitational")
        compose.onNodeWithTag("confirmLog").performClick()
        compose.waitUntil(5_000) { compose.onAllNodesWithTag("nav-My times").fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText("Autumn Invitational · 2026-10-17").assertExists()
        compose.onNodeWithText("58.32 · PB").performClick()
        compose.onNodeWithText("Manually logged performance").assertExists()
        capture("android-history-detail")
        compose.onNodeWithText("Edit swim").performScrollTo().performClick()
        compose.onNodeWithTag("logTime").performTextReplacement("57.99")
        compose.onNodeWithTag("logDate").performScrollTo().performTextReplacement("")
        compose.onNodeWithTag("confirmLog").performClick()
        compose.onNodeWithText("57.99").assertExists()
        compose.onNodeWithText("Unknown date").assertExists()
        compose.onNodeWithText("Compare this swim").performScrollTo().performClick()
        compose.onNodeWithTag("timeInput").assertTextContains("57.99")
        compose.onNodeWithTag("unavailableConversion").assertExists()
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText("57.99 · PB").assertExists()
        capture("android-history")
        compose.onNodeWithText("57.99 · PB").performClick()
        compose.onNodeWithText("Delete swim").performScrollTo().performClick()
        compose.onNodeWithText("Delete this logged swim?").assertExists()
        compose.onAllNodesWithText("Delete swim").onLast().performClick()
        compose.onNodeWithText("No logged swims").assertExists()
    }

    @Test fun documentImportPreviewAndExportPreserveThePortableRecords() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val input = java.io.File(context.cacheDir, "history-test-input.json")
        input.writeBytes(instrumentation.context.assets.open("contract-v1.json").use { it.readBytes() })
        val output = java.io.File(context.cacheDir, "history-test-output.json")
        output.delete()
        val monitor = object : Instrumentation.ActivityMonitor() {
            override fun onStartActivity(intent: Intent): Instrumentation.ActivityResult? = when (intent.action) {
                Intent.ACTION_OPEN_DOCUMENT -> Instrumentation.ActivityResult(Activity.RESULT_OK, Intent().setData(Uri.fromFile(input)))
                Intent.ACTION_CREATE_DOCUMENT -> {
                    assertEquals("application/json", intent.type)
                    Instrumentation.ActivityResult(Activity.RESULT_OK, Intent().setData(Uri.fromFile(output)))
                }
                else -> null
            }
        }
        instrumentation.addMonitor(monitor)
        try {
            compose.onNodeWithTag("nav-My times").performClick()
            compose.onNodeWithText("No logged swims").assertExists()
            compose.onNodeWithText("Import").performClick()
            compose.onNodeWithText("5 new swims · 0 duplicates · 0 rejected").assertExists()
            capture("android-import-review")
            compose.onNodeWithText("Cancel").performClick()
            compose.onNodeWithText("No logged swims").assertExists()
            compose.onNodeWithText("Import").performClick()
            compose.onNodeWithText("5 new swims · 0 duplicates · 0 rejected").assertExists()
            compose.onNodeWithTag("confirmImport").performClick()
            compose.waitUntil(5_000) { compose.onAllNodesWithTag("confirmImport").fetchSemanticsNodes().isEmpty() }
            compose.onNodeWithText("Export").performClick()
            compose.waitUntil(5_000) { output.exists() && output.length() > 0 }
            val exported = HistoryArchive.preview(output.readBytes(), emptyList()).records
            val original = HistoryArchive.preview(input.readBytes(), emptyList()).records
            assertEquals(original.toSet(), exported.toSet())
            compose.onNodeWithText("Import").performClick()
            compose.onNodeWithText("0 new swims · 5 duplicates · 0 rejected").assertExists()
            compose.onNodeWithTag("confirmImport").assertIsNotEnabled()
            compose.onNodeWithText("Cancel").performClick()
        } finally {
            instrumentation.removeMonitor(monitor)
            input.delete(); output.delete()
        }
    }

    private fun assertSharedTime(chooser: Intent?, time: String) {
        assertEquals(Intent.ACTION_CHOOSER, chooser?.action)
        @Suppress("DEPRECATION")
        val send = chooser!!.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)!!
        assertEquals(Intent.ACTION_SEND, send.action)
        assertEquals("text/plain", send.type)
        val url = Uri.parse(send.getStringExtra(Intent.EXTRA_TEXT))
        assertEquals("turnmark.app", url.host)
        assertEquals("/", url.path)
        val input = Uri.parse("https://example.invalid/?${url.encodedFragment}")
        assertEquals(time, input.getQueryParameter("t"))
        assertEquals("SCY", input.getQueryParameter("c"))
        assertEquals("100", input.getQueryParameter("d"))
    }

    // Opt-in full-device screenshots for local visual review; ordinary CI needs
    // no external storage permissions and still checks the relevant workflows.
    private fun capture(name: String) {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        if (InstrumentationRegistry.getArguments().getString("turnmarkScreenshots") != "true") return
        compose.waitForIdle()
        instrumentation.uiAutomation.waitForIdle(250, 5_000)
        val bitmap = instrumentation.uiAutomation.takeScreenshot()
        try {
            instrumentation.targetContext.openFileOutput("$name.png", Context.MODE_PRIVATE).use {
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
        } finally { bitmap.recycle() }
    }

    @Test fun resultContextUsesDestinationDistanceAndCategory() {
        compose.onNodeWithTag("inputCourse-LCM").performScrollTo().performClick()
        compose.onNodeWithText("Distance: 100 m").performScrollTo().performClick()
        compose.onNodeWithText("400 m").performClick()
        compose.onNodeWithText("Men", useUnmergedTree = true).performScrollTo().performClick()
        compose.onNodeWithTag("targetCourse-SCY").performScrollTo().performClick()
        compose.onNodeWithTag("resultContext").assertTextEquals("500 yd Freestyle · SCY · Men")
        compose.onNodeWithTag("targetCourse-LCM").performScrollTo().performClick()
        compose.onNodeWithTag("resultContext").assertTextEquals("400 m Freestyle · LCM · Men")
        compose.onNodeWithText("Original time").assertExists()
    }

    @Test fun invalidTimeHasNoResult() {
        compose.onNodeWithTag("timeInput").performScrollTo().performTextReplacement("0")
        compose.onNodeWithTag("invalidTime").assertExists()
        compose.onNodeWithTag("resultTime").assertDoesNotExist()
    }

    @Test fun unsupportedComparisonStaysUnavailable() {
        compose.onNodeWithText("Stroke: Freestyle").performScrollTo().performClick()
        compose.onNodeWithText("Individual medley").performClick()
        compose.onNodeWithTag("unavailableConversion").assertExists()
        compose.onNodeWithTag("resultTime").assertDoesNotExist()
    }
}
