"""Offline pilot only: validate results, match races and hold out swimmers."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Race:
    source: str
    race_id: str
    swimmer_id: str
    meet_id: str
    date: date
    course: str
    distance: int
    stroke: str
    category: str
    time_cs: int
    age_years: float | None

    @property
    def athlete(self):
        return self.source, self.swimmer_id

    @property
    def key(self):
        return self.source, self.race_id


def read_results(path: Path) -> tuple[list[Race], dict[str, int]]:
    races: dict[tuple[str, str], Race] = {}
    counts = {"rows": 0, "excluded": 0, "duplicates": 0}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"source", "race_id", "swimmer_id", "meet_id", "date", "course",
                    "distance", "stroke", "category", "time_cs", "status", "age_years"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for line, row in enumerate(reader, 2):
            counts["rows"] += 1
            # The pilot deliberately excludes non-freestyle, distance events,
            # relays/splits and invalid results instead of guessing mappings.
            if (row["status"] != "OK" or row["stroke"] != "freestyle"
                    or row["course"] not in {"SCY", "LCM"}
                    or row["distance"] not in {"50", "100", "200"}):
                counts["excluded"] += 1
                continue
            try:
                if any(not row[key].strip() for key in ("source", "race_id", "swimmer_id", "meet_id")):
                    raise ValueError("Identifiers must be nonempty")
                if row["category"] not in {"women", "men"}:
                    raise ValueError("Unknown published category")
                if not row["time_cs"].isascii() or not row["time_cs"].isdigit():
                    raise ValueError("time_cs must be positive integer centiseconds")
                time_cs = int(row["time_cs"])
                if not 0 < time_cs <= 360000:
                    raise ValueError("time_cs outside the core's supported range")
                age = float(row["age_years"]) if row["age_years"] else None
                if age is not None and not 0 <= age <= 110:
                    raise ValueError("Invalid age")
                race = Race(row["source"], row["race_id"], row["swimmer_id"], row["meet_id"],
                            date.fromisoformat(row["date"]), row["course"], int(row["distance"]),
                            row["stroke"], row["category"], time_cs, age)
            except (ValueError, TypeError) as error:
                raise ValueError(f"CSV line {line}: {error}") from error
            if race.key in races:
                if races[race.key] != race:
                    raise ValueError(f"Conflicting source race ID at CSV line {line}")
                counts["duplicates"] += 1
            races[race.key] = race
    return list(races.values()), counts


def partition(athlete: tuple[str, str]) -> str:
    # Independent of race order and outcomes. Never split the same swimmer's
    # race pairs or reversed pairs across training, validation and test.
    bucket = int.from_bytes(hashlib.sha256(json.dumps(athlete).encode()).digest()[:8], "big") % 100
    return "train" if bucket < 70 else "validation" if bucket < 85 else "test"


def match(races: list[Race], max_days: int = 30) -> list[dict]:
    if not 1 <= max_days <= 90:
        raise ValueError("Choose a matching window between 1 and 90 days")
    groups: dict[tuple, list[Race]] = {}
    for race in races:
        groups.setdefault((*race.athlete, race.distance, race.stroke, race.category), []).append(race)
    pairs = []
    for key, group in sorted(groups.items()):
        candidates = sorted(
            (abs((b.date - a.date).days), a.date, b.date, a.race_id, b.race_id, a, b)
            for a in group if a.course == "SCY"
            for b in group if b.course == "LCM" and abs((b.date - a.date).days) <= max_days
        )
        used = set()
        for gap, _, _, _, _, source, target in candidates:
            if source.key in used or target.key in used:
                continue
            used.update((source.key, target.key))
            pairs.append({
                "swimmer_key": json.dumps(source.athlete),
                "partition": partition(source.athlete),
                "source": {**asdict(source), "date": source.date.isoformat()},
                "target": {**asdict(target), "date": target.date.isoformat()},
                "gap_days": (target.date - source.date).days,
            })
    return pairs


def prepare(csv_path: Path, output: Path, manifest: Path, max_days: int = 30) -> dict:
    provenance = json.loads(manifest.read_text())
    for key in ("source_url", "retrieved", "reuse_notes", "age_precision", "synthetic"):
        if key not in provenance:
            raise ValueError(f"Dataset manifest requires {key}")
    if not isinstance(provenance["synthetic"], bool):
        raise ValueError("synthetic must be a boolean")
    date.fromisoformat(provenance["retrieved"])
    if any(not isinstance(provenance[key], str) or not provenance[key].strip()
           for key in ("source_url", "reuse_notes", "age_precision")):
        raise ValueError("Dataset provenance fields must be nonempty strings")
    races, counts = read_results(csv_path)
    pairs = match(races, max_days)
    output.mkdir(parents=True, exist_ok=True)
    (output / "pairs.json").write_text(json.dumps(pairs, indent=2) + "\n")
    report = {
        "pilot": "SCY-to-LCM-freestyle-50-100-200",
        "dataset": provenance,
        "input_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "matching_window_days": max_days,
        "counts": {**counts, "eligible_races": len(races), "matched_pairs": len(pairs)},
        "partitions": {name: {"pairs": sum(p["partition"] == name for p in pairs),
                               "swimmers": len({p["swimmer_key"] for p in pairs if p["partition"] == name})}
                       for name in ("train", "validation", "test")},
        "validated_for_product": False,
    }
    (output / "dataset-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-days", type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(prepare(args.csv, args.output, args.manifest, args.max_days), indent=2))
