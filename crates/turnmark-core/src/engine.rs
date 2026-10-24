use crate::types::*;
use serde_json::{json, Value};
use std::sync::LazyLock;

// Snapshots are immutable and embedded: no network, filesystem or platform API.
const YOUTH_AGES: [&str; 5] = ["10u", "11-12", "13-14", "15-16", "17-18"];

static CONVERSIONS: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/conversions.json")));
static COLORADO: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/colorado.json")));
static EMPIRICAL: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/empirical.json")));
static SOURCES: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/sources.json")));
static YOUTH: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/standards.json")));
static MASTERS: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/masters.json")));
static NATIONAL: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/national-standards.json")));
static POINTS: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/points.json")));

fn snapshot(input: &str) -> Value {
    serde_json::from_str(input).expect("checked-in snapshot must be valid JSON")
}
fn invalid(field: &str, reason: ValidationReason) -> Failure {
    Failure::Invalid {
        field: field.to_owned(),
        reason,
    }
}
fn unavailable(reason: CoverageReason, provenance: Provenance) -> Failure {
    Failure::Unavailable {
        reason,
        provenance: Box::new(provenance),
    }
}
fn object(input: &Value, field: &str) -> Result<(), Failure> {
    input
        .as_object()
        .map(|_| ())
        .ok_or_else(|| invalid(field, ValidationReason::InvalidInput))
}
fn category(input: &Value) -> Result<Category, Failure> {
    match input.as_str() {
        Some("women") => Ok(Category::Women),
        Some("men") => Ok(Category::Men),
        _ => Err(invalid("table", ValidationReason::InvalidCategory)),
    }
}
fn course(input: &Value, field: &str) -> Result<Course, Failure> {
    match input.as_str() {
        Some("SCY") => Ok(Course::SCY),
        Some("SCM") => Ok(Course::SCM),
        Some("LCM") => Ok(Course::LCM),
        _ => Err(invalid(field, ValidationReason::InvalidCourse)),
    }
}
fn course_key(course: Course) -> &'static str {
    match course {
        Course::SCY => "SCY",
        Course::SCM => "SCM",
        Course::LCM => "LCM",
    }
}
fn category_key(category: Category) -> &'static str {
    match category {
        Category::Women => "women",
        Category::Men => "men",
    }
}
fn stroke_key(stroke: Stroke) -> &'static str {
    match stroke {
        Stroke::Freestyle => "FR",
        Stroke::Backstroke => "BK",
        Stroke::Breaststroke => "BR",
        Stroke::Butterfly => "FL",
        Stroke::IndividualMedley => "IM",
    }
}
pub(crate) fn actual_distance(distance: u32, course: Course, stroke: Stroke) -> u32 {
    if course == Course::SCY && stroke == Stroke::Freestyle {
        match distance {
            400 => 500,
            800 => 1000,
            1500 => 1650,
            _ => distance,
        }
    } else {
        distance
    }
}
fn event(input: &Value, field: &str) -> Result<(SwimEvent, u32), Failure> {
    object(input, field)?;
    let course = course(&input["course"], &format!("{field}.course"))?;
    let stroke = match input["stroke"].as_str() {
        Some("freestyle") => Stroke::Freestyle,
        Some("backstroke") => Stroke::Backstroke,
        Some("breaststroke") => Stroke::Breaststroke,
        Some("butterfly") => Stroke::Butterfly,
        Some("individual-medley") => Stroke::IndividualMedley,
        _ => {
            return Err(invalid(
                &format!("{field}.stroke"),
                ValidationReason::InvalidStroke,
            ))
        }
    };
    let distances = event_distances(stroke);
    // as_f64 also accepts JSON 100.0, just as the JavaScript number contract does.
    let distance = distances
        .iter()
        .copied()
        .find(|d| {
            input["distance"].as_f64() == Some(f64::from(actual_distance(*d, course, stroke)))
        })
        .ok_or_else(|| {
            invalid(
                &format!("{field}.distance"),
                ValidationReason::InvalidDistance,
            )
        })?;
    Ok((
        SwimEvent {
            distance: actual_distance(distance, course, stroke),
            stroke,
            course,
        },
        distance,
    ))
}
fn swim(input: &Value) -> Result<(SwimEvent, u32, f64), Failure> {
    object(input, "swim")?;
    let seconds = input["time"]
        .as_str()
        .and_then(parse_time)
        .ok_or_else(|| invalid("swim.time", ValidationReason::InvalidTime))?;
    let (event, distance) = event(&input["event"], "swim.event")?;
    Ok((event, distance, seconds))
}
pub(crate) fn published(event: &SwimEvent, distance: u32) -> bool {
    !(event.stroke == Stroke::IndividualMedley && distance == 100 && event.course == Course::LCM)
}

