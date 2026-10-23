import XCTest

final class BenchmarkUITests: TurnmarkUITestCase {
    @MainActor func testBenchmarkPreviewScoresEstimateAndKeepsOriginal() {
        let app = launch()
        chooseCourseConversion("Colorado Timing", in: app)
        reach(app.buttons["openBenchmarks"], in: app); app.buttons["openBenchmarks"].tap()
        chooseBenchmark("World Aquatics points", in: app)
        XCTAssertTrue(app.staticTexts["benchmarkUnavailable"].exists)
        let basis = app.buttons["benchmarkBasis"]
        reach(basis, in: app, earlier: true); basis.tap()
        app.buttons["Converted estimate · LCM"].tap()
        XCTAssertEqual(app.staticTexts["benchmarkEstimateTime"].label, "1:06.33")
        XCTAssertEqual(app.staticTexts["benchmarkEstimateContext"].label, "100 m Freestyle · LCM · Women")
        reach(app.staticTexts["benchmarkPoints"], in: app)
        XCTAssertTrue(app.staticTexts["benchmarkPoints"].exists)
        capture(app, "Converted estimate points preview")
        reach(app.staticTexts["benchmarkOriginalTime"], in: app, earlier: true)
        XCTAssertEqual(app.staticTexts["benchmarkOriginalTime"].label, "58.32")
        app.buttons["closeBenchmarks"].tap()
        reach(app.buttons["openBenchmarks"], in: app); app.buttons["openBenchmarks"].tap()
        XCTAssertFalse(app.staticTexts["benchmarkEstimateTime"].exists)
        XCTAssertTrue(app.staticTexts["benchmarkUnavailable"].exists)
    }

    @MainActor func testBenchmarkPreviewUnavailableDoesNotSubstituteEnteredTime() {
        let app = launch()
        let stroke = app.buttons["strokePicker"]
        reach(stroke, in: app, earlier: true); stroke.tap(); app.buttons["Individual medley"].tap()
        reach(app.buttons["openBenchmarks"], in: app); app.buttons["openBenchmarks"].tap()
        app.buttons["benchmarkBasis"].tap(); app.buttons["Converted estimate · LCM"].tap()
        XCTAssertTrue(app.staticTexts["benchmarkPreviewUnavailable"].exists)
        XCTAssertFalse(app.staticTexts["benchmarkSummary"].exists)
        XCTAssertFalse(app.staticTexts["benchmarkPoints"].exists)
    }

