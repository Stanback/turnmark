package net.stanback.turnmark

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import uniffi.turnmark_core.parseTime
import java.util.UUID
import kotlin.math.roundToLong

val Draft.canLog get() = parseTime(time) != null
fun SwimRecord.draft(target: Int = 2) = Draft(time, SwimRecord.strokeCodes.indexOf(stroke), distance.toUInt(),
    SwimRecord.courseCodes.indexOf(course), if (category == "women") 0 else 1, target)
fun Draft.record(date: String?, meet: String?, replacing: SwimRecord? = null): SwimRecord {
    val seconds = requireNotNull(parseTime(time)) { "Enter a valid time, such as 58.32 or 1:02.45." }
    require(date == null || SwimRecord.validDay(date)) { "Use a real date in YYYY-MM-DD, or leave it blank." }
    require(meet == null || meet.toByteArray().size <= 200) { "Use a shorter meet name." }
    val now = System.currentTimeMillis()
    return SwimRecord(replacing?.id ?: UUID.randomUUID().toString(), time, (seconds * 100).roundToLong(), distance.toInt(),
        SwimRecord.strokeCodes[strokeIndex], SwimRecord.courseCodes[courseIndex], if (categoryIndex == 0) "women" else "men",
        date, meet?.trim()?.takeIf { it.isNotEmpty() }, replacing?.createdAt ?: now, maxOf(now, replacing?.createdAt ?: 0)).validated()
}

