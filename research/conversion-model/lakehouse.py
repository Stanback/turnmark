"""Local Iceberg/Parquet query experiment, with a rebuildable SQLite hot projection.

`rebuild-hot` replaces the SQLite projection from the committed Iceberg snapshot.

No network ingestion, cloud credentials, uploads or model training. Outputs contain
private race-level data: keep them under ignored target/ or outside the repository.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import statistics
import time
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path


REQUIRED = (
    "source",
    "race_id",
    "swimmer_id",
    "meet_id",
    "date",
    "course",
    "distance",
    "stroke",
    "category",
    "time_cs",
    "status",
    "age_years",
)
HOT_COLUMNS = (
    "source",
    "race_id",
    "swimmer_id",
    "meet_id",
    "race_date",
    "course",
    "distance",
    "stroke",
    "category",
    "time_cs",
)
OPTIONAL_CONTEXT = ("region", "meet_class", "round", "archive_id", "date_precision")
# Repeated keys live once in small dimension tables; each race row and its two
# indexes carry only integers. A 64-character hashed ID repeated in the table and
# in every index made the earlier layout about 813 bytes a race. Uniqueness of
# (source, race_id) is enforced by read_snapshot, so no index stores race_id.
HOT_SCHEMA = """
CREATE TABLE swimmers (
    id INTEGER PRIMARY KEY, source TEXT NOT NULL, swimmer_id TEXT NOT NULL,
    UNIQUE (source, swimmer_id)
);
CREATE TABLE meets (
    id INTEGER PRIMARY KEY, source TEXT NOT NULL, meet_id TEXT NOT NULL,
    UNIQUE (source, meet_id)
);
CREATE TABLE events (
    id INTEGER PRIMARY KEY, course TEXT NOT NULL, distance INTEGER NOT NULL,
    stroke TEXT NOT NULL, category TEXT NOT NULL,
    UNIQUE (course, distance, stroke, category)
);
CREATE TABLE race_rows (
    id INTEGER PRIMARY KEY, swimmer INTEGER NOT NULL REFERENCES swimmers,
    race_day INTEGER NOT NULL, meet INTEGER NOT NULL REFERENCES meets,
    event INTEGER NOT NULL REFERENCES events, time_cs INTEGER NOT NULL,
    race_id TEXT NOT NULL
);
CREATE INDEX athlete_history ON race_rows(swimmer, race_day DESC);
CREATE INDEX meet_results ON race_rows(meet, event, time_cs);
CREATE VIEW races AS
SELECT s.source, r.race_id, s.swimmer_id, m.meet_id,
       date(r.race_day * 86400, 'unixepoch') AS race_date,
       e.course, e.distance, e.stroke, e.category, r.time_cs
