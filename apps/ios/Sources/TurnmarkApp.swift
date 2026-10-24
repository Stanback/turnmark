import SwiftUI
import UIKit
import TurnmarkCore

private let coloradoDistanceCaveat = "Distance caveat: this documented Colorado rule uses a general SCM/SCY multiplier for unequal-distance freestyle events. Check the meet’s required conversion."
private let empiricalLowEvidenceCaveat = "Limited data: few swimmers in Turnmark’s data swam this event in both of these courses at this level, so this equivalent time is less certain and leans on related events and pool geometry."
private let empiricalOutOfRangeCaveat = "Outside the model’s fitted range: this estimate extrapolates beyond the available fit."

private func caveatText(_ caveat: ConversionCaveat) -> String {
    switch caveat {
    case .coloradoShortCourseDistance: return coloradoDistanceCaveat
    case .empiricalLowEvidence: return empiricalLowEvidenceCaveat
    case .empiricalOutOfRange: return empiricalOutOfRangeCaveat
    }
}

let courseNames = ["SCY", "SCM", "LCM"]
let courses: [Course] = [.scy, .scm, .lcm]
let strokeNames = ["Freestyle", "Backstroke", "Breaststroke", "Butterfly", "Individual medley"]
let strokeCodes = ["FR", "BK", "BR", "FL", "IM"]
let strokeImages = ["Swim-freestyle", "Swim-backstroke", "Swim-breaststroke", "Swim-butterfly", "Swim-individual-medley"]
let strokes: [Stroke] = [.freestyle, .backstroke, .breaststroke, .butterfly, .individualMedley]

struct Draft: Codable, Equatable {
    var time = ""
    var strokeIndex = 0
    var distance: UInt32 = 100
    var courseIndex = 0
    var categoryIndex = 0
    var targetIndex = 2
    // Optional for decoding drafts saved before method selection existed.
    var altitudeText: String?
    var elevationUnitIndex: Int?
    var altitudePolicyID: String?
    var altitudePolicy: AltitudePolicy { altitudePolicyID == "ncaa-altitude-2026-27-d1" ? .ncaa : .usaSwimming }
    var elevation: Elevation { Elevation(value: Double(altitudeText ?? "") ?? .nan, unit: elevationUnitIndex == 1 ? .meters : .feet) }
    var altitudeOutcome: AltitudeOutcome { adjustAltitudeWithPolicy(request: AltitudeRequest(swim: swim, elevation: elevation), policy: altitudePolicy) }
    var swim: Swim { Swim(time: time, event: SwimEvent(distance: distance, stroke: strokes[strokeIndex], course: courses[courseIndex])) }
    var methodID: String?
    var method: ConversionMethod {
        switch methodID {
        case "colorado-teamunify-2026": return .colorado
        case "turnmark-empirical-2026": return .empirical
        default: return .ncaa
        }
    }
    var methodLabel: String {
        switch method {
        case .colorado: return "Colorado Timing"
        case .empirical: return "Turnmark Equivalence"
        case .ncaa: return "NCAA"
        }
    }
    static var example: Draft { var input = Draft(); input.time = "58.32"; return input }
    var methodDifference: String? {
        var ncaa = self; ncaa.methodID = "ncaa-2025-27"
        var other = self; other.methodID = method == .empirical ? "turnmark-empirical-2026" : "colorado-teamunify-2026"
        guard case let .available(a, _) = ncaa.outcome, case let .available(b, _) = other.outcome else { return nil }
        return String(format: "%.2fs", abs(Double(a.hundredths) - Double(b.hundredths)) / 100)
    }
    var methodSpread: String? {
        let ids = ["ncaa-2025-27", "colorado-teamunify-2026", "turnmark-empirical-2026"]
        let hs = ids.compactMap { id -> UInt64? in
            var copy = self; copy.methodID = id
            if case let .available(v, _) = copy.outcome { return v.hundredths }
            return nil
        }
        guard hs.count >= 2, let minH = hs.min(), let maxH = hs.max(), courseIndex != targetIndex else { return nil }
        return String(format: "%.2fs", Double(maxH - minH) / 100.0)
    }
    func turnGeometrySummary(_ targetEvent: SwimEvent) -> String? {
        guard courseIndex != targetIndex else { return nil }
        let srcPool: UInt32 = courses[courseIndex] == .lcm ? 50 : 25
        let dstPool: UInt32 = targetEvent.course == .lcm ? 50 : 25
        let srcTurns = max(0, Int(distance / srcPool) - 1)
        let dstTurns = max(0, Int(targetEvent.distance / dstPool) - 1)
        let delta = dstTurns - srcTurns
        let deltaText = delta == 0 ? "" : " · \(delta > 0 ? "+\(delta)" : "−\(abs(delta))") \(abs(delta) == 1 ? "wall" : "walls")"
        return "\(distance) \(unit) \(courseNames[courseIndex]) (\(srcTurns) \(srcTurns == 1 ? "turn" : "turns")) → \(targetEvent.distance) \(targetEvent.course == .scy ? "yd" : "m") \(courseNames[targetIndex]) (\(dstTurns) \(dstTurns == 1 ? "turn" : "turns"))\(deltaText)"
    }
    func methodFormulaSummary(againstNcaa ncaaHundredths: UInt64?) -> String? {
        guard courseIndex != targetIndex, case let .available(value, _) = outcome, value.kind != .swum else { return nil }
        let off = value.offsetSeconds
        let offText = off == 0 ? "" : String(format: " %@ %.2fs", off > 0 ? "+" : "−", abs(off))
        var deltaText = ""
        if let ncaaH = ncaaHundredths {
            if method == .ncaa {
                deltaText = " · NCAA baseline"
            } else {
                let d = (Double(value.hundredths) - Double(ncaaH)) / 100.0
                deltaText = String(format: " · %@%.2fs vs NCAA", d >= 0 ? "+" : "−", abs(d))
            }
        }
        return String(format: "× %.5f%@%@", value.factor, offText, deltaText)
    }

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
        let request = ConversionRequest(swim: swim, to: courses[targetIndex], table: categoryIndex == 0 ? .women : .men)
        if altitudeText != nil {
            return convertSwimAtAltitude(request: request, method: method, elevation: elevation, policy: altitudePolicy)
        }
        return convertSwimWithMethod(request: request, method: method)
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
    mutating func setElevationUnit(_ unit: Int) {
        if let text = altitudeText, let value = Double(text), value.isFinite, value >= 0, unit != (elevationUnitIndex ?? 0) {
            altitudeText = unit == 1 ? String(format: "%.1f", value * 0.3048) : String(format: "%.0f", (value / 0.3048).rounded())
        }
        elevationUnitIndex = unit
    }
    var altitudeFeet: String {
        if case let .available(value, _) = altitudeOutcome { return String(value.elevationFeet) }
        return "0"
    }
    var shareURL: URL {
        var query = URLComponents()
        query.queryItems = [
            URLQueryItem(name: "t", value: time), URLQueryItem(name: "s", value: strokeCodes[strokeIndex]),
            URLQueryItem(name: "d", value: String(options.first(where: { $0.event.distance == distance })?.canonicalDistance ?? distance)),
            URLQueryItem(name: "c", value: courseNames[courseIndex]),
            URLQueryItem(name: "g", value: categoryIndex == 0 ? "women" : "men"),
            URLQueryItem(name: "h", value: altitudeText == nil ? "0" : altitudeFeet)]
        if altitudeText != nil && altitudePolicy == .ncaa { query.queryItems?.append(URLQueryItem(name: "ap", value: "ncaa-altitude-2026-27-d1")) }
        if method != .ncaa, let methodID { query.queryItems?.append(URLQueryItem(name: "m", value: methodID)) }
        var url = URLComponents(string: "https://turnmark.app/")!
        url.percentEncodedFragment = query.percentEncodedQuery
        return url.url!
    }
}

