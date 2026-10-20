package net.stanback.turnmark

import kotlin.math.roundToInt
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.BorderStroke
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
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.layout.positionInParent
import kotlinx.coroutines.launch
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
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.text.rememberTextMeasurer
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
val strokeImages = listOf(R.drawable.ic_swim_freestyle, R.drawable.ic_swim_backstroke, R.drawable.ic_swim_breaststroke, R.drawable.ic_swim_butterfly, R.drawable.ic_swim_individual_medley)
val strokeCodes = listOf("FR", "BK", "BR", "FL", "IM")

private const val coloradoDistanceCaveat = "Distance caveat: this documented Colorado rule uses a general SCM/SCY multiplier for unequal-distance freestyle events. Check the meet’s required conversion."

data class Draft(
    val time: String = "", val strokeIndex: Int = 0, val distance: UInt = 100u,
    val courseIndex: Int = 0, val categoryIndex: Int = 0, val targetIndex: Int = 2,
    val methodId: String = "ncaa-2025-27",
    val altitudeText: String? = null, val elevationUnitIndex: Int = 0,
    val altitudePolicyId: String = "usa-swimming-altitude-2026",
) {
    val method get() = if (methodId == "colorado-teamunify-2026") ConversionMethod.COLORADO else ConversionMethod.NCAA
    val methodLabel get() = if (method == ConversionMethod.COLORADO) "Colorado Timing" else "NCAA"
    val options get() = getEventOptions(courses[courseIndex], strokes[strokeIndex])
    val altitudePolicy get() = if (altitudePolicyId == "ncaa-altitude-2026-27-d1") AltitudePolicy.NCAA else AltitudePolicy.USA_SWIMMING
    val swim get() = Swim(time, SwimEvent(distance, strokes[strokeIndex], courses[courseIndex]))
    val elevation get() = Elevation(altitudeText?.toDoubleOrNull() ?: Double.NaN, if (elevationUnitIndex == 1) ElevationUnit.METERS else ElevationUnit.FEET)
    val altitudeOutcome get() = adjustAltitudeWithPolicy(AltitudeRequest(swim, elevation), altitudePolicy)
    val outcome get(): ConversionOutcome {
        val request = ConversionRequest(swim, courses[targetIndex], if (categoryIndex == 0) Category.WOMEN else Category.MEN)
        return if (altitudeText == null) convertSwimWithMethod(request, method)
            else convertSwimAtAltitude(request, method, elevation, altitudePolicy)
    }
    val methodDifference: String? get() {
        val ncaa = copy(methodId = "ncaa-2025-27").outcome as? ConversionOutcome.Available ?: return null
        val colorado = copy(methodId = "colorado-teamunify-2026").outcome as? ConversionOutcome.Available ?: return null
        return String.format(java.util.Locale.ROOT, "%.2fs", kotlin.math.abs(ncaa.value.hundredths.toDouble() - colorado.value.hundredths.toDouble()) / 100)
    }
    val available get() = outcome is ConversionOutcome.Available
    val category get() = if (categoryIndex == 0) "Women" else "Men"
    val unit get() = if (courseIndex == 0) "yd" else "m"
    val label get() = "$distance $unit ${strokeNames[strokeIndex]} · ${courses[courseIndex]} · $category"
    fun resultLabel(event: SwimEvent): String =
        "${event.distance} ${if (event.course == Course.SCY) "yd" else "m"} ${strokeNames[strokes.indexOf(event.stroke)]} · ${event.course} · $category"
    fun reconcile(): Draft = if (options.any { it.event.distance == distance }) this
        else copy(distance = options.first().event.distance)
    fun withElevationUnit(unit: Int): Draft {
        val value = altitudeText?.toDoubleOrNull()
        val text = if (value != null && value.isFinite() && value >= 0 && unit != elevationUnitIndex)
            if (unit == 1) String.format(java.util.Locale.ROOT, "%.1f", value * .3048)
            else String.format(java.util.Locale.ROOT, "%.0f", (value / .3048).roundToInt().toDouble())
            else altitudeText
        return copy(altitudeText = text, elevationUnitIndex = unit)
    }
    fun encode(): String = JSONObject().put("time", time).put("stroke", strokeIndex)
        .put("distance", distance.toLong()).put("course", courseIndex)
        .put("category", categoryIndex).put("target", targetIndex).put("method", methodId).put("altitude", altitudeText ?: JSONObject.NULL)
        .put("elevationUnit", elevationUnitIndex).put("altitudePolicy", altitudePolicyId).toString()
    val shareUrl: String get() {
        val query = Uri.Builder().appendQueryParameter("t", time)
            .appendQueryParameter("s", strokeCodes[strokeIndex])
            .appendQueryParameter("d", options.first { it.event.distance == distance }.canonicalDistance.toString())
            .appendQueryParameter("c", courses[courseIndex].name)
            .appendQueryParameter("g", if (categoryIndex == 0) "women" else "men")
            .appendQueryParameter("h", if (altitudeText == null) "0" else (altitudeOutcome as? AltitudeOutcome.Available)?.value?.elevationFeet?.toString() ?: "0").apply {
                if (altitudeText != null && altitudePolicy == AltitudePolicy.NCAA) appendQueryParameter("ap", altitudePolicyId)
                if (method == ConversionMethod.COLORADO) appendQueryParameter("m", methodId)
            }.build().encodedQuery
        return Uri.parse("https://turnmark.app/").buildUpon().encodedFragment(query).build().toString()
    }
    companion object {
        val example get() = Draft(time = "58.32")
        fun decode(text: String?): Draft? = runCatching {
            val json = JSONObject(text ?: return null)
            val distance = json.getLong("distance")
            require(distance in 1..UInt.MAX_VALUE.toLong())
            val draft = Draft(json.getString("time"), json.getInt("stroke"), distance.toUInt(),
                json.getInt("course"), json.getInt("category"), json.getInt("target"),
                json.optString("method", "ncaa-2025-27"),
                if (json.has("altitude") && !json.isNull("altitude")) json.getString("altitude") else null,
                json.optInt("elevationUnit", 0), json.optString("altitudePolicy", "usa-swimming-altitude-2026"))
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
    var benchmarkingJSON by rememberSaveable { mutableStateOf<String?>(null) }
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
                        TopAppBar(title = {
                            if (tab == 1) Text("My times", fontWeight = FontWeight.Bold)
                            else BoxWithConstraints(Modifier.fillMaxWidth().testTag("converterBrand")
                                .clearAndSetSemantics { contentDescription = "Turnmark"; heading() }) {
                                val style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
                                val wordmark = buildAnnotatedString {
                                    append("turnmark")
                                    withStyle(SpanStyle(color = c.accent)) { append(".") }
                                }
                                val wordmarkWidth = rememberTextMeasurer().measure(wordmark, style = style).size.width
                                val showWordmark = wordmarkWidth <= with(LocalDensity.current) { (maxWidth - 34.dp).toPx() }
                                Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                                    Icon(painterResource(R.drawable.ic_swim_brand_wave), null, tint = c.accent, modifier = Modifier.size(27.dp))
                                    if (showWordmark) Text(wordmark, style = style, maxLines = 1)
                                }
                            }
                        },
                            colors = TopAppBarDefaults.topAppBarColors(containerColor = c.canvas), actions = {
                            if (tab == 1) {
                                IconButton(enabled = history.ready && !history.busy, onClick = { loggingJSON = draft.copy(time = "").encode() }, modifier = Modifier.testTag("recordTime")) {
                                    Icon(painterResource(R.drawable.ic_swim_log_swim), contentDescription = "Log swim")
                                }
                            } else {
                                var expanded by remember { mutableStateOf(false) }
                                Box {
                                    IconButton(onClick = { expanded = true }, modifier = Modifier.testTag("converterMenu")) {
                                        Icon(Icons.Default.MoreVert, contentDescription = "More options")
                                    }
                                    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                                        DropdownMenuItem(text = { Text("About Turnmark") }, onClick = {
                                            expanded = false; focus.clearFocus(); keyboard?.hide(); showingMethod = true
                                        }, leadingIcon = { Icon(Icons.Default.Info, null) }, modifier = Modifier.testTag("converterAbout"))
                                        DropdownMenuItem(text = { Text("Methodology and coverage") }, onClick = {
                                            expanded = false
                                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://turnmark.app/#method")))
                                        }, leadingIcon = { Icon(Icons.Default.ArrowForward, null) })
                                    }
                                }
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
                        about = { showingMethod = true }, benchmarks = { focus.clearFocus(); keyboard?.hide(); benchmarkingJSON = it.encode() })
                }
            }
        }
        Draft.decode(benchmarkingJSON)?.let { input -> BenchmarkSheet(input) { benchmarkingJSON = null } }
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
                Text("NCAA factors are the default. Colorado Timing formulas are available in the overflow menu. Reverse and cross-metric NCAA conversions are derived estimates. The original time stays separate.")
                Text("A converted time is not an official swim or confirmation of meet-entry eligibility.")
                TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://turnmark.app/#method"))) }) { Text("Methodology and coverage") }
                TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://turnmark.app/#resources"))) }) { Text("Swimming resources") }
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
    update: (Draft) -> Unit, add: () -> Unit, about: () -> Unit, benchmarks: (Draft) -> Unit) {
    val timeFocus = remember { FocusRequester() }
    var editingTime by remember { mutableStateOf(false) }
    val restoreTimeFocus = editingTime
    val scroll = rememberScrollState()
    val focus = LocalFocusManager.current
    val keyboard = LocalSoftwareKeyboardController.current
    val scope = rememberCoroutineScope()
    var resultOffset by remember { mutableIntStateOf(0) }
    val inputs = remember { movableContentOf<Draft, Boolean> { current, ready ->
        Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            ConverterInputs(current, ready, update, add, timeFocus) { editingTime = it }
        }
    } }
    AdaptiveWorkspace(modifier, name = "converter", primary = {
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) { inputs(draft, historyReady) }
    }, supporting = { tabletop ->
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) {
            ResultCard(draft, compact = tabletop, benchmarks = benchmarks, selectCourse = { update(draft.copy(targetIndex = it)) }, log = if (historyReady) add else null)
        }
    }, compact = {
        Column(Modifier.fillMaxSize().verticalScroll(scroll).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            inputs(draft, historyReady)
            if (draft.available) OutlinedButton(onClick = {
                focus.clearFocus(); keyboard?.hide()
                scope.launch { scroll.animateScrollTo(resultOffset) }
            }, modifier = Modifier.fillMaxWidth().testTag("seeResults")) {
                Text("See your results"); Spacer(Modifier.width(8.dp)); Icon(Icons.Default.KeyboardArrowDown, null)
            }
            Box(Modifier.onGloballyPositioned { resultOffset = it.positionInParent().y.toInt() }) {
                ResultCard(draft, compact = true, benchmarks = benchmarks,
                    selectCourse = { update(draft.copy(targetIndex = it)) }, log = if (historyReady) add else null)
            }
            Text("On this device. Works offline.", style = MaterialTheme.typography.bodySmall, color = LocalTurnmarkColors.current.textMuted)
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
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text("Your swim", style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                TextButton(onClick = { focus.clearFocus(); keyboard?.hide(); update(draft.copy(time = "")) }, modifier = Modifier.testTag("resetConverter")) {
                    Text("Reset"); Spacer(Modifier.width(6.dp)); Icon(Icons.Default.Refresh, null, Modifier.size(16.dp))
                }
            }
            Text("Your time", style = MaterialTheme.typography.labelLarge)
            OutlinedTextField(draft.time, { update(draft.copy(time = it)) },
                modifier = Modifier.fillMaxWidth().focusRequester(timeFocus).onFocusChanged { editing(it.isFocused) }.testTag("timeInput"), singleLine = true,
                shape = MaterialTheme.shapes.medium,
                textStyle = MaterialTheme.typography.headlineLarge.copy(fontFeatureSettings = "tnum"),
                trailingIcon = {
                    if (draft.time.isNotEmpty()) IconButton(onClick = { update(draft.copy(time = "")); timeFocus.requestFocus() }) {
                        Icon(Icons.Default.Clear, contentDescription = "Clear time")
                    }
                },
                placeholder = { Text("58.32") },
                supportingText = { Text(if (draft.time.isEmpty()) "Enter seconds or a time like 1:02.45" else "Results update as you type") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii, imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = {
                    focus.clearFocus(); keyboard?.hide()
                }))

            @Composable fun StrokeChoice(modifier: Modifier) {
                Choice("Stroke", if (draft.strokeIndex == 4) "IM" else strokeNames[draft.strokeIndex], strokeNames,
                    modifier.semantics { stateDescription = strokeNames[draft.strokeIndex] },
                    labelIcon = strokeImages[draft.strokeIndex], optionIcons = strokeImages) { update(draft.copy(strokeIndex = it)) }
            }
            @Composable fun DistanceChoice(modifier: Modifier) {
                Choice("Distance", "${draft.distance} ${draft.unit}", draft.options.map { "${it.event.distance} ${draft.unit}" }, modifier, labelIcon = R.drawable.ic_swim_distance) {
                    update(draft.copy(distance = draft.options[it].event.distance))
                }
            }
            BoxWithConstraints(Modifier.fillMaxWidth()) {
                if (largeText || maxWidth < 320.dp) {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        StrokeChoice(Modifier.fillMaxWidth()); DistanceChoice(Modifier.fillMaxWidth())
                    }
                } else {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        StrokeChoice(Modifier.weight(1f)); DistanceChoice(Modifier.weight(1f))
                    }
                }
            }
            CourseControl("Swum in", "inputCourse", draft.courseIndex) { update(draft.copy(courseIndex = it)) }
            Text("Published category", style = MaterialTheme.typography.labelLarge)
            BoxWithConstraints(Modifier.fillMaxWidth()) {
                if (maxWidth < 240.dp) {
                    Choice("Published category", draft.category, listOf("Women", "Men"), Modifier.fillMaxWidth()) {
                        update(draft.copy(categoryIndex = it))
                    }
                } else {
                    SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                        listOf("Women", "Men").forEachIndexed { index, label ->
                            SegmentedButton(selected = draft.categoryIndex == index, onClick = { update(draft.copy(categoryIndex = index)) },
                                shape = SegmentedButtonDefaults.itemShape(index, 2)) { Text(label) }
                        }
                    }
                }
            }
            var calculationExpanded by rememberSaveable { mutableStateOf(draft.altitudeText != null || draft.methodId == "colorado-teamunify-2026") }
            TextButton(onClick = { calculationExpanded = !calculationExpanded }, modifier = Modifier.testTag("calculationOptions")) {
                Text("Calculation options"); Spacer(Modifier.width(8.dp)); Icon(Icons.Default.KeyboardArrowDown, null)
            }
            if (calculationExpanded) {
                Choice("Course conversion", if (draft.methodId == "colorado-teamunify-2026") "Colorado Timing" else "NCAA (default)", listOf("NCAA (default)", "Colorado Timing"), Modifier.fillMaxWidth()) {
                    update(draft.copy(methodId = if (it == 1) "colorado-teamunify-2026" else "ncaa-2025-27"))
                }
                Row(Modifier.fillMaxWidth(), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                    Text("Adjust for altitude", modifier = Modifier.weight(1f))
                    Switch(checked = draft.altitudeText != null, onCheckedChange = { update(draft.copy(altitudeText = if (it) "0" else null)) }, modifier = Modifier.testTag("altitudeEnabled"))
                }
                if (draft.altitudeText != null) {
                    OutlinedTextField(value = draft.altitudeText, onValueChange = { update(draft.copy(altitudeText = it)) },
                        label = { Text("Pool elevation") }, singleLine = true, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal, imeAction = ImeAction.Done),
                        keyboardActions = KeyboardActions(onDone = { focus.clearFocus(); keyboard?.hide() }),
                        modifier = Modifier.fillMaxWidth().testTag("poolElevation"))
                    Choice("Elevation unit", if (draft.elevationUnitIndex == 1) "Meters" else "Feet", listOf("Feet", "Meters"), Modifier.fillMaxWidth()) {
                        update(draft.withElevationUnit(it))
                    }
                    Choice("Altitude policy", if (draft.altitudePolicy == AltitudePolicy.NCAA) "NCAA · 2026–27 Division I" else "USA Swimming (default)",
                        listOf("USA Swimming (default)", "NCAA · 2026–27 Division I"), Modifier.fillMaxWidth()) {
                        update(draft.copy(altitudePolicyId = if (it == 1) "ncaa-altitude-2026-27-d1" else "usa-swimming-altitude-2026"))
                    }
                    val preview = draft.altitudeOutcome
                    if (preview is AltitudeOutcome.Available) Text("Altitude deduction: −${String.format(java.util.Locale.ROOT, "%.2f", preview.value.adjustmentSeconds)}s. Sea-level estimate: ${preview.value.adjustedTime}. Applied before course conversion.",
                        style = MaterialTheme.typography.bodySmall, color = c.textMuted)
                }
            }
        }
    }
}

