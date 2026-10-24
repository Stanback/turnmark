# Directory breadth first, then broader race acquisition

The current purpose is **local model training and evaluation**. Publish the
organizational/facility facts, evidence, source/format map and coverage gaps as
reusable groundwork, like the conceptual lakehouse reference. Others can run
with it, or the owner can revisit it later. Operating a hosted Turnmark results
service remains outside the current scope; this is not a deployment plan.

Build genuinely broad source coverage before scaling the private archive.
**Five million deduplicated actual individual races is the next checkpoint, not
a cap.** A later 10–30 million is an exploration range as accessible sources,
useful history and coverage allow, not a promised obtainable total. Balance
training views after acquisition; do not rewrite the natural-frequency archive
to make the raw sample appear balanced.

The directory target is **85–90% coverage separately within each major U.S.
segment**, with summer-only clubs optional. See the [coverage criteria](team-directory/COVERAGE.md)
and reproducible [coverage audit](team-directory/coverage-audit.json). No measured
national team percentage is established yet; source listings, source-enumeration
counts and deduplicated currently operating teams remain different quantities.

## Current evidence-backed checkpoint

The [public catalog](team-directory/README.md) has 21,206 source-scoped listings at
18,531 source-scoped organizations, with 22,564 affiliations, 10,005 location
records, 8,125 program-location links and 1,300 separately described competition
basins. 20,301 listings assert a U.S. organization and 900 a Canadian one. Every
U.S. program row carries an explicit `program_kind`; the 364 `unknown` rows are
Swimming Canada national-list clubs whose source supplies no type.
It includes the USA Swimming national finder (with 234 YMCA dual-chartered
clubs tagged), Active Competitive YMCA Associations (262 deduplicated), YMCA National
Championship scoring teams (179 listings across 122 teams) and 13 regional YMCA
swim leagues (393 listings across 24 states), the nationwide USMS
finder, NCAA, NAIA (99 listings across 42 varsity swimming institutions), NJCAA, 3C2A/CCCAA, CCS,
school sources across 49 U.S. jurisdictions (all 48 NFHS-sponsoring jurisdictions plus Tennessee `TISCA`/`MTHSSA`/`KISL`, with `SD` and `VT` verified as non-sponsoring states, resolving 51 / 51 jurisdictions), 15 USA Swimming LSC club directories (`1,200` listings), 27 USMS LMSC directories (`424` listings), and nine flagship U.S. summer swim leagues plus RSL (`474` listings). All
activity statuses remain unknown. Source-scoped organizations are not a
deduplicated U.S. total.

The nationwide USMS response supplies 1,124 listings and 1,533 source location
rows, spanning all 50 states and D.C. Its selected Nationwide option and reported
total match the capture; it is not independent proof of complete membership.
Source GUIDs are identities, abbreviations are labels, and registered clubs,
workout groups and parent relationships still need reconciliation. Five
residential-looking location rows are excluded from the public projection.
Regional subset overlap remains visible instead of being merged by name.

School participation/program/alignment coverage is 12,167 listings across 49 U.S.
jurisdictions (all forty-eight NFHS-sponsoring jurisdictions plus Tennessee's
independent `TISCA`/`MTHSSA`/`KISL` high-school swimming leagues), plus two states
(`SD`, `VT`) verified as non-sponsoring high-school jurisdictions without school
listings (`51 / 51` jurisdictions resolved). Each source's seasons, categories and limits are in the
[catalog README](team-directory/README.md). California covers all 10 CIF sections
(`930` deduplicated listings across Southern, San Diego, Central, North Coast, Sac-Joaquin,
Central Coast, Los Angeles, Northern, Oakland and San Francisco Sections).
Connecticut (`179`) and North Dakota (`35`) now include both boys and girls divisions.
Georgia includes GAPPS and a separate GHSA 2024–25 participation survey: 261 boys /
264 girls listings at 270 source school rows, with category totals and both
participant-column sums matched. Those historical positive-participation rows do
not verify current independent teams, and GAPPS/GHSA overlap is unresolved.
Missouri has both classes/categories under 2026 source headings; girls use
the 2025–26 selector because 2026–27 assignments are not released. Iowa's IHSAA
boys and IGHSAU girls remain distinct authorities. New Mexico, Kentucky, Arkansas,
Nevada, Utah, New Hampshire and Louisiana publish combined or unspecified-category school alignments. Published
school/operator IDs retain their namespaces; source row/program IDs do not
silently become shared institutional identities. Illinois includes 146 explicitly
individual-entry-only listings and Maine eight; co-ops remain intact. Regional
LSC/LMSC additions retain unresolved national overlaps and club/workout-group
roles. Minnesota activity listings include co-op members; Idaho keeps regular-season
co-op markers; Hawaii, Alabama, Colorado, Delaware, Louisiana, New Hampshire, New York,
North Carolina, South Carolina, Tennessee and Wyoming use championship or regional/sectional
team entries rather than complete regular-season sponsorship rolls. Pennsylvania district details exceed the
summaries by one per category; Wisconsin strikeouts are excluded after visual
review. The [latest receipt](team-directory/breadth-checkpoint-10.json) checks
the source rows against the public snapshot. No state is declared complete.