pub(crate) fn parse_time(input: &str) -> Option<f64> {
    // Match ECMAScript trim, including BOM and excluding Unicode NEL, so imported
    // text has the same meaning in existing links and every generated library.
    let value = input.trim_matches(|c| {
        matches!(c,
        '\u{0009}'..='\u{000d}' | '\u{0020}' | '\u{00a0}' | '\u{1680}' |
        '\u{2000}'..='\u{200a}' | '\u{2028}' | '\u{2029}' | '\u{202f}' |
        '\u{205f}' | '\u{3000}' | '\u{feff}')
    });
    let parts: Vec<_> = value.split(':').collect();
    if parts.is_empty() || parts.len() > 2 {
        return None;
    }
    let clock = parts.last()?;
    let seconds_parts: Vec<_> = clock.split('.').collect();
    let digits = |s: &str| !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit());
    if seconds_parts.len() > 2 || !digits(seconds_parts[0]) {
        return None;
    }
    if seconds_parts.len() == 2 && (!digits(seconds_parts[1]) || seconds_parts[1].len() > 2) {
        return None;
    }
    let seconds: f64 = clock.parse().ok()?;
    let total = if parts.len() == 2 {
        if !digits(parts[0]) || seconds >= 60.0 {
            return None;
        }
        parts[0].parse::<f64>().ok()? * 60.0 + seconds
    } else {
        seconds
    };
    (total.is_finite() && total > 0.0 && total <= 3600.0).then_some(total)
}
pub(crate) fn truncate(seconds: f64) -> f64 {
    (seconds * 100.0 + 1e-8).floor() / 100.0
}
pub(crate) fn format_time(seconds: f64) -> String {
    let ticks = (seconds * 100.0 + 1e-8).floor() as u64;
    let minutes = ticks / 6000;
    let seconds = ticks / 100 % 60;
    let hundredths = ticks % 100;
    if minutes > 0 {
        format!("{minutes}:{seconds:02}.{hundredths:02}")
    } else {
        format!("{seconds}.{hundredths:02}")
    }
}
fn text(value: &Value) -> String {
    value.as_str().expect("snapshot string").to_owned()
}
fn provenance(data: &Value, id: &str, title: &str, revision: &str) -> Provenance {
    let source = &data["source"];
    Provenance {
        id: id.to_owned(),
        title: text(&source[title]),
        url: text(&source["url"]),
        revision: text(&source[revision]),
        sha256: source["sha256"].as_str().map(str::to_owned),
        verified: None,
    }
}
fn conversion_provenance() -> Provenance {
    let source = &CONVERSIONS["conversionSource"];
    Provenance {
        id: "ncaa-2025-27".to_owned(),
        title: text(&source["title"]),
        url: text(&source["url"]),
        revision: text(&source["revision"]),
        sha256: Some(text(&SOURCES["ncaa"]["sha256"])),
        verified: Some(text(&source["verified"])),
    }
}
pub(crate) fn factor(event: &SwimEvent, distance: u32, table: Category) -> Option<f64> {
    match event.course {
        Course::SCY => Some(1.0),
        Course::SCM => Some(if event.stroke == Stroke::Freestyle {
            CONVERSIONS["shortCourseFactors"]["freestyle"][distance.to_string()]
                .as_f64()
                .unwrap_or_else(|| {
                    CONVERSIONS["shortCourseFactors"]["default"]
                        .as_f64()
                        .unwrap()
                })
        } else {
            CONVERSIONS["shortCourseFactors"]["default"]
                .as_f64()
                .unwrap()
        }),
        Course::LCM => CONVERSIONS["longCourseFactors"][category_key(table)]
            [format!("{distance}-{}", stroke_key(event.stroke))]
        .as_f64(),
    }
}
pub(crate) fn convert(input: &Value) -> Calculation<ConversionValue> {
    object(input, "request")?;
    let method = conversion_method(input.get("method"))?;
    let to = course(&input["to"], "to")?;
    let table = category(&input["table"])?;
    let (event, distance, seconds) = swim(&input["swim"])?;
    let altitude = if input.get("elevation").is_some() {
        let (value, provenance) = altitude(&json!({
            "swim": input["swim"], "elevation": input["elevation"],
            "policy": input.get("altitudePolicy").cloned().unwrap_or(json!("usa-swimming-altitude-2026"))
        }))?;
        Some(AltitudeCalculation { value, provenance })
    } else {
        if input.get("altitudePolicy").is_some() {
            return Err(invalid("elevation", ValidationReason::InvalidElevation));
        }
        None
    };
    let seconds = altitude
        .as_ref()
        .map_or(seconds, |a| a.value.adjusted_seconds);
    let (mut value, provenance) =
        convert_seconds_with_method(event, distance, seconds, to, table, method)?;
    value.altitude = altitude;
    Ok((value, provenance))
}

