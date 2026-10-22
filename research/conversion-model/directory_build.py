"""Build a local queryable DuckDB from the reviewed public directory CSVs.

No network, raw collector cache, athlete records or inferred entity merges.
The committed CSV snapshot remains the portable source of truth.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from directory_export import FIELDS, ORGANIZATION_FIELDS, AFFILIATION_FIELDS
from directory_catalog import load_catalog
from authority_review import load_reviews
from access_signals import load_site_reviews

SNAPSHOT_FILES = {
    "organizations": "organizations_sha256",
    "programs": "programs_sha256",
    "affiliations": "affiliations_sha256",
}


def build_directory(source: Path, output: Path):
    import duckdb

    source, output = Path(source), Path(output)
    if output.exists():
        raise FileExistsError("Choose a fresh DuckDB output path")
    manifest = json.loads((source / "snapshot/manifest.json").read_text())
    if manifest.get("schema_version") != 2 or manifest.get("scope") != "organization-directory-facts":
        raise ValueError("Require the reviewed organization-directory schema v2")
    schemas = {"organizations": ORGANIZATION_FIELDS, "programs": FIELDS, "affiliations": AFFILIATION_FIELDS}
    for table, hash_key in SNAPSHOT_FILES.items():
        path = source / "snapshot" / (table + ".csv")
        with path.open(newline="") as stream:
            if tuple(next(csv.reader(stream), [])) != schemas[table]:
                raise ValueError("Unexpected public directory columns: " + table)
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[hash_key]:
            raise ValueError("Directory CSV differs from its manifest: " + table)
    authority = json.loads((source / "governing-bodies.manifest.json").read_text())
    if hashlib.sha256((source / "governing-bodies.csv").read_bytes()).hexdigest() != authority["file"]["sha256"]:
        raise ValueError("Authority CSV differs from its manifest")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Build atomically; a failed verification/query never leaves a usable-looking DB.
    fd, name = tempfile.mkstemp(prefix=".directory-", suffix=".duckdb", dir=output.parent)
    os.close(fd)
    temporary = Path(name)
    temporary.unlink()
    try:
        with duckdb.connect(str(temporary)) as db:
            for table in SNAPSHOT_FILES:
                db.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv(?, all_varchar=true)",
                           [str(source / "snapshot" / (table + ".csv"))])
            for table, filename in (("governing_bodies", "governing-bodies.csv"),
                                    ("source_catalog", "source-catalog.csv")):
                db.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv(?, all_varchar=true)",
                           [str(source / filename)])
            for table, key in (("organizations", "organization_id"), ("programs", "program_id"),
                               ("affiliations", "affiliation_id"), ("governing_bodies", "authority_id"),
                               ("source_catalog", "source_id")):
                total, distinct, missing = db.execute(
                    f"SELECT count(*), count(DISTINCT {key}), count(*) FILTER (WHERE {key} IS NULL) FROM {table}"
                ).fetchone()
                if total != distinct or missing:
                    raise ValueError("Missing or duplicated directory identities: " + table)
            counts = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                      for table in (*SNAPSHOT_FILES, "governing_bodies")}
            if (counts["programs"] != manifest["programs"] or
                    counts["organizations"] != manifest["source_scoped_organizations"] or
                    counts["affiliations"] != manifest["affiliations"] or
                    counts["governing_bodies"] != authority["governing_bodies"]):
                raise ValueError("Snapshot counts differ from their manifests")
            orphan_programs = db.execute("""
                SELECT count(*) FROM programs p LEFT JOIN organizations o USING (organization_id)
                WHERE o.organization_id IS NULL
            """).fetchone()[0]
            orphan_affiliations = db.execute("""
                SELECT count(*) FROM affiliations a LEFT JOIN programs p USING (program_id)
                WHERE p.program_id IS NULL
            """).fetchone()[0]
            if orphan_programs or orphan_affiliations:
                raise ValueError("Unresolved directory references")
            db.execute("""
                CREATE VIEW coverage_by_source AS
                SELECT source_id, source_url, program_kind,
                       count(*) AS source_scoped_programs,
                       count(DISTINCT organization_id) AS source_scoped_organizations,
                       count(*) FILTER (WHERE status='active') AS verified_active_programs
                FROM programs GROUP BY ALL;
                CREATE VIEW coverage_by_state AS
                SELECT country, coalesce(state,'unknown') AS state, program_kind,
                       count(*) AS source_scoped_programs,
                       count(DISTINCT organization_id) AS source_scoped_organizations
                FROM programs GROUP BY ALL;
                CREATE VIEW shared_website_candidates AS
                SELECT website, count(DISTINCT organization_id) AS organizations,
                       list(DISTINCT organization_id ORDER BY organization_id) AS organization_ids
                FROM organizations WHERE website IS NOT NULL
                GROUP BY website HAVING count(DISTINCT organization_id)>1;
                CREATE TABLE provenance (kind VARCHAR, manifest_json VARCHAR);
            """)
            db.executemany("INSERT INTO provenance VALUES (?,?)", [
                ("directory", json.dumps(manifest, sort_keys=True)),
                ("governing-body-discovery", json.dumps(authority, sort_keys=True)),
            ])
            # Older standalone directory snapshots remain readable. A present
            # supplement must pass its full schema/hash/reference validation.
            catalog_counts = load_catalog(db, source / "catalog") if (source / "catalog").exists() else {}
            review_count = load_reviews(db, source) if (source / "authority-reviews.manifest.json").exists() else 0
            site_review_count = load_site_reviews(db, source) if (source / 'site-access-reviews.manifest.json').exists() else 0
            candidates = db.execute("SELECT count(*) FROM shared_website_candidates").fetchone()[0]
        # Do not replace a file created concurrently after the initial check.
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {**counts, **catalog_counts, "shared_website_candidate_groups": candidates, "authority_homepage_reviews": review_count, "site_access_observations": site_review_count,
            "national_coverage_verified": False, "cross_source_entities_merged": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).with_name("team-directory"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_directory(args.source, args.output), indent=2))
