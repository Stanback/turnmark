import XCTest

final class TurnmarkUITests: XCTestCase {
    @MainActor private func launch(_ extra: [String] = []) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchArguments = ["-uitesting-reset"] + extra
        app.launch()
        return app
    }
    @MainActor private func reach(_ element: XCUIElement, in app: XCUIApplication) {
        for _ in 0..<10 {
            if element.exists && element.isHittable { return }
            let container = !element.exists || element.identifier.isEmpty ? app.scrollViews.element(boundBy: max(app.scrollViews.count - 1, 0)) :
                app.scrollViews.containing(.any, identifier: element.identifier).firstMatch
            let nativeList = app.collectionViews.element(boundBy: max(app.collectionViews.count - 1, 0))
            let editor = app.descendants(matching: .any)["swimEditorForm"].firstMatch
            let scroll = editor.exists ? editor : (container.exists ? container : (nativeList.exists ? nativeList : app))
            if element.exists && element.frame.minY < app.frame.minY + 80 { scroll.swipeDown() }
            else { scroll.swipeUp() }
        }
        XCTAssertTrue(element.exists && element.isHittable, "Element must remain reachable: \(element)")
    }
    @MainActor private func replace(_ field: XCUIElement, with text: String, in app: XCUIApplication) {
        reach(field, in: app); field.tap()
        field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: (field.value as? String ?? "").count) + text)
        let done = app.buttons["dismissSwimKeyboard"]
        if done.exists && done.isHittable { done.tap() }
    }
    @MainActor private func tab(_ title: String, in app: XCUIApplication) {
        let button = app.buttons[title].firstMatch
        XCTAssertTrue(button.waitForExistence(timeout: 5)); button.tap()
    }
    @MainActor private func capture(_ app: XCUIApplication, _ name: String) {
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = name; screenshot.lifetime = .keepAlways; add(screenshot)
    }

    @MainActor func testConversionDetailsAndDraftSurviveRestart() {
        let app = launch()
        replace(app.textFields["timeInput"], with: "1:00", in: app)
        if app.buttons["Done"].firstMatch.isHittable { app.buttons["Done"].firstMatch.tap() }
        else { app.textFields["timeInput"].typeText("\n") }
        let input = app.segmentedControls["inputCourse"].buttons["LCM"]
        reach(input, in: app); input.tap()
        let target = app.segmentedControls["targetCourse"].buttons["SCY"]
        reach(target, in: app); target.tap()
        XCTAssertEqual(app.staticTexts["resultTime"].label, "52.44")
        XCTAssertEqual(app.staticTexts["resultContext"].label, "100 yd Freestyle · SCY · Women")
        let details = app.buttons["conversionDetails"].firstMatch
        reach(details, in: app); details.tap()
        XCTAssertTrue(app.staticTexts["100 m Freestyle · LCM · Women"].waitForExistence(timeout: 5))
        let edition = app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "Edition:")).firstMatch
        reach(edition, in: app); capture(app, "Conversion details")
        let done = app.buttons["Done"].firstMatch
        reach(done, in: app); done.tap()
        reach(app.staticTexts["resultTime"], in: app); capture(app, "Converter result light")
        let appearance = XCUIDevice.shared.appearance
        XCUIDevice.shared.appearance = .dark
        capture(app, "Converter result dark")
        XCUIDevice.shared.appearance = appearance
        app.terminate(); app.launchArguments = []; app.launch()
        XCTAssertEqual(app.staticTexts["resultTime"].label, "52.44")
        XCTAssertEqual(app.textFields["timeInput"].value as? String, "1:00")
        XCTAssertFalse(app.buttons["Saved"].exists)
        XCTAssertFalse(app.buttons["Method"].exists)
        tab("My times", in: app)
        XCTAssertTrue(app.staticTexts["No logged swims"].exists)
    }

    @MainActor func testRecordingEditingComparingAndDeletingActualTimes() {
        let app = launch()
        let stroke = app.buttons["strokePicker"]
        reach(stroke, in: app); stroke.tap(); app.buttons["Individual medley"].tap()
        XCTAssertTrue(app.staticTexts["unavailableConversion"].exists)
        reach(app.buttons["logSwim"], in: app); app.buttons["logSwim"].tap()
        let date = app.textFields["logDate"]
        XCTAssertTrue(date.waitForExistence(timeout: 5))
        replace(date, with: "2026-10-17", in: app)
        replace(app.textFields["logMeet"], with: "Autumn Invitational", in: app)
        app.buttons["confirmLog"].tap()
        tab("My times", in: app)
        XCTAssertTrue(app.staticTexts["Autumn Invitational · 2026-10-17"].exists)
        app.staticTexts["58.32"].tap()
        XCTAssertTrue(app.staticTexts["Manually logged performance"].waitForExistence(timeout: 5))
        capture(app, "Recorded swim detail")
        app.buttons["Edit swim"].tap()
        replace(app.textFields["logTime"], with: "57.99", in: app)
        replace(app.textFields["logDate"], with: "", in: app)
        app.buttons["confirmLog"].tap()
        XCTAssertTrue(app.staticTexts["57.99"].waitForExistence(timeout: 5))
        app.buttons["Compare this swim"].tap()
        XCTAssertEqual(app.textFields["timeInput"].value as? String, "57.99")
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
        app.buttons["confirmLog"].tap()
        XCTAssertTrue(app.staticTexts["57.99"].waitForExistence(timeout: 5))
        app.buttons["recordTime"].tap()
        replace(app.textFields["logTime"], with: "1:00", in: app)
        app.buttons["confirmLog"].tap()
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
        app.buttons["confirmLog"].tap()
        XCTAssertTrue(app.staticTexts["59:59.99"].waitForExistence(timeout: 5))
        app.staticTexts["59:59.99"].tap()
        capture(app, "Recorded swim large text")
        reach(app.buttons["Compare this swim"], in: app); app.buttons["Compare this swim"].tap()
        reach(app.staticTexts["resultTime"], in: app)
        capture(app, "Converter long clock large text")
        reach(app.textFields["timeInput"], in: app)
        capture(app, "Converter large text")
    }

    @MainActor func testTimeEntryKeepsFocusWhenTheWorkspaceRotates() {
        XCUIDevice.shared.orientation = .portrait
        defer { XCUIDevice.shared.orientation = .portrait }
        let app = launch()
        let field = app.textFields["timeInput"]
        replace(field, with: "1:00", in: app)
        XCUIDevice.shared.orientation = .landscapeLeft
        // Type into the existing responder, without tapping/refocusing the field.
        app.typeText(".25")
        XCTAssertEqual(field.value as? String, "1:00.25")
        XCUIDevice.shared.orientation = .portrait
        app.typeText(XCUIKeyboardKey.delete.rawValue)
        XCTAssertEqual(field.value as? String, "1:00.2")
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

    @MainActor func testResultContextUsesDestinationDistanceAndCategory() {
        let app = launch()
        let course = app.segmentedControls["inputCourse"].buttons["LCM"]
        reach(course, in: app); course.tap()
        let distance = app.buttons["distancePicker"]
        reach(distance, in: app); distance.tap(); app.buttons["400 m"].tap()
        let men = app.segmentedControls["category"].buttons["Men"]
        reach(men, in: app); men.tap()
        let target = app.segmentedControls["targetCourse"].buttons["SCY"]
        reach(target, in: app); target.tap()
        XCTAssertEqual(app.staticTexts["resultContext"].label, "500 yd Freestyle · SCY · Men")
        app.segmentedControls["targetCourse"].buttons["LCM"].tap()
        XCTAssertEqual(app.staticTexts["resultContext"].label, "400 m Freestyle · LCM · Men")
        XCTAssertTrue(app.staticTexts["Original time"].exists)
    }

    @MainActor func testInvalidTimeDoesNotProduceResult() {
        let app = launch()
        replace(app.textFields["timeInput"], with: "0", in: app)
        XCTAssertTrue(app.staticTexts["invalidTime"].exists)
        XCTAssertFalse(app.staticTexts["resultTime"].exists)
    }
    @MainActor func testUnsupportedComparisonStaysUnavailable() {
        let app = launch()
        let stroke = app.buttons["strokePicker"]
        reach(stroke, in: app); stroke.tap(); app.buttons["Individual medley"].tap()
        XCTAssertTrue(app.staticTexts["unavailableConversion"].exists)
        XCTAssertFalse(app.staticTexts["resultTime"].exists)
    }
}