pub(crate) fn conversion_method(input: Option<&Value>) -> Result<ConversionMethod, Failure> {
    match input {
        None => Ok(ConversionMethod::Ncaa),
        Some(value) => serde_json::from_value(value.clone())
            .map_err(|_| invalid("method", ValidationReason::UnsupportedMethod)),
    }
}

pub(crate) fn convert_seconds_with_method(
    event: SwimEvent,
    distance: u32,
    seconds: f64,
    to: Course,
    table: Category,
    method: ConversionMethod,
) -> Calculation<ConversionValue> {
    let provenance = match method {
        ConversionMethod::Ncaa => conversion_provenance(),
        ConversionMethod::Colorado => {
            let source = &COLORADO["source"];
            Provenance {
                id: "colorado-teamunify-2026".into(),
                title: text(&source["title"]),
                url: text(&source["url"]),
                revision: text(&source["revision"]),
                sha256: Some(text(&source["sha256"])),
                verified: Some(text(&source["verified"])),
            }
        }
        ConversionMethod::Empirical => {
            let source = &EMPIRICAL["source"];
            Provenance {
                id: "turnmark-empirical-2026".into(),
                title: text(&source["title"]),
                url: text(&source["url"]),
                revision: text(&source["revision"]),
                sha256: Some(text(&source["sha256"])),
                verified: Some(text(&source["verified"])),
            }
        }
    };
    let target = SwimEvent {
        course: to,
        distance: actual_distance(distance, to, event.stroke),
        ..event.clone()
    };
    if !published(&event, distance) || !published(&target, distance) {
        return Err(unavailable(CoverageReason::EventNotPublished, provenance));
    }
    if !seconds.is_finite() || seconds <= 0.0 {
        return Err(invalid("swim.time", ValidationReason::InvalidTime));
    }
    let mut empirical_caveat = None;
    let (seconds, factor, offset_seconds, kind, formula) = if event.course == to {
        (
            seconds,
            1.0,
            0.0,
            ConversionKind::Swum,
            ConversionFormula::None,
        )
    } else if method == ConversionMethod::Colorado {
        let Some((factor, offset)) = colorado_formula(&event, distance, to) else {
            return Err(unavailable(CoverageReason::FactorNotPublished, provenance));
        };
        let converted = truncate(seconds * factor + offset);
        if !converted.is_finite() || converted <= 0.0 {
            return Err(invalid("swim.time", ValidationReason::UnsafeResult));
        }
        let formula = if offset == 0.0 {
            ConversionFormula::Multiplier
        } else {
            ConversionFormula::MultiplierOffset
        };
        (converted, factor, offset, ConversionKind::Derived, formula)
    } else if method == ConversionMethod::Empirical {
        let Some(equivalent) = empirical_equivalent(&event, distance, to, table, seconds) else {
            return Err(unavailable(CoverageReason::FactorNotPublished, provenance));
        };
        empirical_caveat = equivalent.caveat;
        // Truncate the equivalent time once. The reported factor is the unrounded ratio for this
        // entered time, which varies with ability.
        let equivalent = equivalent.seconds;
        let converted = truncate(equivalent);
        if !converted.is_finite() || converted <= 0.0 {
            return Err(invalid("swim.time", ValidationReason::UnsafeResult));
        }
        (
            converted,
            equivalent / seconds,
            0.0,
            ConversionKind::Derived,
            ConversionFormula::Equivalent,
        )
    } else {
        let source = factor(&event, distance, table);
        let target_factor = factor(&target, distance, table);
        let (Some(source), Some(target_factor)) = (source, target_factor) else {
            return Err(unavailable(CoverageReason::FactorNotPublished, provenance));
        };
        let factor = source / target_factor;
        (
            truncate(seconds * factor),
            factor,
            0.0,
            if to == Course::SCY {
                ConversionKind::Published
            } else {
                ConversionKind::Derived
            },
            ConversionFormula::Multiplier,
        )
    };
    Ok((
        ConversionValue {
            time: format_time(seconds),
            seconds,
            hundredths: (seconds * 100.0).round() as u64,
            factor,
            offset_seconds,
            formula,
            altitude: None,
            caveat: if method == ConversionMethod::Colorado
                && event.stroke == Stroke::Freestyle
                && distance >= 400
                && matches!(
                    (event.course, to),
                    (Course::SCY, Course::SCM) | (Course::SCM, Course::SCY)
                ) {
                Some(ConversionCaveat::ColoradoShortCourseDistance)
            } else {
                empirical_caveat
            },
            kind,
            event: target,
        },
        provenance,
    ))
}

