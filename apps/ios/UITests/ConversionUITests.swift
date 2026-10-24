import XCTest

final class ConversionUITests: TurnmarkUITestCase {
    @MainActor func testBlankArrivalEntryAndResetKeepEntryFirst() {
        let app = launch(example: false)
        let field = app.textFields["timeInput"]
        XCTAssertFalse(app.buttons["tryExample"].exists, "Fresh arrival starts with direct time entry")
        XCTAssertFalse(app.staticTexts["resultTime"].exists)
        XCTAssertFalse(app.staticTexts["invalidTime"].exists)
        capture(app, "Native arrival light")
        replace(field, with: "58.32", in: app)
        app.buttons["dismissConverterKeyboard"].tap()
        XCTAssertEqual(field.value as? String, "58.32")
        capture(app, "Native input first light")
        if !app.descendants(matching: .any)["expandedConverter"].firstMatch.exists {
            reach(app.buttons["seeResults"], in: app); app.buttons["seeResults"].tap()
        }
        reach(app.buttons["equivalent-SCM"], in: app)
        XCTAssertTrue(app.buttons["equivalent-SCY"].exists)
        XCTAssertTrue(app.buttons["equivalent-LCM"].exists)
        app.buttons["equivalent-SCM"].tap()
        XCTAssertEqual(app.staticTexts["resultTime"].label, "1:05.08")
        capture(app, "Native equivalents light")
        let appearance = XCUIDevice.shared.appearance
        XCUIDevice.shared.appearance = .dark
        capture(app, "Native equivalents dark")
        XCUIDevice.shared.appearance = appearance
        reach(app.buttons["conversionDetails"], in: app); app.buttons["conversionDetails"].tap()
        XCTAssertTrue(app.staticTexts["methodResult-NCAA"].exists)
        XCTAssertTrue(app.staticTexts["methodResult-Colorado Timing"].exists)
        XCTAssertTrue(app.staticTexts["methodResult-Turnmark Equivalence"].exists)
        XCTAssertTrue(app.descendants(matching: .any)["methodDifference"].firstMatch.exists)
        capture(app, "Native method comparison")
        app.buttons["Done"].firstMatch.tap()
        reach(app.buttons["resetConverter"], in: app, earlier: true); app.buttons["resetConverter"].tap()
        XCTAssertEqual(field.placeholderValue, "58.32")
        XCTAssertFalse(app.staticTexts["resultTime"].exists)
        tab("My times", in: app)
        XCTAssertTrue(app.staticTexts["No logged swims"].exists)
    }