@Composable fun CourseControl(label: String, tag: String, selected: Int, onSelect: (Int) -> Unit) {
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        if (maxWidth < 240.dp) {
            Choice(label, courses[selected].name, courses.map { it.name }, Modifier.fillMaxWidth().testTag(tag), onSelect = onSelect)
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(label, fontWeight = FontWeight.Bold)
                SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                    courses.forEachIndexed { index, course ->
                        SegmentedButton(selected = selected == index, onClick = { onSelect(index) },
                            shape = SegmentedButtonDefaults.itemShape(index, courses.size), modifier = Modifier.testTag("$tag-${course.name}")) { Text(course.name) }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun Choice(label: String, selected: String, values: List<String>, modifier: Modifier, labelIcon: Int? = null, optionIcons: List<Int?>? = null, selectedIcon: Int? = null, maxLines: Int = 1, onSelect: (Int) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    BoxWithConstraints(modifier) {
        val showIcon = maxWidth >= 160.dp && labelIcon != null
        ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }, modifier = Modifier.fillMaxWidth()) {
            val leading: (@Composable () -> Unit)? = selectedIcon?.let { resource ->
                { Icon(painterResource(resource), contentDescription = "Altitude adjusted", modifier = Modifier.size(20.dp)) }
            }
            OutlinedTextField(value = selected, onValueChange = {}, readOnly = true, singleLine = maxLines == 1, maxLines = maxLines, leadingIcon = leading, label = {
                Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    if (showIcon) Icon(painterResource(labelIcon!!), contentDescription = null, modifier = Modifier.size(16.dp))
                    Text(label)
                }
            }, shape = MaterialTheme.shapes.medium,
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                modifier = Modifier.fillMaxWidth().menuAnchor(ExposedDropdownMenuAnchorType.PrimaryNotEditable).testTag("choice-$label"))
            ExposedDropdownMenu(expanded, { expanded = false }) {
                values.forEachIndexed { index, value ->
                    val icon: (@Composable () -> Unit)? = optionIcons?.getOrNull(index)?.let { resource ->
                        { Icon(painterResource(resource), contentDescription = null, modifier = Modifier.size(24.dp)) }
                    }
                    DropdownMenuItem(text = { Text(value) }, leadingIcon = icon, onClick = { expanded = false; onSelect(index) })
                }
            }
        }
    }
}