/// Directional key, as listed in the snapshot's `lowEvidenceCells` and `preciseLatentRanges`.
fn empirical_cell_key(event: &SwimEvent, distance: u32, to: Course, table: Category) -> String {
    format!(
        "{}->{}|{distance}-{}|{}",
        course_key(event.course),
        course_key(to),
        stroke_key(event.stroke),
        category_key(table)
    )
}

/// A course's monotone map onto the shared latent scale: knots (latent, course log seconds).
fn empirical_knots(event_key: &str, course: Course) -> Option<Vec<(f64, f64)>> {
    EMPIRICAL["cells"].get(event_key)?[course_key(course)]["knots"]
        .as_array()?
        .iter()
        .map(|knot| Some((knot.get(0)?.as_f64()?, knot.get(1)?.as_f64()?)))
        .collect::<Option<Vec<_>>>()
        .filter(|knots| knots.len() >= 2)
}

/// Piecewise-linear map through the knots, latent -> course log seconds (or back when
/// `inverse`), continuing with slope 1 beyond the outer knots: outside the training support the
/// time ratio at its edge is held constant.
fn knot_map(knots: &[(f64, f64)], x: f64, inverse: bool) -> f64 {
    let pick = |k: (f64, f64)| if inverse { (k.1, k.0) } else { k };
    let (first, last) = (pick(knots[0]), pick(knots[knots.len() - 1]));
    if x <= first.0 {
        return first.1 + (x - first.0);
    }
    if x >= last.0 {
        return last.1 + (x - last.0);
    }
    let mut i = 0;
    while pick(knots[i + 1]).0 <= x {
        i += 1;
    }
    let (lo, hi) = (pick(knots[i]), pick(knots[i + 1]));
    lo.1 + (x - lo.0) * (hi.1 - lo.1) / (hi.0 - lo.0)
}

struct Equivalent {
    seconds: f64,
    caveat: Option<ConversionCaveat>,
}

/// Equivalent time in seconds before truncation: the entered time's latent ability through the
/// source course's map, then out through the target course's. Every direction composes the same
/// per-course maps, so converting back is the exact inverse and converting through a third course
/// equals converting directly, before truncation. Outside either course's training support the
/// conversion is out of range; inside it, it is low-evidence when the cell is thin or the entered
/// time falls outside the latent range where its bootstrap interval is narrow.
fn empirical_equivalent(
    event: &SwimEvent,
    distance: u32,
    to: Course,
    table: Category,
    seconds: f64,
) -> Option<Equivalent> {
    let event_key = format!(
        "{distance}-{}|{}",
        stroke_key(event.stroke),
        category_key(table)
    );
    let from = empirical_knots(&event_key, event.course)?;
    let target = empirical_knots(&event_key, to)?;
    let latent = knot_map(&from, seconds.ln(), true);
    let equivalent = knot_map(&target, latent, false).exp();
    let low = from[0].0.max(target[0].0);
    let high = from[from.len() - 1].0.min(target[target.len() - 1].0);
    let cell_key = empirical_cell_key(event, distance, to, table);
    let thin = EMPIRICAL["lowEvidenceCells"]
        .as_array()
        .is_some_and(|cells| cells.iter().any(|cell| cell.as_str() == Some(&cell_key)));
    let precise = EMPIRICAL["preciseLatentRanges"][&cell_key]
        .as_array()
        .and_then(|range| Some((range.first()?.as_f64()?, range.get(1)?.as_f64()?)))
        .is_some_and(|(lo, hi)| lo <= latent && latent <= hi);
    let caveat = if !(low <= latent && latent <= high) {
        Some(ConversionCaveat::EmpiricalOutOfRange)
    } else if thin || !precise {
        Some(ConversionCaveat::EmpiricalLowEvidence)
    } else {
        None
    };
    Some(Equivalent {
        seconds: equivalent,
        caveat,
    })
}

