"""Organizational registry tests use invented programs and source metadata."""

import os
from pathlib import Path
import unittest


@unittest.skipUnless(
    os.environ.get("TURNMARK_LAKEHOUSE_TESTS") == "1",
    "Optional DuckDB dependency; see README setup",
)
class TeamRegistryTests(unittest.TestCase):
    def setUp(self):
        import duckdb

        self.constraint_error = duckdb.ConstraintException
        self.db = duckdb.connect()
        self.addCleanup(self.db.close)
        self.db.execute(Path(__file__).with_name("team-registry.sql").read_text())
        self.db.execute("""
            INSERT INTO registry_sources VALUES
            ('toy', 'https://example.test/directory', '2026-10-19T00:00:00Z',
             repeat('0', 64), 'Invented synthetic test records');
            INSERT INTO organizations VALUES
            ('school', 'Example College', 'school', 'US', 'CA', 'Example City',
             'https://example.test', 'toy');
            INSERT INTO programs VALUES
            ('varsity', 'school', 'Example College women', 'collegiate_varsity',
             'swimming_and_diving', 'women', 'active', '2026-07-01', NULL, '2026-10-19', 'toy'),
            ('club', 'school', 'Example College swim club', 'collegiate_club',
             'pool_swimming', 'mixed', 'active', NULL, NULL, '2026-10-19', 'toy');
            INSERT INTO program_affiliations VALUES
            ('a', 'varsity', 'ncaa', 'toy-school', 'Division III', NULL, NULL, 'toy'),
            ('b', 'club', 'college-club-swimming', 'toy-club', NULL, NULL, NULL, 'toy');
        """)

    def test_one_organization_can_have_distinct_programs_and_affiliations(self):
        result = self.db.sql("""
            SELECT program_kind, authority FROM team_directory
            JOIN program_affiliations USING (program_id) ORDER BY program_kind
        """).fetchall()
        self.assertEqual(
            result,
            [
                ("collegiate_club", "college-club-swimming"),
                ("collegiate_varsity", "ncaa"),
            ],
        )
        self.assertEqual(
            self.db.sql("SELECT count(*) FROM registry_vertices").fetchone()[0], 5
        )
        self.assertEqual(
            self.db.sql("SELECT count(*) FROM registry_edges").fetchone()[0], 4
        )

    def test_meet_observation_is_not_a_verified_current_directory_entry(self):
        self.db.execute("""
            INSERT INTO team_observations VALUES
            ('seen', 'toy', 'EXAMPL', 'Example College', 'EX', NULL, NULL, NULL,
             '2025-02-01', NULL, 'observed_only')
        """)
        self.assertEqual(
            self.db.sql("SELECT count(*) FROM team_directory").fetchone()[0], 2
        )
        with self.assertRaises(self.constraint_error):
            self.db.execute(
                "UPDATE team_observations SET verification_status='verified'"
            )

    def test_dangling_affiliations_and_invalid_effective_dates_are_rejected(self):
        with self.assertRaises(self.constraint_error):
            self.db.execute("""INSERT INTO program_affiliations VALUES
                ('missing', 'absent', 'ncaa', 'unknown', NULL, NULL, NULL, 'toy')""")
        with self.assertRaises(self.constraint_error):
            self.db.execute(
                "UPDATE programs SET valid_to='2020-01-01' WHERE program_id='varsity'"
            )


if __name__ == "__main__":
    unittest.main()
