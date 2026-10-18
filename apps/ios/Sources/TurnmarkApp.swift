import SwiftUI
import TurnmarkCore

private let ink = Color(red: 3 / 255, green: 44 / 255, blue: 67 / 255)
private let lime = Color(red: 221 / 255, green: 245 / 255, blue: 140 / 255)
private let courseNames = ["SCY", "SCM", "LCM"]
private let courses: [Course] = [.scy, .scm, .lcm]
private let strokeNames = ["Freestyle", "Backstroke", "Breaststroke", "Butterfly", "Individual medley"]
private let strokeCodes = ["FR", "BK", "BR", "FL", "IM"]
private let strokes: [Stroke] = [.freestyle, .backstroke, .breaststroke, .butterfly, .individualMedley]

private struct Draft: Codable, Equatable {
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
    var label: String { "\(distance) \(strokeNames[strokeIndex]) · \(courseNames[courseIndex])" }
    var shareURL: URL {
        var query = URLComponents()
        query.queryItems = [
            URLQueryItem(name: "t", value: time), URLQueryItem(name: "s", value: strokeCodes[strokeIndex]),
            URLQueryItem(name: "d", value: String(options.first(where: { $0.event.distance == distance })?.canonicalDistance ?? distance)),
            URLQueryItem(name: "c", value: courseNames[courseIndex]),
            URLQueryItem(name: "g", value: categoryIndex == 0 ? "women" : "men"),
            URLQueryItem(name: "h", value: "0")]
        // Keep existing web links working until the separate domain migration.
        var url = URLComponents(string: "https://stanback.github.io/turnmark/")!
        url.percentEncodedFragment = query.percentEncodedQuery
        return url.url!
    }
}

@main
struct TurnmarkApp: App {
    var body: some Scene { WindowGroup { TurnmarkView() } }
}

private struct TurnmarkView: View {
    @State private var draft: Draft
    @State private var tab = 0
    @AppStorage("savedSwim") private var savedJSON = ""
    @FocusState private var editingTime: Bool

