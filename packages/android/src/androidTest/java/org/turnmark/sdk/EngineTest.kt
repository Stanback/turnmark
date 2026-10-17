package org.turnmark.sdk

import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONArray
import org.json.JSONObject
import org.json.JSONTokener
import org.junit.Assert.*
import org.junit.Test
import uniffi.turnmark_core.*

class EngineTest {
    @Test fun typedNativeApi() {
        val event = SwimEvent(100u, Stroke.FREESTYLE, Course.LCM)
        val result = convertSwim(ConversionRequest(Swim("1:00", event), Course.SCY, Category.WOMEN))
        assertTrue(result is ConversionOutcome.Available)
        result as ConversionOutcome.Available
        assertEquals(5244uL, result.value.hundredths)
        assertEquals("ncaa-2025-27", result.provenance.id)
        val masters = getMastersTarget(StandardsRequest(SwimEvent(200u, Stroke.BUTTERFLY, Course.LCM), Category.WOMEN, "18-24"))
        assertTrue(masters is MastersOutcome.Unavailable && masters.reason == CoverageReason.NO_TIME_PUBLISHED)
        assertTrue(convertSwim(ConversionRequest(Swim("invalid", event), Course.SCY, Category.WOMEN)) is ConversionOutcome.Invalid)
    }

    @Test fun portableFixtures() {
        val context = InstrumentationRegistry.getInstrumentation().context
        val fixture = JSONObject(context.assets.open("sdk-conformance.json").bufferedReader().use { it.readText() })
        val cases = fixture.getJSONArray("cases")
        for (i in 0 until cases.length()) {
            val case = cases.getJSONObject(i)
            val input = case.get("input")
            val request = if (input is String) JSONObject.quote(input) else input.toString()
            val output = evaluate(case.getString("operation"), request)
            compare(JSONTokener(output).nextValue(), case.get("expected"), case.getString("id"))
        }
    }

    private fun compare(actual: Any, expected: Any, path: String) {
        when (expected) {
            is JSONObject -> {
                assertTrue(path, actual is JSONObject)
                for (key in expected.keys()) compare((actual as JSONObject).get(key), expected.get(key), "$path.$key")
            }
            is JSONArray -> {
                assertTrue(path, actual is JSONArray)
                actual as JSONArray
                assertEquals(path, expected.length(), actual.length())
                for (i in 0 until expected.length()) compare(actual.get(i), expected.get(i), "$path[$i]")
            }
            is Number -> {
                assertTrue(path, actual is Number)
                assertEquals(path, expected.toDouble(), (actual as Number).toDouble(), 1e-9)
            }
            else -> assertEquals(path, expected, actual)
        }
    }
}
