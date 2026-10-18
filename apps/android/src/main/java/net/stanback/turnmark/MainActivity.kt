package net.stanback.turnmark

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject
import uniffi.turnmark_core.*

val courses = Course.entries
val strokes = Stroke.entries
val strokeNames = listOf("Freestyle", "Backstroke", "Breaststroke", "Butterfly", "Individual medley")
val strokeCodes = listOf("FR", "BK", "BR", "FL", "IM")

data class Draft(
    val time: String = "58.32", val strokeIndex: Int = 0, val distance: UInt = 100u,
    val courseIndex: Int = 0, val categoryIndex: Int = 0, val targetIndex: Int = 2,
) {
    val options get() = getEventOptions(courses[courseIndex], strokes[strokeIndex])
    val outcome get() = convertSwim(ConversionRequest(
        Swim(time, SwimEvent(distance, strokes[strokeIndex], courses[courseIndex])),
        courses[targetIndex], if (categoryIndex == 0) Category.WOMEN else Category.MEN))
    val available get() = outcome is ConversionOutcome.Available
    val category get() = if (categoryIndex == 0) "Women" else "Men"
    val unit get() = if (courseIndex == 0) "yd" else "m"
    val label get() = "$distance $unit ${strokeNames[strokeIndex]} · ${courses[courseIndex]} · $category"
    fun resultLabel(event: SwimEvent): String =
        "${event.distance} ${if (event.course == Course.SCY) "yd" else "m"} ${strokeNames[strokes.indexOf(event.stroke)]} · ${event.course} · $category"
    fun reconcile(): Draft = if (options.any { it.event.distance == distance }) this
        else copy(distance = options.first().event.distance)
    fun encode(): String = JSONObject().put("time", time).put("stroke", strokeIndex)
        .put("distance", distance.toLong()).put("course", courseIndex)
        .put("category", categoryIndex).put("target", targetIndex).toString()
    val shareUrl: String get() {
        val query = Uri.Builder().appendQueryParameter("t", time)
            .appendQueryParameter("s", strokeCodes[strokeIndex])
            .appendQueryParameter("d", options.first { it.event.distance == distance }.canonicalDistance.toString())
            .appendQueryParameter("c", courses[courseIndex].name)
            .appendQueryParameter("g", if (categoryIndex == 0) "women" else "men")
            .appendQueryParameter("h", "0").build().encodedQuery
        return Uri.parse("https://turnmark.app/").buildUpon().encodedFragment(query).build().toString()
    }
    companion object {
        fun decode(text: String?): Draft? = runCatching {
            val json = JSONObject(text ?: return null)
            val distance = json.getLong("distance")
            require(distance in 1..UInt.MAX_VALUE.toLong())
            val draft = Draft(json.getString("time"), json.getInt("stroke"), distance.toUInt(),
                json.getInt("course"), json.getInt("category"), json.getInt("target"))
            require(draft.strokeIndex in strokes.indices && draft.courseIndex in courses.indices &&
                draft.targetIndex in courses.indices && draft.categoryIndex in 0..1)
            require(draft.options.any { it.event.distance == draft.distance })
            draft
        }.getOrNull()
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val preferences = getSharedPreferences("turnmark", Context.MODE_PRIVATE)
        setContent { Turnmark(preferences) }
    }
}

