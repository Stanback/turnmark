"""Conservative response evidence for local collectors; no network or bypass logic.

Cloudflare documents cf-mitigated: challenge at:
https://developers.cloudflare.com/cloudflare-challenges/challenge-types/challenge-pages/detect-response/
An edge provider, a challenge response and a confirmed WAF rule are different
claims. These observations never establish which security product/rule fired.
Only fixed signal codes escape; arbitrary headers, cookies and page text do not.
"""
from html.parser import HTMLParser


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('style', 'script'):
            self.hidden.append(tag)

    def handle_endtag(self, tag):
        if self.hidden and self.hidden[-1] == tag:
            self.hidden.pop()

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def challenge_page(body):
    text = body[:12000].decode('utf-8', 'replace').lower()
    if '<title>azure waf</title>' in text and 'challenge-error-div' in text:
        return True
    if any(x in text for x in ('cf-chl-', 'verify you are human', 'just a moment')):
        return True
    visible = VisibleText()
    visible.feed(text)
    return 'captcha' in ' '.join(visible.parts)


def response_signals(status, headers, body=b''):
    """Evidence from one response; absence never proves that a site has no WAF."""
    headers = {str(k).lower(): str(v).strip().lower() for k, v in headers.items()}
    codes = []
    edge = 'unknown'
    if headers.get('server') == 'cloudflare' or 'cf-ray' in headers:
        edge = 'cloudflare'
        codes.append('cloudflare_edge_header')
    challenge = headers.get('cf-mitigated') == 'challenge'
    if challenge:
        edge = 'cloudflare'
        codes.append('cf_mitigated_challenge')
    text = body[:12000].decode('utf-8', 'replace').lower()
    if '<title>azure waf</title>' in text and 'challenge-error-div' in text:
        codes.append('azure_waf_challenge_page')
    if challenge_page(body):
        challenge = True
        codes.append('challenge_page_marker')
    if status in (401, 403, 429):
        codes.append('http_' + str(status))
    return {
        'edge_provider': edge,
        'protection_observation': 'challenge_observed' if challenge else 'status_only_block' if status in (401, 403, 429) else 'no_challenge_observed',
        'waf_rule_verified': False,
        'browser_review_needed': challenge or status == 403,
        'signal_codes': sorted(codes),
    }


ACCESS_FIELDS = ('review_id', 'origin', 'observed_url', 'checked_at', 'http_status',
                 'edge_provider', 'protection_observation', 'waf_rule_verified',
                 'signal_codes', 'browser_review_status', 'body_sha256',
                 'evidence_kind', 'notes')
SIGNALS = {'cloudflare_edge_header', 'cf_mitigated_challenge',
           'challenge_page_marker', 'azure_waf_challenge_page', 'http_401', 'http_403', 'http_429'}


def read_site_reviews(root):
    """Verify the optional reviewed public ledger independently of raw captures."""
    import csv
    import hashlib
    import json
    from datetime import datetime
    from pathlib import Path
    from urllib.parse import urlsplit, parse_qsl
    import re
    root = Path(root)
    manifest = json.loads((root / 'site-access-reviews.manifest.json').read_text())
    path = root / 'site-access-reviews.csv'
    if manifest.get('schema_version') != 1 or manifest.get('scope') != 'observed-site-access-signals':
        raise ValueError('Unexpected site access review schema')
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError('Access review CSV differs from its manifest')
    with path.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != ACCESS_FIELDS:
            raise ValueError('Unexpected access review columns')
        records = list(reader)
    if len(records) != manifest['rows'] or len({r['review_id'] for r in records}) != len(records):
        raise ValueError('Access review count or identity mismatch')
    for row in records:
        origin = urlsplit(row['origin'])
        url = urlsplit(row['observed_url'])
        if (origin.scheme not in ('http', 'https') or not origin.netloc
                or origin.path or origin.query or origin.fragment or origin.username or origin.password
                or url.scheme != origin.scheme or url.netloc != origin.netloc
                or url.username or url.password or url.fragment):
            raise ValueError('Require an exact public origin and reviewed URL without query credentials')
        if url.query:
            pairs = parse_qsl(url.query, keep_blank_values=True)
            if len(pairs) != 1 or pairs[0][0] != 'MeetID' or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', pairs[0][1]):
                raise ValueError('Only a public MeetID selector is reviewed; no arbitrary query parameters')
        if datetime.fromisoformat(row['checked_at']).tzinfo is None:
            raise ValueError('Require timezone-aware access observation')
        if row['http_status'] and not (row['http_status'].isdigit() and 100 <= int(row['http_status']) <= 599):
            raise ValueError('Invalid observed status')
        if row['edge_provider'] not in ('unknown', 'cloudflare') or row['waf_rule_verified'] != 'false':
            raise ValueError('Unsupported provider or WAF-rule assertion')
        if row['protection_observation'] not in ('challenge_observed', 'status_only_block', 'no_challenge_observed'):
            raise ValueError('Unknown protection observation')
        if not set(filter(None, row['signal_codes'].split(';'))) <= SIGNALS:
            raise ValueError('Unreviewed response signals')
        if row['browser_review_status'] not in ('pending', 'not_needed', 'accessible_in_browser', 'still_blocked', 'browser_unavailable'):
            raise ValueError('Unknown browser review status')
        digest = row['body_sha256']
        if row['evidence_kind'] not in ('cached_response', 'response_signals', 'status_log_only'):
            raise ValueError('Unknown response evidence kind')
        if row['evidence_kind'] == 'status_log_only':
            if digest or row['edge_provider'] != 'unknown' or row['protection_observation'] != 'status_only_block':
                raise ValueError('Status log alone cannot supply response-body/provider evidence')
        elif len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Cached response needs original body SHA-256')
        if not row['notes'] or any(ord(c) < 32 for value in row.values() for c in value):
            raise ValueError('Require plain reviewed context')
    return records, manifest


def load_site_reviews(db, root):
    """Add reviewed source-access facts, without inferring absence of protection."""
    import json
    rows, manifest = read_site_reviews(root)
    db.execute('CREATE TABLE site_access_reviews (' + ','.join(f'{f} VARCHAR' for f in ACCESS_FIELDS) + ')')
    if rows:
        db.executemany('INSERT INTO site_access_reviews VALUES (' + ','.join('?' for _ in ACCESS_FIELDS) + ')',
                       [[row[f] or None for f in ACCESS_FIELDS] for row in rows])
    db.execute('INSERT INTO provenance VALUES (?,?)', ['site-access-observations', json.dumps(manifest, sort_keys=True)])
    return len(rows)
