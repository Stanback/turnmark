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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONObject
import uniffi.turnmark_core.*

private val Ink = Color(0xFF032C43)
private val Lime = Color(0xFFDDF58C)
private val courses = Course.entries
private val strokes = Stroke.entries
private val strokeNames = listOf("Freestyle", "Backstroke", "Breaststroke", "Butterfly", "Individual medley")
private val strokeCodes = listOf("FR", "BK", "BR", "FL", "IM")

private data class Draft(
    val time: String = "58.32", val strokeIndex: Int = 0, val distance: UInt = 100u,
    val courseIndex: Int = 0, val categoryIndex: Int = 0, val targetIndex: Int = 2,
) {
    val options get() = getEventOptions(courses[courseIndex], strokes[strokeIndex])
    val outcome get() = convertSwim(ConversionRequest(
        Swim(time, SwimEvent(distance, strokes[strokeIndex], courses[courseIndex])),
        courses[targetIndex], if (categoryIndex == 0) Category.WOMEN else Category.MEN))
    val available get() = outcome is ConversionOutcome.Available
    val label get() = "$distance ${strokeNames[strokeIndex]} · ${courses[courseIndex]}"
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
        return Uri.parse("https://stanback.github.io/turnmark/").buildUpon().encodedFragment(query).build().toString()
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable private fun Turnmark(preferences: SharedPreferences) {
    var draft by remember { mutableStateOf(Draft.decode(preferences.getString("draft", null)) ?: Draft()) }
    var saved by remember { mutableStateOf(Draft.decode(preferences.getString("saved", null))) }
    var tab by remember { mutableIntStateOf(0) }
    val context = LocalContext.current
    val dark = isSystemInDarkTheme()
    fun update(value: Draft) {
        draft = value.reconcile()
        preferences.edit().putString("draft", draft.encode()).apply()
    }
    MaterialTheme(colorScheme = if (dark) darkColorScheme(primary = Lime, secondaryContainer = Ink, onSecondaryContainer = Lime,
        surface = Color(0xFF122C3C), background = Color(0xFF091F2D))
        else lightColorScheme(primary = Ink, secondaryContainer = Lime, onSecondaryContainer = Ink,
            background = Color(0xFFF0F5F8), surface = Color.White)) {
        Scaffold(topBar = {
            if (tab != 0) TopAppBar(title = {
                Text(if (tab == 1) "Saved swim" else "The method", fontWeight = FontWeight.Bold)
            })
        },
            bottomBar = {
              Column {
                if (tab == 0) ResultSummary(draft)
                NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                    listOf("Convert", "Saved", "Method").forEachIndexed { index, label ->
                        NavigationBarItem(selected = tab == index, onClick = { tab = index },
                            modifier = Modifier.testTag("nav-$label"), label = { Text(label) },
                            icon = {
                                if (index == 2) Icon(Icons.Default.Info, contentDescription = null)
                                else Icon(painterResource(if (index == 0) R.drawable.ic_convert else R.drawable.ic_bookmark), contentDescription = null)
                            })
                    }
                }
              }
            }) { insets ->
            Column(Modifier.padding(insets).fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(20.dp)) {
                when (tab) {
                    0 -> {
                        Card(shape = RoundedCornerShape(24.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
                                Text("Your time", fontWeight = FontWeight.Bold)
                                OutlinedTextField(draft.time, { update(draft.copy(time = it)) },
                                    modifier = Modifier.fillMaxWidth().testTag("timeInput"),
                                    label = { Text("Minutes : seconds . hundredths") }, singleLine = true,
                                    textStyle = MaterialTheme.typography.headlineLarge,
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii))
                                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                    Choice("Stroke", strokeNames[draft.strokeIndex], strokeNames, Modifier.weight(1f)) {
                                        update(draft.copy(strokeIndex = it))
                                    }
                                    Choice("Distance", draft.distance.toString(), draft.options.map { it.event.distance.toString() }, Modifier.weight(1f)) {
                                        update(draft.copy(distance = draft.options[it].event.distance))
                                    }
                                }
                                CourseControl("Swum in", "inputCourse", draft.courseIndex) { update(draft.copy(courseIndex = it)) }
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    listOf("Women", "Men").forEachIndexed { i, text ->
                                        FilterChip(draft.categoryIndex == i, { update(draft.copy(categoryIndex = i)) }, { Text(text) })
                                    }
                                }
                                CourseControl("Compare with", "targetCourse", draft.targetIndex) { update(draft.copy(targetIndex = it)) }
                            }
                        }
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            OutlinedButton(onClick = { saved = draft; preferences.edit().putString("saved", draft.encode()).apply() }, enabled = draft.available) { Text("Save swim") }
                            OutlinedButton(onClick = { share(context, draft) }, enabled = draft.available) { Text("Share") }
                        }
                        Text("Calculated on your device. Works offline.", style = MaterialTheme.typography.bodySmall)
                    }
                    1 -> {
                        val swim = saved
                        if (swim == null) {
                            Text("No saved swim", style = MaterialTheme.typography.headlineSmall)
                            Text("Save a conversion to return to it here.")
                        } else {
                            Text(swim.label, style = MaterialTheme.typography.titleMedium)
                            Text("Entered time: ${swim.time}")
                            ResultCard(swim)
                            Button(onClick = { update(swim); tab = 0 }) { Text("Use this swim") }
                            OutlinedButton(onClick = { share(context, swim) }) { Text("Share saved swim") }
                            TextButton(onClick = { saved = null; preferences.edit().remove("saved").apply() }) { Text("Remove saved swim") }
                        }
                    }
                    else -> {
                        Text("How comparisons work", style = MaterialTheme.typography.headlineSmall)
                        Text("Published NCAA factors estimate a yards time from a metric swim. Reverse and cross-metric conversions are derived estimates. An entered swim remains labeled as entered.")
                        Text("A converted time is not an official swim or confirmation of meet-entry eligibility.")
                        val result = draft.outcome
                        if (result is ConversionOutcome.Available) {
                            Text(result.provenance.title, fontWeight = FontWeight.Bold)
                            Text("Edition: ${result.provenance.id}")
                            TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(result.provenance.url))) }) { Text("Published source") }
                        }
                        Text("Your data", style = MaterialTheme.typography.headlineSmall)
                        Text("Your current inputs and one saved swim stay on this device. Sharing uses a link containing the entered swim. Source links need an internet connection.")
                    }
                }
            }
        }
    }
}