private fun share(context: Context, draft: Draft) {
    context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"; putExtra(Intent.EXTRA_TEXT, draft.shareUrl)
    }, "Share your swim"))
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable private fun Turnmark(preferences: SharedPreferences) {
    var draft by remember { mutableStateOf(Draft.decode(preferences.getString("draft", null)) ?: Draft()) }
    var saved by remember { mutableStateOf(Draft.decode(preferences.getString("saved", null))) }
    var tab by rememberSaveable { mutableIntStateOf(0) }
    var loggingJSON by rememberSaveable { mutableStateOf<String?>(null) }
    var showingMethod by rememberSaveable { mutableStateOf(false) }
    var showingLegacy by rememberSaveable { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val historyDb = remember { SwimHistoryStore(context.applicationContext) }
    val history = remember { HistoryState(historyDb, scope) }
    LaunchedEffect(history) { history.load() }
    DisposableEffect(historyDb) { onDispose { historyDb.close() } }
    var lastDate by rememberSaveable { mutableStateOf(java.time.LocalDate.now().toString()) }
    var lastMeet by rememberSaveable { mutableStateOf("") }
    var lastLogDay by rememberSaveable { mutableStateOf(java.time.LocalDate.now().toString()) }
    val focus = LocalFocusManager.current
    val keyboard = LocalSoftwareKeyboardController.current
    val keyboardVisible = WindowInsets.isImeVisible
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(history.notice) { history.notice?.let { snackbar.showSnackbar(it); history.notice = null } }
    fun update(value: Draft) {
        draft = value.reconcile()
        preferences.edit().putString("draft", draft.encode()).apply()
    }
    TurnmarkTheme {
        val c = LocalTurnmarkColors.current
        BoxWithConstraints(Modifier.fillMaxSize()) {
            val rail = maxWidth >= 700.dp && maxHeight >= 400.dp
            @Composable fun NavIcon(index: Int) {
                if (index == 0) Icon(painterResource(R.drawable.ic_convert), contentDescription = null)
                else Icon(Icons.Default.List, contentDescription = null)
            }
            Row(Modifier.fillMaxSize()) {
                if (rail) NavigationRail(containerColor = c.canvas) {
                    listOf("Convert", "My times").forEachIndexed { index, label ->
                        NavigationRailItem(selected = tab == index, onClick = { tab = index }, icon = { NavIcon(index) },
                            label = { Text(label) }, modifier = Modifier.testTag("nav-$label"))
                    }
                }
                Scaffold(modifier = Modifier.weight(1f).imePadding(), containerColor = c.canvas,
                    snackbarHost = { SnackbarHost(snackbar) }, topBar = {
                        if (tab == 1) TopAppBar(title = { Text("My times", fontWeight = FontWeight.Bold) }, actions = {
                            IconButton(enabled = history.ready && !history.busy, onClick = { loggingJSON = draft.copy(time = "").encode() }, modifier = Modifier.testTag("recordTime")) {
                                Icon(Icons.Default.Add, contentDescription = "Record time")
                            }
                        })
                    }, bottomBar = {
                        if (!rail && !keyboardVisible) NavigationBar {
                            listOf("Convert", "My times").forEachIndexed { index, label ->
                                NavigationBarItem(selected = tab == index, onClick = { tab = index }, icon = { NavIcon(index) },
                                    label = { Text(label) }, modifier = Modifier.testTag("nav-$label"))
                            }
                        }
                    }) { insets ->
                    if (tab == 1) HistoryScreen(history, Modifier.padding(insets), legacy = saved,
                        openLegacy = { showingLegacy = true }, recordNew = { loggingJSON = draft.copy(time = "").encode() }) { update(it.draft(draft.targetIndex)); tab = 0 }
                    else ConverterWorkspace(draft, Modifier.padding(insets), history.ready && !history.busy,
                        update = ::update, add = { focus.clearFocus(); keyboard?.hide(); loggingJSON = draft.encode() },
                        about = { showingMethod = true })
                }
            }
        }
        Draft.decode(loggingJSON)?.let { input ->
            val today = java.time.LocalDate.now().toString()
            SwimEditor(input, initialDate = if (lastLogDay == today) lastDate else today,
                initialMeet = if (lastLogDay == today) lastMeet else "", history = history, dismiss = { loggingJSON = null }) {
                lastDate = it.date ?: ""; lastMeet = it.meet ?: ""; lastLogDay = today
                history.notice = "Time recorded"
            }
        }
        if (showingMethod) ModalBottomSheet(onDismissRequest = { showingMethod = false },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            Column(Modifier.verticalScroll(rememberScrollState()).padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Text("About Turnmark", style = MaterialTheme.typography.headlineSmall)
                Text("How comparisons work", style = MaterialTheme.typography.titleMedium)
                Text("Published NCAA factors estimate a yards time from a metric swim. Reverse and cross-metric conversions are derived estimates. The original time stays separate.")
                Text("A converted time is not an official swim or confirmation of meet-entry eligibility.")
                TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://turnmark.app/#method"))) }) { Text("Methodology and coverage") }
                Text("Your data", style = MaterialTheme.typography.titleMedium)
                Text("Inputs and swim history stay on this device. Export/import moves a copy of recorded swims; there is no account or cloud sync. Sharing includes the original swim in a link. Source links need an internet connection.")
                TextButton(onClick = { showingMethod = false }) { Text("Done") }
            }
        }
        if (showingLegacy && saved != null) ModalBottomSheet(onDismissRequest = { showingLegacy = false },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            val value = saved!!
            Column(Modifier.verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                Text("Previous comparison", style = MaterialTheme.typography.headlineSmall)
                Text("A comparison saved in an earlier version. It is separate from recorded swims.")
                ResultCard(value)
                Button(onClick = { update(value); tab = 0; showingLegacy = false }) { Text("Use these inputs") }
                TextButton(onClick = { saved = null; preferences.edit().remove("saved").apply(); showingLegacy = false }) { Text("Remove previous comparison") }
                TextButton(onClick = { showingLegacy = false }) { Text("Done") }
            }
        }
        history.message?.let { message ->
            AlertDialog(onDismissRequest = { history.message = null }, title = { Text("My times") }, text = { Text(message) },
                confirmButton = { TextButton(onClick = { history.message = null }) { Text("OK") } })
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable private fun ConverterWorkspace(draft: Draft, modifier: Modifier, historyReady: Boolean,
    update: (Draft) -> Unit, add: () -> Unit, about: () -> Unit) {
    val timeFocus = remember { FocusRequester() }
    var editingTime by remember { mutableStateOf(false) }
    val restoreTimeFocus = editingTime
    val inputs = remember { movableContentOf<Draft, Boolean> { current, ready ->
        Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            ConverterInputs(current, ready, update, add, timeFocus) { editingTime = it }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("On this device. Works offline.", style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1f))
                TextButton(onClick = about, modifier = Modifier.testTag("methodology")) { Text("About") }
            }
        }
    } }
    AdaptiveWorkspace(modifier, name = "converter", primary = {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) { inputs(draft, historyReady) }
    }, supporting = { tabletop ->
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) {
            ResultCard(draft, compact = tabletop, selectCourse = { update(draft.copy(targetIndex = it)) })
        }
    }, compact = {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            ResultCard(draft, compact = true, selectCourse = { update(draft.copy(targetIndex = it)) })
            inputs(draft, historyReady)
        }
    }, onPaneChange = { if (restoreTimeFocus) timeFocus.requestFocus() })
}