    @MainActor func testBenchmarksUseOriginalSwimAndRememberAgeSettings() {
        let app = launch()
        let brand = app.descendants(matching: .any)["converterBrand"].firstMatch
        let menu = app.buttons["converterMenu"]
        XCTAssertTrue(brand.exists)
        XCTAssertGreaterThan(brand.frame.width, 90,
            "Ordinary text must show the wordmark as well as the wave")
        XCTAssertLessThan(abs(brand.frame.midY - menu.frame.midY), 12,
            "The compact wordmark and overflow must share the native toolbar row")
        menu.tap(); app.buttons["converterAbout"].tap()
        XCTAssertTrue(app.staticTexts["How comparisons work"].waitForExistence(timeout: 5))
        app.buttons["Done"].firstMatch.tap()
        let benchmarkAction = app.buttons["openBenchmarks"]
        XCTAssertTrue(benchmarkAction.waitForExistence(timeout: 5))
        XCTAssertLessThan(benchmarkAction.frame.height, 80,
            "The ordinary-text benchmark action must not stretch its grouped Form row")
        capture(app, "Converter default")
        reach(app.buttons["openBenchmarks"], in: app); app.buttons["openBenchmarks"].tap()
        XCTAssertEqual(app.staticTexts["benchmarkOriginalTime"].label, "58.32")
        XCTAssertEqual(app.staticTexts["benchmarkSummary"].label, "A standard")
        capture(app, "Youth standards summary")
        XCUIDevice.shared.orientation = .landscapeLeft
        XCTAssertEqual(app.staticTexts["benchmarkOriginalTime"].label, "58.32")
        XCUIDevice.shared.orientation = .portrait
        XCTAssertEqual(app.staticTexts["benchmarkSummary"].label, "A standard")
        let aaaa = app.descendants(matching: .any)["benchmark-level-AAAA"].firstMatch
        reach(aaaa, in: app); capture(app, "Youth standards targets")
        let system = app.buttons["benchmarkTarget"]
        reach(system, in: app, earlier: true); system.tap()
        capture(app, "Unified benchmark choices")
        app.buttons["USMS · Masters"].tap()
        let age = app.buttons["benchmarkAge"]
        reach(age, in: app); age.tap(); app.buttons["40–44"].tap()
        reach(app.staticTexts["benchmarkSummary"], in: app)
        XCTAssertEqual(app.staticTexts["benchmarkSummary"].label, "NQT target met")
        capture(app, "Masters benchmark")
        app.buttons["closeBenchmarks"].tap()
        app.terminate(); app.launchArguments = []; app.launch()
        reach(app.buttons["openBenchmarks"], in: app); app.buttons["openBenchmarks"].tap()
        XCTAssertTrue(app.staticTexts["40–44 · Women · SCY"].waitForExistence(timeout: 5))
        chooseBenchmark("World Aquatics points", in: app, earlier: true)
        XCTAssertTrue(app.staticTexts["benchmarkUnavailable"].exists)
        XCTAssertFalse(app.staticTexts["benchmarkPoints"].exists)
        chooseBenchmark("USMS · Masters", in: app, earlier: true)
        XCTAssertTrue(app.staticTexts["40–44 · Women · SCY"].exists, "Switching to points must preserve the standard's age")
        chooseBenchmark("World Aquatics points", in: app, earlier: true)
        capture(app, "Points unavailable for yards")
        app.buttons["closeBenchmarks"].tap()
        let course = app.segmentedControls["inputCourse"].buttons["LCM"]
        reach(course, in: app, earlier: true); course.tap()
        reach(app.buttons["openBenchmarks"], in: app); app.buttons["openBenchmarks"].tap()
        XCTAssertEqual(app.staticTexts["benchmarkPoints"].label, "697")
        capture(app, "World Aquatics points")
    }

    @MainActor func testRecordedBenchmarkKeepsActualCategoryAndTime() {
        let app = launch()
        replace(app.textFields["timeInput"], with: "1:00.25", in: app, earlier: true)
        let done = app.buttons["dismissConverterKeyboard"]
        if done.waitForExistence(timeout: 3) && done.isHittable {
            XCTAssertNotNil(visibleKeyboard(in: app)); done.tap()
        }
        else { app.textFields["timeInput"].typeText("\n") }
        assertConverterKeyboardDismissed(in: app)
        capture(app, "Converter keyboard dismissed before recording")
        let category = app.segmentedControls["category"]
        reach(category, in: app, earlier: true); category.buttons["Men"].tap()
        reach(app.buttons["logSwim"], in: app); app.buttons["logSwim"].tap()
        XCTAssertTrue(app.buttons["confirmLog"].waitForExistence(timeout: 5)); app.buttons["confirmLog"].tap()
        tab("My times", in: app); app.staticTexts["1:00.25"].tap()
        reach(app.buttons["recordBenchmarks"], in: app); app.buttons["recordBenchmarks"].tap()
        XCTAssertEqual(app.staticTexts["benchmarkOriginalTime"].label, "1:00.25")
        XCTAssertEqual(app.staticTexts["benchmarkContext"].label, "100 yd Freestyle · SCY · Men")
        XCTAssertEqual(app.staticTexts["benchmarkOriginLabel"].label, "Recorded swim")
        capture(app, "Recorded swim standards")
        app.buttons["closeBenchmarks"].tap()
        XCTAssertTrue(app.staticTexts["Manually logged performance"].exists)
    }

