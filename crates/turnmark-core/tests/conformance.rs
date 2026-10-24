use serde_json::{json, Value};
use turnmark_core::*;

#[test]
fn native_event_options_use_authoritative_distances() {
    let yards = get_event_options(Course::SCY, Stroke::Freestyle);
    assert_eq!(
        yards.iter().map(|o| o.event.distance).collect::<Vec<_>>(),
        vec![50, 100, 200, 500, 1000, 1650]
    );
    assert_eq!(yards[3].canonical_distance, 400);
    assert_eq!(
        get_event_options(Course::LCM, Stroke::IndividualMedley)
            .iter()
            .map(|o| o.event.distance)
            .collect::<Vec<_>>(),
        vec![200, 400]
    );
}

fn subset(actual: &Value, expected: &Value, path: &str) {
    match expected {
        Value::Object(fields) => {
            for (key, expected) in fields {
                let actual = actual
                    .get(key)
                    .unwrap_or_else(|| panic!("{path}.{key} missing: {actual}"));
                subset(actual, expected, &format!("{path}.{key}"));
            }
        }
        Value::Array(items) => {
            let actual = actual.as_array().unwrap();
            assert_eq!(actual.len(), items.len(), "{path}");
            for (i, expected) in items.iter().enumerate() {
                subset(&actual[i], expected, &format!("{path}[{i}]"));
            }
        }
        Value::Number(number) => {
            let actual = actual.as_f64().unwrap();
            let expected = number.as_f64().unwrap();
            // Clock hundredths, scores and ticks remain exact; tolerate only binary
            // representation differences in ratios and subtraction-derived gaps.
            assert!(
                (actual - expected).abs() < 1e-9,
                "{path}: {actual} != {expected}"
            );
        }
        _ => assert_eq!(actual, expected, "{path}"),
    }
}
fn run(operation: &str, input: &Value) -> Value {
    serde_json::from_str(&evaluate(operation.to_owned(), input.to_string()).unwrap()).unwrap()
}

#[test]
fn language_neutral_fixtures() {
    let fixtures: Value =
        serde_json::from_str(include_str!("../../../fixtures/sdk-conformance.json")).unwrap();
    for case in fixtures["cases"].as_array().unwrap() {
        subset(
            &run(case["operation"].as_str().unwrap(), &case["input"]),
            &case["expected"],
            case["id"].as_str().unwrap(),
        );
    }
}

/// Holds the engine to the arithmetic the equivalence model was evaluated with. The research
/// pipeline regenerates these cases from data/empirical.json on every export.
#[test]
fn empirical_conversions_match_the_evaluated_reference_to_the_hundredth() {
    let fixture: Value =
        serde_json::from_str(include_str!("../../../fixtures/empirical-parity.json")).unwrap();
    let snapshot: Value =
        serde_json::from_str(include_str!("../../../data/empirical.json")).unwrap();
    assert_eq!(
        fixture["cellsSha256"], snapshot["source"]["sha256"],
        "fixtures/empirical-parity.json describes a different empirical snapshot"
    );
    // A slower entered time never converts faster at a hundredth boundary.
    let breast = |time: &str| {
        run(
            "convert",
            &json!({
                "swim": {"time": time, "event": {"distance": 100, "stroke": "breaststroke", "course": "LCM"}},
                "to": "SCM",
                "table": "women",
                "method": "turnmark-empirical-2026",
            }),
        )["value"]["hundredths"]
            .as_u64()
            .unwrap()
    };
    assert!(breast("1:13.05") >= breast("1:13.04"));
    let cases = fixture["cases"].as_array().unwrap();
    // Six probes for each of the six course directions of every (event, category).
    assert_eq!(
        cases.len(),
        6 * 6 * snapshot["cells"].as_object().unwrap().len()
    );
    for case in cases {
        let input = json!({
            "swim": {"time": case["time"], "event": case["event"]},
            "to": case["to"],
            "table": case["table"],
            "method": "turnmark-empirical-2026",
        });
        let result = run("convert", &input);
        if case.get("expectedStatus").is_some() {
            assert_eq!(
                result["status"], case["expectedStatus"],
                "{} at {}: {result}",
                case["cell"], case["time"]
            );
        } else {
            assert_eq!(
                result["value"]["hundredths"], case["expectedHundredths"],
                "{} at {}: {result}",
                case["cell"], case["time"]
            );
            let caveat = result["value"]
                .get("caveat")
                .cloned()
                .unwrap_or(Value::Null);
            assert_eq!(
                caveat, case["expectedCaveat"],
                "{} caveat at {}: {result}",
                case["cell"], case["time"]
            );
        }
    }
}

