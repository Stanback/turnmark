import SwiftUI
import UniformTypeIdentifiers
import TurnmarkCore

extension Draft {
    var canLog: Bool { parseTime(input: time) != nil }
    init(record: SwimRecord, target: Int = 2) {
        time = record.time; strokeIndex = SwimRecord.strokeCodes.firstIndex(of: record.stroke)!
        distance = UInt32(record.distance); courseIndex = SwimRecord.courseCodes.firstIndex(of: record.course)!
        categoryIndex = record.category == "women" ? 0 : 1; targetIndex = target
    }
    func record(date: String?, meet: String?, replacing old: SwimRecord? = nil) throws -> SwimRecord {
        guard let seconds = parseTime(input: time) else { throw HistoryError.message("Enter a valid time, such as 58.32 or 1:02.45.") }
        if let date, !SwimRecord.validDay(date) { throw HistoryError.message("Use a real date in YYYY-MM-DD, or leave it blank.") }
        if let meet, meet.utf8.count > 200 { throw HistoryError.message("Use a shorter meet name.") }
        let now = SwimRecord.now
        return try SwimRecord(id: old?.id ?? UUID().uuidString.lowercased(), time: time,
            hundredths: Int64((seconds * 100).rounded()), distance: Int(distance),
            stroke: SwimRecord.strokeCodes[strokeIndex], course: courseNames[courseIndex],
            category: categoryIndex == 0 ? "women" : "men", date: date,
            meet: meet.flatMap { $0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : $0.trimmingCharacters(in: .whitespacesAndNewlines) },
            createdAt: old?.createdAt ?? now, updatedAt: max(now, old?.createdAt ?? 0)).validated()
    }
}

@MainActor @Observable final class HistoryController {
    var store: SwimHistoryStore?
    var error: String?
    func open() {
        do { store = try SwimHistoryStore(); error = nil }
        catch { self.error = "History could not be opened. Your stored data has not been replaced. Try again or export from an earlier working version." }
    }
}

struct HistoryDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.json] }
    var data: Data
    init(data: Data = Data()) { self.data = data }
    init(configuration: ReadConfiguration) throws { data = configuration.file.regularFileContents ?? Data() }
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper { FileWrapper(regularFileWithContents: data) }
}

struct SwimEditor: View {
    @Environment(\.dismiss) private var dismiss
    @State var draft: Draft
    var original: SwimRecord? = nil
    @State var date: String
    @State var meet: String
    let save: (SwimRecord) throws -> Void
    @State private var error: String?
    @FocusState private var timeFocused: Bool
    var body: some View {
        NavigationStack {
            Form {
                Section("Actual swim") {
                    TextField("Time", text: $draft.time).keyboardType(.numbersAndPunctuation)
                        .focused($timeFocused).accessibilityIdentifier("logTime")
                    Picker("Stroke", selection: $draft.strokeIndex) {
                        ForEach(strokeNames.indices, id: \.self) { Text(strokeNames[$0]).tag($0) }
                    }
                    Picker("Course", selection: $draft.courseIndex) {
                        ForEach(courseNames.indices, id: \.self) { Text(courseNames[$0]).tag($0) }
                    }
                    Picker("Distance", selection: $draft.distance) {
                        ForEach(draft.options, id: \.event.distance) { Text("\($0.event.distance) \(draft.unit)").tag($0.event.distance) }
                    }
                    Picker("Category", selection: $draft.categoryIndex) { Text("Women").tag(0); Text("Men").tag(1) }
                    Text("Records your entered time. Converted estimates never count as personal bests.").font(.footnote).foregroundStyle(.secondary)
                }
                Section {
                    TextField("YYYY-MM-DD", text: $date).accessibilityLabel("Swim date").accessibilityIdentifier("logDate")
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    TextField("Meet name (optional)", text: $meet).accessibilityIdentifier("logMeet")
                } header: { Text("When and where") } footer: {
                    Text("Use YYYY-MM-DD, or leave the date blank if unknown. Leave meet blank for practice or a time trial.")
                }
                if let error { Section { Text(error).foregroundStyle(.red).accessibilityIdentifier("logError") } }
            }.navigationTitle(original == nil ? "Log swim" : "Edit swim").navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Save") {
                            do { try save(draft.record(date: date.isEmpty ? nil : date, meet: meet, replacing: original)); dismiss() }
                            catch { self.error = error.localizedDescription }
                        }.accessibilityIdentifier("confirmLog").disabled(!draft.canLog)
                    }
                    ToolbarItemGroup(placement: .keyboard) { Spacer(); Button("Done") { timeFocused = false } }
                }
                .onChange(of: draft.courseIndex) { _, _ in draft.reconcile() }
                .onChange(of: draft.strokeIndex) { _, _ in draft.reconcile() }
        }
    }
}