@main
struct TurnmarkApp: App {
    private var testingWithoutAnimations: Bool {
        #if DEBUG
        ProcessInfo.processInfo.environment["TURNMARK_UI_TESTS"] == "1"
        #else
        false
        #endif
    }
    init() {
        #if DEBUG
        if ProcessInfo.processInfo.environment["TURNMARK_UI_TESTS"] == "1" { UIView.setAnimationsEnabled(false) }
        #endif
    }
    var body: some Scene {
        WindowGroup { TurnmarkView().transaction { if testingWithoutAnimations { $0.disablesAnimations = true } } }
    }
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
    @State private var calculationOptionsExpanded = false
    @AppStorage("savedSwim") private var savedJSON = ""
    @FocusState private var editingTime: Bool
    @FocusState private var editingElevation: Bool
    @State private var focusDismissal = 0
    @ScaledMetric(relativeTo: .largeTitle) private var entrySize = 42

    init() {
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-uitesting-reset") {
            UserDefaults.standard.removeObject(forKey: "draft")
            UserDefaults.standard.removeObject(forKey: "savedSwim")
            for key in ["benchmarkMode", "benchmarkSystem", "benchmarkYouthAge", "benchmarkMastersAge", "benchmarkFuturesAge", "benchmarkConfigured"] { UserDefaults.standard.removeObject(forKey: key) }
            if let store = try? SwimHistoryStore() { for swim in store.swims { try? store.remove(swim.id) } }
        }
        if ProcessInfo.processInfo.arguments.contains("-uitesting-example") {
            UserDefaults.standard.set(Draft.example.encoded, forKey: "draft")
        }
        if ProcessInfo.processInfo.arguments.contains("-uitesting-legacy") {
            UserDefaults.standard.set(Draft.example.encoded, forKey: "savedSwim")
        }
        #endif
        let restored = Draft.decode(UserDefaults.standard.string(forKey: "draft")) ?? Draft()
        _draft = State(initialValue: restored)
        _calculationOptionsExpanded = State(initialValue: restored.altitudeText != nil || restored.method != .ncaa)
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
                .navigationTitle("turnmark.").navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    converterBrandToolbar
                    // Keep the brand leading, rather than duplicating the inline
                    // navigation title in the system's centered title position.
                    ToolbarItem(placement: .principal) { Color.clear.frame(width: 0, height: 0).accessibilityHidden(true) }
                    ToolbarItem(placement: .topBarTrailing) {
                        Menu {
                            Button { dismissTimeEntry(); showingMethod = true } label: { Label("About Turnmark", systemImage: "info.circle") }
                                .accessibilityIdentifier("converterAbout")
                            Link(destination: URL(string: "https://turnmark.app/#method")!) {
                                Label("Methodology and coverage", systemImage: "arrow.up.right.square")
                            }
                        } label: { Image(systemName: "ellipsis") }
                            .accessibilityLabel("More options").accessibilityIdentifier("converterMenu")
                    }
                    if editingTime || editingElevation {
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
    private var toolbarWave: some View {
        Image("Swim-brand-wave").resizable().scaledToFit().frame(width: 27, height: 27)
            .foregroundStyle(TurnmarkPalette.accent)
    }
    private var toolbarBrand: some View {
        HStack(spacing: 7) {
            toolbarWave
            if !typeSize.isAccessibilitySize {
                HStack(alignment: .firstTextBaseline, spacing: 1) {
                    Text("turnmark")
                    Text(".").foregroundStyle(TurnmarkPalette.accent)
                }.font(.headline.weight(.bold)).lineLimit(1)
            }
        }.fixedSize(horizontal: true, vertical: false)
            .accessibilityElement(children: .ignore).accessibilityLabel("Turnmark")
            .accessibilityAddTraits(.isHeader).accessibilityIdentifier("converterBrand")
    }
    @ToolbarContentBuilder private var converterBrandToolbar: some ToolbarContent {
        if #available(iOS 26.0, *) {
            ToolbarItem(placement: .topBarLeading) { toolbarBrand }.sharedBackgroundVisibility(.hidden)
        } else {
            ToolbarItem(placement: .topBarLeading) { toolbarBrand }
        }
    }

