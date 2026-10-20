package net.stanback.turnmark

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import uniffi.turnmark_core.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun BenchmarkSheet(draft: Draft, isRecorded: Boolean = false, close: () -> Unit) {
    val context = LocalContext.current
    val preferences = remember { context.getSharedPreferences("turnmark", Context.MODE_PRIVATE) }
    var mode by rememberSaveable { mutableStateOf(preferences.getString("benchmarkMode", "standards").takeIf { it in listOf("standards", "points") } ?: "standards") }
    val programs = remember { getNationalStandardPrograms() }
    val systemIds = listOf("youth", "masters", "futures", "juniors", "nisca")
    val systemLabels = listOf("USA Swimming · Youth", "USMS · Masters") + programs.map { it.label }
    var futuresAge by rememberSaveable { mutableStateOf(preferences.getString("benchmarkFuturesAge", "18 & under").takeIf { it in getStandardAgeGroups(StandardSystem.FUTURES) } ?: "18 & under") }
    var systemName by rememberSaveable { mutableStateOf(preferences.getString("benchmarkSystem", "youth").takeIf { it in systemIds } ?: "youth") }
    var youthAge by rememberSaveable { mutableStateOf(preferences.getString("benchmarkYouthAge", "15-16").takeIf { it in getStandardAgeGroups(StandardSystem.YOUTH) } ?: "15-16") }
    var mastersAge by rememberSaveable { mutableStateOf(preferences.getString("benchmarkMastersAge", "18-24").takeIf { it in getStandardAgeGroups(StandardSystem.MASTERS) } ?: "18-24") }
    var settingsExpanded by rememberSaveable { mutableStateOf(!preferences.getBoolean("benchmarkConfigured", false)) }
    val system = when (systemName) { "masters" -> StandardSystem.MASTERS; "futures" -> StandardSystem.FUTURES; "juniors" -> StandardSystem.JUNIORS; "nisca" -> StandardSystem.NISCA; else -> StandardSystem.YOUTH }
    val program = programs.firstOrNull { it.system == system }
    val age = when(system) { StandardSystem.MASTERS -> mastersAge; StandardSystem.FUTURES -> futuresAge; StandardSystem.YOUTH -> youthAge; else -> "" }
    val provider = program?.let { "${it.title} · ${it.scope}" } ?: if (system == StandardSystem.MASTERS) "USMS · 2026" else "USA Swimming · 2024–28"
    val swim = Swim(draft.time, SwimEvent(draft.distance, strokes[draft.strokeIndex], courses[draft.courseIndex]))
    val table = if (draft.categoryIndex == 0) Category.WOMEN else Category.MEN
    val c = LocalTurnmarkColors.current
    fun save(key: String, value: String) { preferences.edit().putString(key, value).putBoolean("benchmarkConfigured", true).apply() }
    ModalBottomSheet(onDismissRequest = close, containerColor = c.canvas, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 24.dp).padding(bottom = 24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Text("Standards & points", style = MaterialTheme.typography.headlineSmall, modifier = Modifier.weight(1f))
                TextButton(onClick = close, modifier = Modifier.testTag("closeBenchmarks")) { Text("Done") }
            }
            BenchmarkGroup {
                Text(if (isRecorded) "Recorded swim" else "Entered swim", style = MaterialTheme.typography.labelLarge, modifier = Modifier.testTag("benchmarkOriginLabel"))
                BenchmarkClock(draft.time, Modifier.testTag("benchmarkOriginalTime"))
                Text(draft.label, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.testTag("benchmarkContext"))
                Text("Original swim only; no course or altitude estimates.", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
            }
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                listOf("standards" to "Standards", "points" to "Points").forEachIndexed { index, (value, label) ->
                    SegmentedButton(selected = mode == value, onClick = { mode = value; save("benchmarkMode", value) },
                    shape = SegmentedButtonDefaults.itemShape(index, 2), modifier = Modifier.testTag("benchmarkMode-$value")) { Text(label) }
                }
            }
            if (mode == "points") {
                when (val result = getWorldPoints(PointsRequest(swim, table))) {
                    is PointsOutcome.Available -> {
                        val value = result.value
                        NativeResultSurface(compact = true) {
                            Text("World Aquatics · 2026", style = MaterialTheme.typography.labelLarge, color = TurnmarkTokens.dark.textMuted)
                            Text("${value.points} points", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold, color = TurnmarkTokens.dark.text, modifier = Modifier.testTag("benchmarkPoints"))
                            Text("Points for your original ${courses[draft.courseIndex]} swim")
                            TargetLine("1,000-point reference", value.baseTime)
                            TargetLine("Next ${value.nextMilestone.points} points", value.nextMilestone.time)
                            Text("${"%.2f".format(java.util.Locale.ROOT, value.nextMilestone.gapSeconds)}s to the next 100-point step. This is a suggested goal, not a qualifying time.", style = MaterialTheme.typography.bodySmall, color = TurnmarkTokens.dark.textMuted)
                        }
                        BenchmarkSource(result.provenance, "${value.validity}. Scores use the fixed published world-record reference, are not age-adjusted, and may lag newer records.")
                    }
                    is PointsOutcome.Unavailable -> { BenchmarkUnavailable(result.reason, true); BenchmarkSource(result.provenance, "Converted estimates are not scored as actual swims.") }
                    is PointsOutcome.Invalid -> Text("Check the original swim", modifier = Modifier.testTag("benchmarkInvalid"))
                }
            } else {
                when (val result = assessSwimBenchmark(BenchmarkRequest(swim, table, age, system))) {
                    is BenchmarkOutcome.Available -> {
                        val value = result.value
                        NativeResultSurface(compact = true) {
                            Text(provider, style = MaterialTheme.typography.labelLarge, color = TurnmarkTokens.dark.textMuted)
                            Text(if (system == StandardSystem.YOUTH) value.achievedLevel?.let { "$it standard" } ?: "Next target: B"
                                else if (system == StandardSystem.MASTERS) { if (value.achievedLevel != null) "NQT target met" else "NQT benchmark" } else value.achievedLevel?.let { "$it threshold met" } ?: "Next published target",
                                style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = TurnmarkTokens.dark.text, modifier = Modifier.testTag("benchmarkSummary"))
                            Text(listOf(benchmarkAgeLabel(age), draft.category, courses[draft.courseIndex].name).filter { it.isNotEmpty() }.joinToString(" · "), style = MaterialTheme.typography.bodyMedium)
                            value.nextTarget?.let { next ->
                                BenchmarkClock(next.time, Modifier.testTag("benchmarkNextTime"), highlight = true)
                                Text("${"%.2f".format(java.util.Locale.ROOT, next.gapSeconds)}s to ${next.label}")
                            } ?: Text(if (system == StandardSystem.YOUTH) "You meet the top published standard for this selection." else "Your entered time meets this published benchmark.")
                        }
                        if (program == null || value.targets.size > 1 || value.nextTarget == null) BenchmarkGroup {
                            Text(if (system == StandardSystem.MASTERS) "National qualifying benchmark" else "Published time thresholds", style = MaterialTheme.typography.titleMedium)
                            value.targets.forEachIndexed { index, target ->
                                Row(Modifier.fillMaxWidth().testTag("benchmark-level-${target.label}"), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                    Column(Modifier.weight(1f)) {
                                        Text(target.label, fontWeight = FontWeight.SemiBold)
                                        Text(if (target.met) "Met" else "Not met", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
                                    }
                                    Text(target.time, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                                }
                                if (index < value.targets.lastIndex) HorizontalDivider(color = c.borderSubtle)
                            }
                        }
                        BenchmarkSource(result.provenance, program?.note ?: "Benchmarks do not confirm meet-entry eligibility. Meet rules, age dates, qualifying windows and exceptions still apply.")
                    }
                    is BenchmarkOutcome.Unavailable -> { BenchmarkUnavailable(result.reason, false, program?.note); BenchmarkSource(result.provenance, program?.note ?: "No fallback target is substituted. Check the published meet guidance and entry rules.") }
                    is BenchmarkOutcome.Invalid -> Text("Check the original swim and age group", modifier = Modifier.testTag("benchmarkInvalid"))
                }
                BenchmarkGroup {
                    TextButton(onClick = { settingsExpanded = !settingsExpanded }, modifier = Modifier.fillMaxWidth().testTag("benchmarkSettings")) {
                        Column(Modifier.weight(1f)) { Text("Comparison settings"); Text(listOf(provider, benchmarkAgeLabel(age), draft.category).filter { it.isNotEmpty() }.joinToString(" · "), style = MaterialTheme.typography.bodySmall) }
                        Text(if (settingsExpanded) "Hide" else "Change")
                    }
                    if (settingsExpanded) {
                        Choice("Standard system", systemLabels[systemIds.indexOf(systemName)], systemLabels, Modifier.fillMaxWidth().testTag("benchmarkSystem")) {
                            systemName = systemIds[it]; save("benchmarkSystem", systemName)
                        }
                        val ages = getStandardAgeGroups(system)
                        if (ages.isNotEmpty()) Choice("Age group", benchmarkAgeLabel(age), ages.map(::benchmarkAgeLabel), Modifier.fillMaxWidth().testTag("benchmarkAge")) {
                            if (system == StandardSystem.MASTERS) { mastersAge = ages[it]; save("benchmarkMastersAge", mastersAge) }
                            else if (system == StandardSystem.FUTURES) { futuresAge = ages[it]; save("benchmarkFuturesAge", futuresAge) }
                            else { youthAge = ages[it]; save("benchmarkYouthAge", youthAge) }
                        }
                        Text("Category follows the original swim. Change it in the converter or edit the recorded swim.", style = MaterialTheme.typography.bodySmall, color = c.textMuted)
                    }
                }
            }
        }
    }
}

