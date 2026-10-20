"""Fail closed when Gradle succeeds without executing exactly the selected tests."""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET

root = Path(sys.argv[1]) / "build/outputs/androidTest-results" / (sys.argv[4] if len(sys.argv) > 4 else "connected")
runner_failed = any(exit_code.read_text().strip() != "0" for exit_code in root.rglob("test-result-exit-code.txt"))
reports = list(root.rglob("TEST-*.xml"))
if not reports:
    raise SystemExit("No fresh Android instrumentation test reports were produced")
cases = []
failed = runner_failed
for report in reports:
    tree = ET.parse(report)
    for suite in tree.iter():
        if suite.tag in ("testsuite", "testsuites") and any(int(suite.get(key, "0")) for key in ("failures", "errors", "skipped")):
            failed = True
    for case in tree.iter("testcase"):
        outcome = "Passed"
        if any(case.find(kind) is not None for kind in ("failure", "error", "skipped")):
            failed = True
            outcome = "Failed"
        cases.append({"id": f"{case.get('classname')}#{case.get('name')}", "result": outcome, "seconds": float(case.get("time", "0"))})
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(json.dumps(cases, indent=2) + "\n")
if failed:
    raise SystemExit("Android runner or test suite did not pass (failure, error or skip)")
if len(sys.argv) > 2:
    expected = json.loads(Path(sys.argv[2]).read_text())
    actual = [case["id"] for case in cases]
    if not expected or len(set(actual)) != len(actual) or sorted(actual) != sorted(expected):
        raise SystemExit(f"Android test inventory mismatch: missing {sorted(set(expected) - set(actual))}; unexpected {sorted(set(actual) - set(expected))}")
elif len(cases) < 2:
    raise SystemExit(f"Expected at least two Android instrumentation tests; got {len(cases)}")
print(f"Verified {len(cases)} passing Android instrumentation test cases.")