    private func dismissTimeEntry() {
        // Explicit dismissal supersedes any pane-change restoration still
        // waiting on the main actor, including on a busy simulator/device.
        focusDismissal &+= 1
        editingTime = false
        editingElevation = false
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
        ScrollViewReader { scroll in
            Form {
                inputCard
                if draft.available {
                    Section {
                        Button {
                            dismissTimeEntry()
                            scroll.scrollTo("comparison", anchor: .top)
                        } label: { Label("See your results", systemImage: "arrow.down") }
                            .accessibilityIdentifier("seeResults")
                    }.listRowBackground(TurnmarkPalette.surface)
                }
                Section {
                    resultContent(compact: true)
                        .listRowInsets(EdgeInsets()).listRowBackground(Color.clear)
                }.id("comparison")
                localNotice
            }.formStyle(.grouped).scrollContentBackground(.hidden)
                .scrollDismissesKeyboard(.interactively)
                .frame(maxWidth: 600).frame(maxWidth: .infinity)
        }
    }
    private var inputPane: some View {
        Form { inputContent }.formStyle(.grouped).scrollContentBackground(.hidden)
            .scrollDismissesKeyboard(.interactively)
            .frame(maxWidth: 600).frame(maxWidth: .infinity)
    }
    private var resultPane: some View {
        comparisonPane()
    }
    private func comparisonPane(compact: Bool = false) -> some View {
        ScrollView {
            resultContent(compact: compact)
                .padding(20).frame(maxWidth: 620).frame(maxWidth: .infinity)
        }
    }
    private var inputContent: some View {
        Group {
            inputCard
            localNotice
        }.foregroundStyle(TurnmarkPalette.text)
    }
    private func resultContent(compact: Bool) -> some View {
        ConversionResult(input: draft, compact: compact,
            benchmarks: { dismissTimeEntry(); benchmarking = $0 },
            selectCourse: { draft.targetIndex = $0 },
            log: history.store == nil ? nil : { dismissTimeEntry(); logging = draft })
    }
    private var localNotice: some View {
        Section {
            if let logNotice { Text(logNotice).font(.footnote).foregroundStyle(TurnmarkPalette.textMuted).accessibilityIdentifier("logNotice") }
            if history.error != nil { Text("History is unavailable. Open My times to try again.").font(.footnote) }
            Text("On this device. Works offline.").font(.footnote).foregroundStyle(TurnmarkPalette.textMuted)
        }.listRowBackground(Color.clear)
    }
    private var inputCard: some View {
        Section {
            VStack(alignment: .leading, spacing: 8) {
                Text("Your time").font(.subheadline.weight(.semibold))
                HStack {
                    TextField("58.32", text: $draft.time)
                        .font(.system(size: entrySize, weight: .semibold)).monospacedDigit()
                        .keyboardType(.numbersAndPunctuation).focused($editingTime)
                        .submitLabel(.done).onSubmit(dismissTimeEntry)
                        .accessibilityLabel("Your time").accessibilityIdentifier("timeInput")
                    if !draft.time.isEmpty {
                        Button { draft.time = ""; editingTime = true } label: { Image(systemName: "xmark.circle.fill") }
                            .buttonStyle(.borderless).foregroundStyle(.secondary)
                            .accessibilityLabel("Clear time").accessibilityIdentifier("clearConverterTime")
                    }
                }.padding(.vertical, 4)
                Text(draft.time.isEmpty ? "Enter seconds or a time like 1:02.45" : "Results update as you type")
                    .font(.footnote).foregroundStyle(TurnmarkPalette.textMuted)

            }
            if typeSize.isAccessibilitySize { strokePicker; distancePicker }
            else {
                HStack(alignment: .top, spacing: 16) {
                    strokePicker.frame(maxWidth: .infinity, alignment: .leading)
                    distancePicker.frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            coursePicker("Swum in", selection: $draft.courseIndex, id: "inputCourse")
            VStack(alignment: .leading, spacing: 8) {
                Text("Published category").font(.subheadline.weight(.semibold))
                Picker("Published category", selection: $draft.categoryIndex) {
                    Text("Women").tag(0); Text("Men").tag(1)
                }.pickerStyle(.segmented).accessibilityIdentifier("category")
            }
            DisclosureGroup(isExpanded: $calculationOptionsExpanded) {
                Picker("Course conversion", selection: Binding(get: { draft.methodID ?? "ncaa-2025-27" }, set: { draft.methodID = $0 })) {
                    Text("NCAA (default)").tag("ncaa-2025-27")
                    Text("Colorado Timing").tag("colorado-teamunify-2026")
                    Text("Turnmark Equivalence").tag("turnmark-empirical-2026")
                }.pickerStyle(.menu).accessibilityIdentifier("courseConversion")
                Toggle("Adjust for altitude", isOn: Binding(get: { draft.altitudeText != nil }, set: { draft.altitudeText = $0 ? "0" : nil }))
                    .accessibilityIdentifier("altitudeEnabled")
                if draft.altitudeText != nil {
                    TextField("Pool elevation", text: Binding(get: { draft.altitudeText ?? "" }, set: { draft.altitudeText = $0 }))
                        .keyboardType(.numbersAndPunctuation).focused($editingElevation).submitLabel(.done).onSubmit(dismissTimeEntry).accessibilityIdentifier("poolElevation")
                    Picker("Elevation unit", selection: Binding(get: { draft.elevationUnitIndex ?? 0 }, set: { draft.setElevationUnit($0) })) {
                        Text("Feet").tag(0); Text("Meters").tag(1)
                    }.accessibilityIdentifier("elevationUnit")
                    Picker("Altitude policy", selection: Binding(get: { draft.altitudePolicyID ?? "usa-swimming-altitude-2026" }, set: { draft.altitudePolicyID = $0 })) {
                        Text("USA Swimming (default)").tag("usa-swimming-altitude-2026")
                        Text("NCAA · 2026–27 Division I").tag("ncaa-altitude-2026-27-d1")
                    }.accessibilityIdentifier("altitudePolicy")
                    if case let .available(value, _) = draft.altitudeOutcome {
                        Text("Altitude deduction: −\(String(format: "%.2f", value.adjustmentSeconds))s. Sea-level estimate: \(value.adjustedTime). Applied before course conversion.")
                            .font(.footnote).foregroundStyle(TurnmarkPalette.textMuted)
                    }
                }
            } label: { Label("Calculation options", systemImage: "slider.horizontal.3").accessibilityIdentifier("calculationOptions") }
        } header: {
            HStack {
                Text("Your swim").font(.title3.bold()).foregroundStyle(TurnmarkPalette.text)
                Spacer()
                Button { dismissTimeEntry(); draft.time = ""; logNotice = nil } label: { Label("Reset", systemImage: "arrow.counterclockwise") }
                    .font(.subheadline).accessibilityIdentifier("resetConverter")
            }.textCase(nil)
        }
            .listRowBackground(TurnmarkPalette.surface)
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
                    ForEach(strokeNames.indices, id: \.self) { Label(strokeNames[$0], image: strokeImages[$0]).tag($0) }
                }
            } label: {
                HStack(spacing: 5) {
                    Image(strokeImages[draft.strokeIndex]).resizable().scaledToFit().frame(width: 20, height: 20).accessibilityHidden(true)
                    Text(draft.strokeIndex == 4 ? "IM" : strokeNames[draft.strokeIndex])
                    Image(systemName: "chevron.up.chevron.down").font(.caption).accessibilityHidden(true)
                }.foregroundStyle(TurnmarkPalette.accent)
            }.buttonStyle(.borderless).accessibilityLabel("Stroke").accessibilityValue(strokeNames[draft.strokeIndex])
                .accessibilityIdentifier("strokePicker")
        }
    }
    private var distancePicker: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Distance").font(.subheadline.weight(.semibold))
            Menu {
                Picker("Distance", selection: $draft.distance) {
                    ForEach(draft.options, id: \.event.distance) { Text("\($0.event.distance) \(draft.unit)").tag($0.event.distance) }
                }
            } label: {
                HStack(spacing: 5) {
                    Image("Swim-distance").resizable().scaledToFit().frame(width: 20, height: 20).accessibilityHidden(true)
                    Text("\(draft.distance) \(draft.unit)")
                    Image(systemName: "chevron.up.chevron.down").font(.caption).accessibilityHidden(true)
                }.foregroundStyle(TurnmarkPalette.accent)
            }.buttonStyle(.borderless).accessibilityLabel("Distance").accessibilityValue("\(draft.distance) \(draft.unit)")
                .accessibilityIdentifier("distancePicker")
        }
    }
}