/// Direction-specific documented formulas; do not route distance events
/// through an intermediate course or infer an unlisted 100 IM conversion.
fn colorado_formula(event: &SwimEvent, distance: u32, to: Course) -> Option<(f64, f64)> {
    if event.stroke == Stroke::IndividualMedley && distance == 100 {
        return None;
    }
    let short = COLORADO["shortCourseMultiplier"].as_f64()?;
    let long_free = event.stroke == Stroke::Freestyle && distance >= 400;
    let long_factor = if long_free {
        COLORADO["longFreestyleMultipliers"][distance.to_string()].as_f64()?
    } else {
        short
    };
    let increment = if long_free {
        COLORADO["longFreestyleMetricOffsets"][distance.to_string()].as_f64()?
    } else {
        COLORADO["per50Seconds"][stroke_key(event.stroke)].as_f64()? * f64::from(distance) / 50.0
    };
    let yards_increment = if long_free { 0.0 } else { increment };
    match (event.course, to) {
        (Course::SCY, Course::SCM) => Some((short, 0.0)),
        (Course::SCM, Course::SCY) => Some((1.0 / short, 0.0)),
        (Course::SCY, Course::LCM) => Some((long_factor, yards_increment)),
        (Course::LCM, Course::SCY) => Some((1.0 / long_factor, -yards_increment / long_factor)),
        (Course::SCM, Course::LCM) => Some((1.0, increment)),
        (Course::LCM, Course::SCM) => Some((1.0, -increment)),
        _ => None,
    }
}
pub(crate) fn altitude(input: &Value) -> Calculation<AltitudeValue> {
    object(input, "request")?;
    let (event, distance, seconds) = swim(&input["swim"])?;
    let elevation = &input["elevation"];
    let value = elevation["value"].as_f64();
    let unit = elevation["unit"].as_str();
    let valid = match (value, unit) {
        (Some(v), Some("feet")) => {
            v.is_finite() && (0.0..=20000.0).contains(&v) && v.fract() == 0.0
        }
        (Some(v), Some("meters")) => v.is_finite() && (0.0..=6096.0).contains(&v),
        _ => false,
    };
    if !valid {
        return Err(invalid("elevation", ValidationReason::InvalidElevation));
    }
    let policy = match input.get("policy") {
        None => AltitudePolicy::UsaSwimming,
        Some(value) => serde_json::from_value(value.clone())
            .map_err(|_| invalid("policy", ValidationReason::UnsupportedMethod))?,
    };
    let source = &CONVERSIONS[if policy == AltitudePolicy::Ncaa {
        "ncaaAltitudeSource"
    } else {
        "altitudeSource"
    }];
    let provenance = Provenance {
        id: if policy == AltitudePolicy::Ncaa {
            "ncaa-altitude-2026-27-d1"
        } else {
            "usa-swimming-altitude-2026"
        }
        .to_owned(),
        title: text(&source["title"]),
        url: text(&source["url"]),
        revision: text(
            &source[if policy == AltitudePolicy::Ncaa {
                "revision"
            } else {
                "verified"
            }],
        ),
        sha256: source["sha256"].as_str().map(str::to_owned),
        verified: None,
    };
    if !published(&event, distance) {
        return Err(unavailable(CoverageReason::EventNotPublished, provenance));
    }
    let feet = if unit == Some("meters") {
        (value.unwrap() / 0.3048).round()
    } else {
        value.unwrap()
    } as u32;
    let adjustment = if policy == AltitudePolicy::Ncaa {
        let band = if feet < 3000 {
            None
        } else if feet <= 4250 {
            Some(0)
        } else if feet <= 6500 {
            Some(1)
        } else {
            Some(2)
        };
        band.and_then(|b| CONVERSIONS["ncaaAltitudeAdjustments"][distance.to_string()][b].as_f64())
            .unwrap_or(0.0)
    } else {
        altitude_adjustment(distance, f64::from(feet))
    };
    if seconds <= adjustment {
        return Err(invalid("swim.time", ValidationReason::InvalidTime));
    }
    let adjusted = adjusted_seconds(seconds, adjustment);
    Ok((
        AltitudeValue {
            raw_time: format_time(seconds),
            adjusted_time: format_time(adjusted),
            raw_seconds: seconds,
            adjusted_seconds: adjusted,
            adjustment_seconds: adjustment,
            elevation_feet: feet,
            kind: if adjustment > 0.0 {
                AltitudeKind::AltitudeAdjusted
            } else {
                AltitudeKind::Swum
            },
        },
        provenance,
    ))
}
fn edition(input: &Value, expected: &str) -> Result<(), Failure> {
    if input.get("edition").is_some_and(|v| v != expected) {
        Err(invalid("edition", ValidationReason::UnsupportedDataset))
    } else {
        Ok(())
    }
}
fn matches(row: &Value, event: &SwimEvent) -> bool {
    row["course"] == course_key(event.course)
        && row["stroke"] == stroke_key(event.stroke)
        && row["distance"].as_u64() == Some(u64::from(event.distance))
}
pub(crate) fn youth(input: &Value) -> Calculation<YouthValue> {
    object(input, "request")?;
    edition(input, "usa-swimming-2024-28")?;
    let table = category(&input["table"])?;
    let age = input["age"]
        .as_str()
        .filter(|a| YOUTH_AGES.contains(a))
        .ok_or_else(|| invalid("age", ValidationReason::InvalidAgeGroup))?;
    let (event, distance) = event(&input["event"], "event")?;
    let provenance = provenance(&YOUTH, "usa-swimming-2024-28", "title", "revision");
    let row =
        YOUTH["records"].as_array().unwrap().iter().find(|r| {
            matches(r, &event) && r["age"] == age && r["category"] == category_key(table)
        });
    let Some(row) = row.filter(|_| published(&event, distance)) else {
        return Err(unavailable(CoverageReason::EventNotPublished, provenance));
    };
    Ok((
        YouthValue {
            event,
            age: age.to_owned(),
            levels: YOUTH["source"]["levels"]
                .as_array()
                .unwrap()
                .iter()
                .map(text)
                .collect(),
            times: row["times"]
                .as_array()
                .unwrap()
                .iter()
                .map(|v| v.as_f64().unwrap())
                .collect(),
        },
        provenance,
    ))
}
pub(crate) fn masters(input: &Value) -> Calculation<MastersValue> {
    object(input, "request")?;
    edition(input, "usms-nationals-2026")?;
    let table = category(&input["table"])?;
    let age = input["age"]
        .as_str()
        .ok_or_else(|| invalid("age", ValidationReason::InvalidAgeGroup))?;
    let index = MASTERS["ages"]
        .as_array()
        .unwrap()
        .iter()
        .position(|v| v == age);
    if index.is_none() && age != "85+" {
        return Err(invalid("age", ValidationReason::InvalidAgeGroup));
    }
    let (event, _) = event(&input["event"], "event")?;
    let provenance = provenance(&MASTERS, "usms-nationals-2026", "name", "checked");
    if event.course == Course::SCM {
        return Err(unavailable(CoverageReason::CourseNotSupported, provenance));
    }
    if age == "85+" {
        return Err(unavailable(
            CoverageReason::AgeGroupNotPublished,
            provenance,
        ));
    }
    let row = MASTERS["records"]
        .as_array()
        .unwrap()
        .iter()
        .find(|r| matches(r, &event) && r["category"] == category_key(table));
    let Some(row) = row else {
        return Err(unavailable(CoverageReason::EventNotPublished, provenance));
    };
    let value = &row["times"][index.unwrap()];
    let Some(seconds) = value.as_f64() else {
        return Err(unavailable(CoverageReason::NoTimePublished, provenance));
    };
    Ok((
        MastersValue {
            event,
            age: age.to_owned(),
            time: format_time(seconds),
            seconds,
            hundredths: (seconds * 100.0).round() as u64,
        },
        provenance,
    ))
}
pub(crate) fn points(input: &Value) -> Calculation<PointsValue> {
    object(input, "request")?;
    edition(input, "world-aquatics-2026")?;
    let table = category(&input["table"])?;
    let (event, _, seconds) = swim(&input["swim"])?;
    points_seconds(event, seconds, table)
}