/** Native opaque result surface shared by conversions, standards and points. */
@Composable fun NativeResultSurface(compact: Boolean = false, content: @Composable ColumnScope.() -> Unit) {
    val c = TurnmarkTokens.dark
    TurnmarkTheme(dark = true) {
        Surface(shape = RoundedCornerShape(TurnmarkTokens.radiusCard), color = c.surface, contentColor = c.text,
            border = BorderStroke(1.dp, c.borderSubtle), modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.background(Brush.linearGradient(listOf(c.surfaceRaised, c.surface))).drawBehind {
                val ribbon = Path().apply {
                    moveTo(size.width * .45f, 0f)
                    cubicTo(size.width * .72f, 0f, size.width * .76f, size.height * .25f, size.width, size.height * .28f)
                    lineTo(size.width, size.height * .44f)
                    cubicTo(size.width * .72f, size.height * .42f, size.width * .68f, size.height * .08f, size.width * .45f, 0f)
                    close()
                }
                drawPath(ribbon, c.accent.copy(alpha = .07f))
            }.padding(if (compact) 20.dp else 24.dp), verticalArrangement = Arrangement.spacedBy(if (compact) 10.dp else 14.dp), content = content)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun ResultCard(draft: Draft, compact: Boolean = false, benchmarks: ((Draft) -> Unit)? = null, selectCourse: ((Int) -> Unit)? = null, log: (() -> Unit)? = null) {
    var showingDetails by remember { mutableStateOf(false) }
    val result = draft.outcome
    val c = TurnmarkTokens.dark
    val context = LocalContext.current
    NativeResultSurface(compact = compact) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Text("EQUIVALENT TIMES", color = c.textMuted, style = MaterialTheme.typography.labelSmall)
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                courses.forEachIndexed { index, _ -> Box(Modifier.width(18.dp).height(2.dp)
                    .background(if (index == draft.targetIndex) c.resultHighlight else c.borderControl)) }
            }
        }
        if (draft.time.isEmpty()) {
            Text("Enter a swim to compare", style = MaterialTheme.typography.titleMedium, modifier = Modifier.testTag("emptyConversion"))
            Text("See your time in SCY, SCM and LCM.", color = c.textMuted, style = MaterialTheme.typography.bodyMedium)
        } else when (result) {
            is ConversionOutcome.Available -> {
                Text(draft.resultLabel(result.value.event), color = c.textMuted, style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.testTag("resultContext"))
                ResultTime(result.value.time, compact)
                Text((if ((result.value.altitude?.value?.adjustmentSeconds ?: 0.0) > 0 && result.value.kind == ConversionKind.SWUM) "Sea-level estimate" else kindLabel(result.value.kind)) + if (result.value.kind != ConversionKind.SWUM && draft.method == ConversionMethod.COLORADO) " · Colorado Timing" else "", color = c.textMuted, style = MaterialTheme.typography.labelMedium)
                if (result.value.caveat != null) Text(coloradoDistanceCaveat, style = MaterialTheme.typography.bodySmall, color = c.textMuted, modifier = Modifier.testTag("distanceCaveat"))
                if (result.value.kind != ConversionKind.SWUM) Text("From ${draft.time} · ${draft.distance} ${draft.unit} ${courses[draft.courseIndex]}",
                    color = c.textMuted, style = MaterialTheme.typography.bodySmall)

            }
            is ConversionOutcome.Invalid -> {
                Text("Check your time or elevation", color = c.text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.testTag("invalidTime"))
                Text("Try 58.32 or 1:02.45, up to 60 minutes. Elevation must be 0–20,000 whole feet or 0–6,096 meters.", color = c.textMuted, style = MaterialTheme.typography.bodyMedium)
            }
            is ConversionOutcome.Unavailable -> {
                Text("No published conversion", color = c.text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.testTag("unavailableConversion"))
                Text("Choose another event or course comparison.", color = c.textMuted, style = MaterialTheme.typography.bodyMedium)
            }
        }
        if (parseTime(draft.time) != null) {
            HorizontalDivider(color = c.borderSubtle)
            Text("Select a course to focus", color = c.textMuted, style = MaterialTheme.typography.bodySmall)
            courses.forEachIndexed { index, course ->
                val row = draft.copy(targetIndex = index).outcome
                val selected = index == draft.targetIndex
                Surface(onClick = { selectCourse?.invoke(index) }, enabled = selectCourse != null,
                    shape = RoundedCornerShape(TurnmarkTokens.radiusControl),
                    color = if (selected) c.selectedSurface else c.surfaceInput,
                    contentColor = if (selected) c.resultHighlight else c.text,
                    border = BorderStroke(1.dp, if (selected) c.resultHighlight.copy(alpha = .6f) else c.borderSubtle),
                    modifier = Modifier.fillMaxWidth().testTag("equivalent-$course").semantics { stateDescription = if (selected) "Selected" else "" }) {
                    val large = LocalDensity.current.fontScale >= 1.5f
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        val time = if (row is ConversionOutcome.Available) row.value.time else "Unavailable"
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(course.name, style = MaterialTheme.typography.titleSmall)
                                if (selected) Icon(Icons.Default.Check, "Selected", Modifier.size(18.dp))
                            }
                            if (!large) Text(time, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        }
                        if (large) Text(time, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Text(if (row is ConversionOutcome.Available) "${draft.resultLabel(row.value.event)} · ${if ((row.value.altitude?.value?.adjustmentSeconds ?: 0.0) > 0 && row.value.kind == ConversionKind.SWUM) "Sea-level estimate" else kindLabel(row.value.kind)}" else "No published conversion",
                            style = MaterialTheme.typography.bodySmall, color = c.textMuted)
                    }
                }
            }
            Text("Converted times are estimates. Check your meet’s entry rules.", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
            TextButton(onClick = { showingDetails = true }, modifier = Modifier.testTag("conversionDetails")) {
                Icon(Icons.Default.Info, null, Modifier.size(18.dp)); Spacer(Modifier.width(8.dp)); Text("How this is calculated")
            }
            HorizontalDivider(color = c.borderSubtle)
            log?.let { record ->
                Button(onClick = record, modifier = Modifier.fillMaxWidth().testTag("logSwim"),
                    colors = ButtonDefaults.buttonColors(containerColor = c.actionFill, contentColor = c.onAction)) {
                    Icon(painterResource(R.drawable.ic_swim_log_swim), null); Spacer(Modifier.width(8.dp)); Text("Log swim")
                }
                Text("Add your entered swim to My times.", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
            }
            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                benchmarks?.let { open ->
                    FilledTonalButton(onClick = { open(draft) }, modifier = Modifier.heightIn(min = 48.dp).testTag("openBenchmarks")) {
                        Icon(painterResource(R.drawable.ic_standards), null, Modifier.size(18.dp))
                        Spacer(Modifier.width(8.dp)); Text("Standards & points")
                    }
                }
                if (result is ConversionOutcome.Available) IconButton(onClick = { share(context, draft) }, modifier = Modifier.testTag("shareSwim")) {
                    Icon(Icons.Default.Share, contentDescription = "Share")
                }
            }
        }
    }
    if (showingDetails) ModalBottomSheet(onDismissRequest = { showingDetails = false }, containerColor = LocalTurnmarkColors.current.canvas,
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

@Composable private fun CalculationExplanation(title: String, explanation: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
        Text(explanation, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable private fun AltitudeDetails(draft: Draft) {
    val context = LocalContext.current
    val c = LocalTurnmarkColors.current
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Entered swim: ${draft.time}", style = MaterialTheme.typography.bodyMedium)
        listOf("usa-swimming-altitude-2026", "ncaa-altitude-2026-27-d1").forEach { policy ->
            val row = draft.copy(altitudePolicyId = policy).altitudeOutcome
            if (row is AltitudeOutcome.Available) {
                Text(if (policy == "usa-swimming-altitude-2026") "USA Swimming" else "NCAA · 2026–27 Division I", style = MaterialTheme.typography.titleSmall)
                Text("−${String.format(java.util.Locale.ROOT, "%.2f", row.value.adjustmentSeconds)}s → ${row.value.adjustedTime}", modifier = Modifier.testTag("altitudeResult-$policy"))
                TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(row.provenance.url))) }) { Text("Published altitude policy") }
            } else Text("Enter a valid time and pool elevation.", style = MaterialTheme.typography.bodySmall)
        }
        Text("Altitude is deducted before course conversion. Below 3,000 ft, or where the table has no deduction, the time stays unchanged. Meters are rounded to the nearest foot. Use the policy required by your meet.", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
    }
}

