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