@OptIn(ExperimentalLayoutApi::class)
@Composable private fun ConverterInputs(draft: Draft, historyReady: Boolean, update: (Draft) -> Unit, add: () -> Unit,
    timeFocus: FocusRequester, editing: (Boolean) -> Unit) {
    val largeText = LocalDensity.current.fontScale >= 1.5f
    val c = LocalTurnmarkColors.current
    val focus = LocalFocusManager.current
    val keyboard = LocalSoftwareKeyboardController.current
    Card(shape = RoundedCornerShape(TurnmarkTokens.radiusCard), colors = CardDefaults.cardColors(containerColor = c.surface)) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text("Your swim", style = MaterialTheme.typography.titleMedium)
            Text("Your time", style = MaterialTheme.typography.labelLarge)
            OutlinedTextField(draft.time, { update(draft.copy(time = it)) },
                modifier = Modifier.fillMaxWidth().focusRequester(timeFocus).onFocusChanged { editing(it.isFocused) }.testTag("timeInput"), singleLine = true,
                textStyle = MaterialTheme.typography.headlineLarge.copy(fontFeatureSettings = "tnum"),
                supportingText = { Text("For example, 58.32 or 1:02.45") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii, imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = {
                    focus.clearFocus(); keyboard?.hide()
                }))
            FlowRow(maxItemsInEachRow = if (largeText) 1 else 2,
                horizontalArrangement = Arrangement.spacedBy(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Choice("Stroke", if (draft.strokeIndex == 4) "IM" else strokeNames[draft.strokeIndex], strokeNames,
                    Modifier.semantics { stateDescription = strokeNames[draft.strokeIndex] }) { update(draft.copy(strokeIndex = it)) }
                Choice("Distance", "${draft.distance} ${draft.unit}", draft.options.map { "${it.event.distance} ${draft.unit}" }, Modifier) {
                    update(draft.copy(distance = draft.options[it].event.distance))
                }
            }
            CourseControl("Swum in", "inputCourse", draft.courseIndex) { update(draft.copy(courseIndex = it)) }
            Text("Published category", style = MaterialTheme.typography.labelLarge)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("Women", "Men").forEachIndexed { index, label ->
                    FilterChip(draft.categoryIndex == index, { update(draft.copy(categoryIndex = index)) }, { Text(label) })
                }
            }
            CourseControl("Compare with", "targetCourse", draft.targetIndex) { update(draft.copy(targetIndex = it)) }
            HorizontalDivider()
            Button(onClick = add, enabled = draft.canLog && historyReady,
                colors = ButtonDefaults.buttonColors(containerColor = c.actionFill, contentColor = c.onAction),
                modifier = Modifier.fillMaxWidth().testTag("logSwim")) {
                Icon(Icons.Default.Add, contentDescription = null); Spacer(Modifier.width(8.dp)); Text("Record time")
            }
            Text("Record the time you swam, with a date and optional meet.", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
        }
    }
}

