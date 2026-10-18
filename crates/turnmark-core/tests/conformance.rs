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
    assert!(evaluate("convert".into(), "{".into()).is_err());
    assert!(evaluate("typo".into(), "{}".into()).is_err());
    assert!(evaluate(
        "compat".into(),
        json!({"operation": "convert", "args": []}).to_string()
    )
    .is_err());
}
