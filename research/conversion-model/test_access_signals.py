"""Response evidence must not become unsupported WAF or no-WAF claims."""
import json
import unittest
from access_signals import response_signals


class AccessSignalTests(unittest.TestCase):
    def test_403_without_evidence_is_not_named_waf(self):
        row = response_signals(403, {}, b'Forbidden')
        self.assertEqual(row['edge_provider'], 'unknown')
        self.assertEqual(row['protection_observation'], 'status_only_block')
        self.assertTrue(row['browser_review_needed'])
        self.assertFalse(row['waf_rule_verified'])

    def test_edge_on_success_does_not_imply_challenge_or_waf(self):
        row = response_signals(200, {'Server': 'cloudflare', 'CF-Ray': 'invented-trace'})
        self.assertEqual(row['edge_provider'], 'cloudflare')
        self.assertEqual(row['protection_observation'], 'no_challenge_observed')
        self.assertFalse(row['browser_review_needed'])
        self.assertFalse(row['waf_rule_verified'])

    def test_header_only_challenge_requires_review_even_on_http_200(self):
        row = response_signals(200, {'CF-Mitigated': 'challenge'}, b'<h1>Wait</h1>')
        self.assertEqual(row['protection_observation'], 'challenge_observed')
        self.assertTrue(row['browser_review_needed'])
        self.assertIn('cf_mitigated_challenge', row['signal_codes'])

    def test_generic_captcha_does_not_identify_provider(self):
        row = response_signals(200, {}, b'<h1>Complete the CAPTCHA</h1>')
        self.assertEqual(row['edge_provider'], 'unknown')
        self.assertEqual(row['protection_observation'], 'challenge_observed')
        ordinary = response_signals(200, {}, b'<style>.captcha_wrapper{}</style><script>var captchaValue="";</script><p>Public results</p>')
        self.assertFalse(ordinary['browser_review_needed'])

    def test_azure_waf_branded_interstitial_is_distinct_from_plain_403(self):
        row = response_signals(403, {}, b'<title>Azure WAF</title><div id="challenge-error-div">Error</div>')
        self.assertIn('azure_waf_challenge_page', row['signal_codes'])
        self.assertEqual(row['protection_observation'], 'challenge_observed')
        self.assertEqual(row['edge_provider'], 'unknown')
        self.assertFalse(row['waf_rule_verified'])
        ordinary = response_signals(200, {}, b'<p>Azure WAF documentation</p>')
        self.assertFalse(ordinary['browser_review_needed'])

    def test_sensitive_headers_and_body_do_not_escape_projection(self):
        row = response_signals(403, {'Set-Cookie': 'private-cookie', 'Authorization': 'private-token', 'Server': 'private-server-name'}, b'private-athlete-name')
        text = json.dumps(row)
        for value in ['private-cookie', 'private-token', 'private-server-name', 'private-athlete-name']:
            self.assertNotIn(value, text)
        self.assertEqual(set(row), {'edge_provider', 'protection_observation', 'waf_rule_verified', 'browser_review_needed', 'signal_codes'})


class AccessLedgerTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        from access_signals import ACCESS_FIELDS
        self.row = dict(zip(ACCESS_FIELDS, (
            'access:invented', 'https://example.org', 'https://example.org/robots.txt',
            '2026-10-20T12:00:00+00:00', '403', 'unknown', 'status_only_block',
            'false', 'http_403', 'pending', '', 'status_log_only',
            'Historical status only; response headers/body not retained.')))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        import csv
        import hashlib
        from access_signals import ACCESS_FIELDS
        path = self.root / 'site-access-reviews.csv'
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=ACCESS_FIELDS)
            writer.writeheader()
            writer.writerow(self.row)
        (self.root / 'site-access-reviews.manifest.json').write_text(json.dumps({
            'schema_version': 1, 'scope': 'observed-site-access-signals', 'rows': 1,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))

    def test_historical_status_gap_is_preserved_and_tampering_rejected(self):
        from access_signals import read_site_reviews
        self.write()
        rows, _ = read_site_reviews(self.root)
        self.assertEqual(rows[0]['edge_provider'], 'unknown')
        with (self.root / 'site-access-reviews.csv').open('a') as stream:
            stream.write('tampered')
        with self.assertRaises(ValueError):
            read_site_reviews(self.root)

    def test_status_log_cannot_invent_provider_or_body_hash(self):
        from access_signals import read_site_reviews
        for field, value in [('edge_provider', 'cloudflare'), ('body_sha256', 'a' * 64), ('waf_rule_verified', 'true')]:
            original = self.row[field]
            self.row[field] = value
            self.write()
            with self.assertRaises(ValueError):
                read_site_reviews(self.root)
            self.row[field] = original

    def test_query_tokens_and_arbitrary_signal_text_are_not_public_fields(self):
        from access_signals import read_site_reviews
        for field, value in [('observed_url', 'https://example.org/?token=private'), ('signal_codes', 'Set-Cookie: secret')]:
            original = self.row[field]
            self.row[field] = value
            self.write()
            with self.assertRaises(ValueError):
                read_site_reviews(self.root)
            self.row[field] = original
