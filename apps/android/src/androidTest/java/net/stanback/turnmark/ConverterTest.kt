package net.stanback.turnmark

import android.content.Context
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ConverterTest {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()

    @Before fun clearSavedState() {
        ApplicationProvider.getApplicationContext<Context>().getSharedPreferences("turnmark", Context.MODE_PRIVATE).edit().clear().commit()
        compose.activityRule.scenario.recreate()
    }

    @Test fun conversionAndSavedSwimSurviveRecreation() {
        compose.onNodeWithTag("timeInput").performTextReplacement("1:00")
        compose.onNodeWithTag("inputCourse-LCM").performScrollTo().performClick()
        compose.onNodeWithTag("targetCourse-SCY").performScrollTo().performClick()
        compose.onNodeWithTag("resultTime").assertTextEquals("52.44")
        compose.onNodeWithText("Save swim").performScrollTo().performClick()
        compose.activityRule.scenario.recreate()
        compose.onNodeWithTag("nav-Saved").performClick()
        compose.onNodeWithTag("resultTime").assertTextEquals("52.44")
        compose.onNodeWithText("Use this swim").performScrollTo().performClick()
        compose.onNodeWithTag("timeInput").assertTextContains("1:00")
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
