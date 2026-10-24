import XCTest

// Helpers only: each concrete class runs in its own simulator app container.
class TurnmarkUITestCase: XCTestCase {
    @MainActor func launch(_ extra: [String] = [], example: Bool = true) -> XCUIApplication {
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

    @MainActor func visibleKeyboard(in app: XCUIApplication) -> XCUIElement? {
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

    @MainActor func assertConverterKeyboardDismissed(in app: XCUIApplication,
        file: StaticString = #filePath, line: UInt = #line) {
        // iOS may retain a hidden keyboard AX node after a successful dismissal.
        // Assert onscreen keyboard geometry/keys and the entry toolbar are gone.
        // Keyboard key hit-testing itself is not exposed reliably by XCTest.
        let dismissed = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            let done = app.buttons["dismissConverterKeyboard"]
            return self.visibleKeyboard(in: app) == nil && !(done.exists && done.isHittable)
        }, object: nil)
        // A hosted AX query can itself take several seconds while UIKit
        // removes its keyboard node. Keep the same dismissal predicate, but
        // allow another observation after that slow snapshot. This completes
        // immediately when ready; it adds neither sleep nor a test retry.
        let result = XCTWaiter.wait(for: [dismissed], timeout: 15)
        if result != .completed {
            let keyboard = app.keyboards.firstMatch
            print("Dismissal observation: exists=\(keyboard.exists), frame=\(keyboard.exists ? keyboard.frame : .zero), keys=\(keyboard.keys.count)")
        }
        XCTAssertEqual(result, .completed, file: file, line: line)
    }

    @MainActor func entryKeyboard(in app: XCUIApplication) -> XCUIElement? {
        // Query system keyboard geometry only while an app-owned entry toolbar
        // is visible. Hosted XCTest can stall resolving a stale keyboard AX
        // snapshot after entry has ended (for example on recorded-swim detail).
        let converterDone = app.buttons["dismissConverterKeyboard"]
        let recordDone = app.buttons["dismissSwimKeyboard"]
        guard (converterDone.exists && converterDone.isHittable) ||
              (recordDone.exists && recordDone.isHittable) else { return nil }
        return visibleKeyboard(in: app)
    }

    @MainActor func reach(_ element: XCUIElement, in app: XCUIApplication, earlier: Bool = false) {
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

    @MainActor func assertTimeValue(_ text: String, in field: XCUIElement,
        file: StaticString = #filePath, line: UInt = #line) {
        // Hosted XCTest can return before the final keyboard events reach
        // SwiftUI, and a cold accessibility read can itself take several seconds.
        // Allow that read to finish; require the exact value without retyping.
        let entered = XCTNSPredicateExpectation(predicate: NSPredicate(format: "value == %@", text), object: field)
        XCTAssertEqual(XCTWaiter.wait(for: [entered], timeout: 20), .completed,
            "The full time must arrive; observed \(field.value as? String ?? "<no value>")", file: file, line: line)
    }

    @MainActor func replace(_ field: XCUIElement, with text: String, in app: XCUIApplication, earlier: Bool = false) {
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

    @MainActor func chooseCourseConversion(_ label: String, in app: XCUIApplication, open: Bool = true) {
        if open {
            let options = app.descendants(matching: .any)["calculationOptions"].firstMatch
            reach(options, in: app, earlier: true); options.tap()
        }
        let picker = app.descendants(matching: .any)["courseConversion"].firstMatch
        reach(picker, in: app, earlier: true); picker.tap()
        app.buttons[label].tap()
    }

    @MainActor func tab(_ title: String, in app: XCUIApplication) {
        let button = app.buttons[title].firstMatch
        XCTAssertTrue(button.waitForExistence(timeout: 5)); button.tap()
    }

    @MainActor func chooseBenchmark(_ label: String, in app: XCUIApplication, earlier: Bool = false) {
        let target = app.buttons["benchmarkTarget"]
        reach(target, in: app, earlier: earlier); target.tap()
        let item = app.buttons[label]
        for _ in 0..<6 where !(item.exists && item.isHittable) {
            if let anchor = ["USA Swimming · Junior Nationals", "USA Swimming · Futures", "USA Swimming · Youth"]
                .map({ app.buttons[$0] }).first(where: { $0.exists && $0.isHittable }) {
                anchor.swipeUp()
            } else {
                app.swipeUp()
            }
        }
        item.tap()
    }

    /// Taps a button in a sheet's navigation bar (Done, Save). Some devices (iPhone Duo) hide a
    /// sheet's navigation bar while its content is scrolled down, so drag the content back toward
    /// the top until the button is available. Each drag starts mid-sheet and stops as soon as the
    /// button appears, so it scrolls content rather than dismissing the sheet.
    @MainActor func tapSheetBar(_ button: XCUIElement, in app: XCUIApplication) {
        let origin = app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.4))
        for _ in 0..<8 where !(button.exists && button.isHittable) {
            origin.press(forDuration: 0.05, thenDragTo: app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.75)))
        }
        button.tap()
    }

    @MainActor func closeBenchmarks(in app: XCUIApplication) {
        tapSheetBar(app.buttons["closeBenchmarks"], in: app)
    }

    @MainActor func capture(_ app: XCUIApplication, _ name: String) {
        guard ProcessInfo.processInfo.environment["TURNMARK_SCREENSHOTS"] == "1" else { return }
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = name; screenshot.lifetime = .keepAlways; add(screenshot)
    }
}