@Composable fun CourseControl(label: String, tag: String, selected: Int, onSelect: (Int) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(label, fontWeight = FontWeight.Bold)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            courses.forEachIndexed { index, course ->
                FilterChip(selected == index, { onSelect(index) }, { Text(course.name) }, modifier = Modifier.testTag("$tag-${course.name}"))
            }
        }
    }
}

@Composable fun Choice(label: String, selected: String, values: List<String>, modifier: Modifier, onSelect: (Int) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier) {
        OutlinedButton(onClick = { expanded = true }) { Text("$label: $selected") }
        DropdownMenu(expanded, { expanded = false }) {
            values.forEachIndexed { index, value -> DropdownMenuItem(text = { Text(value) }, onClick = { expanded = false; onSelect(index) }) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun ResultCard(draft: Draft, compact: Boolean = false, selectCourse: ((Int) -> Unit)? = null) {
    var showingDetails by remember { mutableStateOf(false) }
    var showingCourses by rememberSaveable { mutableStateOf(false) }
    val result = draft.outcome
    val c = TurnmarkTokens.dark
    val context = LocalContext.current
    TurnmarkTheme(dark = true) {
        Column(Modifier.fillMaxWidth().background(Brush.linearGradient(listOf(c.surfaceRaised, c.surface)), RoundedCornerShape(TurnmarkTokens.radiusCard))
            .padding(if (compact) 20.dp else 24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("YOUR COMPARISON", color = c.textMuted, style = MaterialTheme.typography.labelSmall)
            when (result) {
                is ConversionOutcome.Available -> {
                    Text(draft.resultLabel(result.value.event), color = c.textMuted, style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.testTag("resultContext"))
                    ResultTime(result.value.time, compact)
                    Text(kindLabel(result.value.kind), color = c.textMuted, style = MaterialTheme.typography.labelMedium)
                    if (result.value.kind != ConversionKind.SWUM) Text("From ${draft.time} · ${draft.distance} ${draft.unit} ${courses[draft.courseIndex]}",
                        color = c.textMuted, style = MaterialTheme.typography.bodySmall)
                    if (compact) TextButton(onClick = { showingCourses = !showingCourses }, modifier = Modifier.testTag("courseEquivalents")) {
                        Text(if (showingCourses) "Hide course equivalents" else "All course equivalents")
                    }
                    if (!compact || showingCourses) {
                        HorizontalDivider()
                        courses.forEachIndexed { index, course ->
                            val row = convertSwim(ConversionRequest(Swim(draft.time, SwimEvent(draft.distance, strokes[draft.strokeIndex], courses[draft.courseIndex])),
                                course, if (draft.categoryIndex == 0) Category.WOMEN else Category.MEN))
                            TextButton(onClick = { selectCourse?.invoke(index) }, modifier = Modifier.fillMaxWidth().testTag("equivalent-$course"),
                                colors = ButtonDefaults.textButtonColors(contentColor = if (index == draft.targetIndex) c.resultHighlight else c.text)) {
                                Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                        Row { Text(course.name); if (index == draft.targetIndex) { Spacer(Modifier.width(6.dp)); Icon(Icons.Default.Check, "Selected", Modifier.size(18.dp)) } }
                                        Text(if (row is ConversionOutcome.Available) row.value.time else "Unavailable", fontWeight = FontWeight.Bold)
                                    }
                                    Text(if (row is ConversionOutcome.Available) "${draft.resultLabel(row.value.event)} · ${kindLabel(row.value.kind)}" else "No published conversion",
                                        style = MaterialTheme.typography.bodySmall, color = c.textMuted)
                                }
                            }
                            if (index < 2) HorizontalDivider()
                        }
                    }
                    FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        TextButton(onClick = { showingDetails = true }, modifier = Modifier.testTag("conversionDetails")) {
                            Icon(Icons.Default.Info, null, Modifier.size(18.dp)); Spacer(Modifier.width(6.dp)); Text("Details")
                        }
                        OutlinedButton(onClick = { share(context, draft) }, modifier = Modifier.testTag("shareSwim")) { Text("Share") }
                    }
                }
                is ConversionOutcome.Invalid -> {
                    Text("Check your time", color = c.text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.testTag("invalidTime"))
                    Text("Try 58.32 or 1:02.45, up to 60 minutes.", color = c.textMuted, style = MaterialTheme.typography.bodyMedium)
                }
                is ConversionOutcome.Unavailable -> {
                    Text("No published conversion", color = c.text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.testTag("unavailableConversion"))
                    Text("Choose another event or course comparison.", color = c.textMuted, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
    if (showingDetails && result is ConversionOutcome.Available) ModalBottomSheet(onDismissRequest = { showingDetails = false },
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        ConversionDetails(draft, result) { showingDetails = false }
    }
}

private fun kindLabel(kind: ConversionKind) = when (kind) {
    ConversionKind.SWUM -> "Original time"
    ConversionKind.PUBLISHED -> "Published factor"
    ConversionKind.DERIVED -> "Derived estimate"
}

@Composable private fun ResultTime(time: String, compact: Boolean) {
    val c = LocalTurnmarkColors.current
    val scale = LocalDensity.current.fontScale
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        // Fit the complete clock while body/context retain normal font scaling.
        val size = minOf(if (compact) 44f else 64f, maxWidth.value / (time.length * .64f * scale)).sp
        val split = time.indexOf('.')
        val text = buildAnnotatedString {
            append(if (split >= 0) time.substring(0, split) else time)
            if (split >= 0) withStyle(SpanStyle(color = c.resultHighlight)) { append(time.substring(split)) }
        }
        Text(text, fontSize = size, fontWeight = FontWeight.Bold, color = c.text,
            fontFamily = androidx.compose.ui.text.font.FontFamily.Default, style = MaterialTheme.typography.displayLarge.copy(fontFeatureSettings = "tnum"),
            modifier = Modifier.testTag("resultTime"), maxLines = 1)
    }
}

@Composable private fun ConversionDetails(draft: Draft, result: ConversionOutcome.Available, onClose: () -> Unit) {
    val context = LocalContext.current
    Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp).padding(bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Text("Conversion details", style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
            TextButton(onClick = onClose) { Text("Done") }
        }
        Text("Entered swim", fontWeight = FontWeight.Bold)
        Text(draft.time, style = MaterialTheme.typography.headlineSmall)
        Text(draft.label)
        HorizontalDivider()
        Text(if (result.value.kind == ConversionKind.SWUM) "Same course" else "Comparison", fontWeight = FontWeight.Bold)
        Text(result.value.time, style = MaterialTheme.typography.headlineSmall)
        Text(draft.resultLabel(result.value.event))
        Text(when (result.value.kind) {
            ConversionKind.SWUM -> "The entered time is unchanged."
            ConversionKind.PUBLISHED -> "Uses the published NCAA metric-to-yards factor."
            ConversionKind.DERIVED -> "Derived from the published NCAA factors; this is an estimate."
        })
        Text("Time multiplier: ${result.value.factor}")
        if (result.value.kind != ConversionKind.SWUM) {
            Text("Multiplies the entered seconds by this factor, then truncates to hundredths.",
                style = MaterialTheme.typography.bodySmall)
        }
        HorizontalDivider()
        Text("Source", fontWeight = FontWeight.Bold)
        Text(result.provenance.title)
        Text("Edition: ${result.provenance.id}")
        Text("Revision: ${result.provenance.revision}", style = MaterialTheme.typography.bodySmall)
        TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(result.provenance.url))) }) { Text("Published source") }
        Text("Source links need an internet connection. Calculation and source metadata work offline.", style = MaterialTheme.typography.bodySmall)
        Text("A converted time is not a recorded performance or confirmation of meet-entry eligibility.", style = MaterialTheme.typography.bodySmall)
    }
}
