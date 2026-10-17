import uniffi.turnmark_core.*
import java.util.Base64

fun main() {
    val event = SwimEvent(100u, Stroke.FREESTYLE, Course.LCM)
    val converted = convertSwim(ConversionRequest(Swim("1:00", event), Course.SCY, Category.WOMEN))
    check(converted is ConversionOutcome.Available && converted.value.hundredths == 5244uL && converted.provenance.id == "ncaa-2025-27")
    check(convertSwim(ConversionRequest(Swim("garbage", event), Course.SCY, Category.WOMEN)) is ConversionOutcome.Invalid)
    val points = getWorldPoints(PointsRequest(Swim("51.71", event), Category.WOMEN))
    check(points is PointsOutcome.Available && points.value.points == 1000uL)
    val masters = getMastersTarget(StandardsRequest(SwimEvent(200u, Stroke.BUTTERFLY, Course.LCM), Category.WOMEN, "18-24"))
    check(masters is MastersOutcome.Unavailable && masters.reason == CoverageReason.NO_TIME_PUBLISHED)
    val youth = getYouthStandards(StandardsRequest(SwimEvent(100u, Stroke.FREESTYLE, Course.SCY), Category.WOMEN, "11-12"))
    check(youth is YouthOutcome.Available && youth.value.times.size == 6)
    val altitude = adjustAltitude(AltitudeRequest(Swim("2:00", SwimEvent(200u, Stroke.FREESTYLE, Course.SCY)), Elevation(3000.0, ElevationUnit.FEET)))
    check(altitude is AltitudeOutcome.Available && altitude.value.adjustedSeconds == 119.5)
    try {
        evaluate("convert", "{")
        error("Malformed transport accepted")
    } catch (_: EngineException) { }

    generateSequence(::readlnOrNull).forEach { line ->
        val parts = line.split('\t', limit = 2)
        val request = String(Base64.getDecoder().decode(parts[1]), Charsets.UTF_8)
        println(evaluate(parts[0], request))
    }
}
