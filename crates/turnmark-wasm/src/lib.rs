use wasm_bindgen::prelude::*;

/// Transport only: all validation, data and calculations live in turnmark-core.
#[wasm_bindgen]
pub fn evaluate(operation: &str, request_json: &str) -> Result<String, JsValue> {
    turnmark_core::evaluate(operation.to_owned(), request_json.to_owned())
        .map_err(|error| JsValue::from_str(&error.to_string()))
}

#[wasm_bindgen]
pub fn engine_version() -> String {
    turnmark_core::engine_version()
}
