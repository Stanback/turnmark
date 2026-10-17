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

#[cfg_attr(feature = "native", uniffi::export)]
pub fn convert_swim(request: ConversionRequest) -> ConversionOutcome {
    engine::convert(&json!(request)).into()
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
        _ => return Err(EngineError::UnknownOperation { operation }),
    };
    Ok(result.to_string())
}
