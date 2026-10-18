import SwiftUI
import TurnmarkCore

private let ink = Color(red: 3 / 255, green: 44 / 255, blue: 67 / 255)
private let lime = Color(red: 221 / 255, green: 245 / 255, blue: 140 / 255)
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
    @Environment(\.verticalSizeClass) private var heightClass
    @State private var draft: Draft
    @State private var tab = 0
    @State private var history = HistoryController()
    @State private var logging: Draft?
    @State private var lastMeet = ""
    @State private var logNotice: String?
    @State private var lastLogDay = SwimRecord.day(Date())
    @State private var lastDate = SwimRecord.day(Date())
    @AppStorage("savedSwim") private var savedJSON = ""
    @FocusState private var editingTime: Bool
    private var isSaved: Bool { Draft.decode(savedJSON) == draft }
    private var pinResult: Bool { !typeSize.isAccessibilitySize && heightClass != .compact }

    init() {
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-uitesting-reset") {
            UserDefaults.standard.removeObject(forKey: "draft")
            UserDefaults.standard.removeObject(forKey: "savedSwim")
            if let store = try? SwimHistoryStore() { for swim in store.swims { try? store.remove(swim.id) } }
        }
        #endif
        _draft = State(initialValue: Draft.decode(UserDefaults.standard.string(forKey: "draft")) ?? Draft())
    }
    var body: some View {
        TabView(selection: $tab) {
            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        if !pinResult { ConversionResult(input: draft, compact: true) }
                        inputCard
                        Button { editingTime = false; logging = draft } label: { Label("Log swim", systemImage: "plus.circle.fill") }
                            .buttonStyle(.borderedProminent).controlSize(.large).disabled(!draft.canLog || history.store == nil)
                            .accessibilityIdentifier("logSwim")
                        if let logNotice { Text(logNotice).font(.footnote).accessibilityIdentifier("logNotice") }
                        if history.error != nil { Text("History is unavailable. Open History to try again.").font(.footnote) }
                        swimActions.modifier(SwimActionsStyle()).disabled(!draft.available)
                        Text("Calculated on your device. Works offline.")
                            .font(.footnote).foregroundStyle(.secondary)
                    }.padding()
                }
                .modifier(ConversionResultBar(summary: ConversionResult(input: draft, compact: true), pinned: pinResult))
                .background(Color(uiColor: .systemGroupedBackground))
                .safeAreaInset(edge: .top, spacing: 0) {
                    // Keep scrolling text clear of the system status text.
                    Color.clear.frame(height: 0).background(.regularMaterial)
                        .accessibilityHidden(true).allowsHitTesting(false)
                }
                .toolbar(.hidden, for: .navigationBar)
                .toolbar {
                    if editingTime { ToolbarItemGroup(placement: .keyboard) { Spacer(); Button("Done") { editingTime = false } } }
                }
            }.tabItem { Label("Convert", systemImage: "arrow.left.arrow.right") }.tag(0)
            NavigationStack {
                HistoryScreen(controller: history) { record in draft = Draft(record: record, target: draft.targetIndex); tab = 0 }
            }.tabItem { Label("History", systemImage: "list.bullet.rectangle") }.tag(1)
            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        if let saved = Draft.decode(savedJSON) {
                            Text(saved.label).font(.headline)
                            Text("Saved conversion · not a logged performance").font(.footnote).foregroundStyle(.secondary)
                            Text("Entered time: \(saved.time)").foregroundStyle(.secondary)
                            ConversionResult(input: saved)
                            Button("Log entered swim") { logging = saved }.disabled(!saved.canLog || history.store == nil)
                            Button("Use this swim") { draft = saved; tab = 0 }.buttonStyle(.borderedProminent)
                            ShareLink(item: saved.shareURL) { Label("Share saved swim", systemImage: "square.and.arrow.up") }
                            Button("Remove saved swim", role: .destructive) { savedJSON = "" }
                        } else {
                            ContentUnavailableView("No saved swim", systemImage: "bookmark", description: Text("Save a conversion to return to it here."))
                        }
                    }.padding()
                }.navigationTitle("Saved swim").background(Color(uiColor: .systemGroupedBackground))
            }.tabItem { Label("Saved", systemImage: "bookmark") }.tag(2)
            NavigationStack {
                List {
                    Section("How comparisons work") {
                        Text("Published NCAA factors estimate a yards time from a metric swim. Reverse and cross-metric conversions are derived estimates. An entered swim remains labeled as entered.")
                        Text("A converted time is not an official swim or confirmation of meet-entry eligibility.")
                    }
                    Section("Sources") {
                        if case let .available(_, source) = draft.outcome, let url = URL(string: source.url) {
                            Link(source.title, destination: url)
                            Text("Edition: \(source.id)").font(.footnote)
                        }
                        Link("Methodology and coverage", destination: URL(string: "https://turnmark.app/#method")!)
                    }
                    Section("Your data") {
                        Text("Your inputs, saved conversion and logged swims stay on this device. History export/import moves a copy of your records; there is no account or cloud sync. Sharing uses a link containing the entered swim. Source links need an internet connection.")
                    }
                }.navigationTitle("The method")
            }.tabItem { Label("Method", systemImage: "info.circle") }.tag(3)
        }
        .task { if history.store == nil { history.open() } }
        .sheet(isPresented: Binding(get: { logging != nil }, set: { if !$0 { logging = nil } })) {
            if let logging {
                SwimEditor(draft: logging, date: lastLogDay == SwimRecord.day(Date()) ? lastDate : SwimRecord.day(Date()),
                    meet: lastLogDay == SwimRecord.day(Date()) ? lastMeet : "") { record in
                    guard let store = history.store else { throw HistoryError.message("History is unavailable.") }
                    try store.save(record); logNotice = "Logged \(record.time) · \(record.date ?? "Unknown date") · \(record.meet ?? "No meet")"; lastDate = record.date ?? ""; lastMeet = record.meet ?? ""; lastLogDay = SwimRecord.day(Date())
                    UIAccessibility.post(notification: .announcement, argument: "Swim logged on this device")
                }
            }
        }
        .onChange(of: draft) { _, value in UserDefaults.standard.set(value.encoded, forKey: "draft") }
        .onChange(of: draft.courseIndex) { _, _ in draft.reconcile() }
        .onChange(of: draft.strokeIndex) { _, _ in draft.reconcile() }
    }

    @ViewBuilder private var swimActions: some View {
        if typeSize.isAccessibilitySize {
            VStack(alignment: .leading, spacing: 12) { saveButton; shareButton }
        } else {
            HStack { saveButton; Spacer(); shareButton }
        }
    }

    private var saveButton: some View {
        Button {
            savedJSON = draft.encoded
            UIAccessibility.post(notification: .announcement, argument: "Swim saved on this device")
        } label: { Label(isSaved ? "Saved" : "Save swim", systemImage: isSaved ? "checkmark" : "bookmark") }
            .accessibilityIdentifier("saveSwim")
            .accessibilityValue(isSaved ? "Saved on this device" : "")
    }

    private var shareButton: some View {
        ShareLink(item: draft.shareURL) { Label("Share", systemImage: "square.and.arrow.up") }
            .accessibilityIdentifier("shareSwim")
    }

    private var inputCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Your time").font(.headline)
            TextField("58.32", text: $draft.time)
                .font(.system(size: 42, weight: .semibold, design: .rounded)).monospacedDigit()
                .keyboardType(.numbersAndPunctuation).focused($editingTime)
                .accessibilityLabel("Your time").accessibilityIdentifier("timeInput")
            Text("Minutes : seconds . hundredths").font(.caption).foregroundStyle(.secondary)
            if typeSize.isAccessibilitySize {
                strokePicker
                distancePicker
            } else {
                HStack {
                    strokePicker.layoutPriority(1)
                    Spacer()
                    distancePicker
                }
            }
            Text("Swum in").font(.subheadline.bold())
            Picker("Swum in", selection: $draft.courseIndex) {
                ForEach(courseNames.indices, id: \.self) { Text(courseNames[$0]).tag($0) }
            }.pickerStyle(.segmented).accessibilityIdentifier("inputCourse")
            Text("Published category").font(.subheadline.bold())
            Picker("Published category", selection: $draft.categoryIndex) {
                Text("Women").tag(0); Text("Men").tag(1)
            }.pickerStyle(.segmented).accessibilityIdentifier("category")
            Text("Compare with").font(.subheadline.bold())
            Picker("Compare with", selection: $draft.targetIndex) {
                ForEach(courseNames.indices, id: \.self) { Text(courseNames[$0]).tag($0) }
            }.pickerStyle(.segmented).accessibilityIdentifier("targetCourse")
        }.padding(20).background(Color(uiColor: .secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 24))
    }

    private var strokePicker: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Stroke").font(.subheadline.bold())
            Picker("Stroke", selection: $draft.strokeIndex) {
                ForEach(strokeNames.indices, id: \.self) { Text(strokeNames[$0]).tag($0) }
            }.accessibilityIdentifier("strokePicker")
        }
    }

    private var distancePicker: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Distance").font(.subheadline.bold())
            Picker("Distance", selection: $draft.distance) {
                ForEach(draft.options, id: \.event.distance) { Text("\($0.event.distance) \(draft.unit)").tag($0.event.distance) }
            }.accessibilityIdentifier("distancePicker")
        }
    }
}

