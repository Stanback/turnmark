import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pipeline import Race, match, partition, read_results


class PipelineTests(unittest.TestCase):
    def race(self, race_id, course, day, athlete="a", distance=100, category="women"):
        return Race("fixture", race_id, athlete, "meet", date(2026, 1, day),
                    course, distance, "freestyle", category, 5832, 15)

    def test_matches_are_one_to_one_nearby_and_deterministic(self):
        races = [self.race("y1", "SCY", 1), self.race("y2", "SCY", 2),
                 self.race("m1", "LCM", 3), self.race("m2", "LCM", 15)]
        pairs = match(races, 10)
        self.assertEqual([(p["source"]["race_id"], p["target"]["race_id"]) for p in pairs], [("y2", "m1")])
        self.assertEqual(pairs, match(list(reversed(races)), 10))
        self.assertEqual(pairs[0]["gap_days"], 1)

    def test_does_not_match_different_swimmers_events_or_categories(self):
        races = [self.race("y", "SCY", 1), self.race("a", "LCM", 2, athlete="b"),
                 self.race("b", "LCM", 2, distance=200), self.race("c", "LCM", 2, category="men")]
        self.assertEqual(match(races), [])

    def test_swimmer_partitions_do_not_depend_on_races(self):
        races = [self.race(f"{a}-{d}-{course}", course, 1 if course == "SCY" else 2, athlete=str(a), distance=d)
                 for a in range(100) for d in (50, 100) for course in ("SCY", "LCM")]
        seen = {}
        for p in match(races):
            seen.setdefault(p["swimmer_key"], set()).add(p["partition"])
        self.assertTrue(all(len(parts) == 1 for parts in seen.values()))
        self.assertEqual({partition(("fixture", str(a))) for a in range(100)}, {"train", "validation", "test"})

    def test_conflicting_duplicate_and_fractional_times_are_rejected(self):
        fields = ["source", "race_id", "swimmer_id", "meet_id", "date", "course", "distance",
                  "stroke", "category", "time_cs", "status", "age_years"]
        row = dict(zip(fields, ["fixture", "race", "a", "meet", "2026-01-01", "SCY", "100",
                                "freestyle", "women", "5832", "OK", "15"]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.csv"
            def write(rows):
                with path.open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
            write([row, row])
            self.assertEqual(read_results(path)[1]["duplicates"], 1)
            write([row, {**row, "time_cs": "5900"}])
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                read_results(path)
            write([{**row, "time_cs": "58.32"}])
            with self.assertRaisesRegex(ValueError, "integer centiseconds"):
                read_results(path)


if __name__ == "__main__":
    unittest.main()
