//! Transport for the existing web UI's numeric times and canonical distances.
//! All calculation paths reuse the same engine as the typed native APIs.
use crate::{engine, types::*, EngineError};
use serde::de::DeserializeOwned;
use serde_json::{json, Value};

fn bad(detail: &str) -> EngineError {
    EngineError::InvalidCompatibilityRequest {
        detail: detail.into(),
    }
}
fn arg<T: DeserializeOwned>(args: &[Value], index: usize) -> Result<T, EngineError> {
    serde_json::from_value(args.get(index).cloned().unwrap_or(Value::Null))
        .map_err(|_| bad(&format!("argument {index}")))
}
fn stroke(args: &[Value], index: usize) -> Result<Stroke, EngineError> {
    match args.get(index).and_then(Value::as_str) {
        Some("FR") => Ok(Stroke::Freestyle),
        Some("BK") => Ok(Stroke::Backstroke),
        Some("BR") => Ok(Stroke::Breaststroke),
        Some("FL") => Ok(Stroke::Butterfly),
        Some("IM") => Ok(Stroke::IndividualMedley),
        _ => Err(bad("stroke code")),
    }
}
fn event(distance: u32, course: Course, stroke: Stroke) -> SwimEvent {
    SwimEvent {
        distance: engine::actual_distance(distance, course, stroke),
        course,
        stroke,
    }
}
pub(crate) fn evaluate(input: &Value) -> Result<Value, EngineError> {
    let operation = input["operation"]
        .as_str()
        .ok_or_else(|| bad("operation"))?;
    let args = input["args"].as_array().ok_or_else(|| bad("args"))?;
    Ok(match operation {
        "eventDistances" => json!(engine::event_distances(stroke(args, 0)?)),
        "eventDistance" => json!(engine::actual_distance(
            arg(args, 0)?,
            arg(args, 1)?,
            stroke(args, 2)?
        )),
        "availableEvent" => {
            let distance = arg(args, 0)?;
            json!(engine::published(
                &event(distance, arg(args, 1)?, stroke(args, 2)?),
                distance
            ))
        }
        "toYardFactor" => {
            let distance = arg(args, 1)?;
            let event = event(distance, arg(args, 2)?, stroke(args, 0)?);
            json!(if engine::published(&event, distance) {
                engine::factor(&event, distance, arg(args, 3)?)
            } else {
                None
            })
        }
        "altitudeAdjustment" => json!(engine::altitude_adjustment(
            arg(args, 0)?,
            arg::<Option<f64>>(args, 1)?.unwrap_or(f64::NAN)
        )),
        "adjustedTime" => {
            let seconds = arg::<Option<f64>>(args, 0)?;
            let feet = arg::<Option<f64>>(args, 2)?;
            let adjustment = engine::altitude_adjustment(arg(args, 1)?, feet.unwrap_or(f64::NAN));
            json!(seconds
                .filter(|s| *s > adjustment
                    && feet.is_some_and(|v| (0.0..=20000.0).contains(&v) && v.fract() == 0.0))
                .map(|s| engine::adjusted_seconds(s, adjustment)))
        }
        "truncateTime" => json!(engine::truncate(
            arg::<Option<f64>>(args, 0)?.unwrap_or(f64::NAN)
        )),
        "formatTime" => {
            let seconds = arg::<Option<f64>>(args, 0)?;
            let round = args.get(1).and_then(Value::as_bool).unwrap_or(false);
            json!(
                match seconds.filter(|s| s.is_finite() && *s >= 0.0 && *s <= 90_071_992_547_409.0) {
                    Some(seconds) => engine::format_time(if round {
                        (seconds * 100.0).round() / 100.0
                    } else {
                        seconds
                    }),
                    None => "—".into(),
                }
            )
        }
        "convert" => {
            let distance = arg(args, 2)?;
            let result = engine::convert_seconds(
                event(distance, arg(args, 3)?, stroke(args, 1)?),
                distance,
                arg::<Option<f64>>(args, 0)?.unwrap_or(f64::NAN),
                arg(args, 4)?,
                arg(args, 5)?,
            );
            match result {
                Ok((value, _)) => {
                    json!({"time": value.seconds, "factor": value.factor, "kind": value.kind})
                }
                Err(failure) => {
                    json!({"time": null, "factor": null, "kind": "unavailable", "reason": match failure {
                        Failure::Unavailable { reason: CoverageReason::EventNotPublished, .. } => "100 IM is a short-course event.",
                        Failure::Unavailable { .. } => "No published NCAA long-course factor for this event.",
                        _ => "Enter a valid positive time.",
                    }})
                }
            }
        }
        "getStandards" | "getMastersEntry" => {
            let request = json!({"age": arg::<String>(args, 0)?, "table": arg::<Category>(args, 1)?,
                "event": event(arg(args, 3)?, arg(args, 2)?, stroke(args, 4)?)});
            if operation == "getStandards" {
                json!(engine::youth(&request).ok().map(|(value, _)| value.times))
            } else {
                match engine::masters(&request) {
                    Ok((value, _)) => json!({"entry": value.seconds}),
                    Err(Failure::Unavailable {
                        reason: CoverageReason::NoTimePublished,
                        ..
                    }) => json!({"entry": null}),
                    _ => json!({}),
                }
            }
        }
        "standardStatus" => {
            let time = arg::<Option<f64>>(args, 0)?.unwrap_or(f64::NAN);
            let times: Vec<f64> = arg(args, 1)?;
            let achieved = engine::achieved_standard(time, &times)
                .map(|index| index as i32)
                .unwrap_or(-1);
            json!({"achieved": achieved, "next": if achieved < 5 { Some(achieved + 1) } else { None }})
        }
        "worldPoints" | "worldPointsContext" => {
            let result = engine::points_seconds(
                event(arg(args, 2)?, arg(args, 1)?, stroke(args, 3)?),
                arg::<Option<f64>>(args, 0)?.unwrap_or(f64::NAN),
                arg(args, 4)?,
            );
            match result {
                Ok((value, _)) if operation == "worldPoints" => json!(value.points),
                Ok((value, _)) => {
                    json!({"base": value.base_seconds, "nextMark": value.next_milestone.points,
                    "target": value.next_milestone.seconds, "gap": value.next_milestone.gap_seconds})
                }
                _ => Value::Null,
            }
        }
        _ => {
            return Err(EngineError::UnknownOperation {
                operation: format!("compat.{operation}"),
            })
        }
    })
}
