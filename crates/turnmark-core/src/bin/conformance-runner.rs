use serde_json::Value;
use std::io::{self, BufRead};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    for line in io::stdin().lock().lines() {
        let request: Value = serde_json::from_str(&line?)?;
        let operation = request["operation"].as_str().ok_or("Missing operation")?;
        println!(
            "{}",
            turnmark_core::evaluate(operation.into(), request["input"].to_string())?
        );
    }
    Ok(())
}
