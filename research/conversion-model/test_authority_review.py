"""Metadata receipts are separate from swimming-program coverage."""
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from authority_review import FIELDS, read_reviews


def write_reviews(root, authority_id="r1"):
    row = dict(zip(FIELDS, (authority_id, "http://example.invalid/", "https://example.invalid/",
                           "homepage_cached", "2026-01-01T12:00:00+00:00", "a"*64,
                           "Invented homepage only; no program inferred.")))
    path = root/"authority-reviews.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS); writer.writeheader(); writer.writerow(row)
    manifest = {"schema_version":1, "scope":"authority-homepage-discovery", "authorities":1,
                "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    (root/"authority-reviews.manifest.json").write_text(json.dumps(manifest))


class AuthorityReviewTests(unittest.TestCase):
    def test_source_receipt_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); write_reviews(root)
            rows, _ = read_reviews(root)
            self.assertEqual(rows[0]["entry_url"], "http://example.invalid/")
            self.assertEqual(rows[0]["access_url"], "https://example.invalid/")
            self.assertNotIn("programs_added", rows[0])
            with (root/"authority-reviews.csv").open("a") as stream: stream.write("changed\n")
            with self.assertRaises(ValueError): read_reviews(root)

    def test_public_authority_ledger_covers_the_discovery_index_once(self):
        root = Path(__file__).with_name("team-directory")
        rows, manifest = read_reviews(root)
        with (root/"governing-bodies.csv").open(newline="") as stream:
            authorities = {r["authority_id"] for r in csv.DictReader(stream)}
        self.assertEqual({r["authority_id"] for r in rows}, authorities)
        self.assertEqual(len(rows), len(authorities))
        self.assertEqual(sum(manifest["counts"].values()), len(rows))
