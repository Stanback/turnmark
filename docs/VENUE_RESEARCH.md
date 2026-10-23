# Venue context for conversion-model research

This is an implemented **local research sidecar**, not a pool finder, a new
conversion method or a trained altitude model. The current course-conversion
pilot and its frozen swimmer partitions stay intact. The model experiment needs
venue evidence; the shipped calculator's policy adjustments do not establish
empirical altitude effects.

## What exists now

`research/conversion-model/venue-registry.sql` separates:

- **Facilities:** an aquatic center or site, with source-backed coarse location.
- **Physical pools:** distinct basins within a facility. Elevation is nullable,
  in meters, with its evidence and optional uncertainty. Unknown stays null;
  a genuinely measured zero elevation remains zero.
- **Dated configurations:** a particular basin configured as SCY, SCM or LCM,
  with explicit validity dates and evidence. A documented meet date can give a
  one-day validity interval; do not invent a season-long configuration.
- **Race mappings:** source/race identity to the reviewed configuration, with
  independent evidence and `raw`, `altitude_adjusted` or `unknown` time basis.

One meet can use multiple basins or configurations. A meet-level name or address
is not enough to map every race automatically. Club headquarters, similarly
named pools and facility-level matches never establish physical pool identity.
Configurations may change direction, bulkheads, lanes or other conditions; a
same-pool cohort does not hold all race conditions constant.

`venues.py` builds a fresh DuckDB atomically from a strict JSON contract. Foreign
keys, finite elevation/uncertainty, source hashes, dates and allowed fields are
checked. Personal contact fields and raw payloads are rejected. Collectors,
actual venue mappings, evidence payloads and annotated real pairs stay ignored.
The public fixture is entirely invented.

## Existing-pair cohort audit

The audit labels existing SCY→LCM pairs without re-matching races, changing clocks
or changing train/validation/test assignments:

| Cohort                          | Meaning                                                                     |
| ------------------------------- | --------------------------------------------------------------------------- |
| `unresolved_venue`              | One or both race mappings are missing                                       |
| `non_raw_or_unknown_basis`      | Both venues resolve, but at least one time is adjusted or its basis unknown |
| `same_pool`                     | Both raw swims map to the identical physical basin                          |
| `same_facility_different_pools` | Both raw swims resolve to distinct basins at one facility                   |
| `different_facilities`          | Both raw swims resolve to distinct facilities                               |

Known elevation for both endpoints is reported separately. A same-pool match can
control elevation without knowing its numerical height, but it cannot establish
an altitude-response curve. Other pairs with missing height remain descriptive
venue cohorts, not verified altitude comparisons. A stale configuration date or
wrong course fails for review. Reused races and swimmers crossing partitions
also fail, rather than producing an apparently clean cohort report.

The aggregate report contains cohort counts, independent swimmer/meet/pool counts
and existing partition counts. Identifying mappings remain only in the local
annotated-pairs output. A private meet-enrichment queue prioritizes missing
mappings and unknown time basis by paired-race coverage, without using race
performance to rank acquisition. It contains no individual race IDs or clocks.
This lets us resolve the venues represented in useful pairs before considering
an exhaustive national pool directory.

## Run locally

Use the pinned research environment and fresh output paths:

```sh
target/lakehouse-venv/bin/python research/conversion-model/venues.py create \
  research/conversion-model/fixtures/venues.synthetic.json \
  --output target/venue-example.duckdb

target/lakehouse-venv/bin/python research/conversion-model/venues.py audit \
  /path/to/private/pairs.json --registry /path/to/reviewed-venues.duckdb \
  --output target/conversion-research/venue-audit
```

The synthetic registry is a format example. Its race IDs do not map real
results; do not use it as venue evidence for the private dataset.
The audit writes `venue-report.json`, `pairs-with-venues.json` and
`meet-enrichment-queue.json`. Keep real outputs under ignored `target/` or `data/`.

## Current evidence and remaining work

The checkpoint-03 replay preserves **5,687 pairs**, **2,601 independent swimmers**
and **215 meets**, including the unchanged 768-pair test partition. With an
**empty reviewed venue sidecar**, all 5,687 pairs correctly remain unresolved.
The aggregate [receipt](../research/conversion-model/venue-coverage-checkpoint-03.json)
records that condition explicitly. It does not mean venue evidence cannot be
found in the original meet files or public meet announcements. No actual pool
mapping or altitude measurement has yet been approved for this sidecar.

A cache-only follow-up examined 706 existing SDIF headers and found matching
header candidates for all 215 paired meets. Of those meets, 28 report a nonzero
altitude, 186 report zero and one leaves it blank; no conflicting altitude claims
were found between cached headers for the same meet. **These are source claims,
not verified pool measurements.** Zero may be an export default. The private
review queue retains the original altitude literal, source archive URL/hash and
meet header context, without reading athlete/contact records for enrichment.
No new network requests or verified pool mappings were added by that pass.

The reusable `sdif_venue.py` projection follows the official
[SDIF v3 B1 record](https://www.usms.org/admin/sdifv3f.txt), printed page 10:
altitude is a four-character integer-foot field at positions 138–141. The header
course is only the export's default; it does not prove every race used that
configuration or reveal whether its clock was altitude-adjusted. The parser
preserves blank and zero separately and excludes street/contact fields. Its
fixtures are invented and are not evidence for any real venue.

The next evidence pass should use the private meet queue to find organizational
meet information and facility/configuration documentation. Preserve aliases and
source-scoped meet IDs; record confidence through evidence rather than guessed
location or inferred "fast pool" scores.

Once enough mappings exist, compare the same-pool diagnostic cohort with broader
known-venue samples. For altitude, compare raw-time modeling, the published
policies and simple baselines; do not pre-correct labels and treat the policy as
truth. Keep unknown elevation missing and adjusted clocks separate. The initial
cross-course pilot remains distinct from the same-course altitude study in
[the altitude research protocol](ALTITUDE_RESEARCH.md).

Training, later-meet evaluation, a separate unseen-venue holdout and calibration
remain **unimplemented**. Venue lookup cannot itself demonstrate prediction
quality. Preserve the swimmer-disjoint split; a venue holdout must also keep its
pools out of training and avoid swimmer overlap. Subsetting an existing split
can be audited now, but is not automatically that extra holdout. Pool identity
should initially support grouping and diagnosis, not act as a shortcut feature
that memorizes observed targets. A same-pool subset can be selective and small;
report its coverage rather than promising better nationwide accuracy.