private struct ConversionResult: View {
    let input: Draft
    var compact = false
    @State private var showingDetails = false
    @Environment(\.dynamicTypeSize) private var typeSize
    @ScaledMetric(relativeTo: .largeTitle) private var compactTimeSize = 34
    @ScaledMetric(relativeTo: .largeTitle) private var fullTimeSize = 48

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            switch input.outcome {
            case let .available(value, _):
                Text(input.resultLabel(value.event)).font(.subheadline.bold())
                    .accessibilityIdentifier("resultContext")
                if typeSize.isAccessibilitySize {
                    timeLabel(value.time)
                    detailsButton
                } else {
                    HStack {
                        timeLabel(value.time)
                        Spacer()
                        detailsButton
                    }
                }
                Text(value.kind == .swum ? "Entered swim" : value.kind == .published ? "Published factor" : "Derived estimate")
                    .font(.caption.bold()).foregroundStyle(lime)
                if value.kind != .swum {
                    Text("From \(input.time) · \(input.distance) \(input.unit) \(courseNames[input.courseIndex])")
                        .font(.caption).foregroundStyle(.white.opacity(0.8))
                }
            case .invalid:
                Text("Check your time").font(.headline).accessibilityIdentifier("invalidTime")
                Text("Try 58.32 or 1:02.45, up to 60 minutes.").font(.caption)
            case .unavailable:
                Text("No published conversion").font(.headline).accessibilityIdentifier("unavailableConversion")
                Text("Choose another event or course comparison.").font(.caption)
            }
        }.frame(maxWidth: .infinity, alignment: .leading).padding(compact ? 16 : 24)
            .foregroundStyle(.white).background(ink, in: RoundedRectangle(cornerRadius: compact ? 20 : 24))
            .sheet(isPresented: $showingDetails) { ConversionDetails(input: input) }
    }

    private func timeLabel(_ time: String) -> some View {
        Text(time).font(.system(size: compact ? compactTimeSize : fullTimeSize, weight: .bold, design: .rounded)).monospacedDigit()
            .minimumScaleFactor(0.6).lineLimit(1).accessibilityIdentifier("resultTime")
    }

    private var detailsButton: some View {
        Button { showingDetails = true } label: { Label("Details", systemImage: "info.circle") }
            .font(.subheadline).foregroundStyle(lime).buttonStyle(.plain)
            .fixedSize(horizontal: true, vertical: false)
            .frame(minWidth: 44, minHeight: 44).accessibilityIdentifier("conversionDetails")
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
                    }
                }
            }.navigationTitle("Conversion details").navigationBarTitleDisplayMode(.inline)
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

private struct ConversionResultBar<Summary: View>: ViewModifier {
    let summary: Summary
    var pinned = true

    @ViewBuilder func body(content: Content) -> some View {
        if !pinned {
            content
        } else if #available(iOS 26.0, *) {
            content.safeAreaBar(edge: .bottom, spacing: 0) {
                summary.padding(.horizontal).padding(.vertical, 8)
            }
        } else {
            content.safeAreaInset(edge: .bottom, spacing: 0) {
                summary.padding(.horizontal).padding(.vertical, 8).background(.regularMaterial)
            }
        }
    }
}
