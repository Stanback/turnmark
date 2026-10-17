"""Import 2026 USMS NQT tables; deliberately fail when source editions change."""
import hashlib
from html.parser import HTMLParser
import json
import re
import subprocess
from pathlib import Path

URL = 'https://www.usms.org/events/national-championships/pool-national-championships/national-qualifying-times'
AGES = ['18-24'] + [f'{age}-{age + 4}' for age in range(25, 85, 5)]
STROKES = {'Free': 'FR', 'Back': 'BK', 'Breast': 'BR', 'Fly': 'FL', 'IM': 'IM'}
class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h = False; self.heading = ''; self.in_table = False; self.in_cell = False
        self.cell = ''; self.row = []; self.rows = []; self.tables = []
    def handle_starttag(self, tag, attrs):
        if tag == 'h3': self.h = True; self.heading = ''
        if tag == 'table': self.in_table = True; self.rows = []
        if self.in_table and tag == 'tr': self.row = []
        if self.in_table and tag in ('td', 'th'): self.in_cell = True; self.cell = ''
    def handle_data(self, text):
        if self.h: self.heading += text
        if self.in_cell: self.cell += text
    def handle_endtag(self, tag):
        if tag == 'h3': self.h = False
        if self.in_table and tag in ('td', 'th'):
            self.row.append(' '.join(self.cell.split())); self.in_cell = False
        if self.in_table and tag == 'tr': self.rows.append(self.row)
        if tag == 'table': self.tables.append((self.heading, self.rows)); self.in_table = False

raw = subprocess.check_output(['curl', '-fsSL', URL])
parser = Tables(); parser.feed(raw.decode('utf-8'))
records = []
for index, (course, category, season) in enumerate([('SCY', 'women', 'Spring'), ('SCY', 'men', 'Spring'), ('LCM', 'women', 'Summer'), ('LCM', 'men', 'Summer')]):
    heading, table = parser.tables[index]
    expected = f'2026 USMS {season} Nationals ({course}) - {category.title()}'
    assert heading.strip() == expected, (heading, expected)
    assert table[0] == ['Event', *AGES]
    assert len(table) == (19 if course == 'SCY' else 18)
    for cells in table[1:]:
        assert len(cells) == 14, cells
        match = re.fullmatch(r'(\d+) (Free|Back|Breast|Fly|IM)', cells[0])
        assert match, cells[0]
        distance, stroke = match.groups()
        times = []
        for text in cells[1:]:
            if text == 'NO TIME': times.append(None); continue
            assert re.fullmatch(r'(?:\d+:)?\d{1,2}\.\d{2}', text), text
            parts = text.split(':')
            seconds = float(parts[0]) * 60 + float(parts[1]) if len(parts) == 2 else float(text)
            assert seconds > 0
            times.append(round(seconds, 2))
        records.append({'course': course, 'category': category, 'distance': int(distance), 'stroke': STROKES[stroke], 'times': times})
assert len(records) == 70
assert len({(r['course'], r['category'], r['distance'], r['stroke']) for r in records}) == 70
result = {'source': {'name': '2026 USMS National Qualifying Times', 'url': URL, 'year': 2026, 'checked': '2026-10-16', 'sha256': hashlib.sha256(raw).hexdigest()}, 'ages': AGES, 'records': records}
Path('data/masters.json').write_text(json.dumps(result, indent=2) + '\n')
print(f'Imported {len(records)} event/category rows, {sum(t is not None for r in records for t in r["times"])} published targets; NO TIME retained as null.')