@Composable private fun ResultSummary(draft: Draft) {
    Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 8.dp)
        .background(Ink, RoundedCornerShape(20.dp)).padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        when (val result = draft.outcome) {
            is ConversionOutcome.Available -> {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text("${courses[draft.courseIndex]} → ${courses[draft.targetIndex]}", color = Lime, fontWeight = FontWeight.Bold)
                        Text(when (result.value.kind) { ConversionKind.SWUM -> "Entered swim"; ConversionKind.PUBLISHED -> "Published factor"; ConversionKind.DERIVED -> "Derived estimate" }, color = Lime, style = MaterialTheme.typography.labelMedium)
                    }
                    Text(result.value.time, fontSize = 34.sp, fontWeight = FontWeight.Bold, color = Color.White, modifier = Modifier.testTag("resultTime"))
                }
                Text(result.provenance.title, color = Color.White.copy(alpha = 0.8f), style = MaterialTheme.typography.labelSmall)
            }
            is ConversionOutcome.Invalid -> {
                Text("Check your time", color = Color.White, fontWeight = FontWeight.Bold, modifier = Modifier.testTag("invalidTime"))
                Text("Try 58.32 or 1:02.45, up to 60 minutes.", color = Color.White, style = MaterialTheme.typography.bodySmall)
            }
            is ConversionOutcome.Unavailable -> {
                Text("No published conversion", color = Color.White, fontWeight = FontWeight.Bold, modifier = Modifier.testTag("unavailableConversion"))
                Text("Choose another event or course comparison.", color = Color.White, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable private fun CourseControl(label: String, tag: String, selected: Int, onSelect: (Int) -> Unit) {
    Text(label, fontWeight = FontWeight.Bold)
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        courses.forEachIndexed { index, course ->
            FilterChip(selected == index, { onSelect(index) }, { Text(course.name) }, modifier = Modifier.testTag("$tag-${course.name}"))
        }
    }
}

@Composable private fun Choice(label: String, selected: String, values: List<String>, modifier: Modifier, onSelect: (Int) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier) {
        OutlinedButton(onClick = { expanded = true }) { Text("$label: $selected") }
        DropdownMenu(expanded, { expanded = false }) {
            values.forEachIndexed { index, value -> DropdownMenuItem(text = { Text(value) }, onClick = { expanded = false; onSelect(index) }) }
        }
    }
}

@Composable private fun ResultCard(draft: Draft) {
    Column(Modifier.fillMaxWidth().background(Ink, RoundedCornerShape(24.dp)).padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("${courses[draft.courseIndex]} → ${courses[draft.targetIndex]}", color = Lime, fontWeight = FontWeight.SemiBold)
        when (val result = draft.outcome) {
            is ConversionOutcome.Available -> {
                Text(result.value.time, fontSize = 48.sp, fontWeight = FontWeight.Bold, color = Color.White, modifier = Modifier.testTag("resultTime"))
                Text("${result.value.event.distance} ${strokeNames[draft.strokeIndex]} · ${courses[draft.targetIndex]}", color = Color.White)
                Text(when (result.value.kind) { ConversionKind.SWUM -> "Entered swim"; ConversionKind.PUBLISHED -> "Published factor"; ConversionKind.DERIVED -> "Derived estimate" }, color = Lime, fontWeight = FontWeight.Bold)
                HorizontalDivider(color = Color.White.copy(alpha = 0.2f))
                Text("${result.provenance.title} · ${result.provenance.id}", color = Color.White.copy(alpha = 0.8f), style = MaterialTheme.typography.bodySmall)
            }
            is ConversionOutcome.Invalid -> {
                Text("Check your time", color = Color.White, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.testTag("invalidTime"))
                Text("Enter a positive time such as 58.32 or 1:02.45, up to 60 minutes.", color = Color.White)
            }
            is ConversionOutcome.Unavailable -> {
                Text("No published conversion", color = Color.White, style = MaterialTheme.typography.headlineSmall, modifier = Modifier.testTag("unavailableConversion"))
                Text("This event or course has no published NCAA factor. Choose another comparison.", color = Color.White)
            }
        }
    }
}
