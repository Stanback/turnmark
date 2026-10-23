"""Offline public facility/source supplement: fixed columns, evidence and joins.

Consumes reviewed metadata only. Network acquisition and raw directory payloads
are intentionally outside this module; identities stay source-scoped.
"""
from __future__ import annotations
import csv
import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

SCHEMAS = {
    "evidence_sources": ("evidence_id", "catalog_source_id", "source_url", "retrieved_at", "content_sha256", "scope", "reuse_status"),
    "facilities": ("facility_id", "authority", "authority_id", "name", "address1", "address2", "city", "state", "state_raw", "postal_code", "country", "latitude", "longitude", "location_status", "evidence_id", "listing_checked"),
    "program_facilities": ("relation_id", "program_id", "facility_id", "authority_listing_id", "relationship", "status", "valid_from", "valid_to", "evidence_id"),
    "pool_basins": ("pool_id", "facility_id", "name", "length_m", "width_m", "geometry_notes", "elevation_m", "elevation_uncertainty_m", "elevation_basis", "evidence_id", "listing_checked"),
    "formats": ("format_id", "name", "kind", "public_adapter", "adapter_scope", "limitations", "specification_url"),
    "source_access": ("access_id", "catalog_source_id", "entry_url", "data_url", "http_method", "access_status", "request_contract", "collection_policy"),
    "source_formats": ("access_id", "format_id", "evidence_status", "notes"),
}
PRIMARY_KEYS = {table: fields[0] for table, fields in SCHEMAS.items() if table != "source_formats"}


def _url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username
            or parsed.password or any(c.isspace() for c in value)):
        raise ValueError("Require a public HTTP(S) evidence URL")


def _number(value, *, low, high):
    if value == "":
        return None
    number = float(value)
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError("Non-finite or out-of-range location/geometry")
    return number


def validate_tables(tables):
    if set(tables) != set(SCHEMAS):
        raise ValueError("Require exactly the allowlisted catalog tables")
    ids = {}
    for table, fields in SCHEMAS.items():
        seen = set()
        for row in tables[table]:
            if set(row) != set(fields) or any(not isinstance(v, str) for v in row.values()):
                raise ValueError("Unexpected catalog columns/types: " + table)
            if any(any(ord(c) < 32 for c in value) for value in row.values()):
                raise ValueError("Control characters in catalog facts")
            key = row[PRIMARY_KEYS[table]] if table in PRIMARY_KEYS else (row["access_id"], row["format_id"])
            if not key or key in seen:
                raise ValueError("Missing/duplicate catalog identity: " + table)
            seen.add(key)
            for field in ("source_url", "entry_url", "data_url", "specification_url"):
                if row.get(field): _url(row[field])
            for field in ("listing_checked", "valid_from", "valid_to"):
                if row.get(field): date.fromisoformat(row[field])
        ids[table] = seen
    for row in tables["evidence_sources"]:
        if not row["catalog_source_id"] or not row["source_url"] or not row["scope"] or not row["reuse_status"]:
            raise ValueError("Missing source evidence context")
        if not re.fullmatch(r"[0-9a-f]{64}", row["content_sha256"]):
            raise ValueError("Require original source SHA-256")
        stamp = datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00"))
        if stamp.tzinfo is None: raise ValueError("Require timezone-aware retrieval time")
    for table in ("facilities", "program_facilities", "pool_basins"):
        for row in tables[table]:
            if row["evidence_id"] not in ids["evidence_sources"]:
                raise ValueError("Unresolved source evidence")
    for row in tables["facilities"]:
        if not row["name"] or not row["authority"] or not row["authority_id"] or not row["listing_checked"]:
            raise ValueError("Missing facility identity/context")
        if row["location_status"] not in ("source_reported_unverified", "mailing_address_withheld", "operator_published"):
            raise ValueError("Unknown location evidence status")
        lat = _number(row["latitude"], low=-90, high=90)
        lon = _number(row["longitude"], low=-180, high=180)
        if (lat is None) != (lon is None) or (lat, lon) == (0, 0):
            raise ValueError("Require a coordinate pair; sentinel 0/0 is unknown")
        if row["location_status"] == "mailing_address_withheld" and any(row[k] for k in ("address1", "address2", "latitude", "longitude")):
            raise ValueError("Mailing address/coordinates must be withheld")
    source_keys = [(r["authority"], r["authority_id"]) for r in tables["facilities"]]
    if len(set(source_keys)) != len(source_keys): raise ValueError("Duplicate source facility key")
    for row in tables["program_facilities"]:
        if row["facility_id"] not in ids["facilities"] or not row["program_id"] or not row["authority_listing_id"]:
            raise ValueError("Unresolved program/facility relation")
        if row["relationship"] != "listed_training_location" or row["status"] != "unknown":
            raise ValueError("Directory listing is not verified operation or race location")
        if row["valid_to"] and row["valid_from"] and row["valid_to"] < row["valid_from"]:
            raise ValueError("Inverted listing validity")
    for row in tables["pool_basins"]:
        if row["facility_id"] not in ids["facilities"] or not row["name"] or not row["listing_checked"]:
            raise ValueError("Unresolved basin context")
        for field in ("length_m", "width_m"):
            _number(row[field], low=0.01, high=1000)
        elevation = _number(row["elevation_m"], low=-500, high=9000)
        uncertainty = _number(row["elevation_uncertainty_m"], low=0, high=10000)
        if row["elevation_basis"] not in ("unknown", "operator_published", "surveyed", "terrain_estimate"):
            raise ValueError("Unknown elevation basis")
        if (elevation is None) != (row["elevation_basis"] == "unknown") or (elevation is None and uncertainty is not None):
            raise ValueError("Elevation requires an explicit evidence basis")
    for row in tables["source_access"]:
        if not row["catalog_source_id"] or not row["entry_url"] or not row["collection_policy"]:
            raise ValueError("Missing source access context")
        if row["http_method"] not in ("GET", "POST", "unknown"):
            raise ValueError("Unexpected source method")
    for row in tables["source_formats"]:
        if row["access_id"] not in ids["source_access"] or row["format_id"] not in ids["formats"]:
            raise ValueError("Unresolved source-format reference")
        if row["evidence_status"] not in ("observed", "discovery_only"):
            raise ValueError("Unexpected format evidence status")