FROM race_rows r
JOIN swimmers s ON s.id = r.swimmer
JOIN meets m ON m.id = r.meet
JOIN events e ON e.id = r.event;
"""
HISTORY_SQL = """SELECT r.race_id, r.time_cs FROM race_rows r
JOIN swimmers s ON s.id = r.swimmer WHERE s.source = ? AND s.swimmer_id = ?
ORDER BY r.race_day DESC, r.id LIMIT 50"""


def literal(value: str) -> str:
    """Quote paths for SQL statements that cannot take bound view parameters."""
    return "'" + value.replace("'", "''") + "'"


def read_snapshot(path: Path, max_rows: int = 1_000_000):
    """Validate actual results of all events; this is broader than model eligibility."""
    import pyarrow as pa

    schema = pa.schema(
        [
            ("source", pa.string()),
            ("race_id", pa.string()),
            ("swimmer_id", pa.string()),
            ("meet_id", pa.string()),
            ("race_date", pa.date32()),
            ("course", pa.string()),
            ("distance", pa.int32()),
            ("stroke", pa.string()),
            ("category", pa.string()),
            ("time_cs", pa.int64()),
            ("age_years", pa.float64()),
            ("year", pa.int32()),
            *((name, pa.string()) for name in OPTIONAL_CONTEXT),
        ]
    )
    rows = {}
    duplicates = 0
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not set(REQUIRED) <= set(reader.fieldnames or []):
            raise ValueError("Missing normalized result columns")
        for line, record in enumerate(reader, 2):
            try:
                if record["status"] != "OK":
                    raise ValueError(
                        "Only valid actual finishes belong in this snapshot"
                    )
                if any(not record[key].strip() for key in REQUIRED[:4]):
                    raise ValueError("Missing source-scoped identity")
                day = date.fromisoformat(record["date"])
                distance, clock = int(record["distance"]), int(record["time_cs"])
                age = float(record["age_years"]) if record["age_years"] else None
                if distance <= 0 or clock <= 0:
                    raise ValueError(
                        "Distance and integer centiseconds must be positive"
                    )
                if age is not None and (not math.isfinite(age) or not 0 < age <= 110):
                    raise ValueError("Invalid age")
                if record["course"] not in {"SCY", "SCM", "LCM"}:
                    raise ValueError("Invalid course")
                if record["category"] not in {"women", "men"}:
                    raise ValueError("Unsupported published category")
                if record["stroke"] not in {
                    "freestyle",
                    "backstroke",
                    "breaststroke",
                    "butterfly",
                    "individual-medley",
                }:
                    raise ValueError("Invalid stroke")
                row = {key: record[key] for key in REQUIRED[:4]}
                row.update(
                    race_date=day,
                    course=record["course"],
                    distance=distance,
                    stroke=record["stroke"],
                    category=record["category"],
                    time_cs=clock,
                    age_years=age,
                    year=day.year,
                )
                # Preserve archive/cohort context without inventing absent metadata.
                row.update(
                    {name: record.get(name) or None for name in OPTIONAL_CONTEXT}
                )
                key = (row["source"], row["race_id"])
                if key in rows:
                    if rows[key] != row:
                        raise ValueError("Conflicting source/race identity")
                    duplicates += 1
                else:
                    rows[key] = row
                if len(rows) > max_rows:
                    raise ValueError("Snapshot exceeds local in-memory row budget")
            except (ValueError, TypeError) as error:
                # Do not echo swimmer-level rows or identifiers into logs.
                raise ValueError(
                    f"Invalid normalized result on line {line}: {error}"
                ) from error
    if not rows:
        raise ValueError("Empty snapshot")
    table = pa.Table.from_pylist(list(rows.values()), schema=schema)
    return table.sort_by(
        [
            (key, "ascending")
            for key in (
                "year",
                "course",
                "source",
                "swimmer_id",
                "race_date",
                "race_id",
            )
        ]
    ), duplicates


def create_hot(table, path: Path):
    """Use ordinary SQLite SQL supported by D1; never claim this benchmarks D1."""
    epoch = date(1970, 1, 1)
    keys = {"swimmers": {}, "meets": {}, "events": {}}

    def key(kind, value):
        return keys[kind].setdefault(value, len(keys[kind]) + 1)

    rows = [
        (
            key("swimmers", (row["source"], row["swimmer_id"])),
            (row["race_date"] - epoch).days,
            key("meets", (row["source"], row["meet_id"])),
            key(
                "events",
                (row["course"], row["distance"], row["stroke"], row["category"]),
            ),
            row["time_cs"],
            row["race_id"],
        )
        for row in table.select(HOT_COLUMNS).to_pylist()
    ]
    # Insert each swimmer's races together in (date, race_id) order, so row IDs
    # break same-day ties the way race IDs do and a history read stays local.
    rows.sort(key=lambda row: (row[0], row[1], row[5]))
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript(HOT_SCHEMA)
        for kind, width in (("swimmers", 2), ("meets", 2), ("events", 4)):
            db.executemany(
                f"INSERT INTO {kind} VALUES (?{', ?' * width})",
                ((ident, *value) for value, ident in keys[kind].items()),
            )
        db.executemany(
            "INSERT INTO race_rows (swimmer, race_day, meet, event, time_cs, race_id)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        db.execute("ANALYZE")
    with closing(sqlite3.connect(path)) as db:
        db.execute("VACUUM")


def rebuild_hot(output: Path):
    """Replace the hot projection from the committed Iceberg snapshot it mirrors."""
    import duckdb

    snapshot_path = output / "snapshot.json"
    snapshot = json.loads(snapshot_path.read_text())
    with duckdb.connect(str(output / "queries.duckdb"), read_only=True) as db:
        db.execute("LOAD iceberg")
        table = db.sql(f"SELECT {', '.join(HOT_COLUMNS)} FROM races").to_arrow_table()
    if table.num_rows != snapshot["rows"]:
        raise ValueError("Iceberg snapshot row count differs from snapshot.json")
    staged = output / "hot.sqlite3.new"
    staged.unlink(missing_ok=True)
    create_hot(table, staged)
    staged.replace(output / "hot.sqlite3")
    snapshot["hot_sqlite_bytes"] = (output / "hot.sqlite3").stat().st_size
    staged_report = output / "snapshot.json.new"
    staged_report.write_text(json.dumps(snapshot, indent=2) + "\n")
    staged_report.replace(snapshot_path)
    return snapshot


def build(csv_path: Path, manifest_path: Path, output: Path, max_rows=1_000_000):
    import duckdb
    import pyarrow
    import pyiceberg
    from pyiceberg.catalog import load_catalog
    from pyiceberg.partitioning import PartitionField, PartitionSpec
    from pyiceberg.transforms import IdentityTransform

    manifest = json.loads(manifest_path.read_text())
    for key in ("source_url", "retrieved", "reuse_notes", "age_precision", "synthetic"):
        if key not in manifest:
            raise ValueError(f"Missing manifest field: {key}")
    if not isinstance(manifest["synthetic"], bool):
        raise ValueError("Manifest synthetic flag must be a boolean")
    table, duplicates = read_snapshot(csv_path, max_rows)
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    # A failed build is deliberately unpublished: snapshot.json is written last.
    # Do not rename the warehouse afterwards; Iceberg records absolute file URIs.
    warehouse = output / "warehouse"
    catalog = load_catalog(
        "local",
        type="sql",
        uri=f"sqlite:///{output / 'catalog.sqlite3'}",
        warehouse=warehouse.as_uri(),
    )
    catalog.create_namespace("research")
    iceberg = catalog.create_table(
        "research.races",
        schema=table.schema,
        properties={"format-version": "2", "write.parquet.compression-codec": "zstd"},
    )
    spec = PartitionSpec(
        *[
            PartitionField(
                source_id=iceberg.schema().find_field(name).field_id,
                field_id=1000 + index,
                transform=IdentityTransform(),
                name=name,
            )
            for index, name in enumerate(("year", "course"))
        ]
    )
    with iceberg.update_spec() as update:
        for field in spec.fields:
            update.add_field(
                iceberg.schema().find_column_name(field.source_id),
                field.transform,
                field.name,
            )
    iceberg.append(table)
    active = sorted(task.file.file_path for task in iceberg.scan().plan_files())
    metadata = iceberg.metadata_location
    # Pin the catalog's committed metadata, never guess the latest filename or
    # glob a table's directory (which could include obsolete/deleted data).
    with duckdb.connect(str(output / "queries.duckdb")) as db:
        db.execute(
            "LOAD iceberg"
        )  # Install explicitly during setup, not implicitly here.
        db.execute(
            f"CREATE VIEW races AS SELECT * FROM iceberg_scan({literal(metadata)})"
        )
        files = ",".join(literal(path) for path in active)
        db.execute(
            f"CREATE VIEW parquet_snapshot AS SELECT * FROM read_parquet([{files}], hive_partitioning=false)"
        )
        if db.sql("SELECT count(*) FROM races").fetchone()[0] != table.num_rows:
            raise ValueError("Iceberg readback row count mismatch")
        # Full multiset equality catches field/type/value differences as well as count.
        difference = db.sql("""
            SELECT count(*) FROM (
              (SELECT * FROM races EXCEPT ALL SELECT * FROM parquet_snapshot)
              UNION ALL
              (SELECT * FROM parquet_snapshot EXCEPT ALL SELECT * FROM races)
            )
        """).fetchone()[0]
        if difference:
            raise ValueError("Iceberg/Parquet readback differs")
    create_hot(table, output / "hot.sqlite3")
    report = {
        "format_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "manifest": manifest,
        "rows": table.num_rows,
        "duplicates": duplicates,
        "iceberg_snapshot_id": iceberg.current_snapshot().snapshot_id,
        "iceberg_metadata": metadata,
        "active_data_files": active,
        "parquet_bytes": sum(
            Path(path.removeprefix("file://")).stat().st_size for path in active
        ),
        "hot_sqlite_bytes": (output / "hot.sqlite3").stat().st_size,
        "versions": {
            "duckdb": duckdb.__version__,
            "pyarrow": pyarrow.__version__,
            "pyiceberg": pyiceberg.__version__,
        },
        "validated_for_product": False,
    }
    catalog.close()
    (output / "snapshot.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def timed(call):
    start = time.perf_counter()
    result = call()
    return result, (time.perf_counter() - start) * 1000


def probe(output: Path):
    """Execute aggregate analytics + indexed history and verify cross-tier parity."""
    import duckdb

    snapshot = json.loads((output / "snapshot.json").read_text())
    db = duckdb.connect(str(output / "queries.duckdb"), read_only=True)
    try:
        db.execute("LOAD iceberg")
        cohorts = db.sql("""
            SELECT year, course, category, count(*) AS races,
                   count(DISTINCT (source, swimmer_id)) AS swimmers
            FROM races GROUP BY ALL ORDER BY year, course, category
        """).fetchall()
        first = db.sql(
            "SELECT source, swimmer_id FROM races ORDER BY source, swimmer_id LIMIT 1"
        ).fetchone()
        with closing(sqlite3.connect(output / "hot.sqlite3")) as hot:
            query = HISTORY_SQL
            history, hot_first = timed(lambda: hot.execute(query, first).fetchall())
            warm = [
                timed(lambda: hot.execute(query, first).fetchall())[1] for _ in range(5)
            ]
            expected = db.execute(
                """SELECT race_id, time_cs FROM races
                WHERE source=? AND swimmer_id=? ORDER BY race_date DESC, race_id LIMIT 50""",
                first,
            ).fetchall()
            if history != expected:
                raise ValueError(
                    "Hot projection differs from committed Iceberg snapshot"
                )
            plan = [row[3] for row in hot.execute("EXPLAIN QUERY PLAN " + query, first)]
            if not any("athlete_history" in line for line in plan):
                raise ValueError("History lookup does not use athlete index")
            if (
                hot.execute("SELECT count(*) FROM races").fetchone()[0]
                != snapshot["rows"]
            ):
                raise ValueError("Hot projection row count mismatch")
        year, course = cohorts[0][:2]
        sql = "SELECT category, count(*), avg(time_cs) FROM races WHERE year=? AND course=? GROUP BY category ORDER BY category"
        _, first_scan = timed(lambda: db.execute(sql, [year, course]).fetchall())
        scans = [
            timed(lambda: db.execute(sql, [year, course]).fetchall())[1]
            for _ in range(5)
        ]
        result = {
            "rows": snapshot["rows"],
            "parquet_bytes": snapshot["parquet_bytes"],
            "hot_sqlite_bytes": snapshot["hot_sqlite_bytes"],
            "parquet_bytes_per_row": snapshot["parquet_bytes"] / snapshot["rows"],
            "hot_bytes_per_row": snapshot["hot_sqlite_bytes"] / snapshot["rows"],
            "cohorts": [
                dict(zip(("year", "course", "category", "races", "swimmers"), row))
                for row in cohorts
            ],
            "history_index_plan": plan,
            "history_matches_iceberg": True,
            "local_ms": {
                "history_first": hot_first,
                "history_warm_median": statistics.median(warm),
                "filtered_iceberg_first": first_scan,
                "filtered_iceberg_warm_median": statistics.median(scans),
            },
            "timing_scope": "Single local process; caches are warm; not a D1/R2 latency or capacity benchmark",
            "validated_for_product": False,
        }
        (output / "probe.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("build")
    create.add_argument("csv", type=Path)
    create.add_argument("--manifest", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--max-rows", type=int, default=1_000_000)
    check = commands.add_parser("probe")
    check.add_argument("output", type=Path)
    rebuild = commands.add_parser("rebuild-hot")
    rebuild.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        report = build(args.csv, args.manifest, args.output, args.max_rows)
        # Aggregate metadata only. The full private manifest stays on disk.
        print(
            json.dumps(
                {
                    key: report[key]
                    for key in (
                        "rows",
                        "duplicates",
                        "parquet_bytes",
                        "hot_sqlite_bytes",
                    )
                }
            )
        )
    elif args.command == "rebuild-hot":
        report = rebuild_hot(args.output)
        print(json.dumps({key: report[key] for key in ("rows", "hot_sqlite_bytes")}))
    else:
        print(json.dumps(probe(args.output), indent=2))


if __name__ == "__main__":
    main()