private struct HistoryGroup: Identifiable {
    let date: String?
    let meet: String?
    var swims: [SwimRecord]
    var id: String { (date ?? "unknown") + "|" + (meet ?? "") }
    var title: String { [meet, date ?? "Unknown date"].compactMap { $0 }.joined(separator: " · ") }
}

struct HistoryScreen: View {
    let controller: HistoryController
    let compare: (SwimRecord) -> Void
    @State private var selected: SwimRecord?
    @State private var importing = false
    @State private var exporting = false
    @State private var document = HistoryDocument()
    @State private var preview: HistoryImport?
    @State private var message: String?
    @State private var showingMessage = false
    private var groups: [HistoryGroup] {
        var result: [HistoryGroup] = []
        for swim in controller.store?.swims ?? [] {
            if let i = result.firstIndex(where: { $0.date == swim.date && $0.meet == swim.meet }) { result[i].swims.append(swim) }
            else { result.append(HistoryGroup(date: swim.date, meet: swim.meet, swims: [swim])) }
        }
        return result
    }
    var body: some View {
        List {
            if let error = controller.error {
                Section { Text(error); Button("Try again") { controller.open() } }
            } else if groups.isEmpty {
                ContentUnavailableView("No logged swims", systemImage: "list.bullet.rectangle",
                    description: Text("Enter an actual time in Convert, then choose Log swim. Saved conversions stay separate."))
            }
            forGroups
            Section {
                Text("Actual swims only. Personal bests compare the same distance, stroke, course and category.")
                Text("Stored on this device. Export a copy to keep a backup or move to another phone.")
            }.font(.footnote).foregroundStyle(.secondary)
        }.navigationTitle("History")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Menu {
                        Button("Export history", systemImage: "square.and.arrow.up") {
                            do {
                                document = HistoryDocument(data: try HistoryArchive.encode(controller.store?.swims ?? [])); exporting = true
                            } catch { report(error) }
                        }.disabled(controller.store == nil || controller.store?.swims.isEmpty == true)
                        Button("Import history", systemImage: "square.and.arrow.down") { importing = true }.disabled(controller.store == nil)
                    } label: { Label("History files", systemImage: "ellipsis.circle") }.accessibilityIdentifier("historyFiles")
                }
            }
            .sheet(item: $selected) { record in
                SwimDetail(record: record, controller: controller, compare: { compare($0); selected = nil })
            }
            .fileExporter(isPresented: $exporting, document: document, contentType: .json, defaultFilename: "turnmark-history") { result in
                if case let .failure(error) = result { report(error) }
            }
            .fileImporter(isPresented: $importing, allowedContentTypes: [.json]) { result in
                do {
                    let url = try result.get(); let scoped = url.startAccessingSecurityScopedResource()
                    defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                    let handle = try FileHandle(forReadingFrom: url); defer { try? handle.close() }
                    let data = try handle.read(upToCount: HistoryImport.maxBytes + 1) ?? Data()
                    preview = try HistoryImport.preview(data, existing: controller.store?.swims ?? [])
                } catch { report(error) }
            }
            .sheet(isPresented: Binding(get: { preview != nil }, set: { if !$0 { preview = nil } })) {
                if let preview { ImportReview(preview: preview) {
                    guard let store = controller.store else { throw HistoryError.message("History is unavailable.") }
                    try store.apply(preview); self.preview = nil
                    message = "Imported \(preview.records.count) swims. Existing records were kept."; showingMessage = true
                } }
            }
            .alert("History", isPresented: $showingMessage) { Button("OK", role: .cancel) {} } message: { Text(message ?? "") }
    }
    private var forGroups: some View {
        ForEach(groups) { group in
            Section(group.title) {
                ForEach(group.swims) { swim in
                    Button { selected = swim } label: {
                        VStack(alignment: .leading, spacing: 6) {
                            HStack(alignment: .firstTextBaseline) {
                                Text(swim.time).font(.title2.bold()).monospacedDigit()
                                if controller.store?.isBest(swim) == true { Text("PB").font(.caption.bold()).foregroundStyle(.secondary) }
                            }
                            Text(swim.eventLabel).font(.subheadline).foregroundStyle(.secondary)
                        }.foregroundStyle(.primary).padding(.vertical, 4)
                    }.buttonStyle(.plain).accessibilityIdentifier("history-\(swim.id)")
                }
            }
        }
    }
    private func report(_ error: Error) { message = error.localizedDescription; showingMessage = true }
}

