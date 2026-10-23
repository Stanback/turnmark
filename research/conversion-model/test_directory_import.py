"""Invented listings exercise source identity, publication boundaries and rollback."""
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path

from directory_import import identity, import_directory


@unittest.skipUnless(os.environ.get("TURNMARK_LAKEHOUSE_TESTS") == "1", "Optional DuckDB")
class DirectoryImportTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.db = duckdb.connect()
        self.addCleanup(self.db.close)
        self.db.execute(Path(__file__).with_name("team-registry.sql").read_text())
        self.row = dict(organization_key="17", organization_name="Sample University",
                        organization_kind="school", country="unknown", state=None,
                        city=None, website="https://example.test/", program_key="17:MSW",
                        program_name="Sample University · Men's swimming and diving",
                        program_kind="collegiate_varsity", discipline="swimming_and_diving",
                        category="men", authority="example", authority_id="17",
                        jurisdiction="source academicYear 2027")

    def add(self, rows, source="listing"):
        return import_directory(self.db, source_id=source, source_url="https://example.test/directory",
                                retrieved_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
                                content_sha256="a" * 64, reuse_notes="Synthetic", records=rows)

    def test_categories_share_org_but_not_program_and_unrelated_authorities_stay_separate(self):
        women = {**self.row, "program_key":"17:WSW", "category":"women"}
        self.add([self.row, women])
        self.add([{**self.row, "authority":"unrelated"}], "other")
        self.assertEqual(self.db.sql("SELECT count(*) FROM organizations").fetchone()[0], 2)
        self.assertEqual(self.db.sql("SELECT count(*) FROM programs").fetchone()[0], 3)
        self.assertEqual(self.db.sql("SELECT DISTINCT status, valid_from, valid_to FROM programs").fetchall(), [("unknown", None, None)])
        self.assertNotEqual(identity("program", "a:b", "c"), identity("program", "a", "b:c"))

    def test_contacts_unknown_types_and_duplicates_fail_before_import(self):
        for rows in ([{**self.row, "email":"private@example.test"}],
                     [{**self.row, "program_kind":"invented"}], [self.row, self.row]):
            with self.assertRaises(ValueError): self.add(rows)
        self.assertEqual(self.db.sql("SELECT count(*) FROM registry_sources").fetchone()[0], 0)

    def test_conflicting_existing_facts_roll_back_source_and_program(self):
        self.add([self.row])
        with self.assertRaises(ValueError):
            self.add([{**self.row, "organization_name":"Different", "program_key":"new"}], "conflict")
        self.assertEqual(self.db.sql("SELECT count(*) FROM registry_sources").fetchone()[0], 1)
        self.assertEqual(self.db.sql("SELECT count(*) FROM programs").fetchone()[0], 1)
