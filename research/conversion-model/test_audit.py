import csv, tempfile, unittest
from pathlib import Path
from audit import audit, pair_coverage, age_band


class AuditTests(unittest.TestCase):
    def test_coverage_counts_unique_people_and_missing_cells_without_exporting_ids(
        self,
    ):
        rows = [
            {
                "source": "toy",
                "race_id": "race-a",
                "swimmer_id": "private-athlete-id",
                "meet_id": "private-meet-id",
                "course": "SCY",
                "category": "women",
                "age_years": "12",
                "stroke": "freestyle",
                "distance": "100",
                "date": "2025-01-01",
                "status": "OK",
            }
        ]
        rows.append({**rows[0], "race_id": "race-b"})
        rows.append(rows[0])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.csv"
            with p.open("w") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            r = audit(p)
        self.assertEqual(
            (r["races"], r["swimmers"], r["meets"], r["duplicate_rows"]), (2, 1, 1, 1)
        )
        filled = next(
            c
            for c in r["cells"]
            if c["course"] == "SCY"
            and c["category"] == "women"
            and c["age_band"] == "11-12"
            and c["event"] == "100 freestyle"
        )
        self.assertEqual((filled["races"], filled["swimmers"]), (2, 1))
        self.assertTrue(any(c["races"] == 0 for c in r["cells"]))
        self.assertNotIn("private-", str(r))

    def test_unknown_age_is_separate_and_nonfinite_rejected(self):
        self.assertEqual(age_band(""), "unknown")
        self.assertEqual(age_band(10), "10u")
        self.assertEqual(age_band(10.9), "10u")
        self.assertEqual(age_band(12.9), "11-12")
        self.assertEqual(age_band(18.9), "17-18")
        self.assertEqual(age_band(19), "19+")
        with self.assertRaises(ValueError):
            age_band(float("nan"))

    def test_pair_counts_keep_partitions_and_athlete_counts(self):
        source = {
            "category": "men",
            "age_years": 16,
            "distance": 50,
            "stroke": "freestyle",
            "meet_id": "y",
        }
        pairs = [
            {
                "partition": "train",
                "source": source,
                "target": {"meet_id": "m"},
                "swimmer_key": "hidden",
                "gap_days": -12,
            }
        ] * 2
        r = pair_coverage(pairs)
        self.assertEqual(r["cells"][0]["pairs"], 2)
        self.assertEqual(r["cells"][0]["swimmers"], 1)
        self.assertEqual(r["absolute_gap_days"], {"12": 2})
        self.assertNotIn("hidden", str(r))


if __name__ == "__main__":
    unittest.main()