@Composable private fun ConversionDetails(draft: Draft, result: ConversionOutcome, onClose: () -> Unit) {
    val context = LocalContext.current
    val c = LocalTurnmarkColors.current
    val comparisons = listOf("ncaa-2025-27", "colorado-teamunify-2026").map { draft.copy(methodId = it) }
    Column(Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 24.dp).padding(bottom = 16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Text("Conversion details", style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
            TextButton(onClick = onClose) { Text("Done") }
        }
        Column(Modifier.fillMaxWidth().weight(1f, fill = false).verticalScroll(rememberScrollState())
            .padding(horizontal = 24.dp).padding(bottom = 32.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Compare methods · ${courses[draft.targetIndex]}", style = MaterialTheme.typography.titleMedium)
                if (result is ConversionOutcome.Available) Text(draft.resultLabel(result.value.event),
                    style = MaterialTheme.typography.bodySmall, color = c.textMuted)
            }
            Surface(shape = RoundedCornerShape(TurnmarkTokens.radiusCard), color = c.surface,
                border = BorderStroke(1.dp, c.borderSubtle)) {
                Column(Modifier.padding(horizontal = 16.dp)) {
                    comparisons.forEach { comparison ->
                        BoxWithConstraints(Modifier.fillMaxWidth().padding(vertical = 16.dp)) {
                            val stacked = maxWidth < 240.dp || LocalDensity.current.fontScale >= 1.5f
                            val label: @Composable () -> Unit = {
                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                                    Text(comparison.methodLabel, style = MaterialTheme.typography.titleSmall)
                                    if (comparison.method == draft.method) Icon(Icons.Default.Check, "Selected method", Modifier.size(18.dp), tint = c.accent)
                                }
                            }
                            val clock: @Composable () -> Unit = {
                                when (val outcome = comparison.outcome) {
                                    is ConversionOutcome.Available -> Text(outcome.value.time,
                                        style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold,
                                        modifier = Modifier.testTag("methodResult-${comparison.methodLabel}"))
                                    is ConversionOutcome.Unavailable -> Text("Unavailable", style = MaterialTheme.typography.bodyMedium, color = c.textMuted)
                                    is ConversionOutcome.Invalid -> Text("Check your time", style = MaterialTheme.typography.bodyMedium, color = c.textMuted)
                                }
                            }
                            if (stacked) Column(verticalArrangement = Arrangement.spacedBy(6.dp)) { label(); clock() }
                            else Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) { label(); clock() }
                        }
                        HorizontalDivider(color = c.borderSubtle)
                    }
                    draft.methodDifference?.let { Text("Method difference: $it", style = MaterialTheme.typography.titleSmall,
                        modifier = Modifier.padding(vertical = 16.dp).testTag("methodDifference")) }
                }
            }
            Text("Two conversion rules, not a prediction range or confidence interval. Use the method required by your meet.",
                style = MaterialTheme.typography.bodySmall, color = c.textMuted)
            if (comparisons.any { (it.outcome as? ConversionOutcome.Available)?.value?.caveat != null })
                Text(coloradoDistanceCaveat, style = MaterialTheme.typography.bodySmall, color = c.textMuted)
            if (draft.altitudeText != null) { Text("Altitude adjustment", style = MaterialTheme.typography.titleMedium); AltitudeDetails(draft) }
            Text("Why the times differ", style = MaterialTheme.typography.titleMedium)
            CalculationExplanation("NCAA", "Factors vary by event and course, not age. Long-course factors use separate men’s and women’s tables; short-course meters-to-yards factors are shared. NCAA publishes metric-to-yards factors; reverse and SCM/LCM conversions are derived.")
            CalculationExplanation("Colorado Timing", "Documented multipliers plus fixed time offsets. The formulas vary by event and course, not age or category.")
            CalculationExplanation("Pool length", "Shorter pools mean more turns and push-offs. These rules do not adjust for your starts, underwater skill, technique, endurance or individual development.")
            CalculationExplanation("Distance events", "500, 1000 and 1650 yards map to 400, 800 and 1500 meters.")
            if (result is ConversionOutcome.Available) {
                HorizontalDivider(color = c.borderSubtle)
                Text("Selected calculation · ${draft.methodLabel}", style = MaterialTheme.typography.titleMedium)
                CalculationExplanation("Entered swim · ${draft.time}", draft.label)
                CalculationExplanation("Comparison · ${result.value.time}", draft.resultLabel(result.value.event))
                if (result.value.kind == ConversionKind.SWUM) Text("The course is unchanged; any selected altitude deduction is applied first.", style = MaterialTheme.typography.bodyMedium)
                else {
                    Surface(shape = RoundedCornerShape(TurnmarkTokens.radiusControl), color = c.surfaceRaised) {
                        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Time multiplier: ${String.format(java.util.Locale.ROOT, "%.5f", result.value.factor)}", style = MaterialTheme.typography.bodyMedium)
                            if (result.value.offsetSeconds != 0.0) Text("Time offset: ${result.value.offsetSeconds} seconds", style = MaterialTheme.typography.bodyMedium)
                            Text("After any altitude deduction, multiply the seconds, add any offset, then truncate to hundredths. The factor is rounded here for display.",
                                style = MaterialTheme.typography.bodySmall, color = c.textMuted)
                        }
                    }
                }
                HorizontalDivider(color = c.borderSubtle)
                Text("Source", style = MaterialTheme.typography.titleMedium)
                CalculationExplanation(result.provenance.title, "Edition: ${result.provenance.id}")
                Text("Revision: ${result.provenance.revision}", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
                TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(result.provenance.url))) }) { Text("Published source") }
                comparisons.firstOrNull { it.method != draft.method }?.let { other ->
                    val alternative = other.outcome
                    if (alternative is ConversionOutcome.Available) TextButton(onClick = {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(alternative.provenance.url)))
                    }) { Text("${other.methodLabel} source") }
                }
            }
            HorizontalDivider(color = c.borderSubtle)
            Text("Standards, points and logged performances use your original swim, before altitude or course conversion.", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
            Text("A converted time is not a recorded performance or confirmation of meet-entry eligibility.", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
            Text("Calculations and source metadata work offline. Source links need a connection.", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
        }
    }
}