private struct ImportReview: View {
    let preview: HistoryImport
    let apply: () throws -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var error: String?
    var body: some View {
        NavigationStack {
            List {
                Text("\(preview.records.count) new swims · \(preview.duplicates) duplicates · \(preview.rejected.count) rejected")
                Text("Existing records are kept, even when an imported record with the same ID has changed. Import never overwrites a swim.")
                ForEach(Array(preview.rejected.enumerated()), id: \.offset) { _, reason in Text(reason).font(.footnote) }
                ForEach(preview.records) { Text("\($0.time) · \($0.eventLabel)\n\($0.date ?? "Unknown date") · \($0.meet ?? "No meet")") }
                if let error { Text(error).foregroundStyle(.red) }
            }.navigationTitle("Review import").navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                    ToolbarItem(placement: .confirmationAction) { Button("Import") {
                        do { try apply() } catch { self.error = error.localizedDescription }
                    }.disabled(preview.records.isEmpty) }
                }
        }
    }
}

private struct SwimDetail: View {
    let record: SwimRecord
    let controller: HistoryController
    let compare: (SwimRecord) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var editing = false
    @State private var deleting = false
    @State private var error: String?
    private var current: SwimRecord { controller.store?.swims.first { $0.id == record.id } ?? record }
    var body: some View {
        NavigationStack {
            List {
                Section("Actual swim") {
                    Text(current.time).font(.largeTitle.bold()).monospacedDigit()
                    Text(current.eventLabel)
                    if controller.store?.isBest(current) == true { Label("Personal best", systemImage: "checkmark") }
                    Text(current.date ?? "Unknown date"); Text(current.meet ?? "No meet")
                    Text("Manually logged performance").font(.footnote).foregroundStyle(.secondary)
                }
                Section {
                    Button("Compare this swim") { compare(current) }
                    Button("Edit swim") { editing = true }
                    Button("Delete swim", role: .destructive) { deleting = true }
                }
                if let error { Text(error).foregroundStyle(.red) }
            }.navigationTitle("Logged swim").navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
                .sheet(isPresented: $editing) {
                    SwimEditor(draft: Draft(record: current), original: current, date: current.date ?? "", meet: current.meet ?? "") {
                        guard let store = controller.store else { throw HistoryError.message("History is unavailable.") }; try store.save($0)
                    }
                }
                .confirmationDialog("Delete this logged swim?", isPresented: $deleting, titleVisibility: .visible) {
                    Button("Delete swim", role: .destructive) {
                        do { try controller.store?.remove(current.id); dismiss() } catch { self.error = error.localizedDescription }
                    }.accessibilityIdentifier("confirmDeleteSwim")
                }
        }
    }
}
