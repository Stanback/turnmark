//! Offline authoritative engine. Native bindings are typed; the JSON entry point
//! supplies the identical validation contract to JavaScript and conformance tools.
mod compat;
mod engine;
mod types;
use serde_json::{json, Value};
pub use types::*;

#[cfg(feature = "native")]
uniffi::setup_scaffolding!();

#[derive(Debug, thiserror::Error)]
#[cfg_attr(feature = "native", derive(uniffi::Error))]
pub enum EngineError {
    #[error("Malformed JSON: {detail}")]
    MalformedJson { detail: String },
    #[error("Unknown operation: {operation}")]
    UnknownOperation { operation: String },
    #[error("Invalid compatibility request: {detail}")]
    InvalidCompatibilityRequest { detail: String },
}

#[cfg_attr(feature = "native", uniffi::export)]
pub fn engine_version() -> String {
    env!("CARGO_PKG_VERSION").to_owned()
}

#[cfg_attr(feature = "native", uniffi::export)]
pub fn parse_time(input: String) -> Option<f64> {
    engine::parse_time(&input)
}

/// Published input events and their legacy web-link distance, from the core's
/// event definitions. Native controls and share adapters must not reimplement
/// the 400/500, 800/1000 or 1500/1650 mappings.
#[cfg_attr(feature = "native", uniffi::export)]
pub fn get_event_options(course: Course, stroke: Stroke) -> Vec<EventOption> {
    engine::event_distances(stroke)
        .iter()
        .filter_map(|&distance| {
            let event = SwimEvent {
                distance: engine::actual_distance(distance, course, stroke),
                stroke,
                course,
            };
            engine::published(&event, distance).then_some(EventOption {
                event,
                canonical_distance: distance,
            })
        })
        .collect()
}

#[cfg_attr(feature = "native", uniffi::export)]
pub fn convert_swim(request: ConversionRequest) -> ConversionOutcome {
    engine::convert(&json!(request)).into()
}
/// Explicit alternative method. The original typed entry point remains NCAA.
#[cfg_attr(feature = "native", uniffi::export)]
pub fn convert_swim_with_method(
    request: ConversionRequest,
    method: ConversionMethod,
) -> ConversionOutcome {
    let mut input = json!(request);
    input["method"] = json!(method);
    engine::convert(&input).into()
}
#[cfg_attr(feature = "native", uniffi::export)]
pub fn adjust_altitude(request: AltitudeRequest) -> AltitudeOutcome {
    engine::altitude(&json!(request)).into()
}
#[cfg_attr(feature = "native", uniffi::export)]
pub fn get_youth_standards(request: StandardsRequest) -> YouthOutcome {
    engine::youth(&json!(request)).into()
}
#[cfg_attr(feature = "native", uniffi::export)]
pub fn get_masters_target(request: StandardsRequest) -> MastersOutcome {
    engine::masters(&json!(request)).into()
}
#[cfg_attr(feature = "native", uniffi::export)]
pub fn get_world_points(request: PointsRequest) -> PointsOutcome {
    engine::points(&json!(request)).into()
}

#[cfg_attr(feature = "native", uniffi::export)]
pub fn assess_swim_benchmark(request: BenchmarkRequest) -> BenchmarkOutcome {
    engine::benchmark(&json!(request)).into()
}

#[cfg_attr(feature = "native", uniffi::export)]
pub fn get_standard_age_groups(system: StandardSystem) -> Vec<String> {
    engine::standard_age_groups(system)
}

/// Invalid requests return structured outcomes. Malformed JSON and unknown
/// operation names are transport errors, rather than calculation results.
#[cfg_attr(feature = "native", uniffi::export)]
pub fn evaluate(operation: String, request_json: String) -> Result<String, EngineError> {
    let request: Value =
        serde_json::from_str(&request_json).map_err(|e| EngineError::MalformedJson {
            detail: e.to_string(),
        })?;
    let result = match operation.as_str() {
        "compat" => compat::evaluate(&request)?,
        "parse" => json!(request.as_str().and_then(engine::parse_time)),
        "convert" => json!(ConversionOutcome::from(engine::convert(&request))),
        "altitude" => json!(AltitudeOutcome::from(engine::altitude(&request))),
        "youth" => json!(YouthOutcome::from(engine::youth(&request))),
        "masters" => json!(MastersOutcome::from(engine::masters(&request))),
        "points" => json!(PointsOutcome::from(engine::points(&request))),
        "benchmark" => json!(BenchmarkOutcome::from(engine::benchmark(&request))),
        _ => return Err(EngineError::UnknownOperation { operation }),
    };
    Ok(result.to_string())
}