def read_catalog(root: Path):
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("schema_version") != 1 or manifest.get("scope") != "public-research-metadata":
        raise ValueError("Require public research catalog schema v1")
    if set(manifest["files"]) != set(SCHEMAS): raise ValueError("Unexpected catalog manifest tables")
    tables = {}
    for table, fields in SCHEMAS.items():
        path = root / (table + ".csv")
        receipt = manifest["files"][table]
        if hashlib.sha256(path.read_bytes()).hexdigest() != receipt["sha256"]:
            raise ValueError("Catalog CSV differs from its manifest: " + table)
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != fields: raise ValueError("Unexpected catalog columns: " + table)
            tables[table] = list(reader)
        if len(tables[table]) != receipt["rows"]: raise ValueError("Catalog count differs from manifest")
    validate_tables(tables)
    return tables, manifest


def write_catalog(output: Path, tables, review):
    """Publish a reviewed, already-projected metadata snapshot to a fresh path."""
    validate_tables(tables)
    output = Path(output)
    if output.exists(): raise FileExistsError("Choose a fresh catalog output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".catalog-", dir=output.parent) as name:
        temporary = Path(name) / "snapshot"
        temporary.mkdir()
        manifest = {"schema_version": 1, "scope": "public-research-metadata",
                    "national_coverage_verified": False, "review": review, "files": {}}
        for table, fields in SCHEMAS.items():
            rows = sorted(tables[table], key=lambda r: tuple(r[f] for f in fields))
            path = temporary / (table + ".csv")
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
                writer.writeheader(); writer.writerows(rows)
            manifest["files"][table] = {"rows": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        read_catalog(temporary)
        # mkdir reserves the destination without replacing a concurrent writer.
        output.mkdir()
        try:
            for path in temporary.iterdir(): os.link(path, output / path.name)
        except BaseException:
            for path in output.iterdir(): path.unlink()
            output.rmdir()
            raise
    return manifest


def load_catalog(db, source: Path):
    """Load the supplement after the base directory; validate cross-file joins."""
    tables, manifest = read_catalog(source)
    for table, fields in SCHEMAS.items():
        columns = ", ".join(f'"{field}" VARCHAR' for field in fields)
        db.execute(f'CREATE TABLE {table} ({columns})')
        if tables[table]:
            db.executemany(f'INSERT INTO {table} VALUES ({",".join("?" for _ in fields)})',
                           [[row[f] or None for f in fields] for row in tables[table]])
    for sql in (
        "SELECT count(*) FROM program_facilities f ANTI JOIN programs p USING (program_id)",
        "SELECT count(*) FROM evidence_sources e ANTI JOIN source_catalog s ON e.catalog_source_id=s.source_id",
        "SELECT count(*) FROM source_access a ANTI JOIN source_catalog s ON a.catalog_source_id=s.source_id",
    ):
        if db.execute(sql).fetchone()[0]: raise ValueError("Unresolved base-directory catalog references")
    db.execute("""
        CREATE VIEW program_locations AS
        SELECT p.program_id, p.organization_name, p.program_kind,
               f.facility_id, f.name AS facility_name, f.city, f.state,
               f.address1, f.postal_code, f.location_status,
               r.relationship, r.status, r.evidence_id
        FROM program_facilities r JOIN programs p USING (program_id)
        JOIN facilities f USING (facility_id);
        CREATE VIEW facility_coverage AS
        SELECT state, location_status, count(*) AS source_scoped_facilities,
               count(*) FILTER (WHERE latitude IS NOT NULL) AS reported_coordinate_pairs
        FROM facilities GROUP BY ALL;
        CREATE VIEW program_location_coverage AS
        SELECT p.source_id, p.program_kind, count(*) AS source_scoped_programs,
               count(*) FILTER (WHERE r.program_id IS NOT NULL) AS programs_with_listed_location,
               count(*) FILTER (WHERE r.program_id IS NULL) AS programs_without_listed_location
        FROM programs p LEFT JOIN (SELECT DISTINCT program_id FROM program_facilities) r
        USING (program_id) GROUP BY ALL;
        CREATE VIEW source_format_access AS
        SELECT a.*, f.format_id, f.name AS format_name, f.public_adapter,
               f.adapter_scope, f.limitations, j.evidence_status
        FROM source_access a JOIN source_formats j USING (access_id)
        JOIN formats f USING (format_id);
    """)
    db.execute("INSERT INTO provenance VALUES (?,?)", ["public-research-catalog", json.dumps(manifest, sort_keys=True)])
    return {table: len(rows) for table, rows in tables.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="Verify a public catalog without DuckDB/network access")
    check.add_argument("catalog", type=Path)
    export = commands.add_parser("export", help="Export reviewed normalized tables and review notes")
    export.add_argument("facts", type=Path, help='JSON object with exactly "tables" and "review" keys')
    export.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "validate":
        _, result = read_catalog(args.catalog)
    else:
        facts = json.loads(args.facts.read_text())
        if set(facts) != {"tables", "review"} or not isinstance(facts["review"], dict):
            raise ValueError("Require reviewed normalized tables and review notes")
        result = write_catalog(args.output, facts["tables"], facts["review"])
    print(json.dumps(result, indent=2))
