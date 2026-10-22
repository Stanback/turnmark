"""Import normalized organizational facts into an existing local registry.

Source-specific fetchers stay local. They emit these fixed fields from reviewed
JSON, CSV or HTML listings; raw responses and contact fields never enter here.
Identifiers are authority-scoped, so categories share an organization without
merging similarly named schools/clubs from unrelated sources.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from directory_export import public_website

FIELDS = {
    "organization_key", "organization_name", "organization_kind", "country",
    "state", "city", "website", "program_key", "program_name", "program_kind",
    "discipline", "category", "authority", "authority_id", "jurisdiction",
}
KINDS = {"age_group", "masters", "collegiate_varsity", "collegiate_club",
         "high_school", "summer_league", "learn_to_swim", "other", "unknown"}
ORGANIZATIONS = {"club", "school", "association", "league", "other", "unknown"}
DISCIPLINES = {"pool_swimming", "open_water", "swimming_and_diving", "other", "unknown"}


def identity(kind, authority, key):
    # Length-delimited components cannot alias when keys contain punctuation.
    components = (kind, authority, key)
    return str(uuid.uuid5(uuid.NAMESPACE_URL,
                         "urn:turnmark:registry:" + "".join(f"{len(v)}:{v}" for v in components)))


def import_directory(db, *, source_id, source_url, retrieved_at,
                     content_sha256, reuse_notes, records):
    """Atomically add one reviewed listing; never infer active status or dates."""
    if (not isinstance(retrieved_at, datetime) or retrieved_at.tzinfo is None
            or not source_url.startswith("https://")
            or len(content_sha256) != 64
            or any(c not in "0123456789abcdef" for c in content_sha256)
            or not source_id or not reuse_notes):
        raise ValueError("A source needs its URL, timezone-aware retrieval, hash and reuse notes")
    records = list(records)
    seen = set()
    organizations = {}
    for row in records:
        if set(row) != FIELDS:
            raise ValueError("Unexpected normalized fields; contacts and raw payloads are excluded")
        if any(not isinstance(v, (str, type(None))) for v in row.values()):
            raise ValueError("Normalized facts must be strings or null")
        if any(not row[k] for k in ("organization_key", "organization_name", "program_key",
                                     "program_name", "authority", "authority_id", "country")):
            raise ValueError("Missing organizational identity or name")
        if (row["organization_kind"] not in ORGANIZATIONS or row["program_kind"] not in KINDS
                or row["discipline"] not in DISCIPLINES
                or row["category"] not in {"men", "women", "mixed", "unknown"}):
            raise ValueError("Unreviewed organizational classification")
        key = (row["authority"], row["program_key"])
        if key in seen:
            raise ValueError("Duplicate program in listing")
        seen.add(key)
        org_key = (row["authority"], row["organization_key"])
        facts = tuple(row[k] for k in ("organization_name", "organization_kind", "country", "state", "city", "website"))
        if org_key in organizations and organizations[org_key] != facts:
            raise ValueError("Conflicting organization facts need review")
        organizations[org_key] = facts
    if not records:
        raise ValueError("Empty source listing")
    db.execute("BEGIN TRANSACTION")
    try:
        db.execute("INSERT INTO registry_sources VALUES (?,?,?,?,?)",
                   [source_id, source_url, retrieved_at, content_sha256, reuse_notes])
        for (authority, key), facts in organizations.items():
            org = identity("organization", authority, key)
            existing = db.execute("SELECT name, organization_kind, country, state, city, website FROM organizations WHERE organization_id=?", [org]).fetchone()
            cleaned = (*facts[:5], public_website(facts[5]))
            if existing and existing != cleaned:
                raise ValueError("Existing organization differs; reconcile evidence explicitly")
            if not existing:
                db.execute("INSERT INTO organizations VALUES (?,?,?,?,?,?,?,?)",
                           [org, *cleaned, source_id])
        for row in records:
            org = identity("organization", row["authority"], row["organization_key"])
            program = identity("program", row["authority"], row["program_key"])
            db.execute("INSERT INTO programs VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
                program, org, row["program_name"], row["program_kind"], row["discipline"],
                row["category"], "unknown", None, None, retrieved_at.date(), source_id,
            ])
            db.execute("INSERT INTO program_affiliations VALUES (?,?,?,?,?,?,?,?)", [
                identity("affiliation", row["authority"], row["program_key"]), program,
                row["authority"], row["authority_id"], row["jurisdiction"], None, None, source_id,
            ])
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return {"programs_added": len(records), "organizations_observed": len(organizations)}
