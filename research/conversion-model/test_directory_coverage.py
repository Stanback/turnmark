import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from directory_coverage import audit


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "snapshot").mkdir()
        programs = [
            ["p1", "o1", "masters", "US", "CO", "mixed", "unknown", "s1"],
            ["p2", "o2", "high_school", "US", "FL", "women", "unknown", "s2"],
            ["p3", "o3", "collegiate_varsity", "unknown", "", "men", "unknown", "s3"],
        ]
        self.write("snapshot/programs.csv", ["program_id", "organization_id", "program_kind", "country",
                                            "state", "category", "status", "source_id"], programs)
        self.write("snapshot/organizations.csv", ["organization_id"], [["o1"], ["o2"], ["o3"]])
        self.write("snapshot/affiliations.csv", ["program_id", "authority"],
                   [["p1", "usms:public-finder"], ["p1", "usms:public-finder"], ["p3", "ncaa"]])
        self.write("governing-bodies.csv", ["program_listing_status"], [["partial_swimming_imported"]])
        self.write("source-catalog.csv", ["source_id", "segment", "publisher", "collection_status"],
                   [["naia", "collegiate_varsity", "NAIA", "reviewed_access_gap"],
                    ["vpa-no-swimming", "high_school", "VPA", "reviewed_no_sponsorship"]])
        manifest = {"generated_at": "2026-10-21T00:00:00Z"}
        for name in ("programs", "organizations", "affiliations"):
            manifest[name + "_sha256"] = hashlib.sha256((self.root / "snapshot" / (name + ".csv")).read_bytes()).hexdigest()
        (self.root / "snapshot/manifest.json").write_text(json.dumps(manifest))

    def write(self, path, header, rows):
        with (self.root / path).open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(header)
            writer.writerows(rows)

    def test_repeated_affiliations_do_not_inflate_universe(self):
        result = audit(self.root)
        self.assertEqual(result["source_universes"]["usms_finder"]["source_scoped_listings"], 1)
        self.assertEqual(result["source_universes"]["ncaa"]["us_country_asserted_listings"], 0)

    def test_unknown_denominators_never_become_coverage_or_zero_teams(self):
        result = audit(self.root)
        self.assertIsNone(result["national_team_coverage_percent"])
        self.assertEqual(result["school_jurisdictions_with_listings"], 1)
        self.assertIn("DC", result["school_jurisdictions_without_listings"])
        missing = next(s for s in result["school_states"] if s["state"] == "CA")
        self.assertIsNone(missing["eligible_unique_teams"])
        self.assertEqual(missing["scope_status"], "no_imported_school_listing")
        non_sponsoring = next(s for s in result["school_states"] if s["state"] == "VT")
        self.assertEqual(non_sponsoring["scope_status"], "verified_non_sponsoring_authority")
        covered = next(s for s in result["school_states"] if s["state"] == "FL")
        self.assertEqual(covered["categories"], {"women": 1})
        self.assertIsNone(covered["team_coverage_percent"])

    def test_source_snapshot_tampering_is_rejected(self):
        with (self.root / "snapshot/programs.csv").open("a") as stream:
            stream.write("unexpected\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            audit(self.root)


if __name__ == "__main__":
    unittest.main()