    init() {
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("-uitesting-reset") {
            UserDefaults.standard.removeObject(forKey: "draft")
            UserDefaults.standard.removeObject(forKey: "savedSwim")
        }
        #endif
        _draft = State(initialValue: Draft.decode(UserDefaults.standard.string(forKey: "draft")) ?? Draft())
    }
    var body: some View {
        TabView(selection: $tab) {
            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        inputCard
                        HStack {
                            Button { savedJSON = draft.encoded } label: { Label("Save swim", systemImage: "bookmark") }
                                .accessibilityIdentifier("saveSwim")
                            Spacer()
                            ShareLink(item: draft.shareURL) { Label("Share", systemImage: "square.and.arrow.up") }
                                .accessibilityIdentifier("shareSwim")
                        }.modifier(SwimActionsStyle()).disabled(!draft.available)
                        Text("Calculated on your device. Works offline.")
                            .font(.footnote).foregroundStyle(.secondary)
                    }.padding()
                }
                .modifier(ConversionResultBar(summary: resultSummary))
                .background(Color(uiColor: .systemGroupedBackground))
                .toolbar(.hidden, for: .navigationBar)
                .toolbar {
                    if editingTime { ToolbarItemGroup(placement: .keyboard) { Spacer(); Button("Done") { editingTime = false } } }
                }
            }.tabItem { Label("Convert", systemImage: "arrow.left.arrow.right") }.tag(0)
            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        if let saved = Draft.decode(savedJSON) {
                            Text(saved.label).font(.headline)
                            Text("Entered time: \(saved.time)").foregroundStyle(.secondary)
                            resultCard(saved)
                            Button("Use this swim") { draft = saved; tab = 0 }.buttonStyle(.borderedProminent)
                            ShareLink(item: saved.shareURL) { Label("Share saved swim", systemImage: "square.and.arrow.up") }
                            Button("Remove saved swim", role: .destructive) { savedJSON = "" }
                        } else {
                            ContentUnavailableView("No saved swim", systemImage: "bookmark", description: Text("Save a conversion to return to it here."))
                        }
                    }.padding()
                }.navigationTitle("Saved swim").background(Color(uiColor: .systemGroupedBackground))
            }.tabItem { Label("Saved", systemImage: "bookmark") }.tag(1)
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
                        Link("Methodology and coverage", destination: URL(string: "https://stanback.github.io/turnmark/#method")!)
                    }
                    Section("Your data") {
                        Text("Your current inputs and one saved swim stay on this device. Sharing uses a link containing the entered swim. Source links need an internet connection.")
                    }
                }.navigationTitle("The method")
            }.tabItem { Label("Method", systemImage: "info.circle") }.tag(2)
        }
        .onChange(of: draft) { _, value in UserDefaults.standard.set(value.encoded, forKey: "draft") }
        .onChange(of: draft.courseIndex) { _, _ in draft.reconcile() }
        .onChange(of: draft.strokeIndex) { _, _ in draft.reconcile() }
    }

    @ViewBuilder private var resultSummary: some View {
        VStack(alignment: .leading, spacing: 6) {
            switch draft.outcome {
            case let .available(value, source):
                HStack(alignment: .center) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("\(courseNames[draft.courseIndex]) → \(courseNames[draft.targetIndex])").font(.subheadline.bold())
                        Text(value.kind == .swum ? "Entered swim" : value.kind == .published ? "Published factor" : "Derived estimate").font(.caption)
                    }.foregroundStyle(lime)
                    Spacer()
                    Text(value.time).font(.system(size: 34, weight: .bold, design: .rounded)).monospacedDigit()
                        .minimumScaleFactor(0.6).lineLimit(1).accessibilityIdentifier("resultTime")
                }
                Text(source.title).font(.caption2).foregroundStyle(.white.opacity(0.8))
            case .invalid:
                Text("Check your time").font(.headline).accessibilityIdentifier("invalidTime")
                Text("Try 58.32 or 1:02.45, up to 60 minutes.").font(.caption)
            case .unavailable:
                Text("No published conversion").font(.headline).accessibilityIdentifier("unavailableConversion")
                Text("Choose another event or course comparison.").font(.caption)
            }
        }.frame(maxWidth: .infinity, alignment: .leading).padding(16)
            .foregroundStyle(.white).background(ink, in: RoundedRectangle(cornerRadius: 20))
    }

    private var inputCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Your time").font(.headline)
            TextField("58.32", text: $draft.time)
                .font(.system(size: 42, weight: .semibold, design: .rounded)).monospacedDigit()
                .keyboardType(.numbersAndPunctuation).focused($editingTime)
                .accessibilityLabel("Your time").accessibilityIdentifier("timeInput")
            Text("Minutes : seconds . hundredths").font(.caption).foregroundStyle(.secondary)
            HStack {
                Picker("Stroke", selection: $draft.strokeIndex) {
                    ForEach(strokeNames.indices, id: \.self) { Text(strokeNames[$0]).tag($0) }
                }.accessibilityIdentifier("strokePicker").layoutPriority(1)
                Spacer()
                Picker("Distance", selection: $draft.distance) {
                    ForEach(draft.options, id: \.event.distance) { Text(String($0.event.distance)).tag($0.event.distance) }
                }.accessibilityIdentifier("distancePicker").fixedSize(horizontal: true, vertical: false)
            }
            Text("Swum in").font(.subheadline.bold())
            Picker("Swum in", selection: $draft.courseIndex) {
                ForEach(courseNames.indices, id: \.self) { Text(courseNames[$0]).tag($0) }
            }.pickerStyle(.segmented).accessibilityIdentifier("inputCourse")
            Picker("Published category", selection: $draft.categoryIndex) {
                Text("Women").tag(0); Text("Men").tag(1)
            }.pickerStyle(.segmented).accessibilityIdentifier("category")
            Text("Compare with").font(.subheadline.bold())
            Picker("Compare with", selection: $draft.targetIndex) {
                ForEach(courseNames.indices, id: \.self) { Text(courseNames[$0]).tag($0) }
            }.pickerStyle(.segmented).accessibilityIdentifier("targetCourse")
        }.padding(20).background(Color(uiColor: .secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 24))
    }

    @ViewBuilder private func resultCard(_ input: Draft) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("\(courseNames[input.courseIndex]) → \(courseNames[input.targetIndex])").font(.subheadline.weight(.semibold))
            }.foregroundStyle(lime)
            switch input.outcome {
            case let .available(value, source):
                Text(value.time).font(.system(size: 48, weight: .bold, design: .rounded)).monospacedDigit()
                    .minimumScaleFactor(0.6).lineLimit(1).accessibilityIdentifier("resultTime")
                Text("\(value.event.distance) \(strokeNames[input.strokeIndex]) · \(courseNames[input.targetIndex])")
                Text(value.kind == .swum ? "Entered swim" : value.kind == .published ? "Published factor" : "Derived estimate")
                    .font(.subheadline.bold()).foregroundStyle(lime)
                Divider().overlay(.white.opacity(0.2))
                Text("\(source.title) · \(source.id)").font(.caption).foregroundStyle(.white.opacity(0.8))
            case .invalid:
                Text("Check your time").font(.title2.bold()).accessibilityIdentifier("invalidTime")
                Text("Enter a positive time such as 58.32 or 1:02.45, up to 60 minutes.")
            case .unavailable:
                Text("No published conversion").font(.title2.bold()).accessibilityIdentifier("unavailableConversion")
                Text("This event or course has no published NCAA factor. Choose another comparison.")
            }
        }.frame(maxWidth: .infinity, alignment: .leading).padding(24)
            .foregroundStyle(.white).background(ink, in: RoundedRectangle(cornerRadius: 24))
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

    @ViewBuilder func body(content: Content) -> some View {
        if #available(iOS 26.0, *) {
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
