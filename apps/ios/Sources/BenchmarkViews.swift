import SwiftUI
import TurnmarkCore

/// One original-swim view, shared by Convert and recorded performances.
struct BenchmarkScreen: View {
    let input: Draft
    var isRecorded = false
    @Environment(\.dismiss) private var dismiss
    @AppStorage("benchmarkMode") private var mode = "standards"
    @AppStorage("benchmarkSystem") private var systemName = "youth"
    @AppStorage("benchmarkYouthAge") private var youthAge = "15-16"
    @AppStorage("benchmarkMastersAge") private var mastersAge = "18-24"
    @AppStorage("benchmarkConfigured") private var configured = false
    @State private var settingsExpanded = false
    @State private var sourceExpanded = false
    private let programs = getNationalStandardPrograms()
    private var program: StandardProgram? { programs.first { $0.system == system } }
    @AppStorage("benchmarkFuturesAge") private var futuresAge = "18 & under"
    private var system: StandardSystem {
        switch systemName { case "masters": .masters; case "futures": .futures; case "juniors": .juniors; case "nisca": .nisca; default: .youth }
    }
    private var age: String { system == .masters ? mastersAge : system == .futures ? futuresAge : system == .youth ? youthAge : "" }
    private var swim: Swim { Swim(time: input.time, event: SwimEvent(distance: input.distance, stroke: strokes[input.strokeIndex], course: courses[input.courseIndex])) }
    private var table: TurnmarkCore.Category { input.categoryIndex == 0 ? .women : .men }
    private var assessment: BenchmarkOutcome { assessSwimBenchmark(request: BenchmarkRequest(swim: swim, table: table, age: age, system: system)) }
    private var provider: String { program.map { "\($0.title) · \($0.scope)" } ?? (system == .masters ? "USMS · 2026" : "USA Swimming · 2024–28") }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(input.time).font(.title2.bold()).monospacedDigit().lineLimit(1).minimumScaleFactor(0.6).accessibilityIdentifier("benchmarkOriginalTime")
                        Text(input.label).font(.subheadline).accessibilityIdentifier("benchmarkContext")
                    }.padding(.vertical, 4)
                } header: { Text(isRecorded ? "Recorded swim" : "Entered swim").accessibilityIdentifier("benchmarkOriginLabel") }
                  footer: { Text("Original swim only; no course or altitude estimates.") }
                    .listRowBackground(TurnmarkPalette.surface)
                Section {
                    Picker("Comparison", selection: $mode) { Text("Standards").tag("standards"); Text("Points").tag("points") }
                        .pickerStyle(.segmented).accessibilityIdentifier("benchmarkMode")
                }.listRowBackground(Color.clear).listRowInsets(EdgeInsets())
                if mode == "points" { pointsContent }
                else {
                    benchmarkContent
                    Section {
                        DisclosureGroup(isExpanded: $settingsExpanded) {
                            Picker("Standard system", selection: $systemName) {
                                Text("USA Swimming · Youth").tag("youth"); Text("USMS · Masters").tag("masters")
                                ForEach(programs, id: \.system) { Text($0.label).tag(String(describing: $0.system)) }
                            }.pickerStyle(.menu).accessibilityIdentifier("benchmarkSystem")
                            if !getStandardAgeGroups(system: system).isEmpty { Picker("Age group", selection: Binding(get: { age }, set: {
                                if system == .masters { mastersAge = $0 } else if system == .futures { futuresAge = $0 } else { youthAge = $0 }
                            })) {
                                ForEach(getStandardAgeGroups(system: system), id: \.self) { Text(ageLabel($0)).tag($0) }
                            }.pickerStyle(.menu).accessibilityIdentifier("benchmarkAge") }
                            Text("Category follows the original swim. Change it in the converter or edit the recorded swim.")
                                .font(.footnote).foregroundStyle(TurnmarkPalette.textMuted)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Comparison settings").accessibilityIdentifier("benchmarkSettings")
                                Text([provider, ageLabel(age), input.category].filter { !$0.isEmpty }.joined(separator: " · ")).font(.footnote).foregroundStyle(TurnmarkPalette.textMuted)
                            }
                        }
                    }.listRowBackground(TurnmarkPalette.surface)
                }
            }.formStyle(.grouped).accessibilityIdentifier("benchmarkForm").scrollContentBackground(.hidden).background(TurnmarkPalette.canvas)
                .foregroundStyle(TurnmarkPalette.text).tint(TurnmarkPalette.accent)
                .navigationTitle("Standards & points").navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() }.accessibilityIdentifier("closeBenchmarks") } }
        }.onAppear {
            if !["standards", "points"].contains(mode) { mode = "standards" }
            if !["youth", "masters", "futures", "juniors", "nisca"].contains(systemName) { systemName = "youth" }
            if !getStandardAgeGroups(system: .youth).contains(youthAge) { youthAge = "15-16" }
            if !getStandardAgeGroups(system: .masters).contains(mastersAge) { mastersAge = "18-24" }
            if !getStandardAgeGroups(system: .futures).contains(futuresAge) { futuresAge = "18 & under" }
            settingsExpanded = !configured
        }.onChange(of: mode) { _, _ in configured = true }
            .onChange(of: systemName) { _, _ in configured = true }
            .onChange(of: youthAge) { _, _ in configured = true }
            .onChange(of: mastersAge) { _, _ in configured = true }
    }

    @ViewBuilder private var benchmarkContent: some View {
        switch assessment {
        case let .available(value, provenance):
            Section {
                VStack(alignment: .leading, spacing: 12) {
                    Text(provider).font(.caption.weight(.semibold)).foregroundStyle(TurnmarkResultPalette.textMuted)
                    Text(system == .youth ? value.achievedLevel.map { "\($0) standard" } ?? "Next target: B" : system == .masters ? (value.achievedLevel == nil ? "NQT benchmark" : "NQT target met") : value.achievedLevel.map { "\($0) threshold met" } ?? "Next published target")
                        .font(.title2.bold()).accessibilityIdentifier("benchmarkSummary")
                    Text([ageLabel(value.age), input.category, courseNames[input.courseIndex]].filter { !$0.isEmpty }.joined(separator: " · ")).font(.subheadline)
                    if let next = value.nextTarget {
                        Text(next.time).font(.largeTitle.bold()).monospacedDigit().foregroundStyle(TurnmarkResultPalette.resultHighlight).accessibilityIdentifier("benchmarkNextTime")
                        Text("\(next.gapSeconds, specifier: "%.2f")s to \(next.label)").font(.subheadline)
                    } else { Text(system == .youth ? "You meet the top published standard for this selection." : "Your entered time meets this published benchmark.").font(.subheadline) }
                }.frame(maxWidth: .infinity, alignment: .leading).padding(20)
                    .foregroundStyle(TurnmarkResultPalette.text).background(NativeResultSurface())
            }.listRowInsets(EdgeInsets()).listRowBackground(Color.clear)
            if program == nil || value.targets.count > 1 || value.nextTarget == nil { Section(system == .masters ? "National qualifying benchmark" : "Published time thresholds") {
                ForEach(value.targets, id: \.label) { target in
                    HStack {
                        Text(target.label).fontWeight(.semibold)
                        if target.met { Image(systemName: "checkmark").foregroundStyle(TurnmarkPalette.accent).accessibilityLabel("Met") }
                        Spacer()
                        Text(target.time).font(.headline).monospacedDigit()
                    }.accessibilityElement(children: .combine).accessibilityIdentifier("benchmark-level-\(target.label)")
                }
            }.listRowBackground(TurnmarkPalette.surface) }
            source(provenance, note: program?.note ?? "Benchmarks do not confirm meet-entry eligibility. Meet rules, age dates, qualifying windows and exceptions still apply.")
        case let .unavailable(reason, provenance):
            unavailable(reason, points: false)
            source(provenance, note: "No fallback target is substituted. Check the published meet guidance and entry rules.")
        case .invalid:
            Section { Label("Check the original swim", systemImage: "exclamationmark.circle"); Text("Use a valid time, event and age group.").font(.subheadline) }.listRowBackground(TurnmarkPalette.surface)
        }
    }
    @ViewBuilder private var pointsContent: some View {
        switch getWorldPoints(request: PointsRequest(swim: swim, table: table)) {
        case let .available(value, provenance):
            Section {
                VStack(alignment: .leading, spacing: 12) {
                    Text("World Aquatics · 2026").font(.caption.weight(.semibold)).foregroundStyle(TurnmarkResultPalette.textMuted)
                    Text(value.points.formatted()).font(.largeTitle.bold()).monospacedDigit().lineLimit(1).minimumScaleFactor(0.5).accessibilityIdentifier("benchmarkPoints")
                    Text("Points for your original \(courseNames[input.courseIndex]) swim").font(.subheadline).foregroundStyle(TurnmarkResultPalette.textMuted)
                    Divider().overlay(TurnmarkResultPalette.borderSubtle)
                    LabeledContent("1,000-point reference", value: value.baseTime).font(.subheadline).monospacedDigit()
                    LabeledContent("Next \(value.nextMilestone.points) points", value: value.nextMilestone.time).font(.subheadline).monospacedDigit()
                    Text("\(value.nextMilestone.gapSeconds, specifier: "%.2f")s to the next 100-point step. This is a suggested goal, not a qualifying time.")
                        .font(.footnote).foregroundStyle(TurnmarkResultPalette.textMuted)
                }.frame(maxWidth: .infinity, alignment: .leading).padding(20)
                    .foregroundStyle(TurnmarkResultPalette.text).background(NativeResultSurface())
            }.listRowInsets(EdgeInsets()).listRowBackground(Color.clear)
            source(provenance, note: "\(value.validity). Scores use the fixed published world-record reference, are not age-adjusted, and may lag newer records.")
        case let .unavailable(reason, provenance):
            unavailable(reason, points: true)
            source(provenance, note: "Converted estimates are not scored as actual swims.")
        case .invalid:
            Section { Label("Check the original swim", systemImage: "exclamationmark.circle") }.listRowBackground(TurnmarkPalette.surface)
        }
    }
    private func unavailable(_ reason: CoverageReason, points: Bool) -> some View {
        Section {
            Label(points && reason == .courseNotSupported ? "SCY isn’t scored" : "No published \(points ? "points" : "target")", systemImage: "info.circle").font(.headline).accessibilityIdentifier("benchmarkUnavailable")
            Text(coverageMessage(reason, points: points)).font(.subheadline)
        }.listRowBackground(TurnmarkPalette.surface)
    }
    private func coverageMessage(_ reason: CoverageReason, points: Bool) -> String {
        switch reason {
        case .courseNotSupported: return points ? "World Aquatics points need an original SCM or LCM swim. SCY swims aren’t scored." : program?.note ?? "USMS publishes 2026 NQTs for SCY and LCM, not SCM."
        case .ageGroupNotPublished: return "No NQT is published for this age group in the bundled 2026 table. Meet-specific rules and exceptions apply."
        case .noTimePublished: return "This event has no NQT in the published table for this age group. Check the meet’s entry guidance."
        default: return "This event has no published \(points ? "base time" : "target") in the selected table. Missing source data stays unavailable."
        }
    }
    private func source(_ provenance: Provenance, note: String) -> some View {
        Section {
            DisclosureGroup(isExpanded: $sourceExpanded) {
                Text(provenance.title).font(.subheadline)
                Text("Edition: \(provenance.id)").font(.footnote)
                Text("Revision: \(provenance.revision)").font(.footnote)
                if let url = URL(string: provenance.url) { Link("Published source", destination: url) }
                Text("Source links need an internet connection. Lookups and comparisons work offline.").font(.footnote)
            } label: { Text("Source and coverage") }
        } footer: { Text(note) }.listRowBackground(TurnmarkPalette.surface)
    }
    private func ageLabel(_ age: String) -> String { age == "10u" ? "10 & under" : age.replacingOccurrences(of: "-", with: "–") }
}
