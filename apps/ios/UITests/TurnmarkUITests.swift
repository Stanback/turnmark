import XCTest

final class TurnmarkUITests: XCTestCase {
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
        XCTAssertTrue(app.descendants(matching: .any)["methodDifference"].firstMatch.exists)
        capture(app, "Native method comparison")
        app.buttons["Done"].firstMatch.tap()
        reach(app.buttons["resetConverter"], in: app, earlier: true); app.buttons["resetConverter"].tap()
        XCTAssertEqual(field.placeholderValue, "58.32")
        XCTAssertFalse(app.staticTexts["resultTime"].exists)
        tab("My times", in: app)
        XCTAssertTrue(app.staticTexts["No logged swims"].exists)
    }

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
        app.buttons["closeBenchmarks"].tap()
        app.terminate(); app.launchArguments = []; app.launch()
        let restoredElevation = app.textFields["poolElevation"]
        reach(restoredElevation, in: app)
        XCTAssertEqual(restoredElevation.value as? String, "5000")
        reach(app.staticTexts["resultTime"], in: app)
        XCTAssertEqual(app.staticTexts["resultTime"].label, "1:06.61")
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

    @MainActor private func launch(_ extra: [String] = [], example: Bool = true) -> XCUIApplication {
        let app = XCUIApplication()
        app.launchEnvironment["TURNMARK_UI_TESTS"] = "1"
        app.launchArguments = ["-uitesting-reset"] + (example ? ["-uitesting-example"] : []) + extra
        app.launch()
        if example {
            // Workflow cases use a deterministic debug-only fixture. The
            // dedicated arrival case exercises real typing from a blank field.
            let results = app.buttons["seeResults"]
            if !app.descendants(matching: .any)["expandedConverter"].firstMatch.exists { reach(results, in: app); results.tap() }
        }
        return app
    }
    @MainActor private func visibleKeyboard(in app: XCUIApplication) -> XCUIElement? {
        let keyboard = app.keyboards.firstMatch
        guard keyboard.exists else { return nil }
        // The system keyboard may occupy the Duo's other display, outside
        // the app's primary AX frame. Check its own geometry and key content.
        let frame = keyboard.frame
        guard frame.width > 0, frame.height > 0,
              frame.minX.isFinite, frame.minY.isFinite,
              keyboard.keys.firstMatch.exists else { return nil }
        return keyboard
    }
    @MainActor private func assertConverterKeyboardDismissed(in app: XCUIApplication,
        file: StaticString = #filePath, line: UInt = #line) {
        // iOS may retain a hidden keyboard AX node after a successful dismissal.
        // Assert onscreen keyboard geometry/keys and the entry toolbar are gone.
        // Keyboard key hit-testing itself is not exposed reliably by XCTest.
        let dismissed = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            let done = app.buttons["dismissConverterKeyboard"]
            return self.visibleKeyboard(in: app) == nil && !(done.exists && done.isHittable)
        }, object: nil)
        let result = XCTWaiter.wait(for: [dismissed], timeout: 5)
        if result != .completed {
            let keyboard = app.keyboards.firstMatch
            print("Dismissal observation: exists=\(keyboard.exists), frame=\(keyboard.exists ? keyboard.frame : .zero), keys=\(keyboard.keys.count)")
        }
        XCTAssertEqual(result, .completed, file: file, line: line)
    }
    @MainActor private func entryKeyboard(in app: XCUIApplication) -> XCUIElement? {
        // Query system keyboard geometry only while an app-owned entry toolbar
        // is visible. Hosted XCTest can stall resolving a stale keyboard AX
        // snapshot after entry has ended (for example on recorded-swim detail).
        let converterDone = app.buttons["dismissConverterKeyboard"]
        let recordDone = app.buttons["dismissSwimKeyboard"]
        guard (converterDone.exists && converterDone.isHittable) ||
              (recordDone.exists && recordDone.isHittable) else { return nil }
        return visibleKeyboard(in: app)
    }
    @MainActor private func reach(_ element: XCUIElement, in app: XCUIApplication, earlier: Bool = false) {
        // A hittable element already owns its native touch geometry. Avoid
        // repeatedly snapshotting navigation chrome during sheet transitions.
        if !earlier && element.exists && element.isHittable { return }
        // SwiftUI can retain a dismissed sheet's navigation/tab AX frames.
        // Search within the stable app viewport instead of waiting for that
        // decorative chrome to agree. The target must still be hittable with
        // its center inside content, clear of the header and floating tab bar.
        var viewport = CGRect.zero
        let settled = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            let frame = app.frame
            guard frame.width > 0, frame.height > 200,
                  frame.minX.isFinite, frame.minY.isFinite,
                  frame.maxX.isFinite, frame.maxY.isFinite else { return false }
            viewport = frame
            return true
        }, object: nil)
        guard XCTWaiter.wait(for: [settled], timeout: 5) == .completed else {
            XCTFail("App viewport must settle before scrolling"); return
        }
        var visibleTop = viewport.minY + (earlier ? min(120, viewport.height / 4) : 80)
        if earlier {
            let navigation = app.navigationBars.firstMatch
            if navigation.exists {
                let bar = navigation.frame
                // Use coherent main-window chrome when available, but never
                // let a dismissed sheet's offscreen frame block the search.
                if bar.minY.isFinite, bar.maxY.isFinite,
                   bar.minY >= viewport.minY, bar.minY < viewport.minY + viewport.height * 0.15,
                   bar.maxY > bar.minY, bar.maxY + 12 < viewport.midY {
                    visibleTop = bar.maxY + 12
                }
            }
        }
        let tabBottom = earlier ? viewport.maxY - 100 : viewport.maxY
        let nativeList = app.collectionViews.element(boundBy: max(app.collectionViews.count - 1, 0))
        let editor = app.descendants(matching: .any)["swimEditorForm"].firstMatch
        let hasEditor = editor.exists
        var keyboard = entryKeyboard(in: app)
        for attempt in 0..<16 {
            // Scrolling may dismiss an existing keyboard; it cannot summon a
            // new one. Once absent, avoid probing stale system keyboard AX.
            if attempt > 0 && keyboard != nil { keyboard = entryKeyboard(in: app) }
            // The earlier-result search must stay in the content viewport.
            // Other callers can intentionally target native toolbar buttons.
            let keyboardTop = keyboard.flatMap { element -> CGFloat? in
                let frame = element.frame
                return frame.intersects(viewport) && frame.minY > visibleTop ? frame.minY : nil
            }
            let visibleBottom = min(keyboardTop ?? viewport.maxY - 40, tabBottom) - 16
            let exists = element.exists
            let frame = exists ? element.frame : CGRect.zero
            if exists && element.isHittable {
                // XCTest may call a one-pixel sliver hittable. A tap must land
                // inside the visible form, above the keyboard and home area.
                if frame.midY > visibleTop && frame.midY < visibleBottom { return }
            }
            let container = !exists || element.identifier.isEmpty ? app.scrollViews.element(boundBy: max(app.scrollViews.count - 1, 0)) :
                app.scrollViews.containing(.any, identifier: element.identifier).firstMatch
            let collection = exists && !element.identifier.isEmpty ? app.collectionViews.containing(.any, identifier: element.identifier).firstMatch : nativeList
            let scroll = hasEditor ? editor : (container.exists ? container : (collection.exists ? collection : (nativeList.exists ? nativeList : app)))
            // A grouped Form virtualizes rows that have scrolled away. When
            // the target is absent, search both directions before failing;
            // once its row is loaded, its actual geometry chooses direction.
            let downward = exists ? frame.minY < visibleTop : earlier || attempt >= 6
            if let keyboardTop {
                // The form extends behind the keyboard. XCTest's default swipe
                // can start in its assistant bar, which never scrolls the form.
                let visible = scroll.frame.intersection(viewport)
                let done = app.buttons["dismissSwimKeyboard"]
                let bottom = min(visible.maxY, keyboardTop,
                    done.exists ? done.frame.minY : visible.maxY) - 12
                let top = max(visible.minY, viewport.minY + 140)
                let upper = top + (bottom - top) * 0.2
                let lower = top + (bottom - top) * 0.8
                let origin = app.coordinate(withNormalizedOffset: .zero)
                let start = origin.withOffset(CGVector(dx: visible.midX, dy: downward ? upper : lower))
                let end = origin.withOffset(CGVector(dx: visible.midX, dy: downward ? lower : upper))
                start.press(forDuration: 0.1, thenDragTo: end)
            } else if downward {
                // Avoid flinging past the earlier result card, whose lazy
                // Form row may otherwise retain stale AX coordinates.
                if earlier { scroll.swipeDown(velocity: .slow) }
                else { scroll.swipeDown() }
            } else { scroll.swipeUp() }
        }
        if earlier { XCTFail("Element must remain reachable inside the content viewport: \(element)") }
        else { XCTAssertTrue(element.exists && element.isHittable, "Element must remain reachable: \(element)") }
    }
    @MainActor private func assertTimeValue(_ text: String, in field: XCUIElement,
        file: StaticString = #filePath, line: UInt = #line) {
        // Hosted XCTest can return before the final keyboard events reach
        // SwiftUI. Require the entire value, without retrying the input.
        let entered = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", text), object: field)
        XCTAssertEqual(XCTWaiter.wait(for: [entered], timeout: 5), .completed,
            "The full time must arrive; observed \(field.value as? String ?? "<no value>")", file: file, line: line)
    }
    @MainActor private func replace(_ field: XCUIElement, with text: String, in app: XCUIApplication, earlier: Bool = false) {
        reach(field, in: app, earlier: earlier)
        if field.identifier == "timeInput" {
            // A center tap can place the caret before existing digits. Exercise
            // the app's real clear action instead of assuming an end caret.
            let clear = app.buttons["clearConverterTime"]
            if clear.exists { reach(clear, in: app); clear.tap() }
            else { field.tap() }
            field.typeText(text)
            assertTimeValue(text, in: field)
        } else {
            field.tap()
            field.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: (field.value as? String ?? "").count) + text)
        }
        let done = app.buttons["dismissSwimKeyboard"]
        if done.exists && done.isHittable { done.tap() }
    }
    @MainActor private func chooseCourseConversion(_ label: String, in app: XCUIApplication, open: Bool = true) {
        if open {
            let options = app.descendants(matching: .any)["calculationOptions"].firstMatch
            reach(options, in: app, earlier: true); options.tap()
        }
        let picker = app.descendants(matching: .any)["courseConversion"].firstMatch
        reach(picker, in: app, earlier: true); picker.tap()
        app.buttons[label].tap()
    }
    @MainActor private func tab(_ title: String, in app: XCUIApplication) {
        let button = app.buttons[title].firstMatch
        XCTAssertTrue(button.waitForExistence(timeout: 5)); button.tap()
    }
    @MainActor private func capture(_ app: XCUIApplication, _ name: String) {
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = name; screenshot.lifetime = .keepAlways; add(screenshot)
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
        let system = app.descendants(matching: .any)["benchmarkSystem"].firstMatch
        reach(system, in: app); system.tap(); app.buttons["USMS · Masters"].tap()
        let age = app.descendants(matching: .any)["benchmarkAge"].firstMatch
        reach(age, in: app); age.tap(); app.buttons["40–44"].tap()
        reach(app.staticTexts["benchmarkSummary"], in: app)
        XCTAssertEqual(app.staticTexts["benchmarkSummary"].label, "NQT target met")
        capture(app, "Masters benchmark")
        app.buttons["closeBenchmarks"].tap()
        app.terminate(); app.launchArguments = []; app.launch()
        reach(app.buttons["openBenchmarks"], in: app); app.buttons["openBenchmarks"].tap()
        XCTAssertTrue(app.staticTexts["40–44 · Women · SCY"].waitForExistence(timeout: 5))
        app.segmentedControls["benchmarkMode"].buttons["Points"].tap()
        XCTAssertTrue(app.staticTexts["benchmarkUnavailable"].exists)
        XCTAssertFalse(app.staticTexts["benchmarkPoints"].exists)
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
        let system = app.descendants(matching: .any)["benchmarkSystem"].firstMatch
        reach(system, in: app); system.tap(); app.buttons["USA Swimming · Futures"].tap()
        let age = app.descendants(matching: .any)["benchmarkAge"].firstMatch
        reach(age, in: app); age.tap(); app.buttons["19 & over"].tap()
        let target = app.staticTexts["benchmarkNextTime"]
        reach(target, in: app, earlier: true)
        XCTAssertTrue(app.staticTexts["49.79"].firstMatch.exists)
        let original = app.staticTexts["benchmarkOriginalTime"]
        reach(original, in: app, earlier: true)
        XCTAssertEqual(original.label, "58.32")
        reach(target, in: app)
        capture(app, "Futures original swim benchmark")
        reach(system, in: app, earlier: true); system.tap(); app.buttons["USA Swimming · Junior Nationals"].tap()
        let junior = app.staticTexts["benchmarkNextTime"]
        reach(junior, in: app, earlier: true); XCTAssertEqual(junior.label, "49.79")
        reach(system, in: app, earlier: true); system.tap(); app.buttons["NISCA · All-America"].tap()
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
        let system = app.descendants(matching: .any)["benchmarkSystem"].firstMatch
        reach(system, in: app); system.tap(); app.buttons["USMS · Masters"].tap()
        let missing = app.descendants(matching: .any)["benchmarkUnavailable"].firstMatch
        // Changing systems can preserve the settings row's scroll position.
        // SwiftUI's lazy Form may not expose the preceding state until scrolled.
        let form = app.descendants(matching: .any)["benchmarkForm"].firstMatch
        for _ in 0..<6 {
            if missing.exists && missing.isHittable { break }
            form.swipeDown()
        }
        reach(missing, in: app); XCTAssertTrue(missing.exists)
        XCTAssertTrue(missing.label.contains("No published target"))
        capture(app, "Missing Masters target large text")
        app.buttons["closeBenchmarks"].tap()
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
        app.buttons["confirmLog"].tap()
        XCTAssertTrue(app.staticTexts["59:59.99"].waitForExistence(timeout: 5))
        app.staticTexts["59:59.99"].tap()
        capture(app, "Recorded swim large text")
        reach(app.buttons["Compare this swim"], in: app); app.buttons["Compare this swim"].tap()
        reach(app.staticTexts["resultTime"], in: app)
        capture(app, "Converter long clock large text")
        reach(app.textFields["timeInput"], in: app, earlier: true)
        capture(app, "Converter large text")
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