fn clock(hundredths: u64) -> String {
    let (minutes, rest) = (hundredths / 6000, hundredths % 6000);
    if minutes > 0 {
        format!("{minutes}:{:02}.{:02}", rest / 100, rest % 100)
    } else {
        format!("{}.{:02}", rest / 100, rest % 100)
    }
}

/// Entered distance and stroke for a snapshot event key such as "1500-FR" in one course.
fn entered_event(event_key: &str, course: &str) -> Value {
    let (distance, code) = event_key.split_once('-').unwrap();
    let mut distance: u32 = distance.parse().unwrap();
    let stroke = match code {
        "FR" => "freestyle",
        "BK" => "backstroke",
        "BR" => "breaststroke",
        "FL" => "butterfly",
        _ => "individual-medley",
    };
    if course == "SCY" && code == "FR" {
        distance = match distance {
            400 => 500,
            800 => 1000,
            1500 => 1650,
            other => other,
        };
    }
    json!({"distance": distance, "stroke": stroke, "course": course})
}

/// The equivalence map composes one monotone map per course, so before rounding it inverts and
/// composes exactly. With the engine's single truncation, A -> B -> A returns the entered time or
/// up to 0.05 s faster (a truncation can be stretched where a course's map is flatter than the
/// other's), A -> C -> B is within 0.05 s of A -> B, and a slower entered time never converts
/// faster. Samples run from well below to well above each course's training support.
#[test]
fn empirical_conversions_invert_compose_and_stay_monotone() {
    let snapshot: Value =
        serde_json::from_str(include_str!("../../../data/empirical.json")).unwrap();
    let courses = ["SCY", "SCM", "LCM"];
    let convert = |time: u64, event: &Value, to: &str, table: &str| -> u64 {
        let result = run(
            "convert",
            &json!({
                "swim": {"time": clock(time), "event": event},
                "to": to,
                "table": table,
                "method": "turnmark-empirical-2026",
            }),
        );
        result["value"]["hundredths"]
            .as_u64()
            .unwrap_or_else(|| panic!("{event} {to} {table} at {time}: {result}"))
    };
    for (cell_key, params) in snapshot["cells"].as_object().unwrap() {
        let (event_key, table) = cell_key.split_once('|').unwrap();
        for from in courses {
            let knots = params[from]["knots"].as_array().unwrap();
            let middle_knot = &knots[knots.len() / 2];
            let center = middle_knot[1].as_f64().unwrap().exp() * 100.0;
            let event = entered_event(event_key, from);
            for to in courses.iter().filter(|c| **c != from) {
                let via = courses.iter().find(|c| **c != from && *c != to).unwrap();
                let back_event = entered_event(event_key, to);
                let mut previous = 0;
                for step in 0..=40 {
                    // 0.6x to 1.6x the course location, plus an odd hundredth offset.
                    let time = (center * (0.6 + step as f64 * 0.025)) as u64 + step % 7;
                    let forward = convert(time, &event, to, table);
                    assert!(forward >= previous, "{cell_key} {from}->{to} at {time}");
                    previous = forward;
                    let back = convert(forward, &back_event, from, table);
                    assert!(
                        back <= time && time - back <= 5,
                        "{cell_key} {from}->{to}->{from}: {time} -> {forward} -> {back}"
                    );
                    let middle = convert(time, &event, via, table);
                    let composed = convert(middle, &entered_event(event_key, via), to, table);
                    assert!(
                        composed.abs_diff(forward) <= 5,
                        "{cell_key} {from}->{via}->{to}: {composed} vs {forward}"
                    );
                }
            }
        }
    }
}

