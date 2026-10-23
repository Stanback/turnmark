"""Offline coverage audit of source assertions, never a national-team estimate."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

US_JURISDICTIONS = frozenset("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())
UNIVERSES = {
    "usa_swimming_finder": ("usa-swimming:org-unit", "Source clubs; youth/program mix unresolved"),
    "ymca_usas_dual_charter": ("ymca:usas-dual-charter", "USA Swimming finder clubs explicitly named as YMCA programs; non-USAS YMCA-only clubs not separately enumerated"),
    "ymca_competitive_associations": ("ymca:competitive-association", "Active YMCA competitive swimming associations from 2025-2026 YMCA National Championship CEO declarations and filtered COI filings"),
    "ymca_national_scoring_teams": ("ymca:nationals-team-scores", "Scoring teams from 2025-2026 YMCA Short Course & Long Course National Championships"),
    "usms_finder": ("usms:public-finder", "Clubs and workout groups require reconciliation"),
    "ncaa": ("ncaa", "Category-specific varsity sponsorship; NAIA/NJCAA not included"),
    "naia": ("naia", "NAIA Men's and Women's varsity swimming & diving institutions across 2026 National Championship qualifiers and conference/sponsorship rosters"),
    "njcaa": ("njcaa:swimming-and-diving", "NJCAA swimming & diving institutions from 2025-2026 championship and CSCAA All-America releases"),
    "cccaa_3c2a": ("3c2a:swimming-and-diving", "California Community College Athletic Association (3C2A) swimming & diving programs across 9 conferences"),
    "college_club_swimming": ("college-club-swimming", "Registration status and current operation differ"),
}


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def audit(source):
    source = Path(source)
    manifest = json.loads((source / "snapshot/manifest.json").read_text())
    tables = {}
    for name in ("programs", "organizations", "affiliations"):
        path = source / "snapshot" / f"{name}.csv"
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[f"{name}_sha256"]:
            raise ValueError(f"Snapshot hash mismatch: {name}")
        tables[name] = read_csv(path)
    programs = {p["program_id"]: p for p in tables["programs"]}
    if len(programs) != len(tables["programs"]):
        raise ValueError("Duplicate program identity")
    universes = {}
    for key, (authority, limitation) in UNIVERSES.items():
        ids = {a["program_id"] for a in tables["affiliations"] if a["authority"] == authority}
        if not ids <= programs.keys():
            raise ValueError("Affiliation references absent program")
        selected = [programs[i] for i in ids]
        universes[key] = {
            "source_scoped_listings": len(selected),
            "us_country_asserted_listings": sum(p["country"] == "US" for p in selected),
            "source_scoped_organizations": len({p["organization_id"] for p in selected}),
            "limitation": limitation,
            "national_eligible_team_denominator": None,
            "national_matched_unique_teams": None,
            "national_team_coverage_percent": None,
        }
    school = [p for p in programs.values() if p["program_kind"] == "high_school" and p["country"] == "US"]
    by_state = defaultdict(list)
    for p in school:
        by_state[p["state"]].append(p)
    authorities = read_csv(source / "governing-bodies.csv")
    catalog = read_csv(source / "source-catalog.csv")
    no_sponsorship_states = set()
    for r in catalog:
        if r.get("segment") == "high_school" and r.get("collection_status") == "reviewed_no_sponsorship":
            sid = r.get("source_id", "")
            for prefix, st_code in (("sdhsaa-", "SD"), ("tssaa-", "TN"), ("vpa-", "VT")):
                if sid.startswith(prefix):
                    no_sponsorship_states.add(st_code)
    states = []
    for state in sorted(US_JURISDICTIONS):
        selected = by_state[state]
        if selected:
            scope_status = "partial_source_assertions"
        elif state in no_sponsorship_states:
            scope_status = "verified_non_sponsoring_authority"
        else:
            scope_status = "no_imported_school_listing"
        states.append({
            "state": state, "source_scoped_school_listings": len(selected),
            "source_scoped_organizations": len({p["organization_id"] for p in selected}),
            "categories": dict(sorted(Counter(p["category"] for p in selected).items())),
            "source_ids": sorted({p["source_id"] for p in selected}),
            "scope_status": scope_status,
            "eligible_unique_teams": None, "matched_unique_teams": None, "team_coverage_percent": None,
        })
    counts = Counter(p["program_kind"] for p in programs.values())
    return {
        "schema_version": 1,
        "snapshot_generated_at": manifest["generated_at"],
        "programs_sha256": manifest["programs_sha256"],
        "target_team_coverage_percent": [85, 90],
        "target_applies_separately_per_segment": True,
        "summer_clubs_required_for_target": False,
        "source_scoped_listings": len(programs),
        "source_scoped_organizations": len(tables["organizations"]),
        "program_kinds": dict(sorted(counts.items())),
        "activity_status": dict(sorted(Counter(p["status"] for p in programs.values()).items())),
        "source_universes": universes,
        "school_jurisdictions_with_listings": sum(bool(by_state[s]) for s in US_JURISDICTIONS),
        "school_jurisdictions_without_listings": [s for s in sorted(US_JURISDICTIONS) if not by_state[s]],
        "school_states": states,
        "authority_import_status": dict(sorted(Counter(a["program_listing_status"] for a in authorities).items())),
        "catalog_source_statuses": [
            {k: r[k] for k in ("source_id", "segment", "publisher", "collection_status")}
            for r in catalog
        ],
        "additional_unresolved_universes": ["YMCA/non-USAS youth", "NJCAA/other collegiate associations",
                                             "independent/private school authorities", "middle school where sponsored",
                                             "unaffiliated year-round clubs"],
        "national_team_coverage_percent": None,
        "national_coverage_verified": False,
        "limitations": [
            "Listing/category/co-op/individual-entry rows are not unique independent teams",
            "No-import jurisdictions are gaps, never zero-team claims",
            "National finder capture is not all-team or current-operation completeness",
            "Source editions differ; compare denominators only within matching scope and season",
            "No cross-provider name-based merges or blended national percentage",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent / "team-directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("source_scoped_listings", "school_jurisdictions_with_listings",
                                           "school_jurisdictions_without_listings", "national_team_coverage_percent")}))


if __name__ == "__main__":
    main()
