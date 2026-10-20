#!/usr/bin/env python3
"""Build offline benchmarks from reviewed numeric transcriptions of official PDFs.

The USA Swimming PDFs are image-only; OCR is not trusted as numerical input.
Keep sources local, inspect every row, then edit the small CSV transcription.
--verify-sources downloads only the pinned documents and verifies fingerprints.
"""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import tempfile
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {'futures': 136, 'juniors': 68, 'nisca': 32}


def seconds(clock):
    if not re.fullmatch(r'(?:\d+:)?\d{1,2}\.\d{2}', clock):
        raise ValueError(f'Invalid published clock: {clock!r}')
    parts = clock.split(':')
    if len(parts) == 2 and Decimal(parts[1]) >= 60:
        raise ValueError(f'Invalid seconds component: {clock}')
    result = Decimal(parts[-1]) + (Decimal(parts[0]) * 60 if len(parts) == 2 else 0)
    if not 0 < result < 3600:
        raise ValueError(f'Out-of-range target: {clock}')
    return float(result)


def build():
    manifest = json.loads((ROOT / 'data/national-sources.json').read_text())
    programs = {p['id']: p for p in manifest['programs']}
    records = []
    seen = set()
    with (ROOT / 'data/source-tables/national-2027.csv').open() as source:
        reader = csv.DictReader(source)
        assert reader.fieldnames == ['program', 'age', 'course', 'category', 'distance', 'stroke', 'consideration', 'standard']
        for row in reader:
            program = programs[row['program']]
            assert row['category'] in ('women', 'men')
            assert row['course'] in (('SCY', 'SCM') if row['program'] == 'nisca' else ('SCY', 'LCM'))
            assert row['age'] in (program['ages'] or [''])
            assert row['stroke'] in ('FR', 'BK', 'BR', 'FL', 'IM')
            distance = int(row['distance'])
            assert distance in (50, 100, 200, 400, 500, 800, 1000, 1500, 1650)
            assert row['stroke'] == 'FR' or distance in (50, 100, 200, 400)
            key = tuple(row[k] for k in ('program', 'age', 'course', 'category', 'distance', 'stroke'))
            assert key not in seen, f'Duplicate key: {key}'
            seen.add(key)
            clocks = [row['consideration'], row['standard']] if row['program'] == 'nisca' else [row['standard']]
            assert row['program'] == 'nisca' or not row['consideration']
            times = list(map(seconds, clocks))
            assert all(a > b for a, b in zip(times, times[1:])), f'Target order: {key}'
            records.append(dict(program=row['program'], age=row['age'], course=row['course'], category=row['category'], distance=distance, stroke=row['stroke'], times=times))
    assert Counter(r['program'] for r in records) == EXPECTED
    for program in programs.values():
        subset = [r for r in records if r['program'] == program['id']]
        expected_per_age = 68 if program['id'] == 'futures' else len(subset)
        for age in program['ages'] or ['']:
            assert sum(r['age'] == age for r in subset) == expected_per_age
            events = ({'FR': [50, 100, 200, 400], 'BK': [100], 'BR': [100], 'FL': [100], 'IM': [200]}
                      if program['id'] == 'nisca' else
                      {'FR': [50, 100, 200, 400, 800, 1500], 'BK': [50, 100, 200], 'BR': [50, 100, 200], 'FL': [50, 100, 200], 'IM': [200, 400]})
            for course in (('SCY', 'SCM') if program['id'] == 'nisca' else ('SCY', 'LCM')):
                expected = {(stroke, {400: 500, 800: 1000, 1500: 1650}.get(distance, distance)
                             if stroke == 'FR' and course == 'SCY' else distance)
                            for stroke, distances in events.items() for distance in distances}
                for category in ('women', 'men'):
                    actual = {(r['stroke'], r['distance']) for r in subset
                              if r['age'] == age and r['course'] == course and r['category'] == category}
                    assert actual == expected, f'Unexpected event coverage: {program["id"]}/{age}/{course}/{category}'
    return dict(schemaVersion=1, programs=list(programs.values()), records=records,
                transcriptionSha256=hashlib.sha256((ROOT / 'data/source-tables/national-2027.csv').read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--verify-sources', action='store_true')
    args = parser.parse_args()
    snapshot = build()
    if args.verify_sources:
        sources = {}
        for p in snapshot['programs']:
            for source in [p['source'], *p.get('sourceByCourse', {}).values(), *([p['rules']] if 'rules' in p else [])]:
                sources[source['url']] = source
        with tempfile.TemporaryDirectory() as directory:
            for i, source in enumerate(sources.values()):
                path = Path(directory) / f'{i}.pdf'
                subprocess.run(['curl', '-fsSL', '--retry', '2', '--max-time', '60', source['url'], '-o', str(path)], check=True)
                assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'], f"Source changed; review before updating: {source['url']}"
    output = json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n'
    destination = ROOT / 'data/national-standards.json'
    if args.check:
        assert json.loads(destination.read_text()) == snapshot, 'National snapshot is stale; run the importer'
    else:
        destination.write_text(output)
    print(f"Verified {len(snapshot['records'])} event/category/age records across three benchmark programs")


if __name__ == '__main__':
    main()