/// Elevation adjusts the entered swim in whole hundredths, so the conversion still rounds once:
/// an altitude-adjusted conversion equals converting the adjusted clock time directly.
#[test]
fn altitude_adjusted_conversions_round_once() {
    let conversions: Value =
        serde_json::from_str(include_str!("../../../data/conversions.json")).unwrap();
    for table in ["altitudeAdjustments", "ncaaAltitudeAdjustments"] {
        for bands in conversions[table].as_object().unwrap().values() {
            for adjustment in bands.as_array().unwrap() {
                let hundredths = adjustment.as_f64().unwrap() * 100.0;
                assert!(
                    (hundredths - hundredths.round()).abs() < 1e-9,
                    "{table}: {adjustment}"
                );
            }
        }
    }
    for method in [
        "ncaa-2025-27",
        "colorado-teamunify-2026",
        "turnmark-empirical-2026",
    ] {
        for time in ["1:52.37", "4:01.09", "16:12.71"] {
            let distance = match time {
                "1:52.37" => 200,
                "4:01.09" => 400,
                _ => 1500,
            };
            let event = json!({"distance": distance, "stroke": "freestyle", "course": "LCM"});
            let adjusted = run(
                "convert",
                &json!({"swim": {"time": time, "event": event}, "to": "SCY", "table": "women",
                        "method": method, "elevation": {"value": 5280, "unit": "feet"}}),
            );
            let clock = adjusted["value"]["altitude"]["value"]["adjustedTime"]
                .as_str()
                .unwrap()
                .to_owned();
            let direct = run(
                "convert",
                &json!({"swim": {"time": clock, "event": event}, "to": "SCY", "table": "women",
                        "method": method}),
            );
            assert_eq!(
                adjusted["value"]["hundredths"], direct["value"]["hundredths"],
                "{method} {time}"
            );
        }
    }
}

#[test]
fn all_published_points_bases_and_milestone_hundredths() {
    let data: Value = serde_json::from_str(include_str!("../../../data/points.json")).unwrap();
    for row in data["events"].as_array().unwrap() {
        for table in ["women", "men"] {
            let stroke = match row["stroke"].as_str().unwrap() {
                "FR" => "freestyle",
                "BK" => "backstroke",
                "BR" => "breaststroke",
                "FL" => "butterfly",
                _ => "individual-medley",
            };
            let mut input = json!({"table": table, "swim": {"time": format!("{:.2}", row[table].as_f64().unwrap()),
                "event": {"course": row["course"], "distance": row["distance"], "stroke": stroke}}});
            let result = run("points", &input);
            assert_eq!(result["value"]["points"], 1000);
            let milestone = &result["value"]["nextMilestone"];
            input["swim"]["time"] = milestone["time"].clone();
            assert!(run("points", &input)["value"]["points"].as_u64().unwrap() >= 1100);
            input["swim"]["time"] = json!(format!(
                "{:.2}",
                milestone["seconds"].as_f64().unwrap() + 0.01
            ));
            assert!(run("points", &input)["value"]["points"].as_u64().unwrap() < 1100);
        }
    }
}

#[test]
fn typed_native_contract_and_transport_errors() {
    assert_eq!(parse_time("\u{feff}1:02.45\u{00a0}".into()), Some(62.45));
    assert_eq!(parse_time("\u{0085}1:02.45".into()), None);
    let event = SwimEvent {
        distance: 100,
        stroke: Stroke::Freestyle,
        course: Course::LCM,
    };
    let result = convert_swim(ConversionRequest {
        swim: Swim {
            time: "1:00".into(),
            event,
        },
        to: Course::SCY,
        table: Category::Women,
    });
    let ConversionOutcome::Available { value, provenance } = result else {
        panic!("typed conversion unavailable")
    };
    assert_eq!(value.hundredths, 5244);
    assert_eq!(provenance.id, "ncaa-2025-27");
    let empirical = convert_swim_with_method(
        ConversionRequest {
            swim: Swim {
                time: "1:00".into(),
                event: SwimEvent {
                    distance: 100,
                    stroke: Stroke::Freestyle,
                    course: Course::LCM,
                },
            },
            to: Course::SCY,
            table: Category::Women,
        },
        ConversionMethod::Empirical,
    );
    let ConversionOutcome::Available {
        value: emp_val,
        provenance: emp_prov,
    } = empirical
    else {
        panic!("empirical conversion unavailable")
    };
    assert_eq!(emp_prov.id, "turnmark-empirical-2026");
    assert_eq!(emp_val.kind, ConversionKind::Derived);
    assert!(emp_val.hundredths >= 5100 && emp_val.hundredths <= 5300);
    // Distance mapping & monotonicity check: 1650y SCY -> 1500m LCM Men maps to 1500m and rises monotonically
    let mut prev_hundredths = 0;
    for sample_time in ["14:13.00", "15:30.00", "17:00.00"] {
        let mile = convert_swim_with_method(
            ConversionRequest {
                swim: Swim {
                    time: sample_time.into(),
                    event: SwimEvent {
                        distance: 1650,
                        stroke: Stroke::Freestyle,
                        course: Course::SCY,
                    },
                },
                to: Course::LCM,
                table: Category::Men,
            },
            ConversionMethod::Empirical,
        );
        let ConversionOutcome::Available {
            value: mile_val, ..
        } = mile
        else {
            panic!("empirical 1650y->1500m conversion unavailable")
        };
        assert_eq!(mile_val.event.distance, 1500);
        assert!(mile_val.hundredths > prev_hundredths);
        prev_hundredths = mile_val.hundredths;
    }
    let emp_data: Value =
        serde_json::from_str(include_str!("../../../data/empirical.json")).unwrap();
    assert_eq!(emp_data["schemaVersion"], 3);
    assert_eq!(emp_data["cells"].as_object().unwrap().len(), 28);
    assert!(evaluate("convert".into(), "{".into()).is_err());
    assert!(evaluate("typo".into(), "{}".into()).is_err());
    assert!(evaluate(
        "compat".into(),
        json!({"operation": "convert", "args": []}).to_string()
    )
    .is_err());
}

