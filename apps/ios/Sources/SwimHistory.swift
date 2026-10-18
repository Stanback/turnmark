import Foundation
import SwiftData
import TurnmarkCore

// Portable records contain only actual, user-entered swims. Comparison outputs
// never enter this store. Keep this contract aligned with apps/history/README.md.
struct SwimRecord: Codable, Equatable, Identifiable {
    let id: String
    var time: String
    var hundredths: Int64
    var distance: Int
    var stroke: String
    var course: String
    var category: String
    var date: String?
    var meet: String?
    let createdAt: Int64
    var updatedAt: Int64

    static let strokeCodes = ["FR", "BK", "BR", "FL", "IM"]
    static let strokes: [Stroke] = [.freestyle, .backstroke, .breaststroke, .butterfly, .individualMedley]
    static let strokeNames = ["Freestyle", "Backstroke", "Breaststroke", "Butterfly", "Individual medley"]
    static let courseCodes = ["SCY", "SCM", "LCM"]
    static let courses: [Course] = [.scy, .scm, .lcm]
    static var now: Int64 { Int64(Date().timeIntervalSince1970 * 1000) }
    static func day(_ date: Date) -> String {
        let parts = Calendar(identifier: .gregorian).dateComponents([.year, .month, .day], from: date)
        return String(format: "%04d-%02d-%02d", parts.year!, parts.month!, parts.day!)
    }
    static func validDay(_ text: String) -> Bool {
        guard text.count == 10, text.range(of: #"^\d{4}-\d{2}-\d{2}$"#, options: .regularExpression) != nil else { return false }
        let values = text.split(separator: "-").compactMap { Int($0) }
        guard values.count == 3, (1...9999).contains(values[0]) else { return false }
        // Foundation's Gregorian calendar has a 1582 cutover; archives use
        // proleptic Gregorian dates, matching Android's ISO LocalDate.
        let year = values[0], month = values[1], day = values[2]
        guard (1...12).contains(month) else { return false }
        let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
        let days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        return (1...days[month - 1]).contains(day)
    }
    func validated() throws -> SwimRecord {
        guard id.range(of: #"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"#, options: .regularExpression) != nil, time.utf8.count <= 32,
              let seconds = parseTime(input: time), hundredths == Int64((seconds * 100).rounded()),
              let s = Self.strokeCodes.firstIndex(of: stroke), let c = Self.courseCodes.firstIndex(of: course),
              ["women", "men"].contains(category), distance > 0, distance <= Int(UInt32.max),
              getEventOptions(course: Self.courses[c], stroke: Self.strokes[s]).contains(where: { $0.event.distance == UInt32(distance) }),
              date == nil || Self.validDay(date!),
              meet == nil || (!meet!.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && meet!.utf8.count <= 200),
              createdAt >= 0, updatedAt >= createdAt, updatedAt <= 253402300799999 else {
            throw HistoryError.message("Invalid swim, date, identifier or timestamps.")
        }
        return self
    }
    var eventLabel: String { "\(distance) \(course == "SCY" ? "yd" : "m") \(Self.strokeNames[Self.strokeCodes.firstIndex(of: stroke)!]) · \(course) · \(category == "women" ? "Women" : "Men")" }
    var comparisonKey: String { "\(distance)|\(stroke)|\(course)|\(category)" }
}

enum HistoryError: LocalizedError {
    case message(String)
    var errorDescription: String? { if case let .message(text) = self { return text }; return nil }
}

struct HistoryArchive: Codable {
    let format: String
    let version: Int
    let swims: [SwimRecord]
    init(swims: [SwimRecord]) { format = "turnmark.swim-history"; version = 1; self.swims = swims }
    static func encode(_ swims: [SwimRecord]) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(HistoryArchive(swims: swims))
        guard data.count <= HistoryImport.maxBytes, swims.count <= HistoryImport.maxRecords else {
            throw HistoryError.message("History exceeds the current export limit (25,000 swims or 10 MB).")
        }
        return data
    }
}

struct HistoryImport {
    let records: [SwimRecord]
    let duplicates: Int
    let rejected: [String]
    static let maxBytes = 10 * 1024 * 1024
    static let maxRecords = 25000