struct ConversionResult: View {
    @Environment(\.dynamicTypeSize) private var typeSize
    let input: Draft
    var compact = false
    var benchmarks: ((Draft) -> Void)? = nil
    var selectCourse: ((Int) -> Void)? = nil
    var log: (() -> Void)? = nil
    @State private var showingDetails = false
    @ScaledMetric(relativeTo: .largeTitle) private var compactTimeSize = 44
    @ScaledMetric(relativeTo: .largeTitle) private var fullTimeSize = 64

    var body: some View {
        VStack(alignment: .leading, spacing: compact ? 10 : 14) {
            HStack {
                Text("Equivalent times").font(.caption.weight(.semibold)).textCase(.uppercase).tracking(1.5)
                Spacer()
                HStack(spacing: 4) {
                    ForEach(courses.indices, id: \.self) { index in
                        Capsule().fill(index == input.targetIndex ? TurnmarkResultPalette.resultHighlight : TurnmarkResultPalette.borderControl)
                            .frame(width: 18, height: 2)
                    }
                }.accessibilityHidden(true)
            }.foregroundStyle(TurnmarkResultPalette.textMuted)
            if input.time.isEmpty {
                Text("Enter a swim to compare").font(.headline).accessibilityIdentifier("emptyConversion")
                Text("See your time in SCY, SCM and LCM.").font(.subheadline).foregroundStyle(TurnmarkResultPalette.textMuted)
            } else { switch input.outcome {
            case let .available(value, _):
                Text(input.resultLabel(value.event)).font(.subheadline)
                    .foregroundStyle(TurnmarkResultPalette.textMuted).accessibilityIdentifier("resultContext")
                timeLabel(value.time)
                Text(((value.altitude?.value.adjustmentSeconds ?? 0) > 0 && value.kind == .swum ? "Sea-level estimate" : kindLabel(value.kind)) + (value.kind != .swum && input.method == .colorado ? " · Colorado Timing" : "")).font(.footnote.weight(.semibold)).foregroundStyle(TurnmarkResultPalette.textMuted)
                if let caveat = value.caveat { Text(caveatText(caveat)).font(.footnote).foregroundStyle(TurnmarkResultPalette.textMuted).accessibilityIdentifier(caveat == .empiricalLowEvidence ? "lowEvidenceCaveat" : caveat == .empiricalOutOfRange ? "outOfRangeCaveat" : "distanceCaveat") }
                if value.kind != .swum {
                    Text("From \(input.time) · \(input.distance) \(input.unit) \(courseNames[input.courseIndex])")
                        .font(.footnote).foregroundStyle(TurnmarkResultPalette.textMuted)
                }
            case .invalid:
                Text("Check your time or elevation").font(.headline).accessibilityIdentifier("invalidTime")
                Text("Try 58.32 or 1:02.45, up to 60 minutes.").font(.subheadline).foregroundStyle(TurnmarkResultPalette.textMuted)
            case .unavailable:
                Text("No published conversion").font(.headline).accessibilityIdentifier("unavailableConversion")
                Text("Choose another event or course comparison.").font(.subheadline).foregroundStyle(TurnmarkResultPalette.textMuted)
            } }
            if parseTime(input: input.time) != nil {
                Divider().overlay(TurnmarkResultPalette.borderSubtle)
                Text("Select a course to focus").font(.footnote).foregroundStyle(TurnmarkResultPalette.textMuted)
                courseRows
                Text("Converted times are estimates. Check your meet’s entry rules.").font(.footnote).foregroundStyle(TurnmarkResultPalette.textMuted)
                Button { showingDetails = true } label: {
                    Label("How this is calculated", systemImage: "info.circle").font(.subheadline)
                }.buttonStyle(.plain).foregroundStyle(TurnmarkResultPalette.accent)
                    .padding(.vertical, 8).accessibilityIdentifier("conversionDetails")
                Divider().overlay(TurnmarkResultPalette.borderSubtle)
                resultActions
            }
        }.frame(maxWidth: .infinity, alignment: .leading).padding(compact ? 20 : 24)
            .foregroundStyle(TurnmarkResultPalette.text)
            .background(NativeResultSurface())
            .sheet(isPresented: $showingDetails) { ConversionDetails(input: input) }
    }
    private var resultActions: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let log {
                Button(action: log) {
                    Label("Log swim", image: "Swim-log-swim").fontWeight(.semibold)
                        .foregroundStyle(TurnmarkResultPalette.onAction).frame(maxWidth: .infinity)
                }.buttonStyle(.borderedProminent).tint(TurnmarkResultPalette.actionFill).controlSize(.large)
                    .accessibilityIdentifier("logSwim")
                Text("Add your entered swim to My times.").font(.footnote).foregroundStyle(TurnmarkResultPalette.textMuted)
            }
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 12) { benchmarkButton; Spacer(minLength: 0); if input.available { shareButton } }
                VStack(alignment: .leading, spacing: 12) { benchmarkButton; if input.available { shareButton } }
            }.modifier(SwimActionsStyle())
        }.fixedSize(horizontal: false, vertical: true)
            .tint(TurnmarkResultPalette.accent).environment(\.colorScheme, .dark)
    }
    @ViewBuilder private var benchmarkButton: some View {
        if let benchmarks {
            Button { benchmarks(input) } label: {
                Label("Standards & points", systemImage: "chart.bar.xaxis").font(.footnote)
            }
                .labelStyle(.titleAndIcon).fixedSize(horizontal: !typeSize.isAccessibilitySize, vertical: true)
                .disabled(parseTime(input: input.time) == nil).accessibilityIdentifier("openBenchmarks")
        }
    }
    private func timeLabel(_ time: String) -> some View {
        let parts = time.split(separator: ".", maxSplits: 1)
        return (Text(String(parts[0])) + Text(parts.count > 1 ? "." + parts[1] : "").foregroundColor(TurnmarkResultPalette.resultHighlight))
            .font(.system(size: compact ? compactTimeSize : fullTimeSize, weight: .bold)).monospacedDigit()
            .minimumScaleFactor(0.6).lineLimit(1).accessibilityLabel(time).accessibilityIdentifier("resultTime")
    }
    private var courseRows: some View {
        VStack(spacing: 8) {
            ForEach(courses.indices, id: \.self) { index in
                let outcome = destination(index)
                Button { selectCourse?(index) } label: {
                    VStack(alignment: .leading, spacing: 6) {
                        HStack {
                            Text(courseNames[index]).font(.subheadline.weight(.semibold))
                            if index == input.targetIndex { Image(systemName: "checkmark").accessibilityHidden(true) }
                            Spacer()
                            if !typeSize.isAccessibilitySize { Text(outcome.time).font(.title3.bold()).monospacedDigit() }
                        }
                        if typeSize.isAccessibilitySize { Text(outcome.time).font(.title3.bold()).monospacedDigit() }
                        Text(outcome.context).font(.footnote).foregroundStyle(TurnmarkResultPalette.textMuted)
                    }.padding(12).frame(maxWidth: .infinity, alignment: .leading)
                        .background(index == input.targetIndex ? TurnmarkResultPalette.selectedSurface : TurnmarkResultPalette.surfaceInput,
                            in: RoundedRectangle(cornerRadius: TurnmarkPalette.radiusControl))
                        .overlay(RoundedRectangle(cornerRadius: TurnmarkPalette.radiusControl)
                            .strokeBorder(index == input.targetIndex ? TurnmarkResultPalette.resultHighlight.opacity(0.6) : TurnmarkResultPalette.borderSubtle))
                        .contentShape(Rectangle())
                }.buttonStyle(.plain).disabled(selectCourse == nil)
                    .foregroundStyle(index == input.targetIndex ? TurnmarkResultPalette.resultHighlight : TurnmarkResultPalette.text)
                    .accessibilityIdentifier("equivalent-\(courseNames[index])")
                    .accessibilityValue(index == input.targetIndex ? "Selected" : "")
            }
        }
    }
    private func destination(_ index: Int) -> (time: String, context: String) {
        var value = input; value.targetIndex = index
        switch value.outcome {
        case let .available(result, _): return (result.time, "\(value.resultLabel(result.event)) · \((result.altitude?.value.adjustmentSeconds ?? 0) > 0 && result.kind == .swum ? "Sea-level estimate" : kindLabel(result.kind))")
        case .unavailable: return ("Unavailable", "No published conversion")
        case .invalid: return ("—", "Check your time")
        }
    }
    private var shareButton: some View {
        ShareLink(item: input.shareURL) { Label("Share", systemImage: "square.and.arrow.up") }
            .labelStyle(.iconOnly).buttonBorderShape(.circle)
            .accessibilityIdentifier("shareSwim")
    }
}