#[test]
fn benchmark_targets_preserve_every_published_youth_boundary() {
    let data: Value = serde_json::from_str(include_str!("../../../data/standards.json")).unwrap();
    for row in data["records"].as_array().unwrap() {
        let stroke = match row["stroke"].as_str().unwrap() {
            "FR" => "freestyle",
            "BK" => "backstroke",
            "BR" => "breaststroke",
            "FL" => "butterfly",
            _ => "individual-medley",
        };
        for (index, cutoff) in row["times"].as_array().unwrap().iter().enumerate() {
            let cutoff = cutoff.as_f64().unwrap();
            for (offset, met) in [(0.0, true), (0.01, false)] {
                let result = run(
                    "benchmark",
                    &json!({"system":"youth", "age":row["age"], "table":row["category"],
                    "swim":{"time":format!("{:.2}", cutoff + offset), "event":{"distance":row["distance"], "stroke":stroke, "course":row["course"]}}}),
                );
                let target = &result["value"]["targets"][index];
                assert_eq!(result["status"], "available", "{row}");
                assert_eq!(target["met"], met, "{row} target {index}");
                assert!((target["gapSeconds"].as_f64().unwrap() - offset).abs() < 1e-9);
                let parsed = parse_time(target["time"].as_str().unwrap().to_owned()).unwrap();
                assert!((parsed - cutoff).abs() < 1e-9);
            }
        }
    }
}

#[test]
fn benchmark_masters_compares_original_time_and_keeps_source() {
    let event = SwimEvent {
        distance: 100,
        stroke: Stroke::Freestyle,
        course: Course::SCY,
    };
    let MastersOutcome::Available {
        value: target,
        provenance: source,
    } = get_masters_target(StandardsRequest {
        event: event.clone(),
        table: Category::Women,
        age: "18-24".to_owned(),
    })
    else {
        panic!("Published target required")
    };
    for (time, met, gap) in [
        (target.time.clone(), true, 0.0),
        (format!("{:.2}", target.seconds + 0.01), false, 0.01),
    ] {
        let BenchmarkOutcome::Available { value, provenance } =
            assess_swim_benchmark(BenchmarkRequest {
                swim: Swim {
                    time,
                    event: event.clone(),
                },
                table: Category::Women,
                age: "18-24".to_owned(),
                system: StandardSystem::Masters,
            })
        else {
            panic!("Assessment required")
        };
        assert_eq!(provenance, source);
        assert_eq!(value.event, event);
        assert_eq!(value.targets.len(), 1);
        assert_eq!(value.targets[0].met, met);
        assert_eq!(value.targets[0].gap_seconds, gap);
        assert_eq!(value.next_target.is_none(), met);
    }
    assert_eq!(
        get_standard_age_groups(StandardSystem::Youth),
        ["10u", "11-12", "13-14", "15-16", "17-18"]
    );
    assert_eq!(
        get_standard_age_groups(StandardSystem::Masters)
            .last()
            .unwrap(),
        "85+"
    );
}
