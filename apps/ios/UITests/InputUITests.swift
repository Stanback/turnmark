import XCTest

final class InputUITests: TurnmarkUITestCase {
    @MainActor func testAltitudePoliciesKeepOriginalSwimAndPersist() {
        let app = launch(example: false)
        replace(app.textFields["timeInput"], with: "58.32", in: app)
        app.buttons["dismissConverterKeyboard"].tap()
        let options = app.descendants(matching: .any)["calculationOptions"].firstMatch
        reach(options, in: app); options.tap()
        let enabled = app.switches["altitudeEnabled"]
        reach(enabled, in: app); enabled.switches.firstMatch.tap()
        XCTAssertEqual(enabled.value as? String, "1")
        replace(app.textFields["poolElevation"], with: "5000", in: app)
        app.buttons["dismissConverterKeyboard"].tap()
        let unit = app.descendants(matching: .any)["elevationUnit"].firstMatch
        reach(unit, in: app); unit.tap(); app.buttons["Meters"].tap()
        XCTAssertEqual(app.textFields["poolElevation"].value as? String, "1524.0")
        unit.tap(); app.buttons["Feet"].tap()
        XCTAssertEqual(app.textFields["poolElevation"].value as? String, "5000")
        let policy = app.descendants(matching: .any)["altitudePolicy"].firstMatch
        reach(policy, in: app); policy.tap(); app.buttons["NCAA · 2026–27 Division I"].tap()
        reach(options, in: app, earlier: true)
        capture(app, "Native calculation options")
        reach(app.staticTexts["resultTime"], in: app)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "1:06.61")
        reach(app.buttons["conversionDetails"], in: app); app.buttons["conversionDetails"].tap()
        let ncaa = app.staticTexts["altitudeResult-ncaa-altitude-2026-27-d1"]
        reach(ncaa, in: app); XCTAssertEqual(ncaa.label, "−0.10s → 58.22")
        capture(app, "Native altitude policies")
        app.buttons["Done"].firstMatch.tap()
        reach(app.buttons["openBenchmarks"], in: app); app.buttons["openBenchmarks"].tap()
        XCTAssertEqual(app.staticTexts["benchmarkOriginalTime"].label, "58.32")
        app.buttons["benchmarkBasis"].tap(); app.buttons["Converted estimate · LCM"].tap()
        XCTAssertEqual(app.staticTexts["benchmarkEstimateTime"].label, "1:06.61")
        capture(app, "Native altitude benchmark preview")
        app.buttons["closeBenchmarks"].tap()
        app.terminate(); app.launchArguments = []; app.launch()
        let restoredElevation = app.textFields["poolElevation"]
        reach(restoredElevation, in: app)
        XCTAssertEqual(restoredElevation.value as? String, "5000")
        reach(app.staticTexts["resultTime"], in: app)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "1:06.61")
    }

    @MainActor func testTimeEntryKeepsFocusWhenTheWorkspaceRotates() {
        XCUIDevice.shared.orientation = .portrait
        defer { XCUIDevice.shared.orientation = .portrait }
        let app = launch()
        let field = app.textFields["timeInput"]
        replace(field, with: "1:00", in: app, earlier: true)
        XCUIDevice.shared.orientation = .landscapeLeft
        // Type into the existing responder, without tapping/refocusing the field.
        app.typeText(".25")
        assertTimeValue("1:00.25", in: field)
        XCUIDevice.shared.orientation = .portrait
        app.typeText(XCUIKeyboardKey.delete.rawValue)
        assertTimeValue("1:00.2", in: field)
        let done = app.buttons["dismissConverterKeyboard"]
        XCTAssertTrue(done.waitForExistence(timeout: 5)); XCTAssertNotNil(visibleKeyboard(in: app)); done.tap()
        assertConverterKeyboardDismissed(in: app)
        // Starting entry in an already-wide workspace must not collapse its
        // field when the keyboard reduces the available height.
        XCUIDevice.shared.orientation = .landscapeLeft
        replace(field, with: "58.32", in: app, earlier: true)
        XCTAssertEqual(field.value as? String, "58.32")
        XCTAssertTrue(app.descendants(matching: .any)["expandedConverter"].firstMatch.exists)
        XCTAssertTrue(done.waitForExistence(timeout: 5)); XCTAssertNotNil(visibleKeyboard(in: app)); done.tap()
        assertConverterKeyboardDismissed(in: app)
    }
}