The 172 [governing-body starting points](team-directory/governing-bodies.csv)
cover 59 USA Swimming LSCs, 51 NFHS member-state associations, 51 USMS LMSCs and
11 Canadian bodies (Swimming Canada and its ten provincial sections).
Ninety-eight have explicitly partial swimming imports, linked to exact source
documents in the manifest; 74 remain without imported jurisdiction-level swimming lists.
The separate [homepage-review ledger](team-directory/authority-reviews.csv)
records 71 cached homepages, 97 stopped outcomes and four not requested because
of prior access gaps. Stopped includes redirects awaiting review, robots,
network and budget limits. Homepage discovery is not sport-directory coverage.

Canada pass 01 imported eleven Canadian source documents (874 listings): the
Swimming Canada national club list (366 rows with no province or type; province
derived from postal codes, 23 rows without one) and the Swim BC, Swim Alberta
(including NWT clubs), Swim Ontario, Swim Manitoba, Swim Saskatchewan, Swim
Nova Scotia and Swimming NL club lists, plus 1,765 Canadian facility rows
(club-listed addresses and training pools, Swim Alberta's approved competition
pools with five named basins, and StatCan ODRSF pool records under the Open
Government Licence – Canada). Quebec, New Brunswick and PEI clubs appear only
through the national list; Yukon and Nunavut have no listing; U SPORTS/CCAA and
the conference sites returned HTTP 403; a person then confirmed 25 varsity programs and one club team on the universities' own athletics pages (U of Alberta discontinued, Mount Royal/UQAM none, York unconfirmed). The coverage
audit now carries a `countries` dimension and a per-province `canada` block;
no Canadian denominator exists beyond Swim Ontario's "over 140".

The [latest private acquisition checkpoint](acquisition-checkpoint-06.json) has
**3,375,251 actual individual races across 2,454 meets and 138,993 source-scoped
swimmers**. Bounded resumed batches added 2,099,549 deduplicated races from 1,722
additional files across Southeastern, Pacific (2013–2026), North Carolina,
Adirondack, Michigan, Potomac Valley, South Dakota, and Midwestern LSC archives.
The directory-only receipts retain their earlier race checkpoint references;
this acquisition is a separate pass. SCM is now 12,336 races (`2,264,540` SCY,
`1,098,375` LCM), so new source
discovery continues to prioritize SCM, high-altitude LSCs, adult/masters and additional regions. The natural-
frequency archive is preserved; the earlier paired-swim pilot and frozen
partitions are not refitted in this pass. No predictive model is trained or
approved for the app.

## Near-term path to five million races

At acquisition checkpoint 06, 3,375,251 races are 67.5% of the five-million
checkpoint; **1,624,749 additional usable deduplicated races** are needed. The
reviewed queues still contain remaining Pacific, Southeastern, North Carolina,
Michigan, South Texas, Adirondack and Mountain West LSC archive files. Those are
unprocessed files, not guaranteed new meets or a measured race yield. Some can be
duplicates, incomplete, unsupported or missing unambiguous source IDs. Do not
extrapolate them into a promised total.

The next work proceeds in parallel:

- Drain supported exports from existing sources with shared per-origin budgets,
  cached receipts and resumable deduplication.
- Expand actual published season navigation. Pacific's captured index links
  2013–2026; the initial collection only used 2024–2026. Review PVS and Midwestern
  historical season links instead of treating their current exhausted queues as
  the full archive. Retain source/course/year coverage and observed packaging.
  The [subsequent Pacific inventory review](source-inventory-checkpoint-06.json)
  enumerates 2,537 distinct export URLs across the published 2013–2026 indexes,
  versus 456 in the initial 2024–2026 inventory: 2,081 additional candidates.
  All 14 index response hashes/retrieval receipts are retained. This is source
  discovery, not a promised race yield or an updated frozen acquisition total.
- Find raw result exports across additional regions. Prefer supported SDIF with
  stable source identity; validate any new interchange adapter before importing.
  Browser-reviewed result indexes are discovery evidence, not downloaded races.
  Text-only or name-only results do not automatically supply matched-swimmer
  training labels.
- Continue remaining organization-directory gaps alongside acquisition. A broad
  directory helps explain coverage; finishing every state/authority is not a gate
  before importing more supported race exports.

After acquisition, regenerate nearby-date cross-course pairs, freeze swimmer-
disjoint and temporal/region holdouts, and balance only derived training views
or weights. Compare NCAA, documented Colorado and simple statistical baselines
before bounded XGBoost evaluation. Five million race rows alone do not establish
balanced cohorts, sufficient paired labels or a model ready for the product.

## Finish breadth by source universe

| Universe                      | Evidence to review                                                                                        | Completion/disposition to record                                                                                                                                                          |
| ----------------------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| U.S. school swimming          | Sport-specific participation, alignments and seasonal sponsorship from all 50 state associations and D.C. | Import available universes; preserve category, season, co-op and individual-only distinctions; document inaccessible/absent/unsupported sources rather than treating them as zero schools |
| Additional school authorities | Private/independent-school associations, district and middle-school leagues where published               | Keep each publisher's scope explicit; a high-school member list is not evidence of swimming sponsorship                                                                                   |
| Youth/general clubs           | National finder cross-checked against all LSC directories and explicit current-operation evidence         | Missing/extra listings, source IDs, aliases and unresolved matches recorded; facilities never inflate team counts                                                                         |
| Masters                       | Nationwide finder cross-checked against LMSC clubs, workout groups and registration-year evidence         | Distinguish registered parent clubs, workout groups, affiliate/other listing roles and unattached membership; preserve unresolved relationships                                           |
| College varsity               | NCAA seasonal swimming sponsorship plus NAIA/NJCAA sport-specific lists                                   | Institution membership alone is insufficient; categories, divisions and source season retained                                                                                            |
| College clubs                 | CCS listing and registration-year updates                                                                 | Current registration and verified operation remain separate assertions                                                                                                                    |
| YMCA and independent          | Official YMCA association and program directories                                                         | Season/source scope and overlapping affiliations retained; no current program inferred merely from a historical meet appearance                                                           |
| Venues                        | Facility operators and meet documentation                                                                 | Separate source location rows, physical basins, dated course configurations, source-reported coordinates, surveyed/estimated elevations and historical race mappings                      |
| Canada                        | Swimming Canada national list, ten provincial-section directories, university associations (U SPORTS, CCAA, conferences) and open facility data | Keep national and provincial rows separate; derive province only from postal codes; record FNQ/Swim NB/Swim PEI, Yukon/Nunavut and 403-blocked university sources as explicit gaps, never zero |

Summer leagues are optional, opportunistic extras. They are not a priority, a
completeness requirement or a gate before wider race acquisition. Prioritize
schools across more states, year-round clubs and masters coverage.

The desired endpoint is a broad national inventory with explainable gaps,
not a fabricated “100%” badge. Every jurisdiction/source should have an explicit
review disposition and next evidence step. Record denominators only where the
publisher actually defines a universe. General school membership, a region
assignment or a successful HTTP response alone must not create a swim program.
Florida's captured index advertises swimming counts but its documents are
robots-disallowed; North Carolina's captured region assignments still require
sponsorship review. These are concrete gaps, not imported teams.

