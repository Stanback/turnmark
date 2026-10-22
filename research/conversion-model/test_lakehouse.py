"""Opt-in integration tests use invented records only; no downloads during tests."""

import csv
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from lakehouse import REQUIRED, OPTIONAL_CONTEXT, build, probe, read_snapshot


@unittest.skipUnless(
    os.environ.get("TURNMARK_LAKEHOUSE_TESTS") == "1",
    "Optional lakehouse dependencies/extension; see README setup",
)
class LakehouseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "quoted ' path"
        self.root.mkdir()
        self.csv = self.root / "results.csv"
        self.manifest = self.root / "manifest.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "source_url": "synthetic fixture",
                    "retrieved": "2026-10-19",
                    "reuse_notes": "Invented test records",
                    "age_precision": "whole years",
                    "synthetic": True,
                }
            )
        )
        self.rows = [
            dict(zip(REQUIRED, values))
            for values in (
                (
                    "fixture's",
                    "r1",
                    "a",
                    "m1",
                    "2025-12-20",
                    "SCY",
                    100,
                    "freestyle",
                    "women",
                    5832,
                    "OK",
                    15,
                ),
                (
                    "fixture's",
                    "r2",
                    "a",
                    "m2",
                    "2026-01-05",
                    "LCM",
                    100,
                    "freestyle",
                    "women",
                    6672,
                    "OK",
                    15,
                ),
                (
                    "other",
                    "r1",
                    "a",
                    "m1",
                    "2026-01-05",
                    "SCM",
                    100,
                    "backstroke",
                    "men",
                    7000,
                    "OK",
                    "",
                ),
            )
        ]
        self.write(self.rows)

    def write(self, rows):
        with self.csv.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=(*REQUIRED, *OPTIONAL_CONTEXT))
            writer.writeheader()
            writer.writerows(rows)

    def test_snapshot_roundtrip_partitioning_and_indexed_projection(self):
        self.rows[0]["region"] = "Invented region"
        self.write(self.rows + [self.rows[0]])
        output = self.root / "snapshot"
        report = build(self.csv, self.manifest, output)
        self.assertEqual((report["rows"], report["duplicates"]), (3, 1))
        self.assertEqual(len(report["active_data_files"]), 3)
        result = probe(output)
        self.assertEqual(
            read_snapshot(self.csv)[0]
            .column("region")
            .to_pylist()
            .count("Invented region"),
            1,
        )
        self.assertTrue(result["history_matches_iceberg"])
        self.assertEqual(sum(row["races"] for row in result["cohorts"]), 3)
        # Aggregate reports must not leak athlete keys or race-level times.
        self.assertNotIn('swimmer_id":', json.dumps(result))
        self.assertNotIn('"time_cs":', json.dumps(result))
        self.assertNotIn("fixture's", json.dumps(result))
        with self.assertRaises(FileExistsError):
            build(self.csv, self.manifest, output)

    def test_later_catalog_commit_does_not_change_pinned_research_snapshot(self):
        import duckdb
        from pyiceberg.catalog import load_catalog

        output = self.root / "snapshot"
        report = build(self.csv, self.manifest, output)
        catalog = load_catalog(
            "local",
            type="sql",
            uri=f"sqlite:///{output / 'catalog.sqlite3'}",
            warehouse=(output / "warehouse").as_uri(),
        )
        table = catalog.load_table("research.races")
        self.write([{**self.rows[0], "race_id": "new-race"}])
        table.append(read_snapshot(self.csv)[0])
        self.assertNotEqual(
            table.current_snapshot().snapshot_id, report["iceberg_snapshot_id"]
        )
        self.assertEqual(table.scan().to_arrow().num_rows, 4)
        catalog.close()
        with duckdb.connect(str(output / "queries.duckdb"), read_only=True) as db:
            db.execute("LOAD iceberg")
            self.assertEqual(db.sql("SELECT count(*) FROM races").fetchone()[0], 3)
            self.assertEqual(
                db.sql("SELECT count(*) FROM parquet_snapshot").fetchone()[0], 3
            )

    def test_probe_detects_stale_or_corrupted_hot_projection(self):
        output = self.root / "snapshot"
        build(self.csv, self.manifest, output)
        with closing(sqlite3.connect(output / "hot.sqlite3")) as db, db:
            db.execute("UPDATE races SET time_cs = time_cs + 1")
        with self.assertRaisesRegex(ValueError, "projection differs"):
            probe(output)

    def test_validation_rejects_conflicts_nonfinite_age_and_seed_records(self):
        for replacement in (
            {"time_cs": 6000},
            {"age_years": "nan"},
            {"status": "SEED"},
            {"time_cs": "58.32"},
        ):
            self.write(self.rows + [{**self.rows[0], **replacement}])
            with self.assertRaises(ValueError):
                read_snapshot(self.csv)
        self.write(self.rows)
        with self.assertRaisesRegex(ValueError, "row budget"):
            read_snapshot(self.csv, max_rows=2)
        self.write([])
        with self.assertRaisesRegex(ValueError, "Empty snapshot"):
            read_snapshot(self.csv)


if __name__ == "__main__":
    unittest.main()
