package net.stanback.turnmark

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONArray
import org.json.JSONObject
import uniffi.turnmark_core.*
import java.time.LocalDate
import kotlin.math.roundToLong

// Actual performances only; never persist a comparison output as a race.
data class SwimRecord(
    val id: String, val time: String, val hundredths: Long, val distance: Int,
    val stroke: String, val course: String, val category: String,
    val date: String?, val meet: String?, val createdAt: Long, val updatedAt: Long,
) {
    fun validated(): SwimRecord {
        require(id.matches(Regex("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")))
        require(time.toByteArray().size <= 32)
        val seconds = requireNotNull(parseTime(time))
        require(hundredths == (seconds * 100).roundToLong())
        val s = strokeCodes.indexOf(stroke); val c = courseCodes.indexOf(course)
        require(s >= 0 && c >= 0 && category in listOf("women", "men") && distance > 0)
        require(getEventOptions(Course.entries[c], Stroke.entries[s]).any { it.event.distance == distance.toUInt() })
        require(date == null || validDay(date))
        require(meet == null || (meet.isNotBlank() && meet.toByteArray().size <= 200))
        require(createdAt >= 0 && updatedAt >= createdAt && updatedAt <= 253402300799999L)
        return this
    }
    val eventLabel get() = "$distance ${if (course == "SCY") "yd" else "m"} ${strokeNames[strokeCodes.indexOf(stroke)]} · $course · ${if (category == "women") "Women" else "Men"}"
    val comparisonKey get() = "$distance|$stroke|$course|$category"
    fun json() = JSONObject().put("id", id).put("time", time).put("hundredths", hundredths)
        .put("distance", distance).put("stroke", stroke).put("course", course).put("category", category)
        .put("date", date ?: JSONObject.NULL).put("meet", meet ?: JSONObject.NULL)
        .put("createdAt", createdAt).put("updatedAt", updatedAt)
    companion object {
        val strokeCodes = listOf("FR", "BK", "BR", "FL", "IM")
        val strokeNames = listOf("Freestyle", "Backstroke", "Breaststroke", "Butterfly", "Individual medley")
        val courseCodes = listOf("SCY", "SCM", "LCM")
        fun validDay(text: String) = text.matches(Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}")) &&
            runCatching { LocalDate.parse(text).let { it.year in 1..9999 && it.toString() == text } }.getOrDefault(false)
        fun decode(json: JSONObject): SwimRecord {
            fun string(key: String) = json.get(key) as? String ?: error("Expected text")
            fun optional(key: String): String? = if (json.isNull(key)) null else string(key)
            fun integer(key: String): Long {
                val value = json.get(key)
                require(value is Number && value.toDouble().isFinite() && value.toDouble() == value.toLong().toDouble())
                return value.toLong()
            }
            val distance = integer("distance"); require(distance in 1..Int.MAX_VALUE.toLong())
            return SwimRecord(string("id"), string("time"), integer("hundredths"), distance.toInt(), string("stroke"),
                string("course"), string("category"), optional("date"), optional("meet"), integer("createdAt"), integer("updatedAt")).validated()
        }
    }
}

data class HistoryImport(val records: List<SwimRecord>, val duplicates: Int, val rejected: List<String>)
object HistoryArchive {
    const val MAX_BYTES = 10 * 1024 * 1024
    const val MAX_RECORDS = 25000
    fun encode(swims: List<SwimRecord>): ByteArray {
        val bytes = JSONObject().put("format", "turnmark.swim-history").put("version", 1)
        .put("swims", JSONArray().apply { swims.forEach { put(it.json()) } }).toString(2).toByteArray(Charsets.UTF_8)
        require(bytes.size <= MAX_BYTES && swims.size <= MAX_RECORDS) { "History exceeds the current export limit (25,000 swims or 10 MB)." }
        return bytes
    }
    fun preview(bytes: ByteArray, existing: List<SwimRecord>): HistoryImport {
        require(bytes.size <= MAX_BYTES) { "Choose a Turnmark history v1 file (up to 10 MB and 25,000 swims). Nothing was changed." }
        val root = JSONObject(Charsets.UTF_8.newDecoder().decode(java.nio.ByteBuffer.wrap(bytes)).toString())
        require(root.get("format") == "turnmark.swim-history" && root.get("version") is Number && root.getDouble("version") == 1.0) {
            "Choose a Turnmark history v1 file. Nothing was changed."
        }
        val rows = root.getJSONArray("swims"); require(rows.length() <= MAX_RECORDS) { "Import up to 25,000 swims at once." }
        val ids = existing.map { it.id }.toMutableSet(); val records = mutableListOf<SwimRecord>()
        val rejected = mutableListOf<String>(); var duplicates = 0
        for (index in 0 until rows.length()) {
            runCatching { SwimRecord.decode(rows.getJSONObject(index)) }.fold(onSuccess = {
                if (ids.add(it.id)) records.add(it) else duplicates++
            }, onFailure = { rejected.add("Record ${index + 1}: invalid fields, event, time or date.") })
        }
        return HistoryImport(records, duplicates, rejected)
    }
}

// Android owns persistence, not the numerical SDK. Version 1 never touches the
// legacy saved-conversion preference. Future database migrations go in onUpgrade.
class SwimHistoryStore(context: Context, name: String? = "swim-history.db") : SQLiteOpenHelper(context, name, null, 1) {
    override fun onCreate(db: SQLiteDatabase) { db.execSQL("CREATE TABLE swims (id TEXT PRIMARY KEY NOT NULL, payload TEXT NOT NULL)") }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) { error("Unsupported history schema migration") }
    fun load(): List<SwimRecord> = readableDatabase.rawQuery("SELECT payload FROM swims", null).use { cursor ->
        buildList { while (cursor.moveToNext()) add(SwimRecord.decode(JSONObject(cursor.getString(0)))) }
    }.sortedWith(compareByDescending<SwimRecord> { it.date ?: "" }.thenByDescending { it.createdAt }.thenByDescending { it.id })
    fun save(record: SwimRecord) {
        record.validated()
        val values = ContentValues().apply { put("id", record.id); put("payload", record.json().toString()) }
        check(writableDatabase.insertWithOnConflict("swims", null, values, SQLiteDatabase.CONFLICT_REPLACE) != -1L)
    }
    fun remove(id: String) { writableDatabase.delete("swims", "id = ?", arrayOf(id)) }
    fun apply(preview: HistoryImport) {
        val db = writableDatabase
        db.beginTransaction()
        try {
            val ids = load().map { it.id }.toSet()
            for (record in preview.records) if (record.id !in ids) {
                record.validated()
                check(db.insertOrThrow("swims", null, ContentValues().apply {
                    put("id", record.id); put("payload", record.json().toString())
                }) != -1L)
            }
            db.setTransactionSuccessful()
        } finally { db.endTransaction() }
    }
}