Keep source identity namespaces. NCAA's official institution ID can connect its
men's/women's programs. A source program ID, similar school name, short code or
shared facility cannot do the same for unrelated providers. Keep college clubs
separate from varsity and preserve co-op/composite entities until evidence
identifies their members and effective seasons. Source states/provinces and
unknowns are retained; non-U.S. NCAA institutions are not relabeled U.S.

## Preserve reusable evidence and adapters

For each imported or reviewed source, retain canonical/human-facing URLs,
observed data routes where appropriate, authority/source IDs, geographic and
seasonal scope, format, retrieval time and SHA-256, advertised/imported counts,
rejected or unresolved rows, access status and reuse context. A frontend route
is not automatically a documented API. Preserve raw source receipts locally so
parsers can be improved and the archive reprocessed.

The public [source catalog](team-directory/source-catalog.csv),
[facility/source contract](team-directory/CATALOG.md), CSVs and manifests are the
reusable interchange. `directory_build.py` builds a local DuckDB from them with
hash, count, identity and reference checks. Its authority, program/location and
source/format coverage views let contributors inspect gaps without swimmer data.

Network collectors and raw payloads remain local/ignored. Use cache-first,
resumable batches, descriptive identification, ten-second-plus per-origin pacing,
finite budgets, retry/backoff and cooldowns. Review redirects and robots; stop on
access challenges. Route 403/challenge receipts to a separate normal-browser
review lane, recording exact URL/time/status and observed signals. Preserve
unknown causes; a CDN provider or 403 alone is not WAF-rule evidence. Browser
success does not reset an automated cooldown. Public
[site access observations](team-directory/site-access-reviews.csv) retain minimal
reviewed evidence; cookies, tokens and raw headers stay out of public exports.
Prefer one official organizational listing or regional result
archive over thousands of profile requests. Do not fetch rosters to obtain club
names already available in a directory.

Reusable public readers cover explicit CSV/TSV and JSON fields, embedded JSON
literals, ordinary HTML tables, repeated elements and strict layout-text rows.
They project fixed normalized metadata rather than copying source objects or
executing scripts. Ambiguous layouts, duplicate IDs/keys, conflicting facts and
changed counts fail for review. Source-specific maps/collection stay local.
Add interchange adapters when the format recurs, not an ever-growing set of
public one-off website scrapers. The current private result collector uses
SDIF; LENEX and other formats need verified contracts before claiming support.

The public catalog contains organizational/facility facts and attribution;
swimmer records, identity keys, raw source databases, personal contacts and
athlete/coach rosters are excluded. Third-party access does not establish a data
redistribution or training license. Keep source rights/context separate from
the code license. Public addresses are limited to reviewed facility projections,
with mailing-style/residential-looking entries screened as documented.

## Scale result acquisition after the directory pass

Associate official result indexes with jurisdictions/leagues, seasons, meet
scope and observed formats. A directory program only links to a historical team
with evidence; a short meet-file abbreviation is not an official organization
ID. A club's training location is not proof of where its swimmers raced.

Collect supported actual finishes across strokes, distances and SCY/SCM/LCM,
including ordinary meets, slower performance bands and historical seasons.
The initial 50/100/200 freestyle pairing scope must not discard the rest of the
archive. Seeds, relay/split records, disqualifications, duplicate files and
conflicting observations do not count as additional individual-finish labels.
Future supported record types need their own contracts and receipts.

At each checkpoint report raw/deduplicated race counts, unique source-scoped
swimmers/meets, rejected/conflicting records, available/imported seasons,
program/source geography, course/event, age, published category, performance
band and useful cross-course pairs. Archive region is not swimmer home region.
More rows from a dominant SCY archive do not fix sparse SCM, masters, other
regions or independent matched-swimmer coverage.

Preserve the full natural-frequency archive locally. Build balanced training
views/weights separately, with fitting decisions learned only from training
partitions. Keep swimmer-disjoint splits, add later-season and region/unseen-
venue holdouts, and compare NCAA, documented Colorado and simple statistical
baselines before a bounded XGBoost experiment. Do not join people by name across
providers. Do not silently altitude-adjust raw training labels; source clock
basis and empirical venue/altitude cohorts remain separate evidence layers.
