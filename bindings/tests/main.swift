import Foundation

let event = SwimEvent(distance: 100, stroke: .freestyle, course: .lcm)
let conversion = convertSwim(request: ConversionRequest(swim: Swim(time: "1:00", event: event), to: .scy, table: .women))
guard case let .available(value, source) = conversion else { fatalError("Typed conversion failed") }
precondition(value.hundredths == 5244 && source.id == "ncaa-2025-27")
guard case .invalid = convertSwim(request: ConversionRequest(swim: Swim(time: "garbage", event: event), to: .scy, table: .women)) else { fatalError("Invalid time was accepted") }
guard case let .available(points, _) = getWorldPoints(request: PointsRequest(swim: Swim(time: "51.71", event: event), table: .women)) else { fatalError("Points unavailable") }
precondition(points.points == 1000)
guard case let .unavailable(reason, _) = getMastersTarget(request: StandardsRequest(event: SwimEvent(distance: 200, stroke: .butterfly, course: .lcm), table: .women, age: "18-24")) else { fatalError("Missing USMS target invented") }
precondition(reason == .noTimePublished)
guard case let .available(youth, _) = getYouthStandards(request: StandardsRequest(event: SwimEvent(distance: 100, stroke: .freestyle, course: .scy), table: .women, age: "11-12")) else { fatalError("Youth standards unavailable") }
precondition(youth.times.count == 6)
guard case let .available(altitude, _) = adjustAltitude(request: AltitudeRequest(swim: Swim(time: "2:00", event: SwimEvent(distance: 200, stroke: .freestyle, course: .scy)), elevation: Elevation(value: 3000, unit: .feet))) else { fatalError("Altitude unavailable") }
precondition(altitude.adjustedSeconds == 119.5)
do {
    _ = try evaluate(operation: "convert", requestJson: "{")
    fatalError("Malformed transport accepted")
} catch is EngineError { }

// Input: operation TAB base64(JSON). Output: one JSON result per line.
while let line = readLine() {
    let parts = line.split(separator: "\t", maxSplits: 1)
    let data = Data(base64Encoded: String(parts[1]))!
    let request = String(data: data, encoding: .utf8)!
    print(try evaluate(operation: String(parts[0]), requestJson: request))
}
