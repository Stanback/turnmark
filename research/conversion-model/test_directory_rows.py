"""Invented listings exercise reusable offline adapters, never live sources."""
import tempfile
import unittest
from pathlib import Path

from directory_rows import csv_columns, html_table_columns, json_columns, text_columns


class DirectoryRowsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "source.txt"

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def test_csv_and_tsv_project_reviewed_facts_without_contacts(self):
        mapping = {"organization_key": "ID", "organization_name": "Club"}
        self.assertEqual(csv_columns(self.write(
            '\ufeffID,Club,Contact\r\n001,"Example, West",private@example.invalid\r\n'), mapping),
            [{"organization_key": "001", "organization_name": "Example, West"}])
        self.assertEqual(csv_columns(self.write(
            'ID\tClub\tContact\n002\tExample East\tdiscarded\n'), mapping, delimiter="\t"),
            [{"organization_key": "002", "organization_name": "Example East"}])
        for malformed in ('ID,ID,Club\n1,2,Example\n', 'ID,Name\n1,Example\n',
                          'ID,Club\n1,Example,Extra\n'):
            with self.subTest(source=malformed), self.assertRaises(ValueError):
                csv_columns(self.write(malformed), mapping)
        with self.assertRaises(ValueError):
            csv_columns(self.write('Contact\nprivate\n'), {"contact": "Contact"})

    def test_json_explicit_nested_fields_and_ambiguous_source_rejection(self):
        mapping = {"organization_key": "/id", "state": "/location/state", "website": "/website"}
        self.assertEqual(json_columns(self.write(
            '{"items":[{"id":7,"location":{"state":"OR"},"website":null,"contact":"private"}]}'),
            mapping, root="/items"),
            [{"organization_key": "7", "state": "OR", "website": None}])
        self.assertEqual(json_columns(self.write('[{"a/b":{"~key":"value"}}]'),
                                      {"organization_key": "/a~1b/~0key"}),
                         [{"organization_key": "value"}])
        for malformed in ('[{"id":1,"id":2}]', '[{"id":true}]',
                          '[{"id":["ambiguous"]}]', '[{}]', '{}'):
            with self.subTest(source=malformed), self.assertRaises(ValueError):
                json_columns(self.write(malformed), {"organization_key": "/id"})

    def test_html_named_table_text_links_and_layout_ambiguity(self):
        mapping = {"organization_name": "Club", "website": "Site"}
        self.assertEqual(html_table_columns(self.write(
            '<table id="other"><tr><td>Ignore</td></tr></table>'
            '<table id="clubs"><tr><th>Club</th><th>Site</th><th>Contact</th></tr>'
            '<tr><td>Example &amp; <b>Friends</b></td><td><a href="/club">Visit</a></td>'
            '<td>private@example.invalid</td></tr></table>'), mapping,
            table_id="clubs", href_columns=("website",), base_url="https://example.invalid"),
            [{"organization_name": "Example & Friends", "website": "https://example.invalid/club"}])
        for cells in (
            '<td colspan="2">Merged</td>',
            '<td>Club</td><td><a href="/a">A</a><a href="/b">B</a></td>',
            '<td><table><tr><td>Nested</td></tr></table></td><td>Site</td>',
        ):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                html_table_columns(self.write(
                    '<table id="clubs"><tr><th>Club</th><th>Site</th></tr><tr>'
                    + cells + '</tr></table>'), mapping,
                    table_id="clubs", href_columns=("website",))
        with self.assertRaises(ValueError):
            html_table_columns(self.write('<table id="other"></table>'), mapping, table_id="clubs")


    def test_text_table_requires_complete_rows_and_reviewed_count(self):
        pattern = r"\s*(?P<id>\d+) +(?P<name>[A-Za-z ]+?) {2,}(?P<city>[A-Za-z ]+) {2,}(?P<discard>\S+)\s*"
        options = dict(row_pattern=pattern, candidate_pattern=r"^\s*\d+\s", expected_count=2)
        mapping = {"organization_key": "id", "organization_name": "name", "city": "city"}
        valid = "Directory header\n 1 Example West   Sample City   private@example.invalid\n\f 2 Example East   Other City   private\n"
        rows = text_columns(self.write(valid), mapping, **options)
        self.assertEqual(rows[0], {"organization_key":"1", "organization_name":"Example West", "city":"Sample City"})
        self.assertEqual(len(rows), 2)
        for source in (valid.replace(" 2 Example East", " 2 ???"), valid + " 3 Broken row\n", valid.split("\f")[0]):
            with self.subTest(source=source), self.assertRaises(ValueError):
                text_columns(self.write(source), mapping, **options)
        with self.assertRaises(ValueError):
            text_columns(self.write(valid), {"contact":"discard"}, **options)
        with self.assertRaises(ValueError):
            text_columns(self.write(valid), {"organization_name":"missing"}, **options)

    def test_embedded_json_is_literal_only_and_projects_no_unselected_fields(self):
        from directory_rows import embedded_json_columns
        marker = 'Components.Directory, '
        text = '<script>render(Components.Directory, {"data":{"items":[{"id":"01","name":"Example","contact":"private@example.invalid"}]}}, node)</script>'
        rows = embedded_json_columns(self.write(text), {"organization_key":"/id", "organization_name":"/name"}, marker=marker, root="/data/items")
        self.assertEqual(rows, [{"organization_key":"01", "organization_name":"Example"}])
        for source in (text+text, text.replace(marker, 'Other, '), text.replace('{"data":', 'getData()+{"data":'), text.replace('"id":"01"', '"id":"01","id":"02"')):
            with self.subTest(source=source), self.assertRaises(ValueError):
                embedded_json_columns(self.write(source), {"organization_key":"/id"}, marker=marker, root="/data/items")

    def test_jsonp_requires_one_exact_callback_wrapper_around_a_literal(self):
        from directory_rows import jsonp_columns
        mapping = {"organization_name": "/name", "website": "/website"}
        text = 'load_clubs([{"name":"Example Club","website":"https://example.invalid","phone":"private"}]);'
        self.assertEqual(jsonp_columns(self.write(text), mapping, callback="load_clubs"),
                         [{"organization_name": "Example Club", "website": "https://example.invalid"}])
        self.assertEqual(jsonp_columns(self.write('cb({"rows":[{"name":"A","website":null}]})'),
                                       mapping, callback="cb", root="/rows"),
                         [{"organization_name": "A", "website": None}])
        for source in ('other([{"name":"A","website":""}])', 'load_clubs([{"name":"A","website":""}]); alert(1)',
                       'load_clubs([{"name":"A","website":""}]) trailing', 'load_clubs(fetch())',
                       'load_clubs([{"name":"A","name":"B","website":""}])', 'load_clubs([{"name":["A"],"website":""}])'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                jsonp_columns(self.write(source), mapping, callback="load_clubs")
        with self.assertRaises(ValueError):
            jsonp_columns(self.write(text), mapping, callback="load_clubs(")
        with self.assertRaises(ValueError):
            jsonp_columns(self.write(text), {"phone": "/phone"}, callback="load_clubs")

    def test_repeated_elements_project_ids_with_reviewed_count(self):
        from directory_rows import html_element_columns
        text = '<div class="other">ignore</div><td class="team" data-id="01" data-name="Example &amp; East"><a>Shown <b>name</b></a></td><td class="team" data-id="02" data-name="Example West">Other</td>'
        options = dict(tag="td", attributes={"class":"team"}, expected_count=2)
        rows = html_element_columns(self.write(text), {"organization_key":"@data-id", "organization_name":"@data-name"}, **options)
        self.assertEqual(rows[0], {"organization_key":"01", "organization_name":"Example & East"})
        for source in (text.replace('data-id="02"', ''), text.replace('</td>', '', 1), text.replace('class="team"', 'class="changed"', 1)):
            with self.subTest(source=source), self.assertRaises(ValueError):
                html_element_columns(self.write(source), {"organization_key":"@data-id"}, **options)
