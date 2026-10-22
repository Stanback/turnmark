import unittest
from sdif_venue import parse_meet_header


class SdifVenueTests(unittest.TestCase):
    def record(self, altitude=""):
        record = [" "] * 160
        for start, width, value in ((0,2,"B1"),(11,30,"Invented meet"),
                (41,22,"PRIVATE STREET OMITTED"),(85,20,"Sample City"),(105,2,"CO"),
                (117,3,"USA"),(121,8,"01012026"),(129,8,"01022026"),
                (137,4,altitude),(149,1,"Y")):
            record[start:start+width] = value.ljust(width)
        return "".join(record)

    def test_reported_altitude_and_default_course_are_claims_not_pool_identity(self):
        header = parse_meet_header(self.record("5280") + "\r\n")
        self.assertEqual(header["reported_altitude_feet"], 5280)
        self.assertEqual(header["start_date"], "2026-01-01")
        self.assertEqual(header["source_default_course"], "SCY")
        self.assertIsNone(header["verified_pool_id"])
        self.assertEqual(header["time_basis"], "unknown")
        self.assertNotIn("PRIVATE", str(header))

    def test_blank_and_zero_do_not_establish_sea_level(self):
        blank, zero = parse_meet_header(self.record()), parse_meet_header(self.record("0"))
        self.assertIsNone(blank["reported_altitude_feet"])
        self.assertEqual(blank["altitude_claim_status"], "missing")
        self.assertEqual(zero["reported_altitude_feet"], 0)
        self.assertEqual(zero["altitude_claim_status"], "zero_requires_review")

    def test_malformed_header_values_are_not_silently_shifted_or_coerced(self):
        for value in (self.record()[:-1], self.record("52x0"), self.record().replace("01012026", "99999999")):
            with self.subTest(value=value[:2]), self.assertRaises(ValueError): parse_meet_header(value)