private fun benchmarkAgeLabel(age: String) = if (age == "10u") "10 & under" else age.replace("-", "–")

@Composable private fun BenchmarkClock(time: String, modifier: Modifier = Modifier, highlight: Boolean = false) {
    val scale = LocalDensity.current.fontScale
    BoxWithConstraints(Modifier.fillMaxWidth()) {
        Text(time, fontSize = minOf(32f, maxWidth.value / (time.length * .64f * scale)).sp, fontWeight = FontWeight.Bold,
            color = if (highlight) LocalTurnmarkColors.current.resultHighlight else LocalContentColor.current,
            style = MaterialTheme.typography.headlineLarge.copy(fontFeatureSettings = "tnum"), maxLines = 1, modifier = modifier)
    }
}

@Composable private fun TargetLine(label: String, time: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(label, Modifier.weight(1f)); Text(time, fontWeight = FontWeight.SemiBold)
    }
}

@Composable private fun BenchmarkUnavailable(reason: CoverageReason, points: Boolean, programNote: String? = null) {
    val message = when (reason) {
        CoverageReason.COURSE_NOT_SUPPORTED -> if (points) "World Aquatics points need an original SCM or LCM swim. SCY swims aren’t scored." else programNote ?: "USMS publishes 2026 NQTs for SCY and LCM, not SCM."
        CoverageReason.AGE_GROUP_NOT_PUBLISHED -> "No NQT is published for this age group in the bundled 2026 table. Meet-specific rules and exceptions apply."
        CoverageReason.NO_TIME_PUBLISHED -> "This event has no NQT in the published table for this age group. Check the meet’s entry guidance."
        else -> "This event has no published ${if (points) "base time" else "target"} in the selected table. Missing source data stays unavailable."
    }
    BenchmarkGroup {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(Icons.Default.Info, null)
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(if (points && reason == CoverageReason.COURSE_NOT_SUPPORTED) "SCY isn’t scored" else "No published ${if (points) "points" else "target"}", fontWeight = FontWeight.Bold, modifier = Modifier.testTag("benchmarkUnavailable"))
                Text(message, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable private fun BenchmarkSource(provenance: Provenance, note: String) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    val context = LocalContext.current
    BenchmarkGroup {
        Text(note, style = MaterialTheme.typography.bodySmall, color = LocalTurnmarkColors.current.textMuted)
        TextButton(onClick = { expanded = !expanded }) { Text("Source and coverage") }
        if (expanded) {
            Text(provenance.title)
            Text("Edition: ${provenance.id}", style = MaterialTheme.typography.bodySmall)
            Text("Revision: ${provenance.revision}", style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(provenance.url))) }) { Text("Published source") }
            Text("Source links need an internet connection. Lookups and comparisons work offline.", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable private fun BenchmarkGroup(content: @Composable ColumnScope.() -> Unit) {
    Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(TurnmarkTokens.radiusCard),
    colors = CardDefaults.cardColors(containerColor = LocalTurnmarkColors.current.surface)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
    }
}
