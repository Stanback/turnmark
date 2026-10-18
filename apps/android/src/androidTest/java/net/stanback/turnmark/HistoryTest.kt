package net.stanback.turnmark

import android.content.Context
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.json.JSONObject
import org.json.JSONArray
import org.junit.Test
import org.junit.Assert.*
import org.junit.runner.RunWith
import java.util.UUID

@RunWith(AndroidJUnit4::class)
class HistoryTest {
    private fun fixture(name: String) = InstrumentationRegistry.getInstrumentation().context.assets.open(name).use { it.readBytes() }
    private fun records() = HistoryArchive.preview(fixture("contract-v1.json"), emptyList()).records
    @Test fun portableArchiveRoundTripAndDuplicatePolicy() {
        val records = records(); assertEquals(5, records.size)
        assertEquals(records, HistoryArchive.preview(HistoryArchive.encode(records), emptyList()).records)
        assertEquals(5, HistoryArchive.preview(HistoryArchive.encode(records), records).duplicates)
        assertEquals(5, HistoryArchive.preview(HistoryArchive.encode(records + records), emptyList()).duplicates)
        val changed = records[0].copy(time = "58.00", hundredths = 5800)
        assertEquals(1, HistoryArchive.preview(HistoryArchive.encode(listOf(changed)), records).duplicates)
    }
    @Test fun bothPlatformsValidateTheSameImportCases() {
        val cases = JSONArray(fixture("import-cases.json").toString(Charsets.UTF_8))
        val original = JSONObject(fixture("contract-v1.json").toString(Charsets.UTF_8)).getJSONArray("swims").getJSONObject(0)
        for (i in 0 until cases.length()) {
            val sample = cases.getJSONObject(i); val row = JSONObject(original.toString()); val patch = sample.getJSONObject("patch")
            patch.keys().forEach { row.put(it, patch.get(it)) }
            val bytes = JSONObject().put("format", "turnmark.swim-history").put("version", 1).put("swims", JSONArray().put(row)).toString().toByteArray()
            val preview = HistoryArchive.preview(bytes, emptyList())
            assertEquals(sample.getString("name"), if (sample.getBoolean("accepted")) 1 else 0, preview.records.size)
            assertEquals(sample.getString("name"), if (sample.getBoolean("accepted")) 0 else 1, preview.rejected.size)
        }
    }
    @Test fun invalidEnvelopeAndSizeLeaveStoreUnchanged() {
        SwimHistoryStore(ApplicationProvider.getApplicationContext(), null).use { store ->
            store.save(records()[0])
            for (text in listOf("{}", "[]", "{broken", "{\"format\":\"turnmark.swim-history\",\"version\":2,\"swims\":[]}", "{\"format\":\"turnmark.swim-history\",\"version\":true,\"swims\":[]}")) {
                assertTrue(runCatching { HistoryArchive.preview(text.toByteArray(), store.load()) }.isFailure)
            }
            assertTrue(runCatching { HistoryArchive.preview(ByteArray(HistoryArchive.MAX_BYTES + 1), store.load()) }.isFailure)
            assertEquals(1, store.load().size)
        }
    }
    @Test fun persistenceEditingDeletionAndDifferentActualEvents() {
        val context = ApplicationProvider.getApplicationContext<Context>(); val name = "test-${UUID.randomUUID()}.db"
        try {
            val rows = records()
            SwimHistoryStore(context, name).use { store ->
                assertTrue(store.load().isEmpty()); store.apply(HistoryImport(rows, 0, emptyList()))
                assertNotEquals(rows[2].comparisonKey, rows[3].comparisonKey)
                assertEquals(5932L, store.load().filter { it.comparisonKey == rows[0].comparisonKey }.minOf { it.hundredths })
            }
            SwimHistoryStore(context, name).use { store ->
                assertEquals(5, store.load().size)
                val changed = rows[1].copy(time = "1:01", hundredths = 6100, meet = null, date = null)
                store.save(changed); assertEquals(changed, store.load().first { it.id == changed.id })
                store.apply(HistoryArchive.preview(HistoryArchive.encode(rows), store.load()))
                assertEquals(changed, store.load().first { it.id == changed.id })
                store.remove(changed.id); assertEquals(4, store.load().size)
            }
            SwimHistoryStore(context, name).use { assertEquals(4, it.load().size) }
        } finally { context.deleteDatabase(name) }
    }
    @Test fun importRollsBackOnInvalidRecord() {
        SwimHistoryStore(ApplicationProvider.getApplicationContext(), null).use { store ->
            val rows = records()
            assertTrue(runCatching { store.apply(HistoryImport(listOf(rows[0], rows[1].copy(hundredths = 1)), 0, emptyList())) }.isFailure)
            assertTrue(store.load().isEmpty())
            val men = rows[1].copy(category = "men")
            store.save(rows[0]); store.save(men)
            assertNotEquals(rows[0].comparisonKey, men.comparisonKey)
            assertEquals(6000L, store.load().filter { it.comparisonKey == rows[0].comparisonKey }.minOf { it.hundredths })
        }
    }
    @Test fun actualSwimCanBeLoggedWithoutConversion() {
        val draft = Draft(strokeIndex = 4)
        assertFalse(draft.available); assertTrue(draft.canLog)
        val record = draft.record(null, null)
        assertEquals(draft.time, record.time); assertEquals(100, record.distance)
        val metric = Draft(courseIndex = 2, distance = 400u)
        val actual = metric.record("2026-10-17", "Meet")
        assertEquals(400, actual.distance); assertEquals("LCM", actual.course)
        assertEquals(actual.id, metric.copy(targetIndex = 0).record(actual.date, actual.meet, actual).id)
    }
}