pub(crate) fn points_seconds(
    event: SwimEvent,
    seconds: f64,
    table: Category,
) -> Calculation<PointsValue> {
    if !seconds.is_finite() || seconds <= 0.0 {
        return Err(invalid("swim.time", ValidationReason::InvalidTime));
    }
    let provenance = provenance(&POINTS, "world-aquatics-2026", "name", "checked");
    if event.course == Course::SCY {
        return Err(unavailable(CoverageReason::CourseNotSupported, provenance));
    }
    let row = POINTS["events"]
        .as_array()
        .unwrap()
        .iter()
        .find(|r| matches(r, &event));
    let Some(row) = row else {
        return Err(unavailable(CoverageReason::EventNotPublished, provenance));
    };
    let base = row[category_key(table)].as_f64().unwrap();
    let score = 1000.0 * (base / seconds).powi(3);
    const MAX_SAFE: f64 = 9_007_199_254_740_991.0;
    if !score.is_finite() || score.floor() > MAX_SAFE {
        return Err(invalid("swim.time", ValidationReason::UnsafeResult));
    }
    let points = (score + 1e-9).floor() as u64;
    let next = (points / 100 + 1) * 100;
    if next as f64 > MAX_SAFE {
        return Err(invalid("swim.time", ValidationReason::UnsafeResult));
    }
    let target = truncate(base / (next as f64 / 1000.0).cbrt());
    Ok((
        PointsValue {
            points,
            base_time: format_time(base),
            base_seconds: base,
            validity: text(&POINTS["validity"][course_key(event.course)]),
            next_milestone: Milestone {
                points: next,
                time: format_time(target),
                seconds: target,
                gap_seconds: (seconds - target).max(0.0),
            },
        },
        provenance,
    ))
}