    static func preview(_ data: Data, existing: [SwimRecord]) throws -> HistoryImport {
        guard data.count <= maxBytes,
              let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              json["format"] as? String == "turnmark.swim-history",
              let version = json["version"] as? NSNumber, CFGetTypeID(version) != CFBooleanGetTypeID(), version.stringValue == "1",
              let rows = json["swims"] as? [Any], rows.count <= maxRecords else {
            throw HistoryError.message("Choose a Turnmark history v1 file (up to 10 MB and 25,000 swims). Nothing was changed.")
        }
        var ids = Set(existing.map(\.id)); var accepted: [SwimRecord] = []; var rejected: [String] = []; var duplicates = 0
        for (index, row) in rows.enumerated() {
            do {
                guard let object = row as? [String: Any] else { throw HistoryError.message("Expected a swim record.") }
                // JSONDecoder otherwise accepts JSON booleans as numbers on some runtimes.
                for key in ["hundredths", "distance", "createdAt", "updatedAt"] {
                    guard let value = object[key] as? NSNumber, CFGetTypeID(value) != CFBooleanGetTypeID(),
                          value.doubleValue.rounded() == value.doubleValue else { throw HistoryError.message("Expected whole numbers.") }
                }
                let record = try JSONDecoder().decode(SwimRecord.self, from: JSONSerialization.data(withJSONObject: object)).validated()
                if ids.insert(record.id).inserted { accepted.append(record) } else { duplicates += 1 }
            } catch { rejected.append("Record \(index + 1): invalid fields, event, time or date.") }
        }
        return HistoryImport(records: accepted, duplicates: duplicates, rejected: rejected)
    }
}

// Explicit schema version: future local migrations belong here, independently
// of the portable archive version. Payloads preserve the shared record contract.
enum HistorySchemaV1: VersionedSchema {
    static var versionIdentifier: Schema.Version { .init(1, 0, 0) }
    static var models: [any PersistentModel.Type] { [StoredSwim.self] }
    @Model final class StoredSwim {
        @Attribute(.unique) var id: String
        var payload: Data
        init(_ swim: SwimRecord) throws { id = swim.id; payload = try JSONEncoder().encode(swim) }
    }
}
enum HistoryMigration: SchemaMigrationPlan {
    static var schemas: [any VersionedSchema.Type] { [HistorySchemaV1.self] }
    static var stages: [MigrationStage] { [] }
}

@MainActor @Observable final class SwimHistoryStore {
    private let container: ModelContainer
    private(set) var swims: [SwimRecord] = []
    init(inMemory: Bool = false, url: URL? = nil) throws {
        container = try ModelContainer(for: HistorySchemaV1.StoredSwim.self, migrationPlan: HistoryMigration.self,
            configurations: url.map { ModelConfiguration(url: $0) } ?? ModelConfiguration(isStoredInMemoryOnly: inMemory))
        container.mainContext.autosaveEnabled = false
        try reload()
    }
    private func reload() throws {
        swims = try container.mainContext.fetch(FetchDescriptor<HistorySchemaV1.StoredSwim>()).map {
            try JSONDecoder().decode(SwimRecord.self, from: $0.payload).validated()
        }.sorted { ($0.date ?? "", $0.createdAt, $0.id) > ($1.date ?? "", $1.createdAt, $1.id) }
    }
    func save(_ record: SwimRecord) throws {
        let record = try record.validated()
        let context = container.mainContext
        do {
            let rows = try context.fetch(FetchDescriptor<HistorySchemaV1.StoredSwim>())
            if let row = rows.first(where: { $0.id == record.id }) { row.payload = try JSONEncoder().encode(record) }
            else { context.insert(try HistorySchemaV1.StoredSwim(record)) }
            try context.save(); try reload()
        } catch { context.rollback(); throw error }
    }
    func remove(_ id: String) throws {
        let context = container.mainContext
        do {
            for row in try context.fetch(FetchDescriptor<HistorySchemaV1.StoredSwim>()) where row.id == id { context.delete(row) }
            try context.save(); try reload()
        } catch { context.rollback(); throw error }
    }
    func apply(_ preview: HistoryImport) throws {
        let context = container.mainContext
        do {
            let ids = Set(try context.fetch(FetchDescriptor<HistorySchemaV1.StoredSwim>()).map(\.id))
            for record in preview.records where !ids.contains(record.id) { context.insert(try HistorySchemaV1.StoredSwim(record.validated())) }
            try context.save(); try reload()
        } catch { context.rollback(); throw error }
    }
    func isBest(_ swim: SwimRecord) -> Bool {
        swim.hundredths == swims.filter { $0.comparisonKey == swim.comparisonKey }.map(\.hundredths).min()
    }
}
