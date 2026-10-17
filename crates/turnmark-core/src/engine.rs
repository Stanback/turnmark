use crate::types::*;
use serde_json::Value;
use std::sync::LazyLock;

// Snapshots are immutable and embedded: no network, filesystem or platform API.
static CONVERSIONS: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/conversions.json")));
static SOURCES: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/sources.json")));
static YOUTH: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/standards.json")));
static MASTERS: LazyLock<Value> =
    LazyLock::new(|| snapshot(include_str!("../../../data/masters.json")));
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
fn actual_distance(distance: u32, course: Course, stroke: Stroke) -> u32 {
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
    let distances: &[u32] = match stroke {
        Stroke::Freestyle => &[50, 100, 200, 400, 800, 1500],
        Stroke::IndividualMedley => &[100, 200, 400],
        _ => &[50, 100, 200],
    };
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
fn published(event: &SwimEvent, distance: u32) -> bool {
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
fn truncate(seconds: f64) -> f64 {
    (seconds * 100.0 + 1e-8).floor() / 100.0
}
fn format_time(seconds: f64) -> String {
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
fn factor(event: &SwimEvent, distance: u32, table: Category) -> Option<f64> {
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
    if input.get("method").is_some_and(|v| v != "ncaa-2025-27") {
        return Err(invalid("method", ValidationReason::UnsupportedMethod));
    }
    let to = course(&input["to"], "to")?;
    let table = category(&input["table"])?;
    let (event, distance, seconds) = swim(&input["swim"])?;
    let provenance = conversion_provenance();
    let target = SwimEvent {
        course: to,
        distance: actual_distance(distance, to, event.stroke),
        ..event.clone()
    };
    if !published(&event, distance) || !published(&target, distance) {
        return Err(unavailable(CoverageReason::EventNotPublished, provenance));
    }
    let (seconds, factor, kind) = if event.course == to {
        (seconds, 1.0, ConversionKind::Swum)
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
            if to == Course::SCY {
                ConversionKind::Published
            } else {
                ConversionKind::Derived
            },
        )
    };
    Ok((
        ConversionValue {
            time: format_time(seconds),
            seconds,
            hundredths: (seconds * 100.0).round() as u64,
            factor,
            kind,
            event: target,
        },
        provenance,
    ))
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
    let source = &CONVERSIONS["altitudeSource"];
    let provenance = Provenance {
        id: "usa-swimming-altitude-2026".to_owned(),
        title: text(&source["title"]),
        url: text(&source["url"]),
        revision: text(&source["verified"]),
        sha256: None,
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
    let band = if feet <= 4250 {
        0
    } else if feet <= 6500 {
        1
    } else {
        2
    };
    let adjustment = if feet < 3000 {
        0.0
    } else {
        CONVERSIONS["altitudeAdjustments"][distance.to_string()][band]
            .as_f64()
            .unwrap_or(0.0)
    };
    if seconds <= adjustment {
        return Err(invalid("swim.time", ValidationReason::InvalidTime));
    }
    let adjusted = (seconds * 100.0 - adjustment * 100.0).round() / 100.0;
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
        .filter(|a| ["10u", "11-12", "13-14", "15-16", "17-18"].contains(a))
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