/// Opaque numerical content, shared by the converter and benchmark summaries.
/// System glass is reserved for the native actions and navigation above it.
struct NativeResultSurface: View {
    @Environment(\.accessibilityReduceTransparency) private var reduceTransparency
    @Environment(\.colorSchemeContrast) private var contrast
    var body: some View {
        ZStack {
            LinearGradient(colors: [TurnmarkResultPalette.surfaceRaised, TurnmarkResultPalette.surface],
                startPoint: .topLeading, endPoint: .bottomTrailing)
            if !reduceTransparency && contrast != .increased {
                Canvas { context, size in
                    var ribbon = Path()
                    ribbon.move(to: CGPoint(x: size.width * 0.45, y: 0))
                    ribbon.addCurve(to: CGPoint(x: size.width, y: size.height * 0.28),
                        control1: CGPoint(x: size.width * 0.72, y: 0), control2: CGPoint(x: size.width * 0.76, y: size.height * 0.25))
                    ribbon.addLine(to: CGPoint(x: size.width, y: size.height * 0.44))
                    ribbon.addCurve(to: CGPoint(x: size.width * 0.45, y: 0),
                        control1: CGPoint(x: size.width * 0.72, y: size.height * 0.42), control2: CGPoint(x: size.width * 0.68, y: size.height * 0.08))
                    context.fill(ribbon, with: .color(TurnmarkResultPalette.accent.opacity(0.07)))
                }.accessibilityHidden(true).allowsHitTesting(false)
            }
        }.clipShape(RoundedRectangle(cornerRadius: TurnmarkPalette.radiusCard))
            .overlay(RoundedRectangle(cornerRadius: TurnmarkPalette.radiusCard).strokeBorder(TurnmarkResultPalette.borderSubtle))
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
                    Text("NCAA factors are the default. Colorado Timing formulas and optional altitude settings are available under Calculation options. Reverse and cross-metric NCAA conversions are derived estimates. The original time stays separate.")
                    Text("A converted time is not an official swim or confirmation of meet-entry eligibility.")
                    Link("Methodology and coverage", destination: URL(string: "https://turnmark.app/#method")!)
                    Link("Swimming resources", destination: URL(string: "https://turnmark.app/#resources")!)
                }
                Section("Your data") {
                    Text("Inputs and swim history stay on this device. Export/import moves a copy of recorded swims; there is no account or cloud sync. Sharing includes the original swim in a link. Source links need an internet connection.")
                }
            }.navigationTitle("About Turnmark").navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }
}

