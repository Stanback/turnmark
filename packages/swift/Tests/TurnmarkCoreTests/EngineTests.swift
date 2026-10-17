import Foundation
import XCTest
@testable import TurnmarkCore

final class EngineTests: XCTestCase {
    func testTypedConversion() {
        let request = ConversionRequest(swim: Swim(time: "1:00", event: SwimEvent(distance: 100, stroke: .freestyle, course: .lcm)), to: .scy, table: .women)
        guard case let .available(value, provenance) = convertSwim(request: request) else { return XCTFail("Unavailable conversion") }
        XCTAssertEqual(value.hundredths, 5244)
        XCTAssertEqual(provenance.id, "ncaa-2025-27")
    }

    func testPortableFixtures() throws {
        let url = Bundle.module.url(forResource: "sdk-conformance", withExtension: "json", subdirectory: "Fixtures")!
        let document = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String: Any]
        for item in document["cases"] as! [[String: Any]] {
            let input = try JSONSerialization.data(withJSONObject: item["input"]!, options: [.fragmentsAllowed])
            let output = try evaluate(operation: item["operation"] as! String, requestJson: String(data: input, encoding: .utf8)!)
            let actual = try JSONSerialization.jsonObject(with: Data(output.utf8), options: [.fragmentsAllowed])
            compare(actual, item["expected"]!, item["id"] as! String)
        }
    }

    private func compare(_ actual: Any, _ expected: Any, _ path: String) {
        if let expected = expected as? [String: Any] {
            guard let actual = actual as? [String: Any] else { return XCTFail(path) }
            for (key, value) in expected { compare(actual[key] ?? NSNull(), value, "\(path).\(key)") }
        } else if let expected = expected as? [Any] {
            guard let actual = actual as? [Any] else { return XCTFail(path) }
            XCTAssertEqual(actual.count, expected.count, path)
            for (a, e) in zip(actual, expected) { compare(a, e, path) }
        } else if let expected = expected as? NSNumber, let actual = actual as? NSNumber {
            XCTAssertEqual(actual.doubleValue, expected.doubleValue, accuracy: 1e-9, path)
        } else { XCTAssertEqual(String(describing: actual), String(describing: expected), path) }
    }
}
