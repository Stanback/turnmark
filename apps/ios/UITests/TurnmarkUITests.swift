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
        app.swipeUp()
        XCTAssertTrue(app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "Edition:")).firstMatch.exists)
        capture(app, "Conversion details")
        app.buttons["Done"].tap()
        capture(app, "Native converter")
        app.swipeUp()
        app.buttons["saveSwim"].tap()
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
    }

    @MainActor private func capture(_ app: XCUIApplication, _ name: String) {
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = name
        screenshot.lifetime = .keepAlways
        add(screenshot)
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