private struct AltitudeDetails: View {
    let input: Draft
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Entered swim: \(input.time)").font(.subheadline).monospacedDigit()
            ForEach(["usa-swimming-altitude-2026", "ncaa-altitude-2026-27-d1"], id: \.self) { policy in
                var copy: Draft { var value = input; value.altitudePolicyID = policy; return value }
                if case let .available(value, source) = copy.altitudeOutcome {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(policy == "usa-swimming-altitude-2026" ? "USA Swimming" : "NCAA · 2026–27 Division I").font(.subheadline.weight(.semibold))
                        Text("−\(String(format: "%.2f", value.adjustmentSeconds))s → \(value.adjustedTime)").monospacedDigit()
                            .accessibilityIdentifier("altitudeResult-\(policy)")
                        if let url = URL(string: source.url) { Link("Published altitude policy", destination: url).font(.footnote) }
                    }
                } else { Text("Enter a valid time and pool elevation.").font(.footnote) }
            }
            Text("Altitude is deducted before course conversion. Below 3,000 ft, or where the table has no deduction, the time stays unchanged. Meters are rounded to the nearest foot. Use the policy required by your meet.")
                .font(.footnote).foregroundStyle(.secondary)
        }
    }
}

private struct ConversionDetails: View {
    let input: Draft
    @Environment(\.dismiss) private var dismiss
    @Environment(\.dynamicTypeSize) private var typeSize
    private let methodIDs = ["ncaa-2025-27", "colorado-teamunify-2026", "turnmark-empirical-2026"]

