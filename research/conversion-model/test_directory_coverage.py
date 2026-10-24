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
            ["p4", "o4", "age_group", "CA", "ON", "mixed", "unknown", "s4"],
            ["p5", "o4", "masters", "CA", "ON", "mixed", "unknown", "s4"],
            ["p6", "o5", "unknown", "CA", "QC", "unknown", "unknown", "s5"],
            ["p7", "o6", "unknown", "CA", "", "unknown", "unknown", "s5"],
        ]
        self.write("snapshot/programs.csv", ["program_id", "organization_id", "program_kind", "country",
                                            "state", "category", "status", "source_id"], programs)
        self.write("snapshot/organizations.csv", ["organization_id"], [["o1"], ["o2"], ["o3"], ["o4"], ["o5"], ["o6"]])
        self.write("snapshot/affiliations.csv", ["program_id", "authority"],
                   [["p1", "usms:public-finder"], ["p1", "usms:public-finder"], ["p3", "ncaa"],
                    ["p4", "swim-ontario:abbreviation"], ["p5", "swim-ontario:abbreviation"],
                    ["p6", "swimming-canada:club-list-row"], ["p7", "swimming-canada:club-list-row"]])
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

    def test_canada_provinces_separate_provincial_and_national_assertions(self):
        result = audit(self.root)
        self.assertEqual(result["countries"]["CA"], {"source_scoped_listings": 4, "source_scoped_organizations": 3})
        self.assertEqual(result["countries"]["US"]["source_scoped_listings"], 2)
        canada = result["canada"]
        self.assertEqual(canada["national_rows_without_province"], 1)
        self.assertEqual(canada["national_list_listings"], 2)
        self.assertIsNone(canada["national_club_coverage_percent"])
        ontario = next(p for p in canada["provinces"] if p["province"] == "ON")
        self.assertEqual((ontario["provincial_section_listings"], ontario["national_list_listings"]), (2, 0))
        self.assertEqual(ontario["program_kinds"], {"age_group": 1, "masters": 1})
        self.assertEqual(ontario["scope_status"], "partial_source_assertions")
        self.assertIn("over 140", ontario["published_denominator"])
        quebec = next(p for p in canada["provinces"] if p["province"] == "QC")
        self.assertEqual(quebec["scope_status"], "national_list_only")
        self.assertIsNone(quebec["published_denominator"])
        self.assertEqual(canada["provinces_without_listings"], sorted(set("AB BC MB NB NL NS NT NU PE SK YT".split())))
        self.assertIsNone(ontario["club_coverage_percent"])
        # Canadian rows never leak into the U.S. school audit.
        self.assertEqual(result["school_jurisdictions_with_listings"], 1)

    def test_source_snapshot_tampering_is_rejected(self):
        with (self.root / "snapshot/programs.csv").open("a") as stream:
            stream.write("unexpected\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            audit(self.root)


if __name__ == "__main__":
    unittest.main()
