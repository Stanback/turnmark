import XCTest

final class TurnmarkUITests: XCTestCase {
    @MainActor func testConversionAndSavedSwimSurviveRestart() {
        let app = XCUIApplication()
        app.launchArguments = ["-uitesting-reset"]
        app.launch()
        let time = app.textFields["timeInput"]
        XCTAssertTrue(time.waitForExistence(timeout: 10))
        time.tap()
        time.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: (time.value as? String ?? "").count) + "1:00")
        app.buttons["Done"].tap()
        app.segmentedControls["inputCourse"].buttons["LCM"].tap()
        XCTAssertTrue(app.segmentedControls["inputCourse"].buttons["LCM"].isSelected)
        app.segmentedControls["targetCourse"].buttons["SCY"].tap()
        XCTAssertTrue(app.segmentedControls["targetCourse"].buttons["SCY"].isSelected)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "52.44")
        XCTAssertEqual(app.staticTexts["resultContext"].label, "100 yd Freestyle · SCY · Women")
        app.buttons["conversionDetails"].tap()
        XCTAssertTrue(app.navigationBars["Conversion details"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["100 m Freestyle · LCM · Women"].exists)
        let edition = app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "Edition:")).firstMatch
        for _ in 0..<6 {
            if edition.exists && edition.isHittable { break }
            app.swipeUp()
        }
        XCTAssertTrue(edition.exists && edition.isHittable)
        capture(app, "Conversion details")
        app.buttons["Done"].tap()
        capture(app, "Native converter")
        app.swipeUp()
        app.buttons["saveSwim"].tap()
        XCTAssertEqual(app.buttons["saveSwim"].label, "Saved")
        app.terminate()
        app.launchArguments = []
        app.launch()
        XCTAssertTrue(app.staticTexts["resultTime"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.staticTexts["resultTime"].label, "52.44")
        app.tabBars.buttons["Saved"].tap()
        XCTAssertEqual(app.staticTexts["resultTime"].label, "52.44")
        capture(app, "Saved swim")
        app.tabBars.buttons["Method"].tap()
        XCTAssertTrue(app.staticTexts["How comparisons work"].exists)
        capture(app, "Method")
        let appearance = XCUIDevice.shared.appearance
        defer { XCUIDevice.shared.appearance = appearance }
        XCUIDevice.shared.appearance = .dark
        capture(app, "Method dark")
        app.tabBars.buttons["Saved"].tap()
        capture(app, "Saved swim dark")
        app.buttons["Use this swim"].tap()
        XCTAssertEqual(app.textFields["timeInput"].value as? String, "1:00")
        capture(app, "Native converter dark")
        app.tabBars.buttons["Saved"].tap()
        app.buttons["Remove saved swim"].tap()
        XCTAssertTrue(app.staticTexts["No saved swim"].exists)
        app.terminate()
        app.launch()
        app.tabBars.buttons["Saved"].tap()
        XCTAssertTrue(app.staticTexts["No saved swim"].waitForExistence(timeout: 5))
        app.tabBars.buttons["Convert"].tap()
        app.swipeUp()
        XCTAssertEqual(app.buttons["saveSwim"].label, "Save swim")
    }

    @MainActor func testLoggingEditingComparingAndDeletingActualSwims() {
        let app = XCUIApplication()
        app.launchArguments = ["-uitesting-reset"]
        app.launch()
        XCTAssertTrue(app.textFields["timeInput"].waitForExistence(timeout: 10))
        app.buttons["strokePicker"].tap(); app.buttons["Individual medley"].tap()
        XCTAssertTrue(app.staticTexts["unavailableConversion"].exists)
        app.swipeUp(); app.buttons["logSwim"].tap()
        XCTAssertTrue(app.textFields["logDate"].waitForExistence(timeout: 5))
        replace(app.textFields["logDate"], with: "2026-10-17")
        app.textFields["logMeet"].tap(); app.textFields["logMeet"].typeText("Autumn Invitational")
        app.buttons["confirmLog"].tap()
        assertHittable(app.tabBars.buttons["History"])
        app.tabBars.buttons["History"].tap()
        XCTAssertTrue(app.staticTexts["Autumn Invitational · 2026-10-17"].exists)
        app.staticTexts["58.32"].tap()
        XCTAssertTrue(app.staticTexts["Manually logged performance"].exists)
        capture(app, "Logged swim detail")
        app.buttons["Edit swim"].tap()
        replace(app.textFields["logTime"], with: "57.99")
        replace(app.textFields["logDate"], with: "")
        app.buttons["confirmLog"].tap()
        XCTAssertTrue(app.staticTexts["57.99"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Unknown date"].exists)
        app.buttons["Compare this swim"].tap()
        assertHittable(app.textFields["timeInput"])
        XCTAssertEqual(app.textFields["timeInput"].value as? String, "57.99")
        XCTAssertTrue(app.staticTexts["unavailableConversion"].exists)
        app.tabBars.buttons["Saved"].tap()
        XCTAssertTrue(app.staticTexts["No saved swim"].exists)
        app.terminate(); app.launchArguments = []; app.launch()
        app.tabBars.buttons["History"].tap()
        XCTAssertTrue(app.staticTexts["57.99"].waitForExistence(timeout: 5))
        capture(app, "Offline swim history")
        let appearance = XCUIDevice.shared.appearance
        XCUIDevice.shared.appearance = .dark
        capture(app, "Offline swim history dark")
        XCUIDevice.shared.appearance = appearance
        app.staticTexts["57.99"].tap(); app.buttons["Delete swim"].tap()
        XCTAssertTrue(app.buttons["confirmDeleteSwim"].waitForExistence(timeout: 5))
        app.buttons["confirmDeleteSwim"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["No logged swims"].waitForExistence(timeout: 5))
    }

    @MainActor func testHistoryAtAccessibilityTextSize() {
        let app = XCUIApplication()
        app.launchArguments = ["-uitesting-reset", "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch()
        XCTAssertTrue(app.textFields["timeInput"].waitForExistence(timeout: 10))
        for _ in 0..<8 {
            if app.buttons["logSwim"].isHittable { break }
            app.swipeUp()
        }
        app.buttons["logSwim"].tap()
        XCTAssertTrue(app.buttons["confirmLog"].waitForExistence(timeout: 5))
        capture(app, "Log swim large text")
        app.buttons["confirmLog"].tap()
        assertHittable(app.tabBars.buttons["History"])
        app.tabBars.buttons["History"].tap()
        XCTAssertTrue(app.staticTexts["58.32"].waitForExistence(timeout: 5))
        capture(app, "History large text")
        app.staticTexts["58.32"].tap()
        capture(app, "Logged swim large text")
    }

    @MainActor private func replace(_ field: XCUIElement, with text: String) {
        field.tap()
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: (field.value as? String ?? "").count) + text)
    }

    @MainActor private func capture(_ app: XCUIApplication, _ name: String) {
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = name
        screenshot.lifetime = .keepAlways
        add(screenshot)
    }

    @MainActor func testSharingCanBeCancelledWithoutChangingTheSwim() {
        let app = XCUIApplication()
        app.launchArguments = ["-uitesting-reset"]
        app.launch()
        XCTAssertTrue(app.textFields["timeInput"].waitForExistence(timeout: 10))
        app.swipeUp()
        app.buttons["saveSwim"].tap()
        app.buttons["shareSwim"].tap()
        let dismiss = app.descendants(matching: .any)["PopoverDismissRegion"].firstMatch
        XCTAssertTrue(dismiss.waitForExistence(timeout: 5))
        capture(app, "Native share sheet")
        dismiss.tap()
        // The system sheet can finish its dismissal after XCTest's idle wait.
        assertHittable(app.buttons["shareSwim"])
        app.tabBars.buttons["Saved"].tap()
        app.buttons["Share saved swim"].tap()
        XCTAssertTrue(dismiss.waitForExistence(timeout: 5))
        dismiss.tap()
        assertHittable(app.buttons["Use this swim"])
        app.buttons["Use this swim"].tap()
        XCTAssertEqual(app.textFields["timeInput"].value as? String, "58.32")
    }

    @MainActor private func assertHittable(
        _ element: XCUIElement, file: StaticString = #filePath, line: UInt = #line
    ) {
        let ready = XCTNSPredicateExpectation(
            predicate: NSPredicate(format: "exists == true AND hittable == true"), object: element
        )
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 10), .completed, file: file, line: line)
    }

    @MainActor func testResultContextUsesDestinationDistanceAndCategory() {
        let app = XCUIApplication()
        app.launchArguments = ["-uitesting-reset"]
        app.launch()
        XCTAssertTrue(app.textFields["timeInput"].waitForExistence(timeout: 10))
        app.segmentedControls["inputCourse"].buttons["LCM"].tap()
        app.buttons["distancePicker"].tap()
        app.buttons["400 m"].tap()
        app.segmentedControls["category"].buttons["Men"].tap()
        app.swipeUp()
        app.segmentedControls["targetCourse"].buttons["SCY"].tap()
        XCTAssertEqual(app.staticTexts["resultContext"].label, "500 yd Freestyle · SCY · Men")
        app.segmentedControls["targetCourse"].buttons["LCM"].tap()
        XCTAssertEqual(app.staticTexts["resultContext"].label, "400 m Freestyle · LCM · Men")
        XCTAssertTrue(app.staticTexts["Entered swim"].exists)
    }

    @MainActor func testInvalidTimeDoesNotProduceResult() {
        let app = XCUIApplication()
        app.launchArguments = ["-uitesting-reset"]
        app.launch()
        let time = app.textFields["timeInput"]
        XCTAssertTrue(time.waitForExistence(timeout: 10))
        time.tap()
        time.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: (time.value as? String ?? "").count) + "0")
        app.buttons["Done"].tap()
        XCTAssertTrue(app.staticTexts["invalidTime"].exists)
        XCTAssertFalse(app.staticTexts["resultTime"].exists)
    }

    @MainActor func testUnsupportedComparisonStaysUnavailable() {
        let app = XCUIApplication()
        app.launchArguments = ["-uitesting-reset"]
        app.launch()
        app.buttons["strokePicker"].tap()
        app.buttons["Individual medley"].tap()
        XCTAssertTrue(app.staticTexts["unavailableConversion"].exists)
        XCTAssertFalse(app.staticTexts["resultTime"].exists)
    }
}
