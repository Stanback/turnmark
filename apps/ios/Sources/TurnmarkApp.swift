import SwiftUI
import UIKit
import TurnmarkCore

let courseNames = ["SCY", "SCM", "LCM"]
let courses: [Course] = [.scy, .scm, .lcm]
let strokeNames = ["Freestyle", "Backstroke", "Breaststroke", "Butterfly", "Individual medley"]
let strokeCodes = ["FR", "BK", "BR", "FL", "IM"]
let strokes: [Stroke] = [.freestyle, .backstroke, .breaststroke, .butterfly, .individualMedley]

struct Draft: Codable, Equatable {
    var time = "58.32"
    var strokeIndex = 0
    var distance: UInt32 = 100
    var courseIndex = 0
    var categoryIndex = 0
    var targetIndex = 2

    static func decode(_ text: String?) -> Draft? {
        guard let text, let data = text.data(using: .utf8),
              let value = try? JSONDecoder().decode(Draft.self, from: data),
              strokes.indices.contains(value.strokeIndex),
              courses.indices.contains(value.courseIndex),
              courses.indices.contains(value.targetIndex),
              (0...1).contains(value.categoryIndex),
              value.options.contains(where: { $0.event.distance == value.distance }) else { return nil }
        return value
    }
    var encoded: String { String(data: try! JSONEncoder().encode(self), encoding: .utf8)! }
    var options: [EventOption] { getEventOptions(course: courses[courseIndex], stroke: strokes[strokeIndex]) }
    var outcome: ConversionOutcome {
        convertSwim(request: ConversionRequest(
            swim: Swim(time: time, event: SwimEvent(distance: distance, stroke: strokes[strokeIndex], course: courses[courseIndex])),
            to: courses[targetIndex], table: categoryIndex == 0 ? .women : .men))
    }
    var available: Bool { if case .available = outcome { return true }; return false }
    mutating func reconcile() {
        if !options.contains(where: { $0.event.distance == distance }) { distance = options.first?.event.distance ?? 100 }
    }
    var category: String { categoryIndex == 0 ? "Women" : "Men" }
    var unit: String { courseIndex == 0 ? "yd" : "m" }
    var label: String { "\(distance) \(unit) \(strokeNames[strokeIndex]) · \(courseNames[courseIndex]) · \(category)" }
    func resultLabel(_ event: SwimEvent) -> String {
        let stroke = strokeNames[strokes.firstIndex(of: event.stroke)!]
        let course = courseNames[courses.firstIndex(of: event.course)!]
        return "\(event.distance) \(event.course == .scy ? "yd" : "m") \(stroke) · \(course) · \(category)"
    }
    var shareURL: URL {
        var query = URLComponents()
        query.queryItems = [
            URLQueryItem(name: "t", value: time), URLQueryItem(name: "s", value: strokeCodes[strokeIndex]),
            URLQueryItem(name: "d", value: String(options.first(where: { $0.event.distance == distance })?.canonicalDistance ?? distance)),
            URLQueryItem(name: "c", value: courseNames[courseIndex]),
            URLQueryItem(name: "g", value: categoryIndex == 0 ? "women" : "men"),
            URLQueryItem(name: "h", value: "0")]
        var url = URLComponents(string: "https://turnmark.app/")!
        url.percentEncodedFragment = query.percentEncodedQuery
        return url.url!
    }
}

@main
struct TurnmarkApp: App {
    var body: some Scene { WindowGroup { TurnmarkView() } }
}

private struct TurnmarkView: View {
    @Environment(\.dynamicTypeSize) private var typeSize
    @State private var draft: Draft
    @State private var tab = 0
    @State private var history = HistoryController()
    @State private var logging: Draft?
    @State private var benchmarking: Draft?
    @State private var lastMeet = ""
    @State private var logNotice: String?
    @State private var lastLogDay = SwimRecord.day(Date())
    @State private var lastDate = SwimRecord.day(Date())
    @State private var showingMethod = false
    @AppStorage("savedSwim") private var savedJSON = ""
    @FocusState private var editingTime: Bool
    @State private var focusDismissal = 0
    @ScaledMetric(relativeTo: .largeTitle) private var entrySize = 42

