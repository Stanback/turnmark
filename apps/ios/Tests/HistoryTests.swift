import XCTest
@testable import Turnmark

@MainActor final class HistoryTests: XCTestCase {
    func testLongConvertedClocksRetainMethodDifference() {
        var input = Draft.example; input.time = "60:00"
        XCTAssertEqual(input.methodDifference, "121.39s")
        XCTAssertNotNil(input.methodSpread)
        var equivalence = Draft.example; equivalence.methodID = "turnmark-empirical-2026"
        XCTAssertEqual(equivalence.methodLabel, "Turnmark Equivalence")
        if case let .available(value, _) = equivalence.outcome {
            XCTAssertEqual(equivalence.turnGeometrySummary(value.event), "100 yd SCY (3 turns) → 100 m LCM (1 turn) · −2 walls")
            XCTAssertNotNil(equivalence.methodFormulaSummary(againstNcaa: 6672))
        } else {
            XCTFail("Expected available equivalence conversion")
        }
    }
    private func fixture(_ name: String) throws -> Data {
        try Data(contentsOf: XCTUnwrap(Bundle(for: Self.self).url(forResource: name, withExtension: "json")))
    }
    private func records() throws -> [SwimRecord] { try HistoryImport.preview(fixture("contract-v1"), existing: []).records }

    func testPortableArchiveRoundTripAndDuplicatePolicy() throws {
        let records = try records(); XCTAssertEqual(records.count, 5)
        let data = try HistoryArchive.encode(records)
        XCTAssertEqual(try HistoryImport.preview(data, existing: []).records, records)
        let duplicate = try HistoryImport.preview(data, existing: records)
        XCTAssertEqual(duplicate.records.count, 0); XCTAssertEqual(duplicate.duplicates, 5)
        let twice = try HistoryArchive.encode(records + records)
        XCTAssertEqual(try HistoryImport.preview(twice, existing: []).duplicates, 5)
        var changed = records[0]; changed.time = "58.00"; changed.hundredths = 5800
        XCTAssertEqual(try HistoryImport.preview(HistoryArchive.encode([changed]), existing: records).duplicates, 1)
    }
    func testBothPlatformsValidateTheSameImportCases() throws {
        let cases = try XCTUnwrap(JSONSerialization.jsonObject(with: fixture("import-cases")) as? [[String: Any]])
        let original = try XCTUnwrap((JSONSerialization.jsonObject(with: fixture("contract-v1")) as? [String: Any])?["swims"] as? [[String: Any]]).first!
        for sample in cases {
            var row = original
            for (key, value) in sample["patch"] as! [String: Any] { row[key] = value }
            let data = try JSONSerialization.data(withJSONObject: ["format": "turnmark.swim-history", "version": 1, "swims": [row]])
            let preview = try HistoryImport.preview(data, existing: [])
            XCTAssertEqual(preview.records.count, (sample["accepted"] as! Bool) ? 1 : 0, sample["name"] as! String)
            XCTAssertEqual(preview.rejected.count, (sample["accepted"] as! Bool) ? 0 : 1, sample["name"] as! String)
        }
    }
    func testInvalidEnvelopeAndSizeLeaveStoreUnchanged() throws {
        let store = try SwimHistoryStore(inMemory: true); try store.save(records()[0])
        for text in ["{}", "[]", "{broken", "{\"format\":\"turnmark.swim-history\",\"version\":2,\"swims\":[]}", "{\"format\":\"turnmark.swim-history\",\"version\":true,\"swims\":[]}"] {
            XCTAssertThrowsError(try HistoryImport.preview(Data(text.utf8), existing: store.swims))
        }
        XCTAssertThrowsError(try HistoryImport.preview(Data(repeating: 32, count: HistoryImport.maxBytes + 1), existing: store.swims))
        XCTAssertEqual(store.swims.count, 1)
    }
    func testPersistenceEditingDeletionAndPersonalBests() throws {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: folder) }
        let url = folder.appendingPathComponent("history.store")
        let input = try records()
        do {
            let store = try SwimHistoryStore(url: url)
            XCTAssertTrue(store.swims.isEmpty)
            try store.apply(HistoryImport(records: input, duplicates: 0, rejected: []))
            XCTAssertFalse(store.isBest(input[0])); XCTAssertTrue(store.isBest(input[1]))
            XCTAssertTrue(store.isBest(input[2])); XCTAssertTrue(store.isBest(input[3])) // 400 m and 500 yd stay distinct.
        }
        let reopened = try SwimHistoryStore(url: url); XCTAssertEqual(reopened.swims.count, 5)
        var changed = input[1]; changed.time = "1:01"; changed.hundredths = 6100; changed.meet = nil; changed.date = nil
        try reopened.save(changed)
        XCTAssertEqual(reopened.swims.first { $0.id == changed.id }, changed)
        XCTAssertTrue(reopened.isBest(input[0]))
        try reopened.apply(HistoryImport.preview(HistoryArchive.encode(input), existing: reopened.swims))
        XCTAssertEqual(reopened.swims.first { $0.id == changed.id }, changed)
        try reopened.remove(changed.id); XCTAssertEqual(reopened.swims.count, 4)
        XCTAssertEqual(try SwimHistoryStore(url: url).swims.count, 4)
    }
    func testImportRollbackAndCategorySpecificBests() throws {
        let store = try SwimHistoryStore(inMemory: true)
        let rows = try records()
        var invalid = rows[1]; invalid.hundredths = 1
        XCTAssertThrowsError(try store.apply(HistoryImport(records: [rows[0], invalid], duplicates: 0, rejected: [])))
        XCTAssertTrue(store.swims.isEmpty)
        var men = rows[1]; men.category = "men"
        try store.save(rows[0]); try store.save(men)
        XCTAssertTrue(store.isBest(rows[0])); XCTAssertTrue(store.isBest(men))
        var tie = rows[1]; tie.time = rows[0].time; tie.hundredths = rows[0].hundredths
        try store.save(tie)
        XCTAssertTrue(store.isBest(rows[0])); XCTAssertTrue(store.isBest(tie))
    }
    func testActualSwimCanBeLoggedWithoutConversionAndKeepsEnteredTime() throws {
        var draft = Draft.example; draft.strokeIndex = 4
        XCTAssertFalse(draft.available); XCTAssertTrue(draft.canLog)
        let record = try draft.record(date: nil, meet: nil)
        XCTAssertEqual(record.time, draft.time); XCTAssertEqual(record.distance, 100)
        var metric = Draft.example; metric.courseIndex = 2; metric.distance = 400
        let actual = try metric.record(date: "2026-10-17", meet: "Meet")
        XCTAssertEqual(actual.distance, 400); XCTAssertEqual(actual.course, "LCM")
        metric.targetIndex = 0
        XCTAssertEqual(try metric.record(date: actual.date, meet: actual.meet, replacing: actual).id, actual.id)
    }
}
