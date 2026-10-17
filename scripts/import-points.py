"""Import individual-event World Aquatics 2026 base times from the official PDF."""
import hashlib
import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

URL = 'https://resources.fina.org/fina/document/2026/09/05/9b48fb98-233c-4ce9-b67b-bc6163319bbd/Points-Base-times-SCM-and-LCM-2026_09.2026.pdf'
STROKES = {'Freestyle': 'FR', 'Backstroke': 'BK', 'Breaststroke': 'BR', 'Butterfly': 'FL', 'Medley': 'IM'}
with tempfile.TemporaryDirectory() as folder:
    pdf = Path(folder) / 'base-times.pdf'
    urllib.request.urlretrieve(URL, pdf)
    fingerprint = hashlib.sha256(pdf.read_bytes()).hexdigest()
    raw = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
rows = []
for course, page in zip(['SCM', 'LCM'], raw.split('\f')[:2], strict=True):
    assert f'{course} (' in page
    assert ('01.09.2026' if course == 'SCM' else '01.01.2026') in page
    for line in page.splitlines():
        match = re.match(r'^\s*(\d+)m (Freestyle|Backstroke|Breaststroke|Butterfly|Medley)\s+([\d:.]+)\s+([\d.]+)\s+([\d:.]+)\s+([\d.]+)\s*$', line)
        if not match:
            continue
        distance, stroke, male_display, male, female_display, female = match.groups()
        def seconds(value):
            parts = value.split(':')
            return float(parts[0]) * 60 + float(parts[1]) if len(parts) == 2 else float(value)
        assert abs(seconds(male_display) - float(male)) < .001
        assert abs(seconds(female_display) - float(female)) < .001
        rows.append({'course': course, 'distance': int(distance), 'stroke': STROKES[stroke], 'men': float(male), 'women': float(female)})
assert len(rows) == 35, f'Expected 35 events, found {len(rows)}'
assert len({(x['course'], x['distance'], x['stroke']) for x in rows}) == 35
result = {'source': {'name': 'World Aquatics 2026 points base times', 'url': URL, 'method': 'https://www.worldaquatics.com/swimming/points', 'checked': '2026-10-16', 'sha256': fingerprint}, 'validity': {'SCM': 'September 1, 2026 – August 31, 2027', 'LCM': 'January 1 – December 31, 2026'}, 'events': rows}
Path('packages/sdk/src/data/points.json').write_text(json.dumps(result, indent=2) + '\n')
print(f'Imported {len(rows)} events / {len(rows)*2} base times.')
