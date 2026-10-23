"""Export an allowlisted organization directory, never meet or athlete records.

The caller explicitly selects reviewed directory source IDs. SQL names and output
columns are fixed; no source text becomes executable SQL or filesystem paths.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

FIELDS = (
    "program_id", "organization_id", "organization_name", "program_name",
    "program_kind", "discipline", "category", "status", "country", "state",
    "city", "website", "listing_checked", "source_id", "source_url",
)

ORGANIZATION_FIELDS = (
    "organization_id", "organization_name", "organization_kind", "country",
    "state", "city", "website", "listing_checked", "source_id", "source_url",
)

AFFILIATION_FIELDS = (
    "affiliation_id", "program_id", "authority", "authority_id", "jurisdiction",
    "valid_from", "valid_to", "source_id",
)


def public_website(value):
    """Omit contact-like/malformed URLs and unreviewed query parameters."""
    if not value:
        return None
    try:
        url = urlsplit(value)
        if (url.scheme not in ("http", "https") or not url.hostname
                or url.username or url.password or any(c.isspace() for c in value)):
            return None
        allowed = {"team", "teamid", "club", "clubid", "c", "pagetitle", "id"}
        pairs = parse_qsl(url.query, keep_blank_values=True)
        if any(k.casefold() not in allowed and not k.casefold().startswith("utm_") for k, _ in pairs):
            return None
        return urlunsplit((url.scheme, url.netloc, url.path,
                           urlencode([(k, v) for k, v in pairs if not k.casefold().startswith("utm_")]), ""))
    except ValueError:
        return None


def export_directory(database: Path, selection: Path, output: Path):
    import duckdb

    review = json.loads(selection.read_text())
    if set(review) != {"scope", "source_ids", "review_notes"}:
        raise ValueError("Unexpected selection fields")
    if review["scope"] != "organization-directory-facts":
        raise ValueError("Only organizational directory facts can be exported")
    source_ids = review["source_ids"]
    if (not isinstance(source_ids, list) or not source_ids
            or any(not isinstance(s, str) or not s for s in source_ids)
            or len(set(source_ids)) != len(source_ids)):
        raise ValueError("Choose distinct reviewed directory sources")
    if not isinstance(review["review_notes"], str) or not review["review_notes"].strip():
        raise ValueError("Describe the reviewed publication scope")
    if output.exists():
        raise FileExistsError("Use a fresh output directory")
    with duckdb.connect(str(database), read_only=True) as db:
        known = {r[0] for r in db.execute("SELECT source_id FROM registry_sources").fetchall()}
        if not set(source_ids) <= known:
            raise ValueError("A selected source is absent")
        # Do not expose source observations, raw payloads or arbitrary extra columns.
        query = """
            SELECT p.program_id, o.organization_id, o.name, p.name,
                   p.program_kind, p.discipline, p.category, p.status,
                   o.country, o.state, o.city, o.website, p.last_verified,
                   p.evidence_source_id, s.source_url
            FROM programs p JOIN organizations o USING (organization_id)
            JOIN registry_sources s ON s.source_id = p.evidence_source_id
            WHERE p.evidence_source_id IN (SELECT unnest(?))
              AND o.evidence_source_id IN (SELECT unnest(?))
            ORDER BY p.program_id
        """
        rows = db.execute(query, [source_ids, source_ids]).fetchall()
        if not rows:
            raise ValueError("No reviewed directory rows")
        organizations = db.execute("""
            SELECT DISTINCT o.organization_id, o.name, o.organization_kind,
                   o.country, o.state, o.city, o.website,
                   CAST(s.retrieved_at AT TIME ZONE 'UTC' AS DATE),
                   o.evidence_source_id, s.source_url
            FROM organizations o JOIN registry_sources s
              ON s.source_id = o.evidence_source_id
            JOIN programs p USING (organization_id)
            WHERE o.evidence_source_id IN (SELECT unnest(?))
              AND p.evidence_source_id IN (SELECT unnest(?))
            ORDER BY o.organization_id
        """, [source_ids, source_ids]).fetchall()
        sources = db.execute("""
            SELECT source_id, source_url,
                   strftime(retrieved_at AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%S.%fZ'), content_sha256
            FROM registry_sources WHERE source_id IN (SELECT unnest(?))
            ORDER BY source_id
        """, [source_ids]).fetchall()
        affiliations = db.execute("""
            SELECT a.affiliation_id, a.program_id, a.authority, a.authority_id,
                   a.jurisdiction, a.valid_from, a.valid_to, a.evidence_source_id
            FROM program_affiliations a
            JOIN programs p USING (program_id)
            JOIN organizations o USING (organization_id)
            WHERE a.evidence_source_id IN (SELECT unnest(?))
              AND p.evidence_source_id IN (SELECT unnest(?))
              AND o.evidence_source_id IN (SELECT unnest(?))
            ORDER BY a.affiliation_id
        """, [source_ids, source_ids, source_ids]).fetchall()
    rows = [tuple(public_website(value) if FIELDS[i] == "website" else value
                  for i, value in enumerate(row)) for row in rows]
    output.mkdir(parents=True)
    path = output / "programs.csv"
    with path.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerows(rows)
    affiliation_path = output / "affiliations.csv"
    with affiliation_path.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(AFFILIATION_FIELDS)
        writer.writerows(affiliations)
    organization_path = output / "organizations.csv"
    with organization_path.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(ORGANIZATION_FIELDS)
        writer.writerows(tuple(public_website(value) if ORGANIZATION_FIELDS[i] == "website" else value
                               for i, value in enumerate(row)) for row in organizations)
    counts = {field: Counter() for field in ("program_kind", "country", "state", "status")}
    for row in rows:
        for field, counter in counts.items():
            counter[row[FIELDS.index(field)] or "unknown"] += 1
    manifest = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": review["scope"],
        "review_notes": review["review_notes"],
        "programs": len(rows),
        "source_scoped_organizations": len(organizations),
        "organizations_sha256": hashlib.sha256(organization_path.read_bytes()).hexdigest(),
        "counts": {k: dict(sorted(v.items())) for k, v in counts.items()},
        "national_coverage_verified": False,
        "rosters_or_contacts_included": False,
        "affiliations": len(affiliations),
        "affiliations_sha256": hashlib.sha256(affiliation_path.read_bytes()).hexdigest(),
        "programs_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "sources": [dict(zip(("source_id", "source_url", "retrieved_at", "content_sha256"),
                             (sid, url, retrieved, sha)))
                    for sid, url, retrieved, sha in sources],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = export_directory(args.database, args.selection, args.output)
    print(json.dumps({"programs": result["programs"], "national_coverage_verified": False}))