    private var ncaaHundredths: UInt64? {
        var ncaa = input; ncaa.methodID = "ncaa-2025-27"
        if case let .available(v, _) = ncaa.outcome { return v.hundredths }
        return nil
    }

    @ViewBuilder private func methodName(_ comparison: Draft) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack(spacing: 6) {
                Text(comparison.methodLabel).fontWeight(.semibold)
                if comparison.method == input.method {
                    Image(systemName: "checkmark").font(.caption.weight(.semibold))
                        .foregroundStyle(TurnmarkPalette.accent).accessibilityLabel("Selected method")
                }
            }
            if let formula = comparison.methodFormulaSummary(againstNcaa: ncaaHundredths) {
                Text(formula).font(.caption).foregroundStyle(.secondary).monospacedDigit()
            }
        }
    }
    @ViewBuilder private func methodTime(_ comparison: Draft) -> some View {
        switch comparison.outcome {
        case let .available(value, _):
            Text(value.time).font(.title3.weight(.semibold)).monospacedDigit()
                .accessibilityIdentifier("methodResult-\(comparison.methodLabel)")
        case .unavailable: Text("Unavailable").foregroundStyle(.secondary)
        case .invalid: Text("Check your time or elevation").foregroundStyle(.secondary)
        }
    }
    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(methodIDs, id: \.self) { method in
                        var comparison: Draft { var copy = input; copy.methodID = method; return copy }
                        if typeSize.isAccessibilitySize {
                            VStack(alignment: .leading, spacing: 6) { methodName(comparison); methodTime(comparison) }
                        } else {
                            HStack(alignment: .firstTextBaseline, spacing: 16) {
                                methodName(comparison); Spacer(minLength: 8); methodTime(comparison)
                            }.padding(.vertical, 4)
                        }
                    }
                    if let difference = input.methodDifference {
                        LabeledContent("Method difference", value: difference)
                            .accessibilityElement(children: .combine).accessibilityIdentifier("methodDifference")
                    }
                    if let spread = input.methodSpread {
                        LabeledContent("Method spread (all 3)", value: spread)
                            .accessibilityElement(children: .combine)
                    }
                } header: {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Compare methods · \(courseNames[input.targetIndex])")
                        if case let .available(value, _) = input.outcome {
                            Text(input.resultLabel(value.event)).font(.footnote).textCase(nil)
                            if let turns = input.turnGeometrySummary(value.event) {
                                Text(turns).font(.caption).foregroundStyle(.secondary).textCase(nil)
                            }
                        }
                    }
                } footer: {
                    Text("Published rules and an equivalence model, not a prediction range or confidence interval. Use the method required by your meet.")
                }
                var colorado: Draft { var copy = input; copy.methodID = "colorado-teamunify-2026"; return copy }
                var equivalence: Draft { var copy = input; copy.methodID = "turnmark-empirical-2026"; return copy }
                ForEach([colorado, equivalence], id: \.methodID) { draft in
                    if case let .available(value, _) = draft.outcome, let caveat = value.caveat {
                        Section { Text(caveatText(caveat)).font(.footnote).foregroundStyle(.secondary) }
                    }
                }
                Section("Why the times differ") {
                    detail("NCAA", "Factors vary by event and course, not age. Long-course factors use separate men’s and women’s tables; short-course meters-to-yards factors are shared. NCAA publishes metric-to-yards factors; reverse and SCM/LCM conversions are derived.")
                    detail("Colorado Timing", "Documented multipliers plus fixed time offsets. The formulas vary by event and course, not age or category.")
                    detail("Turnmark Equivalence", "Estimates the equivalent time in the other course from 95K pairs of the same swimmer racing both courses within a month (8.51M US swims, 2010–2026), allowing for the randomness in any single swim. Converting back returns the entered time to within 0.02 s.")
                    detail("Pool length", "Shorter pools mean more turns and push-offs. These rules do not adjust for your starts, underwater skill, technique, endurance or individual development.")
                    detail("Distance events", "500, 1000 and 1650 yards map to 400, 800 and 1500 meters.")
                }
                if case let .available(value, source) = input.outcome {
                    if input.altitudeText != nil { Section("Altitude adjustment") { AltitudeDetails(input: input) } }
                    Section("Entered swim") {
                        Text(input.time).font(.title3.weight(.semibold)).monospacedDigit()
                        Text(input.label).font(.subheadline).foregroundStyle(.secondary)
                    }
                    Section(value.kind == .swum ? "Same course" : "Selected calculation · \(input.methodLabel)") {
                        Text(value.time).font(.title3.weight(.semibold)).monospacedDigit()
                        Text(input.resultLabel(value.event)).font(.subheadline).foregroundStyle(.secondary)
                        if value.kind == .swum { Text((value.altitude?.value.adjustmentSeconds ?? 0) > 0 ? "Altitude is deducted first; the course is unchanged." : "The entered time is unchanged.") }
                        else {
                            LabeledContent("Time multiplier", value: String(format: "%.5f", value.factor)).monospacedDigit()
                            if value.offsetSeconds != 0 { Text("Time offset: \(String(value.offsetSeconds)) seconds").monospacedDigit() }
                            Text(input.method == .empirical ? "Turnmark Equivalence: the model’s equivalent time in this course. The multiplier shown applies to this entered time." : "After any altitude deduction, multiply the seconds, add any offset, then truncate to hundredths. The factor is rounded here for display.")
                                .font(.footnote).foregroundStyle(.secondary)
                        }
                    }
                    Section("Source") {
                        Text(source.title)
                        Text("Edition: \(source.id)").font(.footnote).foregroundStyle(.secondary)
                        Text("Revision: \(source.revision)").font(.footnote).foregroundStyle(.secondary)
                        if let url = URL(string: source.url) { Link("Published source", destination: url) }
                        var other: Draft { var copy = input; copy.methodID = input.method == .ncaa ? "colorado-teamunify-2026" : "ncaa-2025-27"; return copy }
                        if case let .available(_, alternative) = other.outcome, let url = URL(string: alternative.url) {
                            Link("\(other.methodLabel) source", destination: url)
                        }
                    }
                }
                Section {
                    Text("Standards, points and logged performances use your original swim, before altitude or course conversion.")
                    Text("A converted time is not a recorded performance or confirmation of meet-entry eligibility.")
                    Text("Calculations and source metadata work offline. Source links need a connection.")
                }.font(.footnote).foregroundStyle(.secondary)
            }.navigationTitle("Conversion details").navigationBarTitleDisplayMode(.inline).toolbar(.visible, for: .navigationBar)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }
    private func detail(_ title: String, _ explanation: String) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title).font(.subheadline.weight(.semibold))
            Text(explanation).font(.subheadline).foregroundStyle(.secondary)
        }.padding(.vertical, 3)
    }
}

// Standard navigation and pickers inherit Liquid Glass from the current SDK.
// Keep the result and input surfaces opaque so the numbers remain easy to read.
private struct SwimActionsStyle: ViewModifier {
    @ViewBuilder func body(content: Content) -> some View {
        if #available(iOS 26.0, *) {
            GlassEffectContainer(spacing: 16) {
                content.buttonStyle(.glass).controlSize(.regular)
            }
        } else {
            content.buttonStyle(.bordered).controlSize(.regular)
        }
    }
}
