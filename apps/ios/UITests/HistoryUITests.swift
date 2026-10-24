import XCTest

final class HistoryUITests: TurnmarkUITestCase {
    @MainActor func testRecordingEditingComparingAndDeletingActualTimes() {
        let app = launch()
        let stroke = app.buttons["strokePicker"]
        reach(stroke, in: app, earlier: true); stroke.tap(); app.buttons["Individual medley"].tap()
        reach(app.staticTexts["unavailableConversion"], in: app)
        XCTAssertTrue(app.staticTexts["unavailableConversion"].exists)
        reach(app.buttons["logSwim"], in: app); app.buttons["logSwim"].tap()
        let date = app.textFields["logDate"]
        XCTAssertTrue(date.waitForExistence(timeout: 5))
        replace(date, with: "2026-10-17", in: app)
        replace(app.textFields["logMeet"], with: "Autumn Invitational", in: app)
        tapSheetBar(app.buttons["confirmLog"], in: app)
        tab("My times", in: app)
        XCTAssertTrue(app.staticTexts["Autumn Invitational · 2026-10-17"].exists)
        app.staticTexts["58.32"].tap()
        XCTAssertTrue(app.staticTexts["Manually logged performance"].waitForExistence(timeout: 5))
        capture(app, "Recorded swim detail")
        app.buttons["Edit swim"].tap()
        replace(app.textFields["logTime"], with: "57.99", in: app)
        replace(app.textFields["logDate"], with: "", in: app)
        tapSheetBar(app.buttons["confirmLog"], in: app)
        XCTAssertTrue(app.staticTexts["57.99"].waitForExistence(timeout: 5))
        app.buttons["Compare this swim"].tap()
        reach(app.textFields["timeInput"], in: app, earlier: true)
        XCTAssertEqual(app.textFields["timeInput"].value as? String, "57.99")
        reach(app.staticTexts["unavailableConversion"], in: app)
        XCTAssertTrue(app.staticTexts["unavailableConversion"].exists)
        app.terminate(); app.launchArguments = []; app.launch()
        tab("My times", in: app)
        XCTAssertTrue(app.staticTexts["57.99"].waitForExistence(timeout: 5))
        capture(app, "My times light")
        let appearance = XCUIDevice.shared.appearance
        XCUIDevice.shared.appearance = .dark; capture(app, "My times dark"); XCUIDevice.shared.appearance = appearance
        app.staticTexts["57.99"].tap()
        reach(app.buttons["Delete swim"], in: app); app.buttons["Delete swim"].tap()
        XCTAssertTrue(app.buttons["confirmDeleteSwim"].waitForExistence(timeout: 5))
        app.buttons["confirmDeleteSwim"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["No logged swims"].waitForExistence(timeout: 5))
    }

    @MainActor func testTimeCanBeRecordedDirectlyFromMyTimesAndFiltered() {
        let app = launch()
        tab("My times", in: app)
        app.buttons["recordTime"].tap()
        XCTAssertFalse(app.buttons["confirmLog"].isEnabled)
        replace(app.textFields["logTime"], with: "57.99", in: app)
        tapSheetBar(app.buttons["confirmLog"], in: app)
        XCTAssertTrue(app.staticTexts["57.99"].waitForExistence(timeout: 5))
        app.buttons["recordTime"].tap()
        replace(app.textFields["logTime"], with: "1:00", in: app)
        tapSheetBar(app.buttons["confirmLog"], in: app)
        XCTAssertTrue(app.staticTexts["1:00"].waitForExistence(timeout: 5))
        app.segmentedControls["timesFilter"].buttons["Best times"].tap()
        XCTAssertTrue(app.staticTexts["57.99"].exists)
        XCTAssertFalse(app.staticTexts["1:00"].exists)
        capture(app, "Best recorded times")
    }

    @MainActor func testEarlierBookmarkRemainsSeparateFromActualTimes() {
        let app = launch(["-uitesting-legacy"])
        tab("My times", in: app)
        XCTAssertTrue(app.staticTexts["No logged swims"].exists)
        let open = app.buttons["Open previous comparison"]
        reach(open, in: app); open.tap()
        let use = app.buttons["Use these inputs"]
        reach(use, in: app); use.tap()
        reach(app.textFields["timeInput"], in: app, earlier: true)
        XCTAssertEqual(app.textFields["timeInput"].value as? String, "58.32")
        tab("My times", in: app)
        reach(open, in: app); open.tap()
        let remove = app.buttons["Remove previous comparison"]
        reach(remove, in: app); remove.tap()
        app.terminate(); app.launchArguments = []; app.launch()
        tab("My times", in: app)
        XCTAssertFalse(app.buttons["Open previous comparison"].exists)
        XCTAssertTrue(app.staticTexts["No logged swims"].exists)
    }

    @MainActor func testRecordingAtAccessibilityTextSize() {
        let app = launch(["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"])
        tab("My times", in: app)
        app.buttons["recordTime"].tap()
        replace(app.textFields["logTime"], with: "59:59.99", in: app)
        replace(app.textFields["logMeet"], with: "Pacific Northwest Masters Long Course Championships", in: app)
        capture(app, "Record time large text")
        tapSheetBar(app.buttons["confirmLog"], in: app)
        XCTAssertTrue(app.staticTexts["59:59.99"].waitForExistence(timeout: 5))
        app.staticTexts["59:59.99"].tap()
        capture(app, "Recorded swim large text")
        reach(app.buttons["Compare this swim"], in: app); app.buttons["Compare this swim"].tap()
        reach(app.staticTexts["resultTime"], in: app)
        capture(app, "Converter long clock large text")
        reach(app.textFields["timeInput"], in: app, earlier: true)
        capture(app, "Converter large text")
    }

    @MainActor func testSharingCanBeCancelledWithoutRecordingATime() {
        let app = launch()
        let share = app.buttons["shareSwim"].firstMatch
        reach(share, in: app); share.tap()
        let copy = app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "Copy")).firstMatch
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == true AND hittable == true"), object: copy)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 30), .completed)
        capture(app, "Native sharing")
        let dismiss = app.descendants(matching: .any)["PopoverDismissRegion"].firstMatch
        XCTAssertTrue(dismiss.isHittable); dismiss.tap()
        let closed = XCTNSPredicateExpectation(predicate: NSPredicate(format: "exists == false"), object: copy)
        XCTAssertEqual(XCTWaiter.wait(for: [closed], timeout: 10), .completed)
        tab("My times", in: app)
        XCTAssertTrue(app.staticTexts["No logged swims"].exists)
    }
}
