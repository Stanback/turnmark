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
        compose.activityRule.scenario.recreate()
    }

    @Test fun conversionAndSavedSwimSurviveRecreation() {
        compose.onNodeWithTag("timeInput").performClick().performTextReplacement("1:00")
        compose.onNodeWithTag("timeInput").assertIsDisplayed()
        capture("android-keyboard")
        compose.onNodeWithTag("timeInput").performImeAction()
        compose.waitUntil(5_000) { compose.onAllNodesWithTag("nav-Convert").fetchSemanticsNodes().isNotEmpty() }
        compose.onNodeWithTag("nav-Convert").assertIsDisplayed()
        compose.onNodeWithTag("inputCourse-LCM").performScrollTo().performClick()
        compose.onNodeWithTag("targetCourse-SCY").performScrollTo().performClick()
        compose.onNodeWithTag("resultTime").assertTextEquals("52.44")
        compose.onNodeWithTag("resultContext").assertTextEquals("100 yd Freestyle · SCY · Women")
        val details = compose.onNodeWithTag("conversionDetails")
        if (compose.activity.resources.configuration.fontScale >= 1.5f) details.performScrollTo()
        details.performClick()
        compose.onNodeWithText("Conversion details").assertExists()
        compose.onNodeWithText("100 m Freestyle · LCM · Women").assertExists()
        compose.onNodeWithText("Edition:", substring = true).performScrollTo().assertIsDisplayed()
        capture("android-details")
        compose.onNodeWithText("Done").performScrollTo().performClick()
        compose.onNodeWithTag("saveSwim").performScrollTo().performClick()
        compose.onNodeWithTag("saveSwim").assertTextContains("Saved")
        capture("android-save-feedback")
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("nav-Saved").performClick()
        compose.onNodeWithTag("resultContext").assertIsDisplayed()
        compose.onNodeWithTag("resultTime").assertTextEquals("52.44")
        capture("android-saved")
        compose.onNodeWithTag("nav-Method").performClick()
        compose.onNodeWithText("How comparisons work").assertExists()
        capture("android-method")
        compose.onNodeWithTag("nav-Saved").performClick()
        compose.onNodeWithText("Use this swim").performScrollTo().performClick()
        compose.onNodeWithTag("timeInput").assertTextContains("1:00").performScrollTo()
        capture("android-converter")
        if (compose.activity.resources.configuration.fontScale >= 1.5f) {
            compose.onNodeWithTag("resultContext").performScrollTo()
            capture("android-large-result")
        }
        compose.onNodeWithTag("nav-Saved").performClick()
        compose.onNodeWithText("Remove saved swim").performScrollTo().performClick()
        compose.onNodeWithText("No saved swim").assertExists()
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("nav-Saved").performClick()
        compose.onNodeWithText("No saved swim").assertExists()
        compose.onNodeWithTag("nav-Convert").performClick()
        compose.onNodeWithTag("saveSwim").assertTextContains("Save swim")
    }

    @Test fun sharingUsesEnteredValuesAndCanBeCancelled() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val captured = AtomicReference<Intent>()
        val monitor = object : Instrumentation.ActivityMonitor() {
            override fun onStartActivity(intent: Intent): Instrumentation.ActivityResult? {
                if (intent.action != Intent.ACTION_CHOOSER) return null
                captured.set(Intent(intent))
                return Instrumentation.ActivityResult(Activity.RESULT_CANCELED, null)
            }
        }
        instrumentation.addMonitor(monitor)
        try {
            compose.onNodeWithTag("saveSwim").performScrollTo().performClick()
            compose.onNodeWithTag("timeInput").performScrollTo().performTextReplacement("1:00")
            compose.onNodeWithTag("timeInput").performImeAction()
            compose.onNodeWithTag("saveSwim").assertTextContains("Save swim")
            compose.onNodeWithText("Share", useUnmergedTree = true).performScrollTo().performClick()
            assertSharedTime(captured.get(), "1:00")
            captured.set(null)
            compose.onNodeWithTag("nav-Saved").performClick()
            compose.onNodeWithText("Share saved swim").performScrollTo().performClick()
            assertSharedTime(captured.get(), "58.32")
        } finally {
            instrumentation.removeMonitor(monitor)
        }
        compose.onNodeWithText("Share saved swim").performScrollTo().performClick()
        val automation = instrumentation.uiAutomation
        compose.waitUntil(5_000) {
            automation.rootInActiveWindow?.packageName?.toString() in listOf("android", "com.android.intentresolver")
        }
        capture("android-share")
        assertTrue(automation.performGlobalAction(AccessibilityService.GLOBAL_ACTION_BACK))
        compose.waitUntil(5_000) { automation.rootInActiveWindow?.packageName?.toString() == "net.stanback.turnmark" }
        compose.onNodeWithText("Use this swim").performScrollTo().performClick()
        compose.onNodeWithTag("timeInput").assertTextContains("58.32")
    }

    private fun assertSharedTime(chooser: Intent?, time: String) {
        assertEquals(Intent.ACTION_CHOOSER, chooser?.action)
        @Suppress("DEPRECATION")
        val send = chooser!!.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)!!
        assertEquals(Intent.ACTION_SEND, send.action)
        assertEquals("text/plain", send.type)
        val url = Uri.parse(send.getStringExtra(Intent.EXTRA_TEXT))
        assertEquals("stanback.github.io", url.host)
        val input = Uri.parse("https://example.invalid/?${url.encodedFragment}")
        assertEquals(time, input.getQueryParameter("t"))
        assertEquals("SCY", input.getQueryParameter("c"))
        assertEquals("100", input.getQueryParameter("d"))
    }

    // Opt-in full-device screenshots for local visual review; ordinary CI needs
    // no external storage permissions and still checks all three screens.
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
        compose.onNodeWithText("Entered swim").assertExists()
    }

    @Test fun invalidTimeHasNoResult() {
        compose.onNodeWithTag("timeInput").performTextReplacement("0")
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
