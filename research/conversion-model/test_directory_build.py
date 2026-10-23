"""Invented CSV snapshots verify the portable local DuckDB build boundary."""
import csv
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from directory_build import build_directory
from directory_export import FIELDS, ORGANIZATION_FIELDS, AFFILIATION_FIELDS


@unittest.skipUnless(os.environ.get("TURNMARK_LAKEHOUSE_TESTS") == "1", "Optional DuckDB")
class DirectoryBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        (self.source / "snapshot").mkdir(parents=True)
        self.manifest = {"schema_version":2, "scope":"organization-directory-facts",
                         "organizations":2, "source_scoped_organizations":2, "programs":2, "affiliations":2}
        self.write("organizations", ORGANIZATION_FIELDS, [
            ["o1", "Example Club", "club", "US", "CA", "Example", "https://example.invalid/team", "2026-01-01", "s1", "https://source.invalid"],
            ["o2", "Example Again", "club", "US", "CA", "Example", "https://example.invalid/team", "2026-01-01", "s2", "https://other.invalid"],
        ])
        self.program_rows = [
            ["p1", "o1", "Example Club", "Example Masters", "masters", "pool_swimming", "mixed", "unknown", "US", "CA", "Example", None, "2026-01-01", "s1", "https://source.invalid"],
            ["p2", "o2", "Example Again", "Example Youth", "age_group", "pool_swimming", "mixed", "unknown", "US", "CA", "Example", None, "2026-01-01", "s2", "https://other.invalid"],
        ]
        self.write("programs", FIELDS, self.program_rows)
        self.write("affiliations", AFFILIATION_FIELDS, [
            ["a1", "p1", "sample", "1", None, None, None, "s1"],
            ["a2", "p2", "other", "2", None, None, None, "s2"],
        ])
        self.csv(self.source / "governing-bodies.csv", ["authority_id", "authority_name"], [["r1", "Example region"]])
        (self.source / "governing-bodies.manifest.json").write_text(json.dumps({"governing_bodies":1, "file":{"sha256":self.sha(self.source / "governing-bodies.csv")}}))
        self.csv(self.source / "source-catalog.csv", ["source_id", "collection_status"], [["s1", "imported"], ["s2", "imported"]])
        self.output = self.root / "directory.duckdb"

    def sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def csv(self, path, fields, rows):
        with path.open("w", newline="") as f:
            w = csv.writer(f); w.writerow(fields); w.writerows(rows)

    def write(self, table, fields, rows):
        path = self.source / "snapshot" / (table + ".csv")
        self.csv(path, fields, rows)
        self.manifest[table + "_sha256"] = self.sha(path)
        (self.source / "snapshot/manifest.json").write_text(json.dumps(self.manifest))

    def test_queries_keep_programs_entities_and_overlap_candidates_distinct(self):
        import duckdb
        result = build_directory(self.source, self.output)
        self.assertEqual(result["programs"], 2)
        self.assertEqual(result["organizations"], 2)
        self.assertFalse(result["cross_source_entities_merged"])
        self.assertEqual(result["shared_website_candidate_groups"], 1)
        with duckdb.connect(str(self.output), read_only=True) as db:
            self.assertEqual(db.sql("SELECT sum(verified_active_programs) FROM coverage_by_source").fetchone()[0], 0)
            self.assertEqual(db.sql("SELECT count(*) FROM provenance").fetchone()[0], 2)
            self.assertEqual(db.sql("SELECT sum(source_scoped_programs) FROM coverage_by_state").fetchone()[0], 2)
        with self.assertRaises(FileExistsError):
            build_directory(self.source, self.output)

    def test_changed_bytes_fail_before_output(self):
        with (self.source / "snapshot/programs.csv").open("a") as f: f.write("tampered\n")
        with self.assertRaises(ValueError): build_directory(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_orphan_or_duplicate_ids_fail_atomically(self):
        self.program_rows[0][1] = "absent"
        self.write("programs", FIELDS, self.program_rows)
        with self.assertRaises(ValueError): build_directory(self.source, self.output)
        self.assertFalse(self.output.exists())
        self.program_rows[0][1] = "o1"
        self.program_rows[1][0] = "p1"
        self.write("programs", FIELDS, self.program_rows)
        with self.assertRaises(ValueError): build_directory(self.source, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".directory-*")), [])

    def test_extra_columns_are_rejected_even_with_a_matching_content_hash(self):
        self.write("programs", (*FIELDS, "private_contact"), [
            [*row, "private@example.invalid"] for row in self.program_rows
        ])
        with self.assertRaises(ValueError): build_directory(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_facility_supplement_links_and_bad_program_references(self):
        from directory_catalog import write_catalog
        from test_directory_catalog import invented_catalog
        import duckdb
        tables = invented_catalog()
        catalog = self.source / "catalog"
        write_catalog(catalog, tables, {"purpose": "Invented"})
        result = build_directory(self.source, self.output)
        self.assertEqual(result["facilities"], 1)
        with duckdb.connect(str(self.output), read_only=True) as db:
            self.assertEqual(db.sql("SELECT organization_name, facility_name FROM program_locations").fetchall(),
                             [("Example Club", "Example Aquatic Center")])
            self.assertEqual(db.sql("SELECT count(*) FROM source_format_access").fetchone()[0], 1)
            self.assertEqual(db.sql("SELECT sum(source_scoped_programs), sum(programs_with_listed_location), sum(programs_without_listed_location) FROM program_location_coverage").fetchone(), (2, 1, 1))
            self.assertEqual(db.sql("SELECT count(*) FROM provenance").fetchone()[0], 3)
        tables["program_facilities"][0]["program_id"] = "absent"
        other = self.source / "bad-catalog"
        write_catalog(other, tables, {})
        for path in other.iterdir():
            (catalog / path.name).write_bytes(path.read_bytes())
        failed = self.root / "failed.duckdb"
        with self.assertRaises(ValueError): build_directory(self.source, failed)
        self.assertFalse(failed.exists())
        self.assertEqual(list(self.root.glob(".directory-*")), [])

    def test_authority_reviews_join_the_discovery_universe(self):
        import duckdb
        from test_authority_review import write_reviews
        self.csv(self.source / "governing-bodies.csv",
                 ["authority_id", "authority_name", "segment", "program_listing_status"],
                 [["r1", "Example region", "high_school", "swimming_not_reviewed"]])
        (self.source / "governing-bodies.manifest.json").write_text(json.dumps({"governing_bodies":1, "file":{"sha256":self.sha(self.source / "governing-bodies.csv")}}))
        write_reviews(self.source)
        result = build_directory(self.source, self.output)
        self.assertEqual(result["authority_homepage_reviews"], 1)
        with duckdb.connect(str(self.output), read_only=True) as db:
            self.assertEqual(db.sql("SELECT homepage_review_status, program_listing_status FROM authority_review_coverage").fetchall(),
                             [("homepage_cached", "swimming_not_reviewed")])
        write_reviews(self.source, authority_id="unrelated")
        failed = self.root / "failed.duckdb"
        with self.assertRaises(ValueError): build_directory(self.source, failed)
        self.assertFalse(failed.exists())
