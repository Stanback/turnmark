"""Validate the published organization-only interchange without network access."""
import csv
import hashlib
import json
import unittest
from pathlib import Path
from directory_export import FIELDS, AFFILIATION_FIELDS, ORGANIZATION_FIELDS, public_website


class PublicDirectorySnapshotTests(unittest.TestCase):
    def test_governing_body_discovery_has_provenance_without_implying_teams(self):
        root = Path(__file__).with_name("team-directory")
        manifest = json.loads((root / "governing-bodies.manifest.json").read_text())
        path = root / manifest["file"]["path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest["file"]["sha256"])
        self.assertEqual(manifest["scope"], "governing-body-discovery-only")
        self.assertEqual(manifest["programs_added"], 0)
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, [
                "authority_id", "authority_name", "country", "jurisdiction",
                "segment", "website", "program_listing_status", "source_id",
            ])
            rows = list(reader)
        self.assertEqual(len(rows), manifest["governing_bodies"])
        self.assertEqual(len({r["authority_id"] for r in rows}), len(rows))
        self.assertEqual({r["jurisdiction"] for r in rows if r["segment"] == "high_school"}, set(
            "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN "
            "MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA "
            "WA WV WI WY".split()))
        sources = {s["source_id"]: s for s in manifest["sources"]}
        for source_id, source in sources.items():
            self.assertEqual(sum(r["source_id"] == source_id for r in rows), source["governing_bodies"])
            self.assertTrue(source["source_url"].startswith("https://"))
            self.assertEqual(len(source["source_content_sha256"]), 64)
            for supporting in source.get("supporting_sources", []):
                self.assertTrue(supporting["source_url"].startswith("https://"))
                self.assertEqual(len(supporting["source_content_sha256"]), 64)
        for row in rows:
            self.assertIn(row["country"], ("US", "CA"))
            self.assertIn(row["segment"], ("high_school", "club_swimming", "masters"))
            if row["country"] == "CA":
                self.assertEqual(row["segment"], "club_swimming")
                self.assertTrue(row["jurisdiction"] == "CA" or row["jurisdiction"] in
                                set("AB BC MB NB NL NS NT NU ON PE QC SK YT".split()))
            self.assertIn(row["source_id"], sources)
            self.assertIn(row["program_listing_status"], ("swimming_not_reviewed", "partial_swimming_imported"))
            self.assertEqual(public_website(row["website"]), row["website"])

        snapshot = json.loads((root / "snapshot/manifest.json").read_text())
        registry_sources = {s["source_id"] for s in snapshot["sources"]}
        reviewed = {r["authority_id"] for r in rows if r["program_listing_status"] == "partial_swimming_imported"}
        reviews = manifest["program_listing_reviews"]
        self.assertEqual({r["authority_id"] for r in reviews}, reviewed)
        self.assertEqual(len(reviews), len(reviewed))
        for review in reviews:
            self.assertFalse(review["national_or_jurisdiction_completeness_verified"])
            self.assertTrue(review["scope"])
            self.assertTrue(review["registry_source_ids"])
            self.assertTrue(set(review["registry_source_ids"]) <= registry_sources)

    def test_public_snapshot_matches_manifest_and_fixed_directory_columns(self):
        root = Path(__file__).with_name("team-directory") / "snapshot"
        manifest = json.loads((root / "manifest.json").read_text())
        path = root / "programs.csv"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest["programs_sha256"])
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            self.assertEqual(tuple(reader.fieldnames), FIELDS)
            rows = list(reader)
        self.assertEqual(len(rows), manifest["programs"])
        self.assertEqual(len({r["program_id"] for r in rows}), len(rows))
        self.assertEqual(len({r["organization_id"] for r in rows}), manifest["source_scoped_organizations"])
        self.assertFalse(manifest["national_coverage_verified"])
        sources = {s["source_id"] for s in manifest["sources"]}
        for row in rows:
            self.assertIn(row["source_id"], sources)
            self.assertIn(row["status"], ("active", "inactive", "unknown"))
            self.assertEqual(public_website(row["website"]) or "", row["website"])

        organization_path = root / "organizations.csv"
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(hashlib.sha256(organization_path.read_bytes()).hexdigest(), manifest["organizations_sha256"])
        with organization_path.open(newline="") as f:
            reader = csv.DictReader(f)
            self.assertEqual(tuple(reader.fieldnames), ORGANIZATION_FIELDS)
            organizations = list(reader)
        self.assertEqual(len(organizations), manifest["source_scoped_organizations"])
        self.assertEqual({r["organization_id"] for r in organizations}, {r["organization_id"] for r in rows})
        for row in organizations:
            self.assertIn(row["source_id"], sources)
            self.assertEqual(public_website(row["website"]) or "", row["website"])

        affiliation_path = root / "affiliations.csv"
        self.assertEqual(hashlib.sha256(affiliation_path.read_bytes()).hexdigest(), manifest["affiliations_sha256"])
        with affiliation_path.open(newline="") as f:
            reader = csv.DictReader(f)
            self.assertEqual(tuple(reader.fieldnames), AFFILIATION_FIELDS)
            affiliations = list(reader)
        self.assertEqual(len(affiliations), manifest["affiliations"])
        program_ids = {r["program_id"] for r in rows}
        for row in affiliations:
            self.assertIn(row["program_id"], program_ids)
            self.assertIn(row["source_id"], sources)

    def test_breadth_receipt_matches_public_metadata_counts(self):
        from collections import Counter
        root = Path(__file__).with_name("team-directory")
        receipt = json.loads((root / "breadth-checkpoint-10.json").read_text())
        snapshot = json.loads((root / "snapshot/manifest.json").read_text())
        self.assertEqual(receipt["program_listings"], snapshot["programs"])
        self.assertEqual(receipt["source_scoped_organizations"], snapshot["source_scoped_organizations"])
        self.assertEqual(receipt["affiliations"], snapshot["affiliations"])
        with (root / "snapshot/programs.csv").open(newline="") as stream:
            programs = list(csv.DictReader(stream))
        self.assertEqual(receipt["program_kind"], dict(Counter(r["program_kind"] for r in programs)))
        self.assertEqual(receipt["school_listing_states"], dict(Counter(r["state"] for r in programs if r["program_kind"] == "high_school")))
        # The new pass receipt must describe the actual source-scoped rows,
        # not just a headline total or school-member discovery count.
        source_ids = set(receipt["new_source_ids"])
        self.assertEqual(len(source_ids), receipt["new_source_documents"])
        self.assertTrue(source_ids <= {s["source_id"] for s in snapshot["sources"]})
        actual = Counter((r["source_id"], r["state"], r["category"])
                         for r in programs if r["source_id"] in source_ids)
        claimed = {(r["source_id"], r["state"], r["category"]): r["listings"]
                   for r in receipt["source_rows"]}
        self.assertEqual(dict(actual), claimed)
        self.assertEqual(sum(actual.values()), receipt["new_program_listings"])
        school_sources = set(receipt["new_school_source_ids"])
        self.assertEqual(len(school_sources), receipt["new_school_source_documents"])
        self.assertEqual(sum(r["program_kind"] == "high_school" and r["source_id"] in school_sources
                             for r in programs), receipt["new_school_program_listings"])
        with (root / "snapshot/affiliations.csv").open(newline="") as stream:
            affiliations = list(csv.DictReader(stream))
        individual_only = {r["program_id"] for r in affiliations
                           if "participation=individual-entry-only" in r["jurisdiction"]}
        self.assertEqual(len(individual_only), receipt["individual_entry_only_school_listings"])
        authorities = json.loads((root / "governing-bodies.manifest.json").read_text())
        self.assertEqual(receipt["partial_jurisdiction_imports"],
                         len(authorities["program_listing_reviews"]))
        catalog = json.loads((root / "catalog/manifest.json").read_text())
        self.assertEqual(receipt["source_location_records"], catalog["files"]["facilities"]["rows"])
        self.assertEqual(receipt["program_location_links"], catalog["files"]["program_facilities"]["rows"])
        self.assertFalse(receipt["national_membership_or_activity_completeness_verified"])
        self.assertFalse(receipt["cross_source_entities_merged"])
        self.assertEqual(receipt["new_races_in_this_metadata_pass"], 0)
