"""Opt-in integration tests use invented records only; no downloads during tests."""

import csv
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

from lakehouse import (
    HOT_COLUMNS,
    OPTIONAL_CONTEXT,
    REQUIRED,
    build,
    literal,
    probe,
    read_snapshot,
    rebuild_hot,
)


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

    def test_measured_snapshot_follows_the_view_selector_and_quoted_paths(self):
        import duckdb
        from pyiceberg.catalog import load_catalog
        from evaluate_and_train import measure_lakehouse_view

        output = self.root / "measured"
        report = build(self.csv, self.manifest, output)
        # The fixture lives under a path containing a quote.
        self.assertEqual(
            measure_lakehouse_view(output / "queries.duckdb"),
            {"iceberg_snapshot_id": report["iceberg_snapshot_id"], "rows": 3},
        )
        catalog = load_catalog(
            "local",
            type="sql",
            uri=f"sqlite:///{output / 'catalog.sqlite3'}",
            warehouse=(output / "warehouse").as_uri(),
        )
        table = catalog.load_table("research.races")
        self.write([{**self.rows[0], "race_id": "new-race"}])
        table.append(read_snapshot(self.csv)[0])
        latest = table.metadata_location
        catalog.close()
        old = report["iceberg_snapshot_id"]
        for name, options, expected in (
            ("pinned.duckdb", f", snapshot_from_id={old}", {"iceberg_snapshot_id": old, "rows": 3}),
            ("timestamp.duckdb", ", snapshot_from_timestamp=TIMESTAMP '2026-01-01'", ValueError),
        ):
            with duckdb.connect(str(self.root / name)) as db:
                db.execute("LOAD iceberg")
                db.execute(f"CREATE VIEW races AS SELECT * FROM iceberg_scan({literal(latest)}{options})")
            if expected is ValueError:
                with self.assertRaises(ValueError):
                    measure_lakehouse_view(self.root / name)
            else:
                self.assertEqual(measure_lakehouse_view(self.root / name), expected)

    def test_duckdb_loader_keeps_a_valid_round_behind_an_impossible_one(self):
        import duckdb
        from datetime import date
        from evaluate_and_train import SwimRecord, deduplicate_best_of_meet, load_swims_from_duckdb

        db_path = self.root / "rounds.duckdb"
        rounds = [
            # An impossible 10.00 100-yard freestyle final next to a valid 58.32 prelim.
            ("src", "prelim", "s1", "m1", date(2026, 1, 5), "SCY", 100, "freestyle", "women", 5832, 15.0, "R"),
            ("src", "final", "s1", "m1", date(2026, 1, 5), "SCY", 100, "freestyle", "women", 1000, 15.0, "R"),
        ]
        with duckdb.connect(str(db_path)) as db:
            db.execute(
                "CREATE TABLE races (source VARCHAR, race_id VARCHAR, swimmer_id VARCHAR, meet_id VARCHAR, "
                "race_date DATE, course VARCHAR, distance INTEGER, stroke VARCHAR, category VARCHAR, "
                "time_cs INTEGER, age_years DOUBLE, region VARCHAR)"
            )
            db.executemany("INSERT INTO races VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rounds)
        from_duckdb, _ = deduplicate_best_of_meet(load_swims_from_duckdb(db_path))
        from_csv, _ = deduplicate_best_of_meet(SwimRecord(*row) for row in rounds)
        self.assertEqual([r.race_id for r in from_duckdb], ["prelim"])
        self.assertEqual([r.race_id for r in from_duckdb], [r.race_id for r in from_csv])

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
            db.execute("UPDATE race_rows SET time_cs = time_cs + 1")
        with self.assertRaisesRegex(ValueError, "projection differs"):
            probe(output)

    def test_rebuild_hot_restores_the_projection_from_the_pinned_snapshot(self):
        output = self.root / "snapshot"
        report = build(self.csv, self.manifest, output)
        with closing(sqlite3.connect(output / "hot.sqlite3")) as db, db:
            db.execute("UPDATE race_rows SET time_cs = time_cs + 1")
        rebuilt = rebuild_hot(output)
        self.assertEqual(rebuilt["iceberg_snapshot_id"], report["iceberg_snapshot_id"])
        self.assertEqual(
            rebuilt["hot_sqlite_bytes"], (output / "hot.sqlite3").stat().st_size
        )
        self.assertTrue(probe(output)["history_matches_iceberg"])
        # The compatibility view returns exactly the snapshot's rows and values.
        columns = ", ".join(HOT_COLUMNS)
        with closing(sqlite3.connect(output / "hot.sqlite3")) as db:
            hot = sorted(db.execute(f"SELECT {columns} FROM races").fetchall())
        expected = sorted(
            tuple(
                value.isoformat() if isinstance(value, date) else value
                for value in row.values()
            )
            for row in read_snapshot(self.csv)[0].select(HOT_COLUMNS).to_pylist()
        )
        self.assertEqual(hot, expected)

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
