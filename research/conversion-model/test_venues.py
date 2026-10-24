"""Invented basins/configurations expose false same-pool matches and unknowns."""
import copy
import json
import os
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pipeline import Race, match
from venues import create_registry, venue_index, classify_pairs, cohort_report, audit, enrichment_queue


def without_digests(value):
    """The value with every *sha256 field checked to be a hex digest and blanked, so a search for
    identifying text can't match a hash by chance."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key.endswith("sha256"):
                assert isinstance(item, str) and re.fullmatch(r"[0-9a-f]{64}", item), (key, item)
                out[key] = "<digest>"
            else:
                out[key] = without_digests(item)
        return out
    if isinstance(value, list):
        return [without_digests(item) for item in value]
    return value


@unittest.skipUnless(os.environ.get("TURNMARK_LAKEHOUSE_TESTS") == "1", "Optional DuckDB")
class VenueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / "venues.json"
        self.database = self.root / "venues.duckdb"
        self.document = json.loads(Path(__file__).with_name("fixtures").joinpath("venues.synthetic.json").read_text())
        self.pairs = match([
            Race("synthetic", "y1", "athlete", "meet-y", date(2026,1,5), "SCY",100,"freestyle","women",5832,15),
            Race("synthetic", "m1", "athlete", "meet-m", date(2026,1,15), "LCM",100,"freestyle","women",6672,15),
        ])

    def create(self):
        self.input.write_text(json.dumps(self.document))
        return create_registry(self.input, self.database)

    def classify(self):
        self.create()
        return classify_pairs(self.pairs, venue_index(self.database))

    def test_same_physical_pool_preserves_clocks_and_frozen_partition(self):
        original = copy.deepcopy(self.pairs)
        pairs = self.classify()
        self.assertEqual(pairs[0]["venue_context"]["cohort"], "same_pool")
        self.assertTrue(pairs[0]["venue_context"]["both_elevations_known"])
        self.assertEqual(self.pairs, original)
        for field in ("source", "target", "partition", "gap_days", "swimmer_key"):
            self.assertEqual(pairs[0][field], original[0][field])
        self.assertEqual(pairs[0]["venue_context"]["source"]["elevation_uncertainty_m"], 5)

    def test_same_facility_with_different_basins_is_not_same_pool(self):
        self.document["race_venues"][1]["configuration_id"] = "toy-second-meters"
        pairs = self.classify()
        self.assertEqual(pairs[0]["venue_context"]["cohort"], "same_facility_different_pools")

    def test_unknown_elevation_is_never_zero_and_unknown_mapping_is_unresolved(self):
        self.document["race_venues"][1]["configuration_id"] = "toy-unknown-meters"
        pairs = self.classify()
        self.assertEqual(pairs[0]["venue_context"]["cohort"], "different_facilities")
        self.assertFalse(pairs[0]["venue_context"]["both_elevations_known"])
        self.assertIsNone(pairs[0]["venue_context"]["target"]["elevation_m"])
        pairs = classify_pairs(self.pairs, {})
        self.assertEqual(pairs[0]["venue_context"]["cohort"], "unresolved_venue")

    def test_adjusted_or_unknown_basis_is_excluded_from_raw_same_pool_cohort(self):
        self.create()
        index = venue_index(self.database)
        for basis in ("altitude_adjusted", "unknown"):
            index[("synthetic","m1")]["time_basis"] = basis
            pairs = classify_pairs(self.pairs, index)
            self.assertEqual(pairs[0]["venue_context"]["cohort"], "non_raw_or_unknown_basis")
            self.assertEqual(pairs[0]["target"]["time_cs"], 6672)

    def test_wrong_course_or_stale_configuration_fails_for_review(self):
        self.create()
        index = venue_index(self.database)
        for override in ({"course":"SCM"}, {"valid_to":date(2026,1,14)}, {"valid_from":date(2026,1,16)}):
            changed = copy.deepcopy(index)
            changed[("synthetic","m1")].update(override)
            with self.assertRaises(ValueError): classify_pairs(self.pairs, changed)

    def test_invalid_metadata_and_contacts_leave_no_database(self):
        import duckdb
        original = copy.deepcopy(self.document)
        changes = [
            ("pools", "elevation_m", float("nan")),
            ("pools", "elevation_uncertainty_m", -1),
            ("pools", "elevation_m", None),
            ("pools", "facility_id", "absent"),
            ("pools", "personal_contact", "private@example.invalid"),
            ("venue_sources", "checked_at", "2026-10-20"),
            ("pool_configurations", "valid_to", "2025-01-01"),
        ]
        for table, field, value in changes:
            self.document = copy.deepcopy(original)
            self.document[table][0][field] = value
            with self.subTest(table=table,field=field), self.assertRaises((ValueError, duckdb.Error)):
                self.create()
            self.assertFalse(self.database.exists())
        self.assertEqual(list(self.root.glob(".venues-*")), [])

    def test_aggregate_report_has_zero_cohorts_and_no_identifying_rows(self):
        self.create()
        path = self.root / "pairs.json"
        path.write_text(json.dumps(self.pairs))
        report = audit(path, self.database, self.root / "audit")
        self.assertEqual(sum(row["pairs"] for row in report["cohorts"]), 1)
        self.assertEqual(report["cohorts"][0]["pairs"], 0)
        self.assertFalse(report["clocks_changed"])
        self.assertFalse(report["partitions_changed"])
        for text in ("athlete", "toy-main", "meet-y", "5832", "6672"):
            self.assertNotIn(text, json.dumps(without_digests(report)))
        with self.assertRaises(FileExistsError): audit(path, self.database, self.root / "audit")
        self.assertTrue((self.root / "audit/pairs-with-venues.json").exists())

    def test_reused_races_and_cross_partition_swimmers_fail(self):
        self.create()
        index = venue_index(self.database)
        with self.assertRaisesRegex(ValueError, "reused"):
            classify_pairs(self.pairs + self.pairs, index)
        other = copy.deepcopy(self.pairs[0])
        other["source"]["race_id"] = "y2"
        other["target"]["race_id"] = "m2"
        other["partition"] = "test" if other["partition"] != "test" else "train"
        with self.assertRaisesRegex(ValueError, "partitions"):
            classify_pairs([self.pairs[0], other], index)

    def test_review_queue_targets_missing_meets_without_race_outcomes(self):
        pairs = classify_pairs(self.pairs, {})
        queue = enrichment_queue(pairs)
        self.assertEqual({row["meet_id"] for row in queue}, {"meet-y", "meet-m"})
        self.assertEqual(sum(row["mapping_missing"] for row in queue), 2)
        for text in ("athlete", "5832", "6672", '"race_id"', '"time_cs"'):
            self.assertNotIn(text, json.dumps(without_digests(queue)))
        self.create()
        self.assertEqual(enrichment_queue(classify_pairs(self.pairs, venue_index(self.database))), [])
