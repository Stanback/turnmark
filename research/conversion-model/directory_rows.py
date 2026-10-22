"""Offline format adapters for reviewed organizational directory columns.

These readers project explicit columns, not entire source records. Source files
stay local. Classifications, authority namespaces and identity reconciliation
remain explicit work before passing normalized facts to directory_import.
"""
from __future__ import annotations

import csv
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

from directory_import import FIELDS


def _columns(mapping):
    if not mapping or not set(mapping) <= FIELDS or any(not isinstance(k, str) or not k or not isinstance(v, str)
                          or not v for k, v in mapping.items()):
        raise ValueError("Explicit output-to-source columns are required")


def csv_columns(path, columns, *, delimiter=","):
    """Read CSV/TSV with strict headers/row widths; discard unselected fields."""
    _columns(columns)
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, delimiter=delimiter, strict=True)
        headers = next(reader, [])
        if len(set(headers)) != len(headers) or not set(columns.values()) <= set(headers):
            raise ValueError("Duplicate or missing source columns")
        indices = {field: headers.index(source) for field, source in columns.items()}
        result = []
        for row in reader:
            if len(row) != len(headers):
                raise ValueError("Source row width differs from its header")
            result.append({field: row[index] for field, index in indices.items()})
        return result


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Duplicate JSON key")
        obj[key] = value
    return obj


def _pointer(obj, pointer):
    if pointer == "":
        return obj
    if not pointer.startswith("/"):
        raise ValueError("Use an explicit JSON pointer")
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(obj, dict) or token not in obj:
            raise ValueError("JSON pointer missing from source object")
        obj = obj[token]
    return obj


def json_columns(path, columns, *, root=""):
    """Project string/null/integer fields from a JSON array; no guessed keys."""
    _columns(columns)
    document = json.loads(Path(path).read_text(encoding="utf-8-sig"),
                          object_pairs_hook=_unique_object)
    return _json_rows(document, columns, root)


def _json_rows(document, columns, root):
    rows = _pointer(document, root)
    if not isinstance(rows, list):
        raise ValueError("Selected JSON root must be an array")
    result = []
    for row in rows:
        projected = {}
        for field, pointer in columns.items():
            value = _pointer(row, pointer)
            if value is not None and type(value) not in (str, int):
                raise ValueError("Selected JSON facts must be strings, integers or null")
            projected[field] = str(value) if type(value) is int else value
        result.append(projected)
    return result


class _Table(HTMLParser):
    def __init__(self, table_id):
        super().__init__(convert_charrefs=True)
        self.table_id = table_id
        self.active = False
        self.matches = 0
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "table":
            if self.active:
                raise ValueError("Nested directory tables require review")
            if attrs.get("id") == self.table_id:
                self.active = True
                self.matches += 1
        if not self.active:
            return
        if tag == "tr":
            if self.row is not None:
                raise ValueError("Malformed table row")
            self.row = []
        if tag in ("th", "td"):
            if self.cell is not None or self.row is None:
                raise ValueError("Malformed table cell")
            if any(attrs.get(key, "1") != "1" for key in ("colspan", "rowspan")):
                raise ValueError("Spanning directory cells require review")
            self.cell = {"text": [], "links": []}
        if tag == "a" and self.cell is not None and attrs.get("href"):
            self.cell["links"].append(attrs["href"])
        if tag == "br" and self.cell is not None:
            self.cell["text"].append(" ")

    def handle_data(self, data):
        if self.active and self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag):
        if not self.active:
            return
        if tag in ("th", "td") and self.cell is not None:
            self.cell["text"] = " ".join("".join(self.cell["text"]).split())
            self.row.append(self.cell)
            self.cell = None
        if tag == "tr" and self.row is not None:
            if self.cell is not None:
                raise ValueError("Unclosed table cell")
            if self.row:
                self.rows.append(self.row)
            self.row = None
        if tag == "table":
            if self.row is not None:
                raise ValueError("Unclosed table row")
            self.active = False


def html_table_columns(path, columns, *, table_id, href_columns=(), base_url=""):
    """Project one ordinary headered HTML table; ambiguous layouts fail closed."""
    _columns(columns)
    if not table_id or not set(href_columns) <= set(columns):
        raise ValueError("Select one table ID and declared link columns")
    table = _Table(table_id)
    table.feed(Path(path).read_text(encoding="utf-8-sig"))
    table.close()
    if table.matches != 1 or table.active or not table.rows:
        raise ValueError("Expected exactly one complete directory table")
    headers = [cell["text"] for cell in table.rows[0]]
    if len(set(headers)) != len(headers) or not set(columns.values()) <= set(headers):
        raise ValueError("Duplicate or missing source columns")
    indices = {field: headers.index(source) for field, source in columns.items()}
    result = []
    for row in table.rows[1:]:
        if len(row) != len(headers):
            raise ValueError("Source row width differs from its header")
        projected = {}
        for field, index in indices.items():
            cell = row[index]
            if field in href_columns:
                links = set(cell["links"])
                if len(links) > 1:
                    raise ValueError("Multiple links in selected organization cell")
                projected[field] = urljoin(base_url, next(iter(links))) if links else None
            else:
                projected[field] = cell["text"]
        result.append(projected)
    return result


