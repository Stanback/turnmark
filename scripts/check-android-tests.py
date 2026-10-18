"""Fail closed when Gradle succeeds without running instrumentation tests."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path(sys.argv[1]) / "build/outputs/androidTest-results/connected/debug"
exit_code = root / "test-result-exit-code.txt"
if exit_code.exists() and exit_code.read_text().strip() != "0":
    raise SystemExit("Android instrumentation runner reported a failure")
reports = list(root.glob("TEST-*.xml"))
if not reports:
    raise SystemExit("No fresh Android instrumentation test reports were produced")
cases = []
for report in reports:
    tree = ET.parse(report)
    for suite in tree.iter():
        if suite.tag in ("testsuite", "testsuites") and any(int(suite.get(key, "0")) for key in ("failures", "errors", "skipped")):
            raise SystemExit(f"Android test suite did not pass: {report.name}")
    for case in tree.iter("testcase"):
        if any(case.find(kind) is not None for kind in ("failure", "error", "skipped")):
            raise SystemExit(f"Android test did not pass: {case.get('classname')}.{case.get('name')}")
        cases.append(case)
if len(cases) < 2:
    raise SystemExit(f"Expected at least two Android instrumentation tests; got {len(cases)}")
print(f"Verified {len(cases)} passing Android instrumentation test cases.")