pub(crate) fn altitude_adjustment(distance: u32, feet: f64) -> f64 {
    if !feet.is_finite() || feet < 3000.0 {
        return 0.0;
    }
    let band = if feet <= 4250.0 {
        0
    } else if feet <= 6500.0 {
        1
    } else {
        2
    };
    CONVERSIONS["altitudeAdjustments"][distance.to_string()][band]
        .as_f64()
        .unwrap_or(0.0)
}

/// The altitude-adjusted swim, computed in whole hundredths. Entered times have at most two
/// decimals and every published adjustment is a whole number of hundredths, so this subtraction is
/// exact: `round` only removes binary floating-point residue and never changes a hundredth, and the
/// conversion's single truncation remains the only rounding.
pub(crate) fn adjusted_seconds(seconds: f64, adjustment: f64) -> f64 {
    ((seconds * 100.0).round() - (adjustment * 100.0).round()) / 100.0
}

pub(crate) fn event_distances(stroke: Stroke) -> &'static [u32] {
    match stroke {
        Stroke::Freestyle => &[50, 100, 200, 400, 800, 1500],
        Stroke::IndividualMedley => &[100, 200, 400],
        _ => &[50, 100, 200],
    }
}

pub(crate) fn standard_age_groups(system: StandardSystem) -> Vec<String> {
    match system {
        StandardSystem::Youth => YOUTH_AGES.iter().map(|age| (*age).to_owned()).collect(),
        StandardSystem::Masters => MASTERS["ages"]
            .as_array()
            .unwrap()
            .iter()
            .map(text)
            .chain(std::iter::once("85+".to_owned()))
            .collect(),
        StandardSystem::Futures | StandardSystem::Juniors | StandardSystem::Nisca => {
            national_program(system)["ages"]
                .as_array()
                .unwrap()
                .iter()
                .map(text)
                .collect()
        }
    }
}

fn national_program(system: StandardSystem) -> &'static Value {
    let id = serde_json::to_value(system).unwrap();
    NATIONAL["programs"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == id)
        .unwrap()
}

