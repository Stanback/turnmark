"""Invented metadata exercises projection, evidence and location boundaries."""
import copy
import csv
import tempfile
import unittest
from pathlib import Path
from directory_catalog import SCHEMAS, validate_tables, read_catalog, write_catalog


def invented_catalog():
    tables = {k: [] for k in SCHEMAS}
    def add(table, **values):
        tables[table].append({key: values.get(key, "") for key in SCHEMAS[table]})
    add("evidence_sources", evidence_id="e1", catalog_source_id="s1",
        source_url="https://example.invalid/finder", retrieved_at="2026-01-01T12:00:00Z",
        content_sha256="a"*64, scope="Invented facility facts", reuse_status="Invented fixture")
    add("facilities", facility_id="f1", authority="example:facility", authority_id="1",
        name="Example Aquatic Center", address1="1 Example Way", city="Example", state="CA",
        country="US", latitude="35", longitude="-120", location_status="source_reported_unverified",
        evidence_id="e1", listing_checked="2026-01-01")
    add("program_facilities", relation_id="r1", program_id="p1", facility_id="f1",
        authority_listing_id="example:1", relationship="listed_training_location", status="unknown", evidence_id="e1")
    add("pool_basins", pool_id="b1", facility_id="f1", name="Main basin", length_m="50",
        elevation_basis="unknown", evidence_id="e1", listing_checked="2026-01-01")
    add("formats", format_id="json", name="JSON", kind="directory", adapter_scope="Invented")
    add("source_access", access_id="a1", catalog_source_id="s1", entry_url="https://example.invalid/finder",
        http_method="GET", access_status="fixture", collection_policy="No network in tests")
    add("source_formats", access_id="a1", format_id="json", evidence_status="observed")
    return tables


class CatalogTests(unittest.TestCase):
    def test_roundtrip_and_unrecognized_private_columns(self):
        tables = invented_catalog()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)/"catalog"
            write_catalog(root, tables, {"purpose": "Invented"})
            loaded, manifest = read_catalog(root)
            self.assertEqual(loaded, tables)
            self.assertFalse(manifest["national_coverage_verified"])
            self.assertEqual(loaded["pool_basins"][0]["elevation_m"], "")
            with self.assertRaises(FileExistsError): write_catalog(root, tables, {})
            with (root/"facilities.csv").open("a") as stream: stream.write("tamper\n")
            with self.assertRaises(ValueError): read_catalog(root)
        tables["facilities"][0]["contact_email"] = "private@example.invalid"
        with self.assertRaises(ValueError): validate_tables(tables)

    def test_invalid_coordinates_elevations_and_orphans_fail(self):
        changes = [
            ("facilities", "latitude", "nan"), ("facilities", "longitude", "181"),
            ("facilities", "latitude", ""), ("facilities", "evidence_id", "missing"),
            ("facilities", "location_status", "mailing_address_withheld"),
            ("facilities", "listing_checked", "2026-02-30"),
            ("pool_basins", "elevation_m", "0"), ("pool_basins", "elevation_uncertainty_m", "5"),
            ("pool_basins", "facility_id", "missing"),
            ("program_facilities", "status", "active"),
            ("source_formats", "format_id", "missing"),
            ("evidence_sources", "retrieved_at", "2026-01-01"),
            ("source_access", "data_url", "https://user:secret@example.invalid/api"),
        ]
        for table, field, value in changes:
            with self.subTest(table=table, field=field, value=value):
                tables = invented_catalog(); tables[table][0][field] = value
                with self.assertRaises(ValueError): validate_tables(tables)
        tables = invented_catalog()
        tables["facilities"][0].update(latitude="0", longitude="0")
        with self.assertRaises(ValueError): validate_tables(tables)
        tables = invented_catalog(); tables["facilities"].append(copy.deepcopy(tables["facilities"][0]))
        with self.assertRaises(ValueError): validate_tables(tables)

    def test_club_address_edges_are_distinct_from_training_locations(self):
        tables = invented_catalog()
        tables["program_facilities"][0]["relationship"] = "listed_club_address"
        validate_tables(tables)
        tables["program_facilities"][0]["relationship"] = "listed_office"
        with self.assertRaises(ValueError): validate_tables(tables)
        # A withheld mailing address can be a club's listed address, never a training pool.
        tables = invented_catalog()
        tables["facilities"][0].update(location_status="mailing_address_withheld", address1="", latitude="", longitude="")
        with self.assertRaisesRegex(ValueError, "withheld mailing address"): validate_tables(tables)
        tables["program_facilities"][0]["relationship"] = "listed_club_address"
        validate_tables(tables)

    def test_unknown_address_and_true_zero_elevation_are_distinct(self):
        tables = invented_catalog()
        tables["facilities"][0].update(location_status="mailing_address_withheld", address1="", latitude="", longitude="")
        tables["program_facilities"][0]["relationship"] = "listed_club_address"
        tables["pool_basins"][0].update(elevation_m="0", elevation_basis="surveyed", elevation_uncertainty_m="0.1")
        validate_tables(tables)

    def test_public_snapshot_is_metadata_only_and_references_public_programs(self):
        root = Path(__file__).with_name("team-directory")
        tables, manifest = read_catalog(root/"catalog")
        with (root/"snapshot/programs.csv").open(newline="") as stream:
            programs = {row["program_id"] for row in csv.DictReader(stream)}
        with (root/"source-catalog.csv").open(newline="") as stream:
            sources = {row["source_id"] for row in csv.DictReader(stream)}
        self.assertTrue({r["program_id"] for r in tables["program_facilities"]} <= programs)
        for table in ("evidence_sources", "source_access"):
            self.assertTrue({r["catalog_source_id"] for r in tables[table]} <= sources)
        self.assertFalse(manifest["national_coverage_verified"])
        self.assertTrue(all(r["elevation_basis"] == "unknown" for r in tables["pool_basins"]))
        self.assertEqual(set(SCHEMAS), set(manifest["files"]))
        for row in tables["formats"]:
            if row["public_adapter"]:
                module, function = row["public_adapter"].split(":")
                import importlib
                self.assertTrue(callable(getattr(importlib.import_module(module.removesuffix(".py")), function)))