@Stable class HistoryState(private val store: SwimHistoryStore, private val scope: CoroutineScope) {
    var swims by mutableStateOf(emptyList<SwimRecord>()); private set
    var ready by mutableStateOf(false); private set
    var busy by mutableStateOf(false); private set
    var message by mutableStateOf<String?>(null)
    var notice by mutableStateOf<String?>(null)
    fun load() = run({ load() }) { ready = true }
    fun save(record: SwimRecord, done: () -> Unit) = run({ save(record); load() }, done)
    fun remove(id: String, done: () -> Unit) = run({ remove(id); load() }, done)
    fun apply(preview: HistoryImport, done: () -> Unit) = run({ apply(preview); load() }, done)
    fun isBest(record: SwimRecord) = record.hundredths == swims.filter { it.comparisonKey == record.comparisonKey }.minOfOrNull { it.hundredths }
    fun io(work: () -> Unit) {
        if (busy) return
        busy = true
        scope.launch {
            try { withContext(Dispatchers.IO) { work() } }
            catch (error: kotlinx.coroutines.CancellationException) { throw error }
            catch (error: Exception) { message = error.message ?: "History could not be read or saved. Nothing was replaced." }
            finally { busy = false }
        }
    }
    private fun run(work: SwimHistoryStore.() -> List<SwimRecord>, done: () -> Unit) {
        if (busy) return
        busy = true
        scope.launch {
            try { swims = withContext(Dispatchers.IO) { store.work() }; ready = true; done() }
            catch (error: kotlinx.coroutines.CancellationException) { throw error }
            catch (error: Exception) { message = "History could not be read or saved. Your stored data has not been replaced. Try again." }
            finally { busy = false }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun SwimEditor(initial: Draft, original: SwimRecord? = null, initialDate: String, initialMeet: String,
    history: HistoryState, dismiss: () -> Unit, saved: (SwimRecord) -> Unit = {}) {
    var draft by remember { mutableStateOf(initial) }
    var date by remember { mutableStateOf(initialDate) }
    var meet by remember { mutableStateOf(initialMeet) }
    var error by remember { mutableStateOf<String?>(null) }
    val focus = LocalFocusManager.current
    Dialog(onDismissRequest = { if (!history.busy) dismiss() }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Scaffold(modifier = Modifier.imePadding(), topBar = {
            TopAppBar(title = { Text(if (original == null) "Log swim" else "Edit swim") }, navigationIcon = {
                TextButton(onClick = dismiss, enabled = !history.busy) { Text("Cancel") }
            }, actions = {
                TextButton(enabled = draft.canLog && !history.busy, modifier = Modifier.testTag("confirmLog"), onClick = {
                    runCatching { draft.record(date.ifEmpty { null }, meet, original) }.fold(onSuccess = { record ->
                        focus.clearFocus(); history.save(record) { saved(record); dismiss() }
                    }, onFailure = { error = it.message ?: "Check the swim and date." })
                }) { Text("Save") }
            })
        }) { insets ->
            Column(Modifier.padding(insets).fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Text("Actual swim", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(draft.time, { draft = draft.copy(time = it) }, label = { Text("Time") },
                    modifier = Modifier.fillMaxWidth().testTag("logTime"), singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done), keyboardActions = KeyboardActions(onDone = { focus.clearFocus() }))
                Choice("Stroke", strokeNames[draft.strokeIndex], strokeNames, Modifier.fillMaxWidth()) { draft = draft.copy(strokeIndex = it).reconcile() }
                CourseControl("Course", "logCourse", draft.courseIndex) { draft = draft.copy(courseIndex = it).reconcile() }
                Choice("Distance", "${draft.distance} ${draft.unit}", draft.options.map { "${it.event.distance} ${draft.unit}" }, Modifier.fillMaxWidth()) {
                    draft = draft.copy(distance = draft.options[it].event.distance)
                }
                Choice("Category", draft.category, listOf("Women", "Men"), Modifier.fillMaxWidth()) { draft = draft.copy(categoryIndex = it) }
                Text("Records your entered time. Converted estimates never count as personal bests.", style = MaterialTheme.typography.bodySmall)
                OutlinedTextField(date, { date = it }, label = { Text("Swim date") }, placeholder = { Text("YYYY-MM-DD") },
                    supportingText = { Text("YYYY-MM-DD, or leave blank if unknown") }, singleLine = true, modifier = Modifier.fillMaxWidth().testTag("logDate"))
                OutlinedTextField(meet, { meet = it }, label = { Text("Meet name (optional)") }, modifier = Modifier.fillMaxWidth().testTag("logMeet"))
                Text("Leave meet blank for practice or a time trial.", style = MaterialTheme.typography.bodySmall)
                error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.testTag("logError")) }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun HistoryScreen(history: HistoryState, modifier: Modifier = Modifier, compare: (SwimRecord) -> Unit) {
    var selected by remember { mutableStateOf<SwimRecord?>(null) }
    var preview by remember { mutableStateOf<HistoryImport?>(null) }
    var export by remember { mutableStateOf<ByteArray?>(null) }
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val importer = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            scope.launch {
                try {
                    val bytes = withContext(Dispatchers.IO) {
                        context.contentResolver.openInputStream(uri)?.use { input ->
                            val out = java.io.ByteArrayOutputStream(); val buffer = ByteArray(8192)
                            while (out.size() <= HistoryArchive.MAX_BYTES) {
                                val count = input.read(buffer, 0, minOf(buffer.size, HistoryArchive.MAX_BYTES + 1 - out.size()))
                                if (count < 0) break
                                out.write(buffer, 0, count)
                            }
                            out.toByteArray()
                        } ?: error("The selected file could not be opened.")
                    }
                    val existing = history.swims
                    preview = withContext(Dispatchers.Default) { HistoryArchive.preview(bytes, existing) }
                } catch (error: Exception) { history.message = "Could not import: ${error.message ?: "invalid history file"}. Nothing was changed." }
            }
        }
    }
    val exporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        val bytes = export; export = null
        if (uri != null && bytes != null) history.io {
            context.contentResolver.openOutputStream(uri, "wt")?.use { it.write(bytes) } ?: error("The export file could not be opened.")
        }
    }
    LazyColumn(modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(enabled = history.ready && !history.busy && history.swims.isNotEmpty(), onClick = {
                    runCatching { HistoryArchive.encode(history.swims) }.fold(onSuccess = { export = it; exporter.launch("turnmark-history.json") }, onFailure = { history.message = it.message })
                }) { Text("Export") }
                OutlinedButton(enabled = history.ready && !history.busy, onClick = { importer.launch(arrayOf("application/json", "text/plain")) }) { Text("Import") }
            }
        }
        if (!history.ready) item {
            Text(if (history.busy) "Opening history…" else "History is unavailable. Your stored data has not been replaced.")
            if (!history.busy) Button(onClick = { history.load() }) { Text("Try again") }
        } else if (history.swims.isEmpty()) item {
            Text("No logged swims", style = MaterialTheme.typography.headlineSmall)
            Text("Enter an actual time in Convert, then choose Log swim. Saved conversions stay separate.")
        }
        val groups = history.swims.groupBy { it.date to it.meet }
        groups.forEach { (key, swims) ->
            item { Text(listOfNotNull(key.second, key.first ?: "Unknown date").joinToString(" · "), fontWeight = FontWeight.Bold) }
            items(swims, key = { it.id }) { swim ->
                Card(Modifier.fillMaxWidth().clickable { selected = swim }.testTag("history-${swim.id}")) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(swim.time + if (history.isBest(swim)) " · PB" else "", style = MaterialTheme.typography.headlineSmall)
                        Text(swim.eventLabel)
                    }
                }
            }
        }
        item {
            Text("Actual swims only. Personal bests compare the same distance, stroke, course and category.", style = MaterialTheme.typography.bodySmall)
            Text("Stored on this device. Export a copy to keep a backup or move to another phone.", style = MaterialTheme.typography.bodySmall)
        }
    }
    selected?.let { record ->
        val current = history.swims.firstOrNull { it.id == record.id } ?: record
        var editing by remember(record.id) { mutableStateOf(false) }
        var deleting by remember(record.id) { mutableStateOf(false) }
        Dialog(onDismissRequest = { selected = null }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
            Scaffold(topBar = { TopAppBar(title = { Text("Logged swim") }, actions = { TextButton(onClick = { selected = null }) { Text("Done") } }) }) { insets ->
                Column(Modifier.padding(insets).fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    Text("Actual swim", style = MaterialTheme.typography.titleMedium)
                    Text(current.time, style = MaterialTheme.typography.displaySmall)
                    Text(current.eventLabel)
                    if (history.isBest(current)) Text("Personal best", fontWeight = FontWeight.Bold)
                    Text(current.date ?: "Unknown date"); Text(current.meet ?: "No meet")
                    Text("Manually logged performance", style = MaterialTheme.typography.bodySmall)
                    Button(onClick = { compare(current); selected = null }) { Text("Compare this swim") }
                    OutlinedButton(onClick = { editing = true }, enabled = !history.busy) { Text("Edit swim") }
                    TextButton(onClick = { deleting = true }, enabled = !history.busy) { Text("Delete swim") }
                }
            }
        }
        if (editing) SwimEditor(current.draft(), current, current.date ?: "", current.meet ?: "", history, { editing = false })
        if (deleting) AlertDialog(onDismissRequest = { deleting = false }, title = { Text("Delete this logged swim?") },
            confirmButton = { TextButton(enabled = !history.busy, onClick = { history.remove(current.id) { deleting = false; selected = null } }) { Text("Delete swim") } },
            dismissButton = { TextButton(onClick = { deleting = false }) { Text("Cancel") } })
    }
    preview?.let { review ->
        Dialog(onDismissRequest = { if (!history.busy) preview = null }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
            Scaffold(topBar = { TopAppBar(title = { Text("Review import") }, navigationIcon = { TextButton(enabled = !history.busy, onClick = { preview = null }) { Text("Cancel") } },
                actions = { TextButton(modifier = Modifier.testTag("confirmImport"), enabled = review.records.isNotEmpty() && !history.busy, onClick = {
                    history.apply(review) { preview = null; history.notice = "Imported ${review.records.size} swims. Existing records were kept." }
                }) { Text("Import") } }) }) { insets ->
                LazyColumn(Modifier.padding(insets).fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    item { Text("${review.records.size} new swims · ${review.duplicates} duplicates · ${review.rejected.size} rejected") }
                    item { Text("Existing records are kept, even when an imported record with the same ID has changed. Import never overwrites a swim.") }
                    items(review.rejected) { Text(it, color = MaterialTheme.colorScheme.error) }
                    items(review.records, key = { it.id }) { Text("${it.time} · ${it.eventLabel}\n${it.date ?: "Unknown date"} · ${it.meet ?: "No meet"}") }
                }
            }
        }
    }
}
