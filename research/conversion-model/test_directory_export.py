"""Invented organization facts only; no network or real directory in tests."""
import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from directory_export import FIELDS, ORGANIZATION_FIELDS, export_directory, public_website


@unittest.skipUnless(os.environ.get("TURNMARK_LAKEHOUSE_TESTS") == "1", "Optional DuckDB")
class DirectoryExportTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dbpath = self.root / "registry.duckdb"
        with duckdb.connect(str(self.dbpath)) as db:
            db.execute(Path(__file__).with_name("team-registry.sql").read_text())
            db.execute("""
                INSERT INTO registry_sources VALUES
                ('directory', 'https://example.test/teams', now(), repeat('0',64), 'Synthetic'),
                ('historical', 'https://example.test/meet', now(), repeat('1',64), 'Synthetic');
                INSERT INTO organizations VALUES
                ('a', 'Example Club', 'club', 'US', 'CA', 'Sample', NULL, 'directory'),
                ('b', 'Other Club', 'club', 'US', 'NY', NULL, NULL, 'historical');
                INSERT INTO programs VALUES
                ('pa','a','Example Club','age_group','pool_swimming','unknown','unknown',NULL,NULL,'2026-01-01','directory'),
                ('pb','b','Other Club','unknown','unknown','unknown','unknown',NULL,NULL,'2026-01-01','historical');
                CREATE TABLE private_athletes(name VARCHAR, email VARCHAR);
                INSERT INTO private_athletes VALUES ('DO NOT EXPORT', 'private@example.test');
            """)
        self.selection = self.root / "selection.json"
        self.selection.write_text(json.dumps({"scope":"organization-directory-facts", "source_ids":["directory"], "review_notes":"Invented facts only"}))

    def test_only_selected_organizational_facts_and_fixed_columns_are_exported(self):
        out = self.root / "public"
        manifest = export_directory(self.dbpath, self.selection, out)
        with (out / "programs.csv").open() as f:
            reader = csv.DictReader(f)
            self.assertEqual(tuple(reader.fieldnames), FIELDS)
            rows = list(reader)
        self.assertEqual(len(rows), 1)
        with (out / "organizations.csv").open() as f:
            reader = csv.DictReader(f)
            self.assertEqual(tuple(reader.fieldnames), ORGANIZATION_FIELDS)
            organizations = list(reader)
        self.assertEqual([r["organization_id"] for r in organizations], ["a"])
        self.assertEqual(manifest["source_scoped_organizations"], len(organizations))
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(rows[0]["status"], "unknown")
        self.assertEqual(manifest["programs"], 1)
        self.assertFalse(manifest["national_coverage_verified"])
        self.assertEqual(len(manifest["sources"]), 1)
        self.assertNotIn("DO NOT EXPORT", "".join(p.read_text() for p in out.iterdir()))
        with self.assertRaises(FileExistsError):
            export_directory(self.dbpath, self.selection, out)

    def test_missing_or_duplicate_sources_fail_without_creating_an_export(self):
        for ids in (["absent"], ["directory", "directory"]):
            selection = json.loads(self.selection.read_text())
            selection["source_ids"] = ids
            self.selection.write_text(json.dumps(selection))
            with self.assertRaises(ValueError):
                export_directory(self.dbpath, self.selection, self.root / "bad")
            self.assertFalse((self.root / "bad").exists())


class PublicWebsiteTests(unittest.TestCase):
    def test_contact_urls_and_unreviewed_query_fields_are_omitted(self):
        self.assertIsNone(public_website("https://coach@example.test"))
        self.assertIsNone(public_website("https://example.test/?token=private"))
        self.assertIsNone(public_website("mailto:coach@example.test"))
        self.assertEqual(public_website("https://example.test/team?team=TOY&utm_source=finder#map"), "https://example.test/team?team=TOY")