pub(crate) fn national_programs() -> Vec<StandardProgram> {
    NATIONAL["programs"]
        .as_array()
        .unwrap()
        .iter()
        .map(|p| StandardProgram {
            system: serde_json::from_value(p["id"].clone()).unwrap(),
            label: text(&p["label"]),
            title: text(&p["title"]),
            scope: text(&p["scope"]),
            ages: p["ages"].as_array().unwrap().iter().map(text).collect(),
            note: text(&p["note"]),
        })
        .collect()
}

fn national_targets(
    input: &Value,
    event: &SwimEvent,
    system: StandardSystem,
) -> Result<(String, Vec<String>, Vec<f64>, Provenance), Failure> {
    let program = national_program(system);
    edition(input, program["edition"].as_str().unwrap())?;
    let table = category(&input["table"])?;
    let ages = standard_age_groups(system);
    let age = if ages.is_empty() {
        ""
    } else {
        input["age"]
            .as_str()
            .filter(|age| ages.iter().any(|a| a == age))
            .ok_or_else(|| invalid("age", ValidationReason::InvalidAgeGroup))?
    };
    let source = program["sourceByCourse"]
        .get(course_key(event.course))
        .unwrap_or(&program["source"]);
    let provenance = provenance(
        &json!({"source": source}),
        program["edition"].as_str().unwrap(),
        "title",
        "revision",
    );
    if !(if system == StandardSystem::Nisca {
        [Course::SCY, Course::SCM]
    } else {
        [Course::SCY, Course::LCM]
    })
    .contains(&event.course)
    {
        return Err(unavailable(CoverageReason::CourseNotSupported, provenance));
    }
    let row = NATIONAL["records"].as_array().unwrap().iter().find(|r| {
        r["program"] == program["id"]
            && r["age"] == age
            && r["category"] == category_key(table)
            && matches(r, event)
    });
    let Some(row) = row else {
        return Err(unavailable(CoverageReason::EventNotPublished, provenance));
    };
    Ok((
        age.to_owned(),
        program["levels"]
            .as_array()
            .unwrap()
            .iter()
            .map(text)
            .collect(),
        row["times"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_f64().unwrap())
            .collect(),
        provenance,
    ))
}

pub(crate) fn achieved_standard(time: f64, times: &[f64]) -> Option<usize> {
    times.iter().rposition(|cut| time <= *cut + 1e-8)
}

/// Assess only the original swim, without course or altitude conversion.
pub(crate) fn benchmark(input: &Value) -> Calculation<BenchmarkValue> {
    object(input, "request")?;
    let system = match input["system"].as_str() {
        Some("youth") => StandardSystem::Youth,
        Some("masters") => StandardSystem::Masters,
        Some("futures") => StandardSystem::Futures,
        Some("juniors") => StandardSystem::Juniors,
        Some("nisca") => StandardSystem::Nisca,
        _ => return Err(invalid("system", ValidationReason::UnsupportedDataset)),
    };
    let (event, _, seconds) = swim(&input["swim"])?;
    let mut request = json!({"event": event, "table": input["table"], "age": input["age"]});
    if let Some(edition) = input.get("edition") {
        request["edition"] = edition.clone();
    }
    let (age, labels, times, provenance) = match system {
        StandardSystem::Youth => {
            let (value, provenance) = youth(&request)?;
            (value.age, value.levels, value.times, provenance)
        }
        StandardSystem::Masters => {
            let (value, provenance) = masters(&request)?;
            (
                value.age,
                vec!["NQT".to_owned()],
                vec![value.seconds],
                provenance,
            )
        }
        StandardSystem::Futures | StandardSystem::Juniors | StandardSystem::Nisca => {
            national_targets(input, &event, system)?
        }
    };
    let achieved = achieved_standard(seconds, &times);
    let targets: Vec<_> = labels
        .into_iter()
        .zip(times)
        .enumerate()
        .map(|(index, (label, target))| TimeTarget {
            label,
            time: format_time(target),
            seconds: target,
            met: achieved.is_some_and(|last| index <= last),
            gap_seconds: ((seconds - target).max(0.0) * 100.0).round() / 100.0,
        })
        .collect();
    let achieved_level = achieved.map(|index| targets[index].label.clone());
    let next_target = targets.iter().find(|target| !target.met).cloned();
    Ok((
        BenchmarkValue {
            event,
            age,
            system,
            entered_time: format_time(seconds),
            entered_seconds: seconds,
            targets,
            achieved_level,
            next_target,
        },
        provenance,
    ))
}
