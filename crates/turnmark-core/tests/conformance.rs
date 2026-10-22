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
    assert!(emp_val.hundredths > 5000 && emp_val.hundredths < 5600);
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