    @MainActor func testNationalBenchmarksKeepOriginalSwimAndAgeTable() {
        let app = launch()
        let open = app.buttons["openBenchmarks"]
        reach(open, in: app); open.tap()
        let system = app.buttons["benchmarkTarget"]
        reach(system, in: app); system.tap(); app.buttons["USA Swimming · Futures"].tap()
        let age = app.buttons["benchmarkAge"]
        reach(age, in: app); age.tap(); app.buttons["19 & over"].tap()
        let target = app.staticTexts["benchmarkNextTime"]
        reach(target, in: app, earlier: true)
        XCTAssertTrue(app.staticTexts["49.79"].firstMatch.exists)
        let original = app.staticTexts["benchmarkOriginalTime"]
        reach(original, in: app, earlier: true)
        XCTAssertEqual(original.label, "58.32")
        reach(target, in: app)
        capture(app, "Futures original swim benchmark")
        chooseBenchmark("USA Swimming · Junior Nationals", in: app, earlier: true)
        let junior = app.staticTexts["benchmarkNextTime"]
        reach(junior, in: app, earlier: true); XCTAssertEqual(junior.label, "49.79")
        chooseBenchmark("NISCA · All-America", in: app, earlier: true)
        let consideration = app.descendants(matching: .any)["benchmark-level-Consideration"].firstMatch
        reach(consideration, in: app, earlier: true); XCTAssertTrue(consideration.exists)
        XCTAssertTrue(app.descendants(matching: .any)["benchmark-level-All-America time"].firstMatch.exists)
        XCTAssertFalse(age.exists)
        capture(app, "NISCA original swim thresholds")
        app.buttons["closeBenchmarks"].tap()
    }

    @MainActor func testBenchmarkMissingTargetAtAccessibilityTextSize() {
        let app = launch(["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"])
        let clock = app.staticTexts["resultTime"]
        reach(clock, in: app)
        XCTAssertGreaterThanOrEqual(clock.frame.minX, app.frame.minX)
        XCTAssertLessThanOrEqual(clock.frame.maxX, app.frame.maxX)
        capture(app, "Converter result largest text")
        let course = app.segmentedControls["inputCourse"].buttons["LCM"]
        reach(course, in: app, earlier: true); course.tap()
        let stroke = app.buttons["strokePicker"]
        reach(stroke, in: app, earlier: true); stroke.tap(); app.buttons["Butterfly"].tap()
        let distance = app.buttons["distancePicker"]
        reach(distance, in: app, earlier: true); distance.tap(); app.buttons["200 m"].tap()
        let benchmarkAction = app.buttons["openBenchmarks"]
        // Entry precedes the result on phones; both must remain reachable at
        // accessibility sizes without shrinking text or hiding course rows.
        reach(benchmarkAction, in: app)
        XCTAssertGreaterThanOrEqual(benchmarkAction.frame.minX, app.frame.minX)
        XCTAssertLessThanOrEqual(benchmarkAction.frame.maxX, app.frame.maxX)
        benchmarkAction.tap()
        guard app.staticTexts["benchmarkContext"].waitForExistence(timeout: 5) else {
            XCTFail("Standards & points must open the original-swim sheet")
            return
        }
        XCTAssertEqual(app.staticTexts["benchmarkContext"].label, "200 m Butterfly · LCM · Women")
        chooseBenchmark("USMS · Masters", in: app)
        let missing = app.staticTexts["benchmarkUnavailable"]
        // Changing systems can preserve the settings row's scroll position.
        // SwiftUI's lazy Form may not expose the preceding state until scrolled.
        let form = app.collectionViews["benchmarkForm"]
        for _ in 0..<6 {
            if missing.exists && missing.isHittable { break }
            form.swipeDown()
        }
        reach(missing, in: app); XCTAssertTrue(missing.exists)
        XCTAssertTrue(missing.label.contains("No published target"))
        capture(app, "Missing Masters target large text")
        app.buttons["closeBenchmarks"].tap()
    }
}