    init() {
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-uitesting-reset") {
            UserDefaults.standard.removeObject(forKey: "draft")
            UserDefaults.standard.removeObject(forKey: "savedSwim")
            for key in ["benchmarkMode", "benchmarkSystem", "benchmarkYouthAge", "benchmarkMastersAge", "benchmarkConfigured"] { UserDefaults.standard.removeObject(forKey: key) }
            if let store = try? SwimHistoryStore() { for swim in store.swims { try? store.remove(swim.id) } }
        }
        if ProcessInfo.processInfo.arguments.contains("-uitesting-legacy") {
            UserDefaults.standard.set(Draft().encoded, forKey: "savedSwim")
        }
        #endif
        _draft = State(initialValue: Draft.decode(UserDefaults.standard.string(forKey: "draft")) ?? Draft())
    }

    var body: some View {
        TabView(selection: $tab) {
            NavigationStack {
                GeometryReader { geometry in
                    let restoreFocus = editingTime
                    let focusRevision = focusDismissal
                    Group {
                        if #available(iOS 27.1, *) {
                            let regions = geometry.reservedRegions(kind: .division)
                            let tabletop = regions.contains { $0.frame.width > $0.frame.height }
                            let expanded = geometry.size.width >= 620 || !regions.isEmpty
                            if regions.isEmpty && expanded && !typeSize.isAccessibilitySize {
                                HStack(alignment: .top, spacing: 0) { inputPane; resultPane }
                                    .accessibilityIdentifier("expandedConverter")
                            } else if !regions.isEmpty {
                                ArrangementView {
                                    if tabletop { comparisonPane(compact: true) } else { inputPane }
                                } secondary: {
                                    if tabletop { inputPane } else { resultPane }
                                }.arrangementViewStyle(.split)
                                    .accessibilityIdentifier("expandedConverter")
                            } else { compactConverter }
                        } else if geometry.size.width >= 700 && !typeSize.isAccessibilitySize {
                            HStack(alignment: .top, spacing: 0) { inputPane; resultPane }
                                .accessibilityIdentifier("expandedConverter")
                        } else { compactConverter }
                    }.task(id: converterLayoutKey(geometry)) {
                        // Reattaching the field to another pane ends its old focus
                        // location. Restore only an entry that was already active.
                        if restoreFocus {
                            await Task.yield()
                            if !Task.isCancelled && focusRevision == focusDismissal { editingTime = true }
                        }
                    }
                }
                .background(TurnmarkPalette.canvas)
                .toolbar(.hidden, for: .navigationBar)
                .toolbar {
                    if editingTime {
                        ToolbarItemGroup(placement: .keyboard) { Spacer(); Button("Done", action: dismissTimeEntry).accessibilityIdentifier("dismissConverterKeyboard") }
                    }
                }
            }.tabItem { Label("Convert", systemImage: "arrow.left.arrow.right") }.tag(0)
            HistoryScreen(controller: history, legacy: Draft.decode(savedJSON), recordNew: {
                var input = draft; input.time = ""; logging = input
            },
                restoreLegacy: { value in draft = value; tab = 0 }, removeLegacy: { savedJSON = "" }) {
                    draft = Draft(record: $0, target: draft.targetIndex); tab = 0
                }
                .tabItem { Label("My times", systemImage: "list.bullet.rectangle") }.tag(1)
        }
        .tint(TurnmarkPalette.accent)
        .task { if history.store == nil { history.open() } }
        .sheet(isPresented: $showingMethod) { MethodScreen() }
        .sheet(isPresented: Binding(get: { benchmarking != nil }, set: { if !$0 { benchmarking = nil } })) {
            if let benchmarking { BenchmarkScreen(input: benchmarking) }
        }
        .sheet(isPresented: Binding(get: { logging != nil }, set: { if !$0 { logging = nil } })) {
            if let logging {
                SwimEditor(draft: logging, date: lastLogDay == SwimRecord.day(Date()) ? lastDate : SwimRecord.day(Date()),
                    meet: lastLogDay == SwimRecord.day(Date()) ? lastMeet : "") { record in
                    guard let store = history.store else { throw HistoryError.message("History is unavailable.") }
                    try store.save(record)
                    logNotice = "Recorded \(record.time) · \(record.date ?? "Unknown date") · \(record.meet ?? "No meet")"
                    lastDate = record.date ?? ""; lastMeet = record.meet ?? ""; lastLogDay = SwimRecord.day(Date())
                    UIAccessibility.post(notification: .announcement, argument: "Time recorded in My times on this device")
                }
            }
        }
        .onChange(of: draft) { _, value in UserDefaults.standard.set(value.encoded, forKey: "draft") }
        .onChange(of: draft.courseIndex) { _, _ in draft.reconcile() }
        .onChange(of: draft.strokeIndex) { _, _ in draft.reconcile() }
    }

    private func dismissTimeEntry() {
        // Explicit dismissal supersedes any pane-change restoration still
        // waiting on the main actor, including on a busy simulator/device.
        focusDismissal &+= 1
        editingTime = false
        UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
    }

    private func converterLayoutKey(_ geometry: GeometryProxy) -> String {
        // Restore focus only when our view hierarchy moves the input field.
        // Keyboard safe-area changes also resize GeometryReader; keying on raw
        // height can restart an older focus task after the user presses Done.
        // Width, native fold regions and text size determine the pane layout;
        // keyboard height must not collapse a wide input workspace.
        if #available(iOS 27.1, *) {
            let regions = geometry.reservedRegions(kind: .division)
            if !regions.isEmpty {
                return regions.contains { $0.frame.width > $0.frame.height } ? "division-tabletop" : "division-book"
            }
            return geometry.size.width >= 620 && !typeSize.isAccessibilitySize ? "expanded" : "compact"
        }
        return geometry.size.width >= 700 && !typeSize.isAccessibilitySize ? "expanded" : "compact"
    }

    private var compactConverter: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                ConversionResult(input: draft, compact: true, benchmarks: { dismissTimeEntry(); benchmarking = $0 }) { draft.targetIndex = $0 }
                inputContent
            }.padding(16).frame(maxWidth: 600).frame(maxWidth: .infinity)
        }.scrollDismissesKeyboard(.interactively)
    }
    private var inputPane: some View {
        ScrollView { inputContent.padding(20).frame(maxWidth: 600).frame(maxWidth: .infinity) }
            .scrollDismissesKeyboard(.interactively)
    }
    private var resultPane: some View {
        comparisonPane()
    }
    private func comparisonPane(compact: Bool = false) -> some View {
        ScrollView {
            ConversionResult(input: draft, compact: compact, benchmarks: { dismissTimeEntry(); benchmarking = $0 }) { draft.targetIndex = $0 }
                .padding(20).frame(maxWidth: 620).frame(maxWidth: .infinity)
        }
    }
    private var inputContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            inputCard
            if let logNotice { Text(logNotice).font(.footnote).foregroundStyle(TurnmarkPalette.textMuted).accessibilityIdentifier("logNotice") }
            if history.error != nil { Text("History is unavailable. Open History to try again.").font(.footnote) }
            HStack {
                Text("On this device. Works offline.").font(.footnote).foregroundStyle(TurnmarkPalette.textMuted)
                Spacer()
                Button { showingMethod = true } label: { Label("About", systemImage: "info.circle") }
                    .font(.footnote).accessibilityIdentifier("methodology")
            }
        }.foregroundStyle(TurnmarkPalette.text)
    }
    private var inputCard: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text("Your swim").font(.headline)
            VStack(alignment: .leading, spacing: 8) {
                Text("Your time").font(.subheadline.weight(.semibold))
                TextField("58.32", text: $draft.time)
                    .font(.system(size: entrySize, weight: .semibold)).monospacedDigit()
                    .keyboardType(.numbersAndPunctuation).focused($editingTime)
                    .submitLabel(.done).onSubmit(dismissTimeEntry)
                    .padding(12).background(TurnmarkPalette.surfaceInput, in: RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).strokeBorder(TurnmarkPalette.borderControl))
                    .accessibilityLabel("Your time").accessibilityIdentifier("timeInput")
                Text("For example, 58.32 or 1:02.45").font(.footnote).foregroundStyle(TurnmarkPalette.textMuted)
            }
            if typeSize.isAccessibilitySize { strokePicker; distancePicker }
            else { HStack { strokePicker; Spacer(); distancePicker } }
            coursePicker("Swum in", selection: $draft.courseIndex, id: "inputCourse")
            VStack(alignment: .leading, spacing: 8) {
                Text("Published category").font(.subheadline.weight(.semibold))
                Picker("Published category", selection: $draft.categoryIndex) {
                    Text("Women").tag(0); Text("Men").tag(1)
                }.pickerStyle(.segmented).accessibilityIdentifier("category")
            }
            coursePicker("Compare with", selection: $draft.targetIndex, id: "targetCourse")
            Divider()
            Button { dismissTimeEntry(); logging = draft } label: {
                Label("Record time", systemImage: "plus").fontWeight(.semibold)
                    .foregroundStyle(TurnmarkPalette.onAction).frame(maxWidth: .infinity)
            }.buttonStyle(.borderedProminent).tint(TurnmarkPalette.actionFill).controlSize(.large)
                .disabled(!draft.canLog || history.store == nil).accessibilityIdentifier("logSwim")
            Text("Record the time you swam, with a date and optional meet.")
                .font(.footnote).foregroundStyle(TurnmarkPalette.textMuted)
        }.padding(20).background(TurnmarkPalette.surface, in: RoundedRectangle(cornerRadius: TurnmarkPalette.radiusCard))
            .overlay(RoundedRectangle(cornerRadius: TurnmarkPalette.radiusCard).strokeBorder(TurnmarkPalette.borderSubtle))
    }
    private func coursePicker(_ title: String, selection: Binding<Int>, id: String) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.subheadline.weight(.semibold))
            Picker(title, selection: selection) {
                ForEach(courseNames.indices, id: \.self) { Text(courseNames[$0]).tag($0) }
            }.pickerStyle(.segmented).accessibilityIdentifier(id)
        }
    }
    private var strokePicker: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Stroke").font(.subheadline.weight(.semibold))
            Menu {
                Picker("Stroke", selection: $draft.strokeIndex) {
                    ForEach(strokeNames.indices, id: \.self) { Text(strokeNames[$0]).tag($0) }
                }
            } label: {
                HStack(spacing: 5) {
                    Text(draft.strokeIndex == 4 ? "IM" : strokeNames[draft.strokeIndex])
                    Image(systemName: "chevron.up.chevron.down").font(.caption).accessibilityHidden(true)
                }
            }.accessibilityLabel("Stroke").accessibilityValue(strokeNames[draft.strokeIndex])
                .accessibilityIdentifier("strokePicker")
        }
    }
    private var distancePicker: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Distance").font(.subheadline.weight(.semibold))
            Picker("Distance", selection: $draft.distance) {
                ForEach(draft.options, id: \.event.distance) { Text("\($0.event.distance) \(draft.unit)").tag($0.event.distance) }
            }.accessibilityIdentifier("distancePicker")
        }
    }
}

