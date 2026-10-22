"""Verify the public authority-homepage review ledger; no collector/network code."""
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = ("authority_id", "entry_url", "access_url", "status", "checked_at",
          "content_sha256", "scope_notes")
STATUSES = {"homepage_cached", "stopped", "not_requested"}


def read_reviews(source):
    source = Path(source)
    manifest = json.loads((source / "authority-reviews.manifest.json").read_text())
    if manifest.get("schema_version") != 1 or manifest.get("scope") != "authority-homepage-discovery":
        raise ValueError("Unexpected authority review schema")
    path = source / "authority-reviews.csv"
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("Authority review CSV differs from manifest")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != FIELDS: raise ValueError("Unexpected review columns")
        rows = list(reader)
    if len(rows) != manifest["authorities"] or len({r["authority_id"] for r in rows}) != len(rows):
        raise ValueError("Missing or duplicate authority reviews")
    for row in rows:
        if row["status"] not in STATUSES or not row["authority_id"] or not row["scope_notes"]:
            raise ValueError("Missing authority review context")
        if datetime.fromisoformat(row["checked_at"]).tzinfo is None:
            raise ValueError("Require timezone-aware review date")
        for key in ("entry_url", "access_url"):
            if not row[key]: continue
            url = urlsplit(row[key])
            if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
                raise ValueError("Require public authority URL")
        digest = row["content_sha256"]
        if row["status"] == "homepage_cached":
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Cached homepage requires source hash")
        elif digest:
            raise ValueError("Do not attach successful-page evidence to an access gap")
    return rows, manifest


def load_reviews(db, source):
    rows, manifest = read_reviews(source)
    db.execute("CREATE TABLE authority_reviews (" + ",".join(f"{f} VARCHAR" for f in FIELDS) + ")")
    if rows:
        db.executemany("INSERT INTO authority_reviews VALUES (" + ",".join("?" for _ in FIELDS) + ")",
                       [[row[f] or None for f in FIELDS] for row in rows])
    if db.sql("SELECT count(*) FROM authority_reviews ANTI JOIN governing_bodies USING (authority_id)").fetchone()[0]:
        raise ValueError("Authority review references unknown authority")
    if db.sql("SELECT count(*) FROM governing_bodies ANTI JOIN authority_reviews USING (authority_id)").fetchone()[0]:
        raise ValueError("Authority review ledger omits a discovery authority")
    db.execute("""CREATE VIEW authority_review_coverage AS
        SELECT g.segment, r.status AS homepage_review_status, g.program_listing_status,
               count(*) AS authorities
        FROM governing_bodies g JOIN authority_reviews r USING (authority_id) GROUP BY ALL""")
    db.execute("INSERT INTO provenance VALUES (?,?)", ["authority-homepage-review", json.dumps(manifest, sort_keys=True)])
    return len(rows)
