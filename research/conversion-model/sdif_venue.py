"""Project organizational B1 header claims from one SDIF v3 record.

Field positions: US Swimming SDIF v3, April 28 1998, B1 printed page 10:
https://www.usms.org/admin/sdifv3f.txt
No network, athlete records, contact/street-address fields or verified pool IDs.
"""
from datetime import datetime
import re

COURSES = {"1":"SCM", "S":"SCM", "2":"SCY", "Y":"SCY", "3":"LCM", "L":"LCM"}


def parse_meet_header(record):
    record = record.rstrip("\r\n")
    if len(record) != 160 or not record.startswith("B1") or any(ord(c) < 32 for c in record):
        raise ValueError("Expected one 160-character SDIF B1 record")
    name = record[11:41].strip()
    if not name:
        raise ValueError("Meet header needs its source name")
    def day(value, required=False):
        if not value.strip() and not required:
            return None
        try:
            return datetime.strptime(value, "%m%d%Y").date().isoformat()
        except ValueError as error:
            raise ValueError("Invalid SDIF meet date") from error
    start, end = day(record[121:129], True), day(record[129:137])
    if end is not None and end < start:
        raise ValueError("Meet header dates are reversed")
    literal = record[137:141].strip()
    if literal and not re.fullmatch(r"-?[0-9]+", literal):
        raise ValueError("Malformed SDIF integer-foot altitude")
    feet = int(literal) if literal else None
    return {"source_meet_name":name, "source_meet_city":record[85:105].strip() or None,
            "source_meet_state":record[105:107].strip() or None,
            "source_meet_country_code":record[117:120].strip() or None,
            "start_date":start, "end_date":end,
            "source_default_course":COURSES.get(record[149:150]),
            "source_default_course_code":record[149:150].strip() or None,
            "reported_altitude_feet_literal":literal or None,
            "reported_altitude_feet":feet,
            "altitude_claim_status":"missing" if feet is None else "zero_requires_review" if feet == 0 else "unverified_source_claim",
            "verified_pool_id":None, "time_basis":"unknown"}
