use serde_json::Value;
use turnmark_core::{evaluate, evaluate_conversion};

#[test]
fn focused_transport_matches_full_contract_fixtures() {
    let fixtures: Value =
        serde_json::from_str(include_str!("../../../fixtures/sdk-conformance.json")).unwrap();
    let mut checked = 0;
    for case in fixtures["cases"].as_array().unwrap() {
        let operation = case["operation"].as_str().unwrap();
        if !["parse", "convert", "altitude"].contains(&operation) {
            continue;
        }
        let input = case["input"].to_string();
        assert_eq!(
            evaluate_conversion(operation.into(), input.clone()).unwrap(),
            evaluate(operation.into(), input).unwrap(),
            "{}",
            case["id"]
        );
        checked += 1;
    }
    assert!(checked > 20);
}

#[test]
fn focused_transport_rejects_unshipped_operations_and_malformed_json() {
    for operation in [
        "youth",
        "masters",
        "points",
        "benchmark",
        "national-programs",
        "compat",
    ] {
        assert!(evaluate_conversion(operation.into(), "{}".into())
            .unwrap_err()
            .to_string()
            .contains("Unknown operation"));
    }
    assert!(evaluate_conversion("convert".into(), "{".into())
        .unwrap_err()
        .to_string()
        .contains("Malformed JSON"));
}
