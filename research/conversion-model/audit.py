"""Aggregate-only coverage audit; no swimmer names or IDs in the output."""

from __future__ import annotations
import csv, json, math
from collections import Counter, defaultdict
from pathlib import Path

AGE_BANDS = ("10u", "11-12", "13-14", "15-16", "17-18", "19+", "unknown")


def age_band(value):
    if value in ("", None):
        return "unknown"
    age = float(value)
    if not math.isfinite(age) or not 0 < age <= 110:
        raise ValueError("Invalid age in audit input")
    return (
        "10u"
        if age < 11
        else "11-12"
        if age < 13
        else "13-14"
        if age < 15
        else "15-16"
        if age < 17
        else "17-18"
        if age < 19
        else "19+"
    )


def audit(path: Path):
    counts = {
        k: Counter()
        for k in (
            "course",
            "category",
            "age_band",
            "event",
            "year",
            "region",
            "meet_class",
        )
    }
    cells = defaultdict(lambda: {"races": 0, "swimmers": set(), "meets": set()})
    ids = set()
    athletes = set()
    meets = set()
    duplicate = 0
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        required = {
            "source",
            "race_id",
            "swimmer_id",
            "meet_id",
            "course",
            "category",
            "age_years",
            "stroke",
            "distance",
            "date",
            "status",
        }
        if not required <= set(reader.fieldnames or []):
            raise ValueError("Missing normalized result columns")
        for row in reader:
            if row["status"] != "OK":
                continue
            key = (row["source"], row["race_id"])
            if key in ids:
                duplicate += 1
                continue
            ids.add(key)
            athlete = (row["source"], row["swimmer_id"])
            meet = (row["source"], row["meet_id"])
            athletes.add(athlete)
            meets.add(meet)
            band = age_band(row["age_years"])
            event = f"{row['distance']} {row['stroke']}"
            for k, value in [
                ("course", row["course"]),
                ("category", row["category"]),
                ("age_band", band),
                ("event", event),
                ("year", row["date"][:4]),
                ("region", row.get("region", "unknown")),
                ("meet_class", row.get("meet_class", "unknown")),
            ]:
                counts[k][value] += 1
            c = cells[(row["course"], row["category"], band, event)]
            c["races"] += 1
            c["swimmers"].add(athlete)
            c["meets"].add(meet)
    # Zero cells remain visible for the initial 3-event SCY/LCM experiment.
    for course in ("SCY", "LCM"):
        for category in ("women", "men"):
            for band in AGE_BANDS:
                for distance in (50, 100, 200):
                    cells[(course, category, band, f"{distance} freestyle")]
    return {
        "races": len(ids),
        "swimmers": len(athletes),
        "meets": len(meets),
        "duplicate_rows": duplicate,
        "cohorts": {k: dict(sorted(v.items())) for k, v in counts.items()},
        "cells": [
            {
                "course": k[0],
                "category": k[1],
                "age_band": k[2],
                "event": k[3],
                "races": c["races"],
                "swimmers": len(c["swimmers"]),
                "meets": len(c["meets"]),
            }
            for k, c in sorted(cells.items())
        ],
        "representative_sample": False,
        "validated_for_product": False,
    }


def pair_coverage(pairs):
    counts = defaultdict(
        lambda: {
            "pairs": 0,
            "swimmers": set(),
            "source_meets": set(),
            "target_meets": set(),
        }
    )
    hist = Counter()
    for p in pairs:
        source, target = p["source"], p["target"]
        key = (
            p["partition"],
            source["category"],
            age_band(source["age_years"]),
            source["distance"],
            source["stroke"],
        )
        c = counts[key]
        c["pairs"] += 1
        c["swimmers"].add(p["swimmer_key"])
        c["source_meets"].add(source["meet_id"])
        c["target_meets"].add(target["meet_id"])
        hist[str(abs(p["gap_days"]))] += 1
    return {
        "cells": [
            {
                "partition": k[0],
                "category": k[1],
                "age_band": k[2],
                "distance": k[3],
                "stroke": k[4],
                "pairs": c["pairs"],
                "swimmers": len(c["swimmers"]),
                "source_meets": len(c["source_meets"]),
                "target_meets": len(c["target_meets"]),
            }
            for k, c in sorted(counts.items())
        ],
        "absolute_gap_days": dict(sorted(hist.items(), key=lambda x: int(x[0]))),
        "validated_for_product": False,
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--pairs", type=Path)
    a = p.parse_args()
    result = audit(a.csv)
    if a.pairs:
        result["matched_pairs"] = pair_coverage(json.loads(a.pairs.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("cells", "matched_pairs")},
            indent=2,
        )
    )