    @MainActor func testConversionMethodPersistsAndKeepsNcaaDefault() {
        let app = launch()
        reach(app.staticTexts["resultTime"], in: app)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "1:06.72")
        chooseCourseConversion("Colorado Timing", in: app)
        reach(app.staticTexts["resultTime"], in: app)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "1:06.33")
        capture(app, "Colorado comparison")
        app.terminate(); app.launchArguments = []; app.launch()
        reach(app.staticTexts["resultTime"], in: app)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "1:06.33")
        let details = app.buttons["conversionDetails"]
        reach(details, in: app); details.tap()
        let explanation = app.staticTexts.matching(NSPredicate(format: "label BEGINSWITH %@", "Factors vary by event and course, not age.")).firstMatch
        reach(explanation, in: app)
        capture(app, "Conversion method explanations")
        reach(app.staticTexts["Time offset: 1.6 seconds"], in: app)
        XCTAssertTrue(app.staticTexts["Time offset: 1.6 seconds"].exists)
        reach(app.staticTexts["Edition: colorado-teamunify-2026"], in: app)
        XCTAssertTrue(app.staticTexts["Edition: colorado-teamunify-2026"].exists)
        app.buttons["Done"].firstMatch.tap()
        chooseCourseConversion("NCAA (default)", in: app, open: false)
        reach(app.staticTexts["resultTime"], in: app)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "1:06.72")
    }

    @MainActor func testDistanceColoradoCaveatUsesCorrectEventContext() {
        let app = launch(example: false)
        replace(app.textFields["timeInput"], with: "4:11.36", in: app)
        app.buttons["dismissConverterKeyboard"].tap()
        let course = app.segmentedControls["inputCourse"].buttons["SCM"]
        reach(course, in: app); course.tap()
        app.buttons["distancePicker"].tap(); app.buttons["400 m"].tap()
        chooseCourseConversion("Colorado Timing", in: app)
        let scy = app.buttons["equivalent-SCY"]
        reach(scy, in: app); scy.tap()
        XCTAssertEqual(app.staticTexts["resultTime"].label, "3:46.45")
        XCTAssertTrue(app.staticTexts["resultContext"].label.contains("500 yd"))
        let note = app.staticTexts["distanceCaveat"]
        reach(note, in: app); XCTAssertTrue(note.label.contains("unequal-distance freestyle"))
        capture(app, "Native distance caveat")
    }

    @MainActor func testLowEvidenceCaveatShowsWithThinCell() {
        // Women's 200 fly, yards to short-course meters (SCY->SCM|200-FL|women), is a low-evidence cell.
        let app = launch(example: false)
        replace(app.textFields["timeInput"], with: "2:20.00", in: app)
        app.buttons["dismissConverterKeyboard"].tap()
        let stroke = app.buttons["strokePicker"]
        reach(stroke, in: app, earlier: true); stroke.tap(); app.buttons["Butterfly"].tap()
        app.buttons["distancePicker"].tap(); app.buttons["200 yd"].tap()
        chooseCourseConversion("Turnmark Equivalence", in: app)
        let scm = app.buttons["equivalent-SCM"]
        reach(scm, in: app); scm.tap()
        XCTAssertEqual(app.staticTexts["resultTime"].label, "2:36.49")
        let note = app.staticTexts["lowEvidenceCaveat"]
        reach(note, in: app); XCTAssertTrue(note.label.contains("Limited data"))
        XCTAssertFalse(app.staticTexts["distanceCaveat"].exists)
        capture(app, "Native low-evidence caveat")
    }

    @MainActor func testConversionDetailsAndDraftSurviveRestart() {
        let app = launch()
        replace(app.textFields["timeInput"], with: "1:00", in: app, earlier: true)
        if app.buttons["Done"].firstMatch.isHittable { app.buttons["Done"].firstMatch.tap() }
        else { app.textFields["timeInput"].typeText("\n") }
        let input = app.segmentedControls["inputCourse"].buttons["LCM"]
        reach(input, in: app, earlier: true); input.tap()
        let target = app.buttons["equivalent-SCY"]
        reach(target, in: app); target.tap()
        reach(app.staticTexts["resultTime"], in: app)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "52.44")
        XCTAssertEqual(app.staticTexts["resultContext"].label, "100 yd Freestyle · SCY · Women")
        let details = app.buttons["conversionDetails"].firstMatch
        reach(details, in: app); details.tap()
        let originalContext = app.staticTexts["100 m Freestyle · LCM · Women"]
        reach(originalContext, in: app)
        XCTAssertTrue(originalContext.exists)
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
        reach(app.staticTexts["resultTime"], in: app)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "52.44")
        reach(app.textFields["timeInput"], in: app, earlier: true)
        XCTAssertEqual(app.textFields["timeInput"].value as? String, "1:00")
        XCTAssertFalse(app.buttons["Saved"].exists)
        XCTAssertFalse(app.buttons["Method"].exists)
        tab("My times", in: app)
        XCTAssertTrue(app.staticTexts["No logged swims"].exists)
    }

    @MainActor func testResultContextUsesDestinationDistanceAndCategory() {
        let app = launch()
        let course = app.segmentedControls["inputCourse"].buttons["LCM"]
        reach(course, in: app, earlier: true); course.tap()
        let distance = app.buttons["distancePicker"]
        reach(distance, in: app, earlier: true); distance.tap(); app.buttons["400 m"].tap()
        let men = app.segmentedControls["category"].buttons["Men"]
        reach(men, in: app, earlier: true); men.tap()
        let target = app.buttons["equivalent-SCY"]
        reach(target, in: app); target.tap()
        XCTAssertEqual(app.staticTexts["resultContext"].label, "500 yd Freestyle · SCY · Men")
        app.buttons["equivalent-LCM"].tap()
        XCTAssertEqual(app.staticTexts["resultContext"].label, "400 m Freestyle · LCM · Men")
        XCTAssertTrue(app.staticTexts["Original time"].exists)
    }

    @MainActor func testInvalidTimeDoesNotProduceResult() {
        let app = launch()
        replace(app.textFields["timeInput"], with: "0", in: app, earlier: true)
        reach(app.staticTexts["invalidTime"], in: app)
        XCTAssertTrue(app.staticTexts["invalidTime"].exists)
        XCTAssertFalse(app.staticTexts["resultTime"].exists)
    }

    @MainActor func testUnsupportedComparisonStaysUnavailable() {
        let app = launch()
        let stroke = app.buttons["strokePicker"]
        reach(stroke, in: app, earlier: true); stroke.tap(); capture(app, "Stroke picker icons")
        app.buttons["Individual medley"].tap()
        reach(app.staticTexts["unavailableConversion"], in: app)
        XCTAssertTrue(app.staticTexts["unavailableConversion"].exists)
        XCTAssertFalse(app.staticTexts["resultTime"].exists)
    }
}