def text_columns(path, columns, *, row_pattern, candidate_pattern, expected_count):
    """Read reviewed row-oriented text, such as a Poppler -layout table export.

    Full-row named captures and an independent candidate detector are required:
    a changed numeric row must fail rather than quietly disappear. The caller
    reviews page headings/notes and the source's advertised row count. Only
    selected normalized fields leave this reader; no PDF/network dependency.
    """
    _columns(columns)
    if type(expected_count) is not int or expected_count <= 0:
        raise ValueError("Require a positive reviewed source row count")
    try:
        row_re, candidate_re = re.compile(row_pattern), re.compile(candidate_pattern)
    except re.error as error:
        raise ValueError("Invalid reviewed text patterns") from error
    if not set(columns.values()) <= row_re.groupindex.keys():
        raise ValueError("Selected text captures are missing")
    rows = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        match = row_re.fullmatch(line)
        if match:
            if not candidate_re.search(line):
                raise ValueError("Row and candidate patterns disagree")
            row = {field: match.group(group) for field, group in columns.items()}
            if any(value is None or not value.strip() for value in row.values()):
                raise ValueError("Selected text facts must be nonempty")
            rows.append({field: value.strip() for field, value in row.items()})
        elif candidate_re.search(line):
            raise ValueError("Unparsed candidate directory row; review layout")
    if len(rows) != expected_count:
        raise ValueError("Source row count differs from reviewed expectation")
    return rows


def embedded_json_columns(path, columns, *, marker, root="", encoding="utf-8-sig"):
    """Project a literal JSON object/array following one explicit script marker.

    Parses JSON only: never evaluates JavaScript, resolves expressions or follows
    URLs. Repeated/missing markers and nonliteral data fail for source review.
    """
    _columns(columns)
    if not isinstance(marker, str) or not marker.strip():
        raise ValueError("Require an explicit embedded JSON marker")
    text = Path(path).read_text(encoding=encoding)
    if text.count(marker) != 1:
        raise ValueError("Expected exactly one embedded JSON marker")
    tail = text.split(marker, 1)[1].lstrip()
    try:
        document, _ = json.JSONDecoder(object_pairs_hook=_unique_object).raw_decode(tail)
    except json.JSONDecodeError as error:
        raise ValueError("Embedded data must be a JSON literal") from error
    return _json_rows(document, columns, root)


class _Elements(HTMLParser):
    def __init__(self, tag, attributes):
        super().__init__(convert_charrefs=True)
        self.tag, self.attributes = tag, attributes
        self.active = None
        self.rows = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if self.active is not None:
            if tag == self.tag: raise ValueError("Nested selected elements require review")
            if tag == "br": self.active["text"].append(" ")
        if tag == self.tag and all(attrs.get(k) == v for k, v in self.attributes.items()):
            if len(attrs) != len(attributes): raise ValueError("Duplicate element attributes")
            self.active = {"attributes": attrs, "text": []}

    def handle_data(self, text):
        if self.active is not None: self.active["text"].append(text)

    def handle_endtag(self, tag):
        if tag == self.tag and self.active is not None:
            self.active["text"] = " ".join("".join(self.active["text"]).split())
            self.rows.append(self.active)
            self.active = None


def html_element_columns(path, columns, *, tag, attributes, expected_count, encoding="utf-8-sig"):
    """Project repeated elements with explicit attribute filters and row count.

    Source fields are `text` or `@attribute-name`. Useful for directory IDs/names
    in repeated link/card/cell markup without scraping unrelated page fields.
    """
    _columns(columns)
    if (not tag or not attributes or type(expected_count) is not int or expected_count < 1
            or any(value != "text" and (not value.startswith("@") or len(value) == 1)
                   for value in columns.values())):
        raise ValueError("Require explicit element selection, columns and reviewed count")
    parser = _Elements(tag, attributes)
    parser.feed(Path(path).read_text(encoding=encoding)); parser.close()
    if parser.active is not None or len(parser.rows) != expected_count:
        raise ValueError("Element rows differ from reviewed expectation")
    result = []
    for row in parser.rows:
        projected = {}
        for field, selector in columns.items():
            value = row["text"] if selector == "text" else row["attributes"].get(selector[1:])
            if value is None or not value.strip(): raise ValueError("Missing selected element fact")
            projected[field] = value
        result.append(projected)
    return result