struct ConversionResult: View {
    let input: Draft
    var compact = false
    var benchmarks: ((Draft) -> Void)? = nil
    var selectCourse: ((Int) -> Void)? = nil
    @State private var showingDetails = false
    @State private var showingCourses = false
    @ScaledMetric(relativeTo: .largeTitle) private var compactTimeSize = 44
    @ScaledMetric(relativeTo: .largeTitle) private var fullTimeSize = 64

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Your comparison").font(.caption.weight(.semibold)).textCase(.uppercase).tracking(1.5)
                .foregroundStyle(TurnmarkResultPalette.textMuted)
            switch input.outcome {
            case let .available(value, _):
                Text(input.resultLabel(value.event)).font(.subheadline)
                    .foregroundStyle(TurnmarkResultPalette.textMuted).accessibilityIdentifier("resultContext")
                timeLabel(value.time)
                Text(kindLabel(value.kind)).font(.footnote.weight(.semibold)).foregroundStyle(TurnmarkResultPalette.textMuted)
                if value.kind != .swum {
                    Text("From \(input.time) · \(input.distance) \(input.unit) \(courseNames[input.courseIndex])")
                        .font(.footnote).foregroundStyle(TurnmarkResultPalette.textMuted)
                }
                if compact {
                    DisclosureGroup("All course equivalents", isExpanded: $showingCourses) { courseRows }
                        .font(.subheadline).tint(TurnmarkResultPalette.accent)
                        .environment(\.colorScheme, .dark).accessibilityIdentifier("courseEquivalents")
                } else { Divider(); courseRows }
                ViewThatFits(in: .horizontal) {
                    HStack { detailsButton; Spacer(); shareButton }
                    VStack(alignment: .leading, spacing: 8) { detailsButton; shareButton }
                }.modifier(SwimActionsStyle()).tint(TurnmarkResultPalette.accent).environment(\.colorScheme, .dark)
            case .invalid:
                Text("Check your time").font(.headline).accessibilityIdentifier("invalidTime")
                Text("Try 58.32 or 1:02.45, up to 60 minutes.").font(.subheadline).foregroundStyle(TurnmarkResultPalette.textMuted)
            case .unavailable:
                Text("No published conversion").font(.headline).accessibilityIdentifier("unavailableConversion")
                Text("Choose another event or course comparison.").font(.subheadline).foregroundStyle(TurnmarkResultPalette.textMuted)
            }
            if let benchmarks {
                Button { benchmarks(input) } label: { Label("Standards & points", systemImage: "chart.bar.xaxis") }
                    .buttonStyle(.bordered).tint(TurnmarkResultPalette.accent).environment(\.colorScheme, .dark)
                    .disabled(parseTime(input: input.time) == nil).accessibilityIdentifier("openBenchmarks")
            }
        }.frame(maxWidth: .infinity, alignment: .leading).padding(compact ? 20 : 24)
            .foregroundStyle(TurnmarkResultPalette.text)
            .background(LinearGradient(colors: [TurnmarkResultPalette.surfaceRaised, TurnmarkResultPalette.surface],
                startPoint: .topLeading, endPoint: .bottomTrailing),
                in: RoundedRectangle(cornerRadius: TurnmarkPalette.radiusCard))
            .overlay(RoundedRectangle(cornerRadius: TurnmarkPalette.radiusCard).strokeBorder(TurnmarkResultPalette.borderSubtle))
            .sheet(isPresented: $showingDetails) { ConversionDetails(input: input) }
    }
    private func timeLabel(_ time: String) -> some View {
        let parts = time.split(separator: ".", maxSplits: 1)
        return (Text(String(parts[0])) + Text(parts.count > 1 ? "." + parts[1] : "").foregroundColor(TurnmarkResultPalette.resultHighlight))
            .font(.system(size: compact ? compactTimeSize : fullTimeSize, weight: .bold)).monospacedDigit()
            .minimumScaleFactor(0.6).lineLimit(1).accessibilityLabel(time).accessibilityIdentifier("resultTime")
    }
    private var courseRows: some View {
        VStack(spacing: 0) {
            ForEach(courses.indices, id: \.self) { index in
                let outcome = destination(index)
                Button { selectCourse?(index) } label: {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(courseNames[index]).font(.subheadline.weight(.semibold))
                            if index == input.targetIndex { Image(systemName: "checkmark").accessibilityHidden(true) }
                            Spacer()
                            Text(outcome.time).font(.headline).monospacedDigit()
                        }
                        Text(outcome.context).font(.footnote).foregroundStyle(TurnmarkResultPalette.textMuted)
                    }.padding(.vertical, 12).contentShape(Rectangle())
                }.buttonStyle(.plain).disabled(selectCourse == nil)
                    .foregroundStyle(index == input.targetIndex ? TurnmarkResultPalette.resultHighlight : TurnmarkResultPalette.text)
                    .accessibilityIdentifier("equivalent-\(courseNames[index])")
                    .accessibilityValue(index == input.targetIndex ? "Selected" : "")
                if index < 2 { Divider() }
            }
        }
    }
    private func destination(_ index: Int) -> (time: String, context: String) {
        var value = input; value.targetIndex = index
        switch value.outcome {
        case let .available(result, _): return (result.time, "\(value.resultLabel(result.event)) · \(kindLabel(result.kind))")
        case .unavailable: return ("Unavailable", "No published conversion")
        case .invalid: return ("—", "Check your time")
        }
    }
    private var detailsButton: some View {
        Button { showingDetails = true } label: { Label("Details", systemImage: "info.circle") }
            .accessibilityIdentifier("conversionDetails")
    }
    private var shareButton: some View {
        ShareLink(item: input.shareURL) { Label("Share", systemImage: "square.and.arrow.up") }
            .accessibilityIdentifier("shareSwim")
    }
}

