"""Offline, evidence-backed venue sidecar and descriptive race-pair cohorts.

Never geocode club addresses, infer pools from meet names, correct clocks or fit
models. Real registry inputs, mappings and annotated pairs must stay gitignored.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = {
    "venue_sources": ("source_id", "source_url", "checked_at", "content_sha256", "reuse_notes"),
    "facilities": ("facility_id", "name", "country", "state", "city", "evidence_source_id"),
    "pools": ("pool_id", "facility_id", "name", "elevation_m", "elevation_uncertainty_m",
              "elevation_source_id", "evidence_source_id"),
    "pool_configurations": ("configuration_id", "pool_id", "course", "valid_from", "valid_to", "evidence_source_id"),
    "race_venues": ("source", "race_id", "configuration_id", "time_basis", "evidence_source_id"),
}
COHORTS = ("unresolved_venue", "non_raw_or_unknown_basis", "same_pool",
           "same_facility_different_pools", "different_facilities")


def create_registry(document: Path, output: Path):
    """Build a fresh DuckDB atomically from one strict reviewed JSON document."""
    import duckdb

    if output.exists():
        raise FileExistsError("Use a fresh venue registry path")
    content = json.loads(document.read_text())
    if set(content) != {"schema_version", *FIELDS} or type(content["schema_version"]) is not int or content["schema_version"] != 1:
        raise ValueError("Expected venue registry schema v1 and its fixed tables")
    for table, fields in FIELDS.items():
        if not isinstance(content[table], list):
            raise ValueError("Venue table must be an array: " + table)
        for row in content[table]:
            if not isinstance(row, dict) or set(row) != set(fields):
                raise ValueError("Unexpected venue fields; no contacts or raw payloads")
            for key, value in row.items():
                if key in ("elevation_m", "elevation_uncertainty_m"):
                    if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                        raise ValueError("Elevation must be finite numeric meters or null")
                elif value is not None and (not isinstance(value, str) or not value.strip()):
                    raise ValueError("Venue text must be nonempty strings or null")
                if value is None and key not in ("country", "state", "city", "elevation_m",
                                                 "elevation_uncertainty_m", "elevation_source_id"):
                    raise ValueError("Missing required venue fact: " + key)
            if table == "venue_sources":
                url = urlsplit(row["source_url"])
                if url.scheme != "https" or not url.hostname or url.username or url.password:
                    raise ValueError("Venue evidence needs a public HTTPS source URL")
                checked = datetime.fromisoformat(row["checked_at"].replace("Z", "+00:00"))
                if checked.tzinfo is None:
                    raise ValueError("Evidence check date needs a timezone")
                sha = row["content_sha256"]
                if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
                    raise ValueError("Evidence needs its source-content SHA-256")
            if table == "pool_configurations":
                for key in ("valid_from", "valid_to"):
                    if date.fromisoformat(row[key]).isoformat() != row[key]:
                        raise ValueError("Configuration dates must use YYYY-MM-DD")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".venues-", suffix=".duckdb", dir=output.parent)
    os.close(fd)
    temporary = Path(name)
    temporary.unlink()
    try:
        with duckdb.connect(str(temporary)) as db:
            db.execute(Path(__file__).with_name("venue-registry.sql").read_text())
            db.execute("BEGIN TRANSACTION")
            for table, fields in FIELDS.items():
                rows = [tuple(row[field] for field in fields) for row in content[table]]
                if rows:
                    db.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in fields)})", rows)
            db.execute("COMMIT")
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {table: len(content[table]) for table in FIELDS}


def venue_index(database: Path):
    import duckdb

    with duckdb.connect(str(database), read_only=True) as db:
        rows = db.execute("""
            SELECT r.source, r.race_id, f.facility_id, p.pool_id,
                   c.configuration_id, c.course, c.valid_from, c.valid_to,
                   p.elevation_m, p.elevation_uncertainty_m, p.elevation_source_id,
                   r.time_basis, r.evidence_source_id, c.evidence_source_id,
                   p.evidence_source_id, f.evidence_source_id
            FROM race_venues r JOIN pool_configurations c USING (configuration_id)
            JOIN pools p USING (pool_id) JOIN facilities f USING (facility_id)
        """).fetchall()
    keys = ("facility_id", "pool_id", "configuration_id", "course", "valid_from", "valid_to",
            "elevation_m", "elevation_uncertainty_m", "elevation_source_id", "time_basis",
            "mapping_source_id", "configuration_source_id", "pool_source_id", "facility_source_id")
    return {(row[0], row[1]): dict(zip(keys, row[2:])) for row in rows}


def classify_pairs(pairs, index):
    """Annotate existing frozen pairs. No re-pairing, split changes or corrections."""
    annotated = []
    swimmer_partitions, used_races = {}, set()
    for pair in pairs:
        a, b = pair["source"], pair["target"]
        athlete = (a["source"], a["swimmer_id"])
        if (athlete != (b["source"], b["swimmer_id"]) or
                json.loads(pair["swimmer_key"]) != list(athlete) or
                pair["partition"] not in ("train", "validation", "test") or
                (a["course"], b["course"]) != ("SCY", "LCM") or
                any(a[k] != b[k] for k in ("distance", "stroke", "category"))):
            raise ValueError("Expected source-scoped same-event SCY/LCM pilot pairs")
        previous = swimmer_partitions.setdefault(athlete, pair["partition"])
        if previous != pair["partition"]:
            raise ValueError("Swimmer crosses frozen partitions")
        for race in (a,b):
            key = (race["source"], race["race_id"])
            if key in used_races:
                raise ValueError("Race reused across pairs")
            used_races.add(key)
        contexts = []
        for side in ("source", "target"):
            race = pair[side]
            context = index.get((race["source"], race["race_id"]))
            if context:
                day = date.fromisoformat(race["date"])
                if context["course"] != race["course"] or not context["valid_from"] <= day <= context["valid_to"]:
                    raise ValueError("Venue configuration conflicts with a race's course/date")
            contexts.append(context)
        a, b = contexts
        if not a or not b:
            cohort = "unresolved_venue"
        elif a["time_basis"] != "raw" or b["time_basis"] != "raw":
            cohort = "non_raw_or_unknown_basis"
        elif a["pool_id"] == b["pool_id"]:
            cohort = "same_pool"
        elif a["facility_id"] == b["facility_id"]:
            cohort = "same_facility_different_pools"
        else:
            cohort = "different_facilities"
        known_elevation = bool(a and b and a["elevation_m"] is not None and b["elevation_m"] is not None)
        annotated.append({**pair, "venue_context": {"cohort": cohort,
            "both_elevations_known": known_elevation,
            "source": a, "target": b}})
    return annotated


def cohort_report(pairs):
    """Aggregates only: no swimmers, meet IDs, facility IDs or per-race clocks."""
    rows = []
    for cohort in COHORTS:
        subset = [p for p in pairs if p["venue_context"]["cohort"] == cohort]
        pools = {p["venue_context"][side]["pool_id"] for p in subset for side in ("source", "target")
                 if p["venue_context"][side]}
        rows.append({"cohort": cohort, "pairs": len(subset),
                     "swimmers": len({p["swimmer_key"] for p in subset}),
                     "meets": len({(p[side]["source"], p[side]["meet_id"]) for p in subset for side in ("source", "target")}),
                     "pools": len(pools),
                     "both_elevations_known": sum(p["venue_context"]["both_elevations_known"] for p in subset),
                     "partitions": dict(sorted(Counter(p["partition"] for p in subset).items()))})
    return {"pairs": len(pairs), "cohorts": rows, "clocks_changed": False,
            "partitions_changed": False, "altitude_model_trained": False,
            "validated_for_product": False}


def enrichment_queue(pairs):
    """Private meet-level review queue, prioritized by missing paired-race coverage.

    Counts and dates guide evidence acquisition; outcome times never rank meets.
    Individual race IDs/swimmer keys are not emitted even in this local queue.
    """
    groups = {}
    for pair in pairs:
        for side in ("source", "target"):
            context = pair["venue_context"][side]
            if context and context["time_basis"] != "unknown":
                continue
            race = pair[side]
            key = (race["source"], race["meet_id"])
            row = groups.setdefault(key, {"races": set(), "swimmers": set(), "courses": set(),
                                          "dates": set(), "mapping_missing": 0, "basis_unknown": 0})
            row["races"].add((race["source"], race["race_id"]))
            row["swimmers"].add(pair["swimmer_key"])
            row["courses"].add(race["course"])
            row["dates"].add(race["date"])
            row["mapping_missing" if context is None else "basis_unknown"] += 1
    return sorted([{"source": source, "meet_id": meet, "paired_races_to_review": len(row["races"]),
                    "paired_swimmers": len(row["swimmers"]), "courses": sorted(row["courses"]),
                    "dates": sorted(row["dates"]), "mapping_missing": row["mapping_missing"],
                    "basis_unknown": row["basis_unknown"]}
                   for (source, meet), row in groups.items()],
                  key=lambda row: (-row["paired_races_to_review"], row["source"], row["meet_id"]))


def audit(pairs_path: Path, database: Path, output: Path):
    if output.exists():
        raise FileExistsError("Use a fresh venue cohort output directory")
    pairs = classify_pairs(json.loads(pairs_path.read_text()), venue_index(database))
    report = {**cohort_report(pairs),
              "pairs_sha256": hashlib.sha256(pairs_path.read_bytes()).hexdigest(),
              "registry_sha256": hashlib.sha256(database.read_bytes()).hexdigest()}
    output.mkdir(parents=True)
    (output / "pairs-with-venues.json").write_text(json.dumps(pairs, default=lambda v: v.isoformat(), indent=2) + "\n")
    (output / "meet-enrichment-queue.json").write_text(json.dumps(enrichment_queue(pairs), indent=2) + "\n")
    (output / "venue-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("document", type=Path)
    create.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("audit")
    check.add_argument("pairs", type=Path)
    check.add_argument("--registry", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = create_registry(args.document, args.output) if args.command == "create" else audit(args.pairs, args.registry, args.output)
    print(json.dumps(result, indent=2))
