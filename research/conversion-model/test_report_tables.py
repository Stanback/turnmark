"""REPORT.md's generated tables must match the committed receipts."""

from __future__ import annotations

import json
import unittest

import render_report_tables as tables
from evaluate_and_train import engine_equivalence

EMPTY_BLOCKS = "".join(f"<!-- receipt:{n} -->\n<!-- /receipt:{n} -->\n" for n in tables.RENDERERS)


class ReportTablesTests(unittest.TestCase):
    def test_report_tables_match_the_receipts(self):
        text = tables.REPORT.read_text(encoding="utf-8")
        rendered = tables.render(text, tables.load_documents())
        self.assertEqual(tables.stale_blocks(text, rendered), [], "run render_report_tables.py")

    def test_every_block_needs_a_renderer_and_every_renderer_a_block(self):
        docs = tables.load_documents()
        tables.render(EMPTY_BLOCKS, docs)
        with self.assertRaises(ValueError):
            tables.render(EMPTY_BLOCKS.replace("receipt:accuracy", "receipt:acuracy"), docs)
        with self.assertRaises(ValueError):
            tables.render(EMPTY_BLOCKS + "<!-- receipt:noise -->\n<!-- /receipt:noise -->\n", docs)

    def test_a_changed_receipt_value_marks_its_block_stale(self):
        ev, acq, snap = tables.load_documents()
        current = tables.render(EMPTY_BLOCKS, (ev, acq, snap))
        changed = json.loads(json.dumps(ev))
        changed["swimmer_disjoint_holdout"]["clean_test"]["turnmark_equivalence"]["mae_seconds"] = 2.7712
        self.assertEqual(tables.stale_blocks(current, tables.render(current, (changed, acq, snap))), ["accuracy"])

    def test_rounding_follows_the_receipt_decimals(self):
        self.assertEqual(tables.fixed(1.255, 2), "1.26")
        self.assertEqual(tables.fixed(-2.365, 2), "−2.37")
        self.assertEqual(tables.signed(0.0, 2), "0.00")
        self.assertEqual(tables.signed(-0.0004, 3), "0.000")
        self.assertEqual(tables.clock(6295), "1:02.95")
        self.assertEqual(tables.clock(5929), "59.29")

    def test_worked_example_matches_the_engine_arithmetic(self):
        docs = tables.load_documents()
        cell = docs[2]["cells"][tables.WORKED_CELL]
        src, dst = cell[tables.WORKED_SOURCE]["knots"], cell[tables.WORKED_TARGET]["knots"]
        rows = {line.split(" | ")[0].strip("| `"): line for line in tables.worked_example(*docs).splitlines()}
        for time_cs in tables.WORKED_TIMES_CS:
            result = engine_equivalence(src, dst, time_cs)
            row = rows[tables.clock(time_cs)]
            with self.subTest(time_cs=time_cs):
                self.assertIn(f"`{tables.clock(result.hundredths)}`", row)
                self.assertEqual("empirical-out-of-range" in row, result.out_of_range)


if __name__ == "__main__":
    unittest.main()