private func kindLabel(_ kind: ConversionKind) -> String {
    kind == .swum ? "Original time" : kind == .published ? "Published factor" : "Derived estimate"
}

struct LegacyComparison: View {
    let input: Draft
    let restore: () -> Void
    let remove: () -> Void
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("A comparison saved in an earlier version. It is separate from recorded swims.").font(.subheadline)
                    ConversionResult(input: input)
                    Button("Use these inputs") { restore(); dismiss() }.buttonStyle(.borderedProminent)
                    Button("Remove previous comparison", role: .destructive) { remove(); dismiss() }
                }.padding()
            }.background(TurnmarkPalette.canvas).navigationTitle("Previous comparison").navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }
}

struct MethodScreen: View {
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        NavigationStack {
            List {
                Section("How comparisons work") {
                    Text("Published NCAA factors estimate a yards time from a metric swim. Reverse and cross-metric conversions are derived estimates. The original time stays separate.")
                    Text("A converted time is not an official swim or confirmation of meet-entry eligibility.")
                    Link("Methodology and coverage", destination: URL(string: "https://turnmark.app/#method")!)
                }
                Section("Your data") {
                    Text("Inputs and swim history stay on this device. Export/import moves a copy of recorded swims; there is no account or cloud sync. Sharing includes the original swim in a link. Source links need an internet connection.")
                }
            }.navigationTitle("About Turnmark").navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }
}

