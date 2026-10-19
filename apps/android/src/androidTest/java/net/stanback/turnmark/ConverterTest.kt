package net.stanback.turnmark

import android.app.Activity
import android.app.Instrumentation
import android.content.Intent
import android.net.Uri
import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.graphics.Bitmap
import androidx.activity.compose.setContent
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
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

    private fun example() { compose.onNodeWithTag("tryExample").performScrollTo().performClick() }

    @Test fun blankArrivalExampleAndResetKeepEntryFirst() {
        compose.onNodeWithTag("timeInput").assert(SemanticsMatcher.expectValue(androidx.compose.ui.semantics.SemanticsProperties.EditableText, androidx.compose.ui.text.AnnotatedString("")))
        compose.onNodeWithTag("invalidTime").assertDoesNotExist()
        compose.onNodeWithTag("resultTime").assertDoesNotExist()
        capture("android-align-arrival-light")
        example()
        capture("android-align-input-light")
        compose.onNodeWithTag("seeResults").performScrollTo().performClick()
        compose.onNodeWithTag("equivalent-SCY").assertExists()
        compose.onNodeWithTag("equivalent-SCM").assertExists()
        compose.onNodeWithTag("equivalent-LCM").assertExists()
        compose.onNodeWithTag("equivalent-SCM").performScrollTo().performClick()
        compose.onNodeWithTag("resultTime").assertTextEquals("1:05.08")
        capture("android-align-results-light")
        compose.onNodeWithTag("conversionDetails").performScrollTo().performClick()
        compose.onNodeWithTag("methodResult-NCAA").performScrollTo().assertTextEquals("1:05.08")
        compose.onNodeWithTag("methodResult-Colorado Timing").performScrollTo().assertTextEquals("1:04.73")
        compose.onNodeWithTag("methodDifference").performScrollTo().assertTextEquals("Method difference: 0.35s")
        capture("android-align-methods")
        compose.onNodeWithText("Done").assertIsDisplayed().performClick()
        compose.onNodeWithTag("resetConverter").performScrollTo().performClick()
        compose.onNodeWithTag("timeInput").assert(SemanticsMatcher.expectValue(androidx.compose.ui.semantics.SemanticsProperties.EditableText, androidx.compose.ui.text.AnnotatedString("")))
        compose.onNodeWithTag("invalidTime").assertDoesNotExist()
        compose.onNodeWithTag("resultTime").assertDoesNotExist()
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText("No logged swims").assertExists()
    }

    @Test fun conversionMethodPersistsAndKeepsNcaaDefault() {
        example()
        compose.onNodeWithTag("resultTime").assertTextEquals("1:06.72")
        compose.onNodeWithTag("converterMenu").performClick()
        compose.onNodeWithTag("conversionMethod-colorado-teamunify-2026").performClick()
        compose.onNodeWithTag("resultTime").assertTextEquals("1:06.33")
        capture("android-colorado-comparison")
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("resultTime").assertTextEquals("1:06.33")
        compose.onNodeWithTag("conversionDetails").performScrollTo().performClick()
        compose.onNodeWithText("Time offset: 1.6 seconds").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Edition: colorado-teamunify-2026").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("Done").assertIsDisplayed().performClick()
        compose.onNodeWithTag("converterMenu").performClick()
        compose.onNodeWithTag("conversionMethod-ncaa-2025-27").performClick()
        compose.onNodeWithTag("resultTime").assertTextEquals("1:06.72")
    }

    @Test fun benchmarksUseOriginalSwimAndRememberAgeSettings() {
        example()
        compose.onNodeWithTag("converterBrand").assertIsDisplayed()
        compose.onNodeWithTag("converterMenu").performClick()
        compose.onNodeWithText("About Turnmark").performClick()
        compose.onNodeWithText("How comparisons work").assertIsDisplayed()
        compose.onNodeWithText("Done").assertIsDisplayed().performClick()
        capture("android-converter-default")
        compose.onNodeWithTag("openBenchmarks").performScrollTo().performClick()
        compose.onNodeWithTag("benchmarkOriginalTime").assertTextEquals("58.32")
        compose.onNodeWithTag("benchmarkSummary").assertTextEquals("A standard")
        capture("android-youth-standards-summary")
        compose.onNodeWithTag("benchmark-level-AAAA").performScrollTo().assertExists()
        capture("android-youth-standards")
        compose.onNodeWithTag("choice-Standard system").performScrollTo().performClick()
        compose.onNodeWithText("USMS · Masters").performClick()
        compose.onNodeWithTag("choice-Age group").performScrollTo().performClick()
        compose.onNodeWithText("40–44").performClick()
        compose.onNodeWithTag("benchmarkSummary").performScrollTo().assertTextEquals("NQT target met")
        capture("android-masters-benchmark")
        compose.onNodeWithTag("closeBenchmarks").performScrollTo().performClick()
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("openBenchmarks").performScrollTo().performClick()
        compose.onNodeWithText("40–44 · Women · SCY").assertExists()
        compose.onNodeWithTag("benchmarkMode-points").performScrollTo().performClick()
        compose.onNodeWithTag("benchmarkUnavailable").assertExists()
        compose.onNodeWithTag("benchmarkPoints").assertDoesNotExist()
        capture("android-points-yards-unavailable")
        compose.onNodeWithTag("closeBenchmarks").performScrollTo().performClick()
        compose.onNodeWithTag("inputCourse-LCM").performScrollTo().performClick()
        compose.onNodeWithTag("openBenchmarks").performScrollTo().performClick()
        compose.onNodeWithTag("benchmarkPoints").assertTextEquals("697 points")
        capture("android-world-points")
    }

    @Test fun recordedBenchmarkKeepsActualCategoryAndTime() {
        example()
        compose.onNodeWithTag("timeInput").performScrollTo().performTextReplacement("1:00.25")
        compose.onNodeWithTag("timeInput").performImeAction()
        compose.onNodeWithText("Men").performScrollTo().performClick()
        compose.onNodeWithText("Men").assertIsSelected()
        compose.onNodeWithTag("logSwim").performScrollTo().performClick()
        compose.onNodeWithTag("confirmLog").performClick()
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText("1:00.25 · PB").performClick()
        compose.onNodeWithTag("recordBenchmarks").performScrollTo().performClick()
        compose.onNodeWithTag("benchmarkOriginalTime").assertTextEquals("1:00.25")
        compose.onNodeWithTag("benchmarkContext").assertTextEquals("100 yd Freestyle · SCY · Men")
        compose.onNodeWithTag("benchmarkOriginLabel").assertTextEquals("Recorded swim")
        capture("android-recorded-standards")
        compose.onNodeWithTag("closeBenchmarks").performScrollTo().performClick()
        compose.onNodeWithText("Manually logged performance").assertExists()
    }

    @Test fun benchmarkMissingTargetKeepsMissingDataVisible() {
        example()
        compose.onNodeWithTag("inputCourse-LCM").performScrollTo().performClick()
        compose.onNodeWithTag("choice-Stroke").performScrollTo().performClick()
        compose.onNodeWithText("Butterfly").performClick()
        compose.onNodeWithTag("choice-Distance").performScrollTo().performClick()
        compose.onNodeWithText("200 m").performClick()
        compose.onNodeWithTag("openBenchmarks").performScrollTo().performClick()
        compose.onNodeWithTag("choice-Standard system").performScrollTo().performClick()
        compose.onNodeWithText("USMS · Masters").performClick()
        compose.onNodeWithTag("benchmarkUnavailable").performScrollTo().assertExists()
        compose.onNodeWithText("This event has no NQT in the published table for this age group. Check the meet’s entry guidance.").assertExists()
        capture("android-missing-masters-target")
    }

    @Test fun benchmarkControlsRemainReachableAtLargeText() {
        example()
        compose.activityRule.scenario.onActivity { activity -> activity.setContent {
            val density = LocalDensity.current
            CompositionLocalProvider(LocalDensity provides Density(density.density, 2f)) {
                TurnmarkTheme(dark = true) { BenchmarkSheet(Draft(time = "2:12.34", strokeIndex = 3, distance = 200u, courseIndex = 2)) {} }
            }
        } }
        compose.onNodeWithTag("choice-Standard system").performScrollTo().performClick()
        compose.onNodeWithText("USMS · Masters").performClick()
        compose.onNodeWithTag("benchmarkUnavailable").performScrollTo().assertIsDisplayed()
        capture("android-benchmarks-large-text-dark")
        compose.onNodeWithTag("choice-Age group").performScrollTo().performClick()
        compose.onNodeWithText("85+").performScrollTo().performClick()
        compose.onNodeWithText("No NQT is published for this age group in the bundled 2026 table. Meet-specific rules and exceptions apply.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithTag("closeBenchmarks").performScrollTo().assertIsDisplayed()
    }

    @Test fun conversionKeepsOriginalAndSupportsContextualDetails() {
        example()
        compose.onNodeWithTag("timeInput").performScrollTo().performClick().performTextReplacement("1:00")
        compose.onNodeWithTag("timeInput").performImeAction()
        compose.waitUntil(5_000) { compose.onAllNodesWithTag("nav-Convert").fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithTag("nav-Saved").assertDoesNotExist()
        compose.onNodeWithTag("nav-Method").assertDoesNotExist()
        compose.onNodeWithTag("inputCourse-LCM").performScrollTo().performClick()
        compose.onNodeWithTag("equivalent-SCY").performScrollTo().performClick()
        compose.onNodeWithTag("resultTime").assertTextEquals("52.44")
        compose.onNodeWithTag("resultContext").assertTextEquals("100 yd Freestyle · SCY · Women")
        compose.onNodeWithTag("conversionDetails").performScrollTo().performClick()
        compose.onNodeWithText("Conversion details").assertExists()
        compose.onNodeWithText("100 m Freestyle · LCM · Women").assertExists()
        compose.onNodeWithText("Edition:", substring = true).performScrollTo().assertIsDisplayed()
        capture("android-details")
        compose.onNodeWithText("Done").assertIsDisplayed().performClick()
        compose.onNodeWithTag("resultTime").performScrollTo()
        capture("android-converter-result")
        compose.onNodeWithTag("timeInput").performScrollTo()
        capture("android-converter-input")
        compose.onNodeWithTag("converterMenu").performClick()
        compose.onNodeWithTag("converterAbout").performClick()
        compose.onNodeWithText("How comparisons work").assertExists()
        compose.onNodeWithText("Done").assertIsDisplayed().performClick()
        compose.onNodeWithTag("nav-My times").performClick()
        compose.onNodeWithText("No logged swims").assertExists()
        compose.onNodeWithTag("nav-Convert").performClick()
        compose.onNodeWithTag("timeInput").assertTextContains("1:00")
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("timeInput").assertTextContains("1:00")
    }

    @Test fun sharingUsesOriginalValuesWithoutRecordingAResult() {
        example()
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
        example()
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
        example()
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
        example()
        val meet = "Pacific Northwest Masters Long Course Championships"
        compose.onNodeWithTag("timeInput").performScrollTo().performTextReplacement("2:12.34")
        compose.onNodeWithTag("timeInput").performImeAction()
        compose.onNodeWithTag("choice-Stroke").performScrollTo().performClick()
        compose.onNodeWithText("Individual medley").performClick()
        compose.onNodeWithTag("choice-Distance").performScrollTo().performClick()
        compose.onNodeWithText("200 yd").performClick()
        compose.onNodeWithTag("resultTime").performScrollTo().assertIsDisplayed()
        capture("android-long-result")
        compose.onNodeWithTag("logSwim").performScrollTo().performClick()
        compose.onNodeWithTag("logMeet").performScrollTo().performTextReplacement(meet)
        capture("android-long-editor")
        compose.onNodeWithTag("confirmLog").performClick()
        // Saving is asynchronous and the IME hides the bottom navigation until
        // its closing animation finishes. Wait for the actual navigation node.
        compose.waitUntil(timeoutMillis = 5_000) {
            compose.onAllNodesWithTag("nav-My times").fetchSemanticsNodes().size == 1
        }
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
        example()
        compose.onNodeWithTag("choice-Stroke").performScrollTo().performClick()
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
        example()
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
        example()
        compose.onNodeWithTag("inputCourse-LCM").performScrollTo().performClick()
        compose.onNodeWithTag("choice-Distance").performScrollTo().performClick()
        compose.onNodeWithText("400 m").performClick()
        compose.onNodeWithText("Men").performScrollTo().performClick()
        compose.onNodeWithTag("equivalent-SCY").performScrollTo().performClick()
        compose.onNodeWithTag("resultContext").assertTextEquals("500 yd Freestyle · SCY · Men")
        compose.onNodeWithTag("equivalent-LCM").performScrollTo().performClick()
        compose.onNodeWithTag("resultContext").assertTextEquals("400 m Freestyle · LCM · Men")
        compose.onNodeWithText("Original time").assertExists()
    }

    @Test fun invalidTimeHasNoResult() {
        example()
        compose.onNodeWithTag("timeInput").performScrollTo().performTextReplacement("0")
        compose.onNodeWithTag("invalidTime").assertExists()
        compose.onNodeWithTag("resultTime").assertDoesNotExist()
    }

    @Test fun unsupportedComparisonStaysUnavailable() {
        example()
        compose.onNodeWithTag("choice-Stroke").performScrollTo().performClick()
        capture("android-stroke-menu")
        compose.onNodeWithText("Individual medley").performClick()
        compose.onNodeWithTag("unavailableConversion").assertExists()
        compose.onNodeWithTag("resultTime").assertDoesNotExist()
    }
}