private struct ConversionDetails: View {
    let input: Draft
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                if case let .available(value, source) = input.outcome {
                    Section("Entered swim") {
                        Text(input.time).font(.title2.bold()).monospacedDigit()
                        Text(input.label)
                    }
                    Section(value.kind == .swum ? "Same course" : "Comparison") {
                        Text(value.time).font(.title2.bold()).monospacedDigit()
                        Text(input.resultLabel(value.event))
                        Text(value.kind == .swum ? "The entered time is unchanged." : value.kind == .published
                             ? "Uses the published NCAA metric-to-yards factor."
                             : "Derived from the published NCAA factors; this is an estimate.")
                        Text("Time multiplier: \(String(value.factor))")
                            .monospacedDigit()
                        if value.kind != .swum {
                            Text("Multiplies the entered seconds by this factor, then truncates to hundredths.")
                                .font(.footnote).foregroundStyle(.secondary)
                        }
                    }
                    Section("Source") {
                        Text(source.title)
                        Text("Edition: \(source.id)")
                        Text("Revision: \(source.revision)").font(.footnote)
                        if let url = URL(string: source.url) { Link("Published source", destination: url) }
                        Text("Source links need an internet connection. Calculation and source metadata work offline.")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                    Section {
                        Text("A converted time is not a recorded performance or confirmation of meet-entry eligibility.")
                        Button("Done") { dismiss() }.accessibilityIdentifier("closeDetailsFooter")
                    }
                }
            }.navigationTitle("Conversion details").navigationBarTitleDisplayMode(.inline).toolbar(.visible, for: .navigationBar)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }
}

// Standard navigation and pickers inherit Liquid Glass from the current SDK.
// Keep the result and input surfaces opaque so the numbers remain easy to read.
private struct SwimActionsStyle: ViewModifier {
    @ViewBuilder func body(content: Content) -> some View {
        if #available(iOS 26.0, *) {
            GlassEffectContainer(spacing: 16) {
                content.buttonStyle(.glass).controlSize(.large)
            }
        } else {
            content.buttonStyle(.bordered).controlSize(.large)
        }
    }
}
