# Public swimming research catalog

This catalog supports **local model training and evaluation**. Like the
[conceptual lakehouse reference](../../../docs/LAKEHOUSE_COST_MODEL.md), it is
open, reusable groundwork someone can extend independently or revisit later.
Operating a hosted Turnmark results service remains outside the current scope.

The snapshot contains **21,206 source-scoped program/participation listings at
18,531 source-scoped organizations**, plus **22,564 affiliations**, **10,005 facility
records**, **8,125 program-location links** and **1,300 separately described competition
basins**. 20,301 listings assert a U.S. organization and 900 a Canadian one (see
[Canada](#canada)). These are source assertions, not
unique physical teams/pools or verified national membership/activity counts.
Swimmer-level results, identity keys, raw payloads and collectors remain local.
Personal contacts and athlete/coach rosters are excluded from public exports.

The [coverage target and acceptance criteria](COVERAGE.md) define the path to
85–90% within each major U.S. segment, excluding summer-only clubs as a
requirement. The [reproducible audit](coverage-audit.json) exposes missing states,
source universes and unknown denominators; the target is not an achieved claim.

## What is covered

| Source universe                | Listings | Scope and limits                                                                                                                   |
| ------------------------------ | -------: | ---------------------------------------------------------------------------------------------------------------------------------- |
| USA Swimming national finder   |    2,558 | Source organization IDs (`age_group`); 234 carry explicit `ymca:usas-dual-charter` affiliations; activity unknown                  |
| YMCA competitive swimming      |      834 | 262 deduplicated competitive YMCA associations, 179 national championship scoring listings, plus 393 regional YMCA league listings across 13 leagues |
| USMS nationwide finder         |    1,124 | Nationwide option selected; row count equals source `totalResults`; club/workout-group roles and parent relationships unresolved   |
| NCAA swimming/diving           |      986 | 442 men's and 544 women's programs at 549 official institution IDs; source academic year 2027; some non-U.S. institutions retained |
| NAIA swimming/diving           |       99 | 49 men's and 50 women's listings across 42 NAIA varsity institutions (2026 championship qualifiers plus conference/sponsorship rosters) |
| NJCAA swimming/diving          |       28 | 14 men's and 14 women's varsity junior-college programs across Regions 3, 6, 8, 11, 15, 18, and 23                                 |
| 3C2A / CCCAA swimming/diving   |      110 | 53 men's and 57 women's California Community College varsity programs across 57 colleges in nine conferences                       |
| College Club Swimming          |      302 | 212 source-registered, 90 not-currently-registered; registration is not independent practice verification                          |
| School listings                |   12,167 | 49 U.S. jurisdictions below (all 48 NFHS-sponsoring jurisdictions plus Tennessee `TISCA`/`MTHSSA`/`KISL`; `SD` and `VT` verified non-sponsoring; 51/51 resolved) |
| Summer swim leagues            |      474 | Nine flagship U.S. summer leagues (`NVSL`, `MCSL`, `PMSL`, `CMSL`, `NWAL`, `SAL`, `TCSL`, `GCSL`, `SSL`) plus `RSL`                |
| Supplemental regional listings |    1,624 | 15 USA Swimming LSC club directories (`1,200` listings) and 27 USMS LMSC club/workout-group directories (`424` listings)           |

The USMS nationwide response is a substantial improvement over the earlier
25-mile LaneMate cache: one public finder page supplied all 1,124 returned
listings and 1,533 location rows, without fetching club profiles or rosters.
Five residential-looking location rows were excluded, leaving 1,528 public
source-scoped location records/links. Source locations span all 50 states and
D.C.; program-level geography stays unknown when a listing spans several cities
or states. This verifies the captured finder response, not that every registered
club/workout group is listed, active or correctly classified. Finder GUIDs are
identity keys. Its abbreviation labels are separate affiliations, can repeat,
and do not establish a parent club or registration relationship.

| School source        | Listings | Source universe                                                                                                                                                                   |
| -------------------- | -------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Alabama AHSAA        |       80 | 1A–5A and 6A–7A State Championship and North Sectional team score/results PDFs published via Huntsville Swim Association / NAHSSL                                                 |
| Alaska ASAA          |       35 | 2026–27 handbook p.184, four conferences; combined list has unknown competition category; document-row identities                                                                 |
| Arizona AIA          |      339 | 169 boys and 170 girls, **2027–28** alignment edition; all six division counts matched; source operator IDs retained; future placement is not verified current activity           |
| Arkansas AAA         |       72 | 2026–27 6A/5A/4A conference assignment tables (10 conferences); category unspecified; document-row identities                                                                     |
| California CIF       |      930 | All **10 CIF Sections**: Southern (686), San Diego (129 across all seven conference alignments), Central (32), Sac-Joaquin (29), Central Coast (26), Los Angeles (17), North Coast (15), Northern (14), Oakland (9), and San Francisco (9) |
| Colorado CHSAA       |      189 | 119 girls (5A/4A/3A) and 70 boys (5A/4A) from official 2024–26 CHSAA CLOC Swimming & Diving classification tables across 121 CO schools and eight co-ops                          |
| Connecticut CIAC     |      179 | 85 girls (`TournamentID=7`) and 94 boys (`TournamentID=105`), 2026–27 divisions; all eight published class totals matched; co-op labels intact                                    |
| Delaware DIAA        |       46 | 2026 DIAA Boys & Girls State Championship relay/final entries and archived DIAA State Finals team rankings                                                                        |
| District of Columbia DCSAA | 29 | 15 boys and 14 girls across 17 DC high schools from official 2026 DCSAA State Championship SDIF C1 institutional team records                                                     |
| Florida FHSAA        |      938 | 468 boys (`sport_id=284`) and 470 girls (`sport_id=285`), 2026–27 FHSAA HomeCampus public hierarchy across Classes 1A–4A; document-scoped school IDs and cities retained          |
| Georgia GAPPS        |       15 | Varsity girls Division II, 2026–27; **GAPPS only, not GHSA**; state denotes association jurisdiction, individual locations and school/homeschool kinds unverified                 |
| Georgia GHSA         |      525 | 2024–25 participation survey pp.37–53: 261 boys / 264 girls listings at 270 source school rows; positive swimming counts and column sums match published totals; historical participation, not current independent-team verification; kept separate from GAPPS |
| Hawaii HHSAA         |       28 | 2026 state championship scoring rows: 13 girls / 15 boys, 19 school names; scoring participation only, not statewide sponsorship; non-scoring/league-only programs absent         |
| Idaho IDHSAA         |       63 | 2026–28 classification/alignment p.4: 6A 23 / 5A 40; 22 regular-season co-op markers; only two explicit category tags; 61 unsplit categories stay unknown                         |
| Illinois IHSA        |      491 | 230 boys (2025–26), 261 girls (2026–27); all 32 sectional team/individual-only counts matched; 146 individual-entry-only listings retained as such                                |
| Indiana IHSAA        |      501 | 246 boys and 255 girls, 2025–26 swimming sectionals; all 40 published sectional school counts matched; category/document identities                                               |
| Iowa IHSAA / IGHSAU  |      100 | 50 boys in 2026 district lists and 50 girls in 2026 state-qualifying assignments; different governing authorities kept separate; category/document identities                     |
| Kansas KSHSAA        |      135 | 59 boys and 76 girls across 81 KS schools (Classes 6A and 5–1A, including four co-ops) from official 2025–26 KSHSAA Swimming & Diving Top 25 / Championship PDFs                  |
| Kentucky KHSAA       |      167 | Nine-region swimming alignment sheet linked by the official page; category and edition not supplied; no expansion into both categories or independent sponsorship claim           |
| Louisiana LHSAA      |      195 | Official LHSAA Swimming Divisions Final Plan (162 schools across Divisions I–IV) plus deduplicated LHSAA State Championship Finals/Scores PDFs                                    |
| Maine MPA            |       45 | 2026–27 bulletin p.8; Class A 23 / B 22 entries, including eight individual-only; two explicit boys and one girls entry; other categories unknown; co-ops intact                  |
| Maryland MPSSAA / WMPSSDL | 160 | 141 public school listings from 2025 MPSSAA 4A/3A and 3A/2A/1A State Championship SDIF C1 records, plus 19 Maryland private/Catholic school listings from 2026 WMPSSDL C1 records |
| Massachusetts MIAA   |      268 | 146 boys and 122 girls, winter alignments for 2025–26/2026–27; all division counts matched; co-op, appeal and source ExpDate context retained                                     |
| Michigan MHSAA       |      308 | 154 girls and 154 boys across 2025–26 Lower Peninsula Divisions 1, 2, 3 and Upper Peninsula Finals SDIF C1 institutional team records                                             |
| Minnesota MSHSL      |      294 | Seven activity-filtered pages: boys 129 (2026–27), girls 165 (2026); school-activity membership includes co-op member cards linking to host teams; not 294 independent teams      |
| Mississippi MHSAA    |      129 | 64 boys and 65 girls, 2025–27 region tables; source Class/Region labels retained                                                                                                  |
| Missouri MSHSAA      |      245 | Boys Classes 1/2 (115) and girls Classes 1/2 (130), source headings 2026; girls explicitly use the 2025–26 selector because 2026–27 is not released; official school IDs retained |
| Montana MHSA         |       25 | 2026–27 alignment: AA 16 / A 9; three co-ops intact; scoring abbreviations are not institution IDs; unknown category                                                              |
| Nebraska NSAA        |       82 | 41 boys and 41 girls, 2026–27 registered schools from official NSAA static HTML template; co-op member school lists preserved in jurisdiction                                      |
| Nevada NIAA          |       68 | 2026–28 combined boys/girls swimming alignment across Class 5A (20), 4A (28), and 3A (20) leagues; all six published league totals matched; category unspecified                  |
| New Hampshire NHIAA  |       97 | 47 boys and 50 girls across all 50 NH member swimming schools (20 Division I, 30 Division II) from 2025–26 NHIAA By-Law Article XXXIV Sect. 4 Divisional Alignment PDF            |
| New Jersey NJSIAA    |      153 | 153 deduplicated NJ high schools from official 2025 and 2026 NJSIAA Meet of Champions SDIF C1 institutional team records hosted by BeSmartt Inc.                                  |
| New Mexico NMAA      |       52 | 2026–28 handbook Section IV page 13; published 52-school total matched after visual review; category unspecified, no expansion into both categories                               |
| New York NYSPHSAA / Fed |   290 | Boys and girls from 2025–2026 NYSPHSAA and NYS Federation (including CHSAA, PSAL, and AIS) State Championship team scores and sectional directories across Sections I–XI          |
| North Carolina NCHSAA / NCISAA | 272 | Public/charter schools across all 2025–2026 NCHSAA regional and state championship classifications (`1A/2A/3A` through `8A`) plus private schools across NCISAA Divisions I–III |
| North Dakota NDHSAA  |       35 | 16 boys and 19 girls source program IDs; identical source program IDs/names reconcile duplicate responsive copies; IDs are not institution IDs; edition unspecified               |
| Ohio OHSAA           |      549 | 2026–27/2027–28 alignments based on 2025–26 first-round teams; individual-only schools excluded by source; official school IDs shared across categories                           |
| Oklahoma OSSAA       |      127 | 64 boys (32 6A, 32 5A) and 63 girls (32 6A, 31 5A), 2026–27 swimming classification PDFs; document-row identities retained                                                        |
| Oregon OSAA          |      261 | 132 girls and 129 boys, 2026–27 teams/leagues; source team IDs are program IDs, not institution IDs                                                                               |
| Pennsylvania PIAA    |      676 | 333 boys and 343 girls, classification season 26/27; all 12 district lists/category captured; official school IDs shared across categories; detail/summary mismatch below         |
| Rhode Island RIIL    |       43 | Winter 2026–27 handbook updated October 16, page 6; 24 school/co-op rows produce 23 girls and 20 boys program flags; all six category/division counts matched visually            |
| South Carolina SCHSL / SCISA | 253 | 165 public school listings across 2026 SCHSL 3A/4A/5A State Championship Team Scores tables plus 88 independent school listings across 2023–2025 SCISA State Swim Meet results |
| Tennessee TISCA / MTHSSA / KISL | 341 | 341 deduplicated boys and girls listings across Tennessee high schools from 2024–2026 TISCA State Championships, MTHSSA Regions, and KISL Championships (non-NFHS authority)      |
| Texas UIL            |    1,111 | 564 source rows across all 80 published 4A/5A/6A districts, 2026–27; boys-only/girls-only markers determine category expansion; wrapped names reviewed                            |
| Utah UHSAA           |      226 | 111 boys and 111 girls from official UHSAA Winter Swimming team directories across 115 UT high schools in Classes 2A–6A (plus four earlier rows)                                  |
| Virginia VISAA / VHSL|      404 | 104 independent school listings (52 boys, 52 girls) from 2026–28 VISAA PDFs, 58 Northern Virginia district SDIF C1 listings, and 242 deduplicated 2025–26 VHSL Class 1–6 & regional schools |
| Washington WIAA      |      241 | 109 boys and 132 girls across eight 2026–27 4A/3A/2A/1A WIAA league standings widgets; document-scoped WPA Network team IDs retained                                              |
| West Virginia WVSSAC |       56 | August 14, 2026 revised regional alignment p.20: Division 1 and 2 each 28 rows; competition category unknown                                                                      |
| Wisconsin WIAA       |      249 | Girls 2026 (135) / boys 2027 (114), Divisions 1 and 2; all four PDFs visually reviewed; two struck-out entries excluded and wrapped co-op labels joined                           |
| Wyoming WHSAA        |       50 | 25 boys (11 3A, 14 4A) and 25 girls (11 3A, 14 4A) across all 25 Wyoming 3A/4A swimming schools from 2025–26 State Championship Team Rankings tables                              |

The 154 individual-entry-only listings (146 Illinois, eight Maine) are **not
full-team participation**.
Explicit co-op names remain intact; member schools are not inferred. Except
where an authority actually supplies institution IDs, category/document-scoped
school identities remain separate. Identical labels are not sufficient to merge
boys/girls, varsity/college-club, masters/youth or cross-provider organizations.
A source alignment is not independently verified current operation; every
activity status remains `unknown`. Massachusetts' source ExpDate is retained
without inventing effective dates or interpreting an unextracted checkbox.

The [breadth receipt](breadth-checkpoint-10.json) records the current public
snapshot (`21,206` source-scoped listings across `631` selected source documents,
`900` of them Canadian across 37 documents; see [Canada](#canada)),
including all 10 California CIF sections (`930` deduplicated listings including San Francisco
AAA and all seven San Diego Section conference alignments), Florida FHSAA 2026–27
boys/girls swimming hierarchy (`938`), North Carolina NCHSAA 1A–8A regional/state
championships and NCISAA Div I–III (`272`), Virginia VISAA 2026–28 Boys/Girls
Division I/II PDFs plus statewide VHSL Classes 1–6 and regional championships (`404`),
Tennessee TISCA State Championships, MTHSSA Regions and KISL Championships (`341`
deduplicated listings), Michigan MHSAA 2025–26 LP
D1/D2/D3 & UP Finals SDIF C1 records (`308`), New York NYSPHSAA Sections I–XI
plus NYS Federation (`290`), Active Competitive YMCA Associations (`262`), YMCA
Short/Long Course National Championship scoring teams (`179` listings across `122`
teams), and 13 regional YMCA swim leagues (`388` listings across `24` states),
South Carolina SCHSL 3A/4A/5A and SCISA State Championships (`253`), Washington
WIAA 2026–27 4A/3A/2A/1A league standings widgets (`241`), Utah UHSAA 2025–26
6A–2A directories (`226`), Louisiana LHSAA Div I–IV (`195`), Colorado CHSAA
5A/4A/3A (`189`), Connecticut CIAC boys and girls divisions (`179`), Maryland
MPSSAA and WMPSSDL C1 records (`160`), New Jersey NJSIAA Meet of Champions C1
records (`153`), Kansas KSHSAA (`135`), Oklahoma OSSAA 6A/5A (`127`), California
3C2A/CCCAA (`110`), New Hampshire NHIAA Div I/II (`97`), NAIA Men's and Women's
varsity swimming & diving institutions (`96` listings across `42` institutions),
Alabama AHSAA (`80`), Nebraska NSAA (`82`), Arkansas AAA (`72`), Nevada NIAA (`68`),
Wyoming WHSAA (`50`), Delaware DIAA (`46`), North Dakota NDHSAA (`35`), District of
Columbia DCSAA (`29`), NJCAA (`28`), nine flagship U.S. summer leagues plus RSL
(`474`), 15 USA Swimming LSC club directories (`1,201`), and 27 USMS LMSC
directories (`423`). It also records affirmative non-sponsorship reviews
(`verified_non_sponsoring_authority`) for South Dakota (`SDHSAA`), Tennessee (`TSSAA`,
while independent `TISCA` sponsors TN high-school swimming), and Vermont (`VPA`).

Across the school sources:
- Georgia includes 525 GHSA school/category listings (261 boys / 264 girls at
  270 source school rows) from the 2024–25 participation survey alongside 15
  GAPPS listings; both categories and participant column sums match the source's
  published totals.
- Minnesota's 294 activity cards are projected within card boundaries and checked
  against the requested Boys/Girls activity filter; shared host-team links do
  not merge school identities or establish independent teams. Idaho's 63-row
  alignment and Hawaii's 28 championship scoring rows preserve co-op and
  scoring-only limitations explicitly.
- Combined school lists (Alaska, Arkansas, Montana, Nevada, New Mexico, West
  Virginia, Kentucky, Utah, New Hampshire, Louisiana) keep competition category `unknown`; enrollment columns
  and scoring abbreviations do not establish competition categories or
  institutional IDs.
- Regional LSC/LMSC additions cover 15 USA Swimming LSCs (Potomac Valley,
  Adirondack, Middle Atlantic, South Texas, Hawaiian, Pacific Northwest, all five
  Pacific Swimming zones, Southern California, Colorado, Florida, Georgia,
  Illinois, Indiana, North Carolina, and Midwestern) plus 27 USMS LMSCs (Florida,
  Minnesota, Pacific Northwest, North Texas, Allegheny Mountain, Nebraska, Ozark,
  Adirondack, Snake River, South Dakota, Niagara, Montana, Illinois, Michigan,
  Connecticut, Florida Gold Coast, Potomac Valley, Indiana, Arizona, South
  Carolina, Inland Northwest, Arkansas, Alaska, Kentucky, Maryland, North Dakota,
  and New England). These remain separate source assertions rather than merged
  national finder rows. Ozark explicitly lists four registered clubs and three
  workout groups under SLAM; other unresolved club/group roles stay unknown.
  Ambiguous single-city or website claims are withheld where a club lists
  multiple locations.
- Iowa's girls are administered by IGHSAU, separately from IHSAA boys.
  Pennsylvania's summary advertises 332 boys and 342 girls while its district
  details list 333 and 343 distinct school IDs (District 3 accounts for both
  differences); the detailed listings are retained with the mismatch visible.
  Wisconsin's rendered pages expose two struck-out names that plain text still
  contains; those entries are excluded. Co-op members are not split into
  separate programs.

School coverage now spans **49 U.S. jurisdictions** with imported
listings (`12,167` source-scoped high-school programs across all 48 NFHS-sponsoring
jurisdictions plus Tennessee's independent `TISCA`/`MTHSSA`/`KISL` leagues) and
**two states without school listings affirmatively verified as not sanctioning high
school swimming** (`SD` and `VT`, recorded alongside `TSSAA` as
`verified_non_sponsoring_authority` in `coverage-audit.json`),
resolving **51 / 51 U.S. state and D.C. jurisdictions**.
Florida's 2026–27 classifications are imported via the public HomeCampus
hierarchy widget (`robots.txt` allows `/`), while `fhsaa.com/documents/` remains
robots-disallowed. Nebraska's registered-school list is extracted from the
official static `<script type="text/html">` template (82 listings) without executing JS.
Michigan (`MHSAA`), Maryland (`MPSSAA` + `WMPSSDL`), the District of Columbia (`DCSAA`),
and Virginia (`VISAA` + `VHSL`) are imported from official
divisional PDFs and state/district championship SDIF `C1` institutional team records,
while Alabama (`AHSAA`), Colorado (`CHSAA`), Delaware (`DIAA`), Kansas (`KSHSAA`),
Louisiana (`LHSAA`), New Hampshire (`NHIAA`), New Jersey (`NJSIAA`), New York
(`NYSPHSAA`), North Carolina (`NCHSAA` + `NCISAA`), South Carolina (`SCHSL` + `SCISA`),
Tennessee (`TISCA` + `MTHSSA` + `KISL`), Utah (`UHSAA`),
and Wyoming (`WHSAA`) are imported from official state/regional championship sheets,
power-point brackets, and participation directories. Championship-entry and
regional/sectional sources remain partial (`partial_swimming_imported`) rather than
complete regular-season membership rolls. Private-school and independent authorities
remain separate universes from NFHS affiliates.

## Canada

Canadian rows follow the same contract: source-scoped listings with explicit
authority namespaces, no cross-source merges, all activity statuses `unknown`.
Eleven source documents supply **874 listings at 808 source-scoped organizations**, and a manual browser review of 26 university athletics pages adds **26 more** (900 Canadian listings in all)
(`CA`). The national list and the provincial section lists describe many of the
same clubs; they are kept as separate assertions (309 of the 508 provincial
listings share a website host or normalized name with a national row, and 217
national rows have such a provincial candidate; none were merged).

| Source                                   | Listings | Scope and limits                                                                                                                                                                      |
| ---------------------------------------- | -------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Swimming Canada club list (`swimming-canada:club-list-row`) | 366 | Public JSONP list: name, address, website, coordinates; type and category blank, so `program_kind` stays `unknown`. No province supplied: derived from the postal code first letter (A NL, B NS, C PE, E NB, G/H/J QC, K–P ON, R MB, S SK, T AB, V BC, Y YT; X0A–X0C NU, other X NT); 23 rows without a postal code have no province. Two `Swim PEI` rows are the provincial section, kept as `association`/`other`. Phone field empty on every row |
| Swim BC (`swim-bc:club-code`)            |       77 | Find-a-Club table with club codes and region tags; 15 rows tagged Masters Clubs become `masters`, the other 62 `age_group`; `Crawl-delay: 10` honoured                                 |
| Swim Alberta (`swim-alberta:club-code`)  |      121 | Find-a-Club cards: code, city, region, training facilities, type (year-round 50 / masters 16 / summer 55) and website; email column dropped; Hay River and Inuvik cards are `NT` (3 listings) |
| Swim Ontario (`swim-ontario:abbreviation`) |    199 | Gatsby `page-data.json` build artifact (not a documented API): 144 clubs; `Age Group and Masters Club` rows become two programs; 10 varsity teams; phone/fax/email and president/head-coach names dropped; the clubs page says "over 140 affiliated clubs" |
| Swim Manitoba (`swim-manitoba:club-listing`) |     26 | Clubs table: 24 clubs; kinds from the services text (age group, masters, university varsity; one para-swimming club kept as `other`); facility address blocks become locations          |
| Swim Saskatchewan (`swim-sask:club-code`, `swim-sask:club-listing`) | 36 | Age-group (11), summer (18), masters (6) and varsity (1) pages sharing one club-code namespace; `SAMS` independent-masters category and footer contacts excluded                      |
| Swim Nova Scotia (`swim-nova-scotia:club-listing`) |   37 | 2026–2027 year-round (14), masters (8) and 2026 summer (15) lists; clubs appearing in several lists share one organization; `(no webpage)`/inactive notes retained                      |
| Swimming NL (`swimming-nl:club-listing`) |       12 | Club Contacts 2026–27 download labels only; the contact PDFs were never fetched; kind from the club name                                                                                 |
| University athletics pages (`university-athletics:browser-review`) | 26 | Manual browser review of 26 official athletics pages (2026-10-23): 25 varsity programs, Carleton as a club team; no page bodies; category `unknown`; city/province derived from the university's location |

Per province (provincial-section listings / national-list rows): AB 118 / 43,
BC 77 / 40, MB 26 / 15, NL 12 / 11, NS 37 / 11, NT 3 / 2, ON 199 / 101, SK 36 / 14;
NB 0 / 13, PE 0 / 3 and QC 0 / 90 are **national-list only**; YT and NU have no
listing in any imported source, and 23 national rows have no province. These
are gaps, not zero-club claims. No Canadian denominator is published beyond Swim
Ontario's rounded "over 140 affiliated clubs"; the [coverage audit](coverage-audit.json)
carries the per-province table under `canada`.

Reviewed but not imported: Swim NB's find-a-club page labels its ~19 club links
by city only (six of those hosts also appear in the national list); Swim PEI
shows two logo links; FNQ's affiliation-policy and club-standings pages were
cached without a directory projection; MSABC's masters table is filled
client-side from a Google Sheet and Masters Swimming Canada offers a map search
only; NWT Swimming's clubs are reached through Swim Alberta's directory. The
U SPORTS and CCAA sites answered the planning fetches with CloudFront HTTP 403
on `robots.txt` (see the [site-access ledger](site-access-reviews.csv)), so
university swimming went through the browser-review lane instead: a person
opened 26 universities' own athletics pages on 2026-10-23 and recorded what
each showed. Those observations are imported under
`university-athletics:browser-review` as **25 `collegiate_varsity` programs and
Carleton as `collegiate_club`** (BC 2, AB 2, SK 1, MB 1, ON 10, QC 5, NS 2, NB 2,
NL 1; Canada West 6, OUA 9, RSEQ 6, AUS 5). Each registry source is the official
page URL; no page body was fetched, so its hash covers the review record, not
the page, and the reuse notes say so. Category stays `unknown` (several pages
expose men's/women's labels; one program per university is kept). City and
province are derived from the university's location, not read from the page.
Discovery came from search results and conference news; U SPORTS' site was not
used. Excluded after review: University of Alberta (swimming discontinued after
2024–25 per its own athletics notice), Mount Royal and UQAM (no swim program
found), York (unconfirmed: its swimming URL redirected to a general page). Eleven
of these universities are also listed as varsity teams by Swim Ontario (9),
Swim Manitoba (1) and Swim Saskatchewan (1); they remain separate assertions,
and two Swim Ontario varsity listings disagree with the review (Carleton is a
club team on its own site; York could not be confirmed). This is not a complete
U SPORTS or CCAA membership roll. Swimming Canada's
`robots.txt` allows the club-list path for `User-agent: *` and declares
`Content-Signal: search=yes,ai-train=no,use=reference`; only organizational
metadata was taken, in one request, and the disallowed `/swimmer/` and
`/swim-meet/` paths were never requested. Eight provincial bodies were read from
the planning pass's cached bodies (one request each, hashes retained) rather
than refetched. No imported Canadian row carried two names, so no alias table
was needed; bilingual body names are recorded in the governing-body manifest.

Canadian facilities add 1,765 source-scoped location rows: 306 Swimming Canada
club-listed street addresses linked as `listed_club_address` rather than
training locations (45 PO-box/mailing rows carry no facility row or edge; 21
coordinate pairs outside Canada blanked, a 22nd belonged to a row without an
address), 144 Swim
Ontario primary pools, 91 Swim Alberta and 31 Swim Manitoba club-listed training
facilities, 90 Swim Alberta approved competition pools (3 September 2026 PDF,
visually transcribed; 5 basins where a note names a 25 m or 50 m course) and
1,103 Statistics Canada ODRSF v1.0 records typed `pool` (ON 615, QC 296, MB 104,
AB 52, BC 22, NB 14; includes wading pools and water-play sites per source
labels; "Contains information licensed under the Open Government Licence –
Canada").

## Evidence, locations and discovery

- [organizations.csv](snapshot/organizations.csv),
  [programs.csv](snapshot/programs.csv) and
  [affiliations.csv](snapshot/affiliations.csv) are the fixed public interchange.
  Their [manifest](snapshot/manifest.json) records hashes, counts, exact source
  URLs, original content hashes and retrieval timestamps. `listing_checked` is a
  check date, not verified activity or an effective season. Source attribution
  and unknowns are preserved.
- The [facility/source contract](CATALOG.md) describes the additive location,
  basin, source-access and format CSVs. Facilities are source-scoped; shared
  addresses do not merge clubs or establish a race's physical basin. `pool_basins.csv`
  records 1,295 separately described competition basins across the USA Swimming
  National Pool Measurement Certification List (948 deduplicated basins across the
  2022 and 2020 editions spanning all 50 states and DC), USMS LMSC Places-to-Swim
  directories (108 basins), Northern Virginia Swimming League's 2026 Handbook
  (102 basins with explicit `25M` / `25Y` courses), Potomac Valley Swimming's venue
  directory (62 basins), Hawaiian Swimming's competition pool directory (26 basins),
  Adirondack Swimming's mandatory water-depth table (20 basins), Suburban Swim
  League's pool directory (17 basins), Pacific Northwest Swimming's host
  aquatic centers (7 basins), and local operator pages (5 basins).
  Elevation and dated race configurations remain unknown in the public snapshot. Mailing-style/residential-looking
  locations are screened out as documented; other addresses/coordinates remain unverified source claims.
  Swim Alberta's approved competition pool list adds 5 basins where its notes name a 25 m or 50 m course.
- The [source catalog](source-catalog.csv) and its source/format joins distinguish
  observed packaging, working public adapters, discovery-only candidates and
  access gaps. A linked archive is not an imported or complete dataset. Third-
  party sources retain their own rights; no source-data license is inferred.
- [governing-bodies.csv](governing-bodies.csv) provides 172 authority starting
  points: 59 USA Swimming LSCs, 51 NFHS member-state associations, 51 USMS
  LMSCs and 11 Canadian bodies (Swimming Canada and its ten provincial sections,
  `country=CA`, two-letter province jurisdictions). Ninety-eight have explicitly
  partial swimming imports; 74 remain without an imported jurisdiction-level
  swimming list (while `SD`, `TN`, and `VT` are separately verified as
  non-sponsoring NFHS authorities in `coverage-audit.json`, and FNQ, Swim NB and
  Swim PEI directories were reviewed without a projectable club list). The
  [manifest](governing-bodies.manifest.json) links exact imported sources/scope.
- [authority-reviews.csv](authority-reviews.csv) separately records a bounded
  homepage/transport review for all 172 starting points: 71 homepages cached,
  97 stopped outcomes and four not requested because of prior access/robots
  gaps. Stopped includes redirects requiring review, network/robots issues and
  exhausted request budgets, not 97 proven inaccessible directories. Original
  HTTP URLs are retained alongside explicitly reviewed same-host HTTPS URLs.
  The [review manifest](authority-reviews.manifest.json) hashes the ledger.
  Homepage access is separate from swimming-directory completeness. No rosters
  or contact pages were fetched to obtain program facts.

LSCs and LMSCs have different identities/jurisdictions and do not map one-to-one
to states. NFHS affiliates, private-school authorities, middle-school leagues,
YMCA and independent programs remain additional source universes. Summer leagues
are optional, opportunistic coverage and do not gate broader race acquisition. The
[directory plan](../DIRECTORY_PLAN.md) tracks these before wider race collection.

## Build and query locally

Install the pinned optional research dependencies, then use a fresh output path:

```sh
target/lakehouse-venv/bin/python research/conversion-model/directory_build.py \
  --output target/swim-directory.duckdb
```

The builder verifies fixed schemas, hashes/counts, unique IDs and references
before atomically publishing the database. It reads only public metadata; no
collector, private registry, swimmer data or network connection is required.
Besides base tables it exposes `coverage_by_source`, `coverage_by_state`,
`program_locations`, `program_location_coverage`, `facility_coverage`,
`source_format_access` and `authority_review_coverage`. For example:

```sql
SELECT program_kind, sum(source_scoped_programs) AS listings
FROM coverage_by_state GROUP BY ALL ORDER BY listings DESC;

SELECT organization_name, facility_name, state, location_status
FROM program_locations
WHERE program_kind = 'masters' AND state = 'CO'
ORDER BY organization_name, facility_name;

SELECT * FROM authority_review_coverage ORDER BY ALL;
```

`shared_website_candidates` reports exact repeated URLs for human review (306
current groups, including Canadian national/provincial pairs). It never merges identities. Institution/group facilities and
provider profile URLs can produce misleading matches. CSV/hash receipts are the
portable interchange; the DuckDB file is an ignored rebuildable artifact.

## Site access and browser review

[Site access observations](site-access-reviews.csv) and their
[manifest](site-access-reviews.manifest.json) retain URL/time-specific status and
minimal protection signals from cached receipts. A 403 with no retained response
headers/body stays **cause unknown**. Cloudflare edge headers identify the CDN;
they do not prove a WAF rule fired. An explicit challenge is a separate observed
state, including the documented `cf-mitigated: challenge` response header.
The ledger also preserves an independently checked Azure WAF-branded challenge
on a public USMS meet-results URL. Its exact security rule remains unknown; a
separate manual browser review confirmed the public page rendered after the
interstitial cleared passively. “No challenge observed” never means that a site
has no WAF. This is a partial access history for collection planning, not a
comprehensive security inventory.

Blocked/challenged sources enter a browser-review queue. An ordinary browser may
show the public page or remain blocked; record that separately. Browser success
never clears an automated collector's cooldown. Do not put cookies, tokens,
private sessions or arbitrary response headers in public notes. The ledger
separates manual browser outcomes from the original blocked responses: three
public pages rendered in a manual browser check, while one asset-host URL
remained unreviewed. Two Canadian university-sport origins (`usports.ca`,
`www.ccaa.ca`) returned CloudFront-generated HTTP 403 bodies to `robots.txt`
requests and are pending browser review. Automated cooldowns remain intact.

The public DuckDB includes `site_access_reviews`. For example:

```sql
SELECT origin, http_status, protection_observation, browser_review_status
FROM site_access_reviews
WHERE browser_review_status = 'pending'
ORDER BY origin;
```

## Reproduce and contribute

For a local registry, the [selection](selection.json) limits the export to 631
reviewed organizational source documents (594 U.S., 11 Canadian lists and 26 browser-reviewed university pages):

```sh
target/lakehouse-venv/bin/python research/conversion-model/directory_export.py \
  research/conversion-model/data/team-registry-18/registry.duckdb \
  --selection research/conversion-model/team-directory/selection.json \
  --output target/public-directory
```

The exporter selects fixed organizational columns, filters malformed/contact-like
website URLs and unreviewed query parameters, and never queries historical
observations or athlete records. Sources and richer private artifacts remain
local; a future contributor needs their own reviewed acquisition route and field
map to reacquire a source. Public CSV-to-DuckDB reproduction works independently.

[directory_import.py](../directory_import.py) accepts normalized facts with
explicit authority-scoped identity, classifications, evidence and unknown status.
[directory_rows.py](../directory_rows.py) supplies reusable offline CSV/TSV, JSON
pointer, JSONP, ordinary HTML-table, repeated-element and strict layout-text readers.
Embedded JSON parsing accepts a literal after one exact marker, and the JSONP
reader accepts one exact callback wrapping one literal; neither executes
JavaScript. Repeated-element parsing requires explicit fields/attribute filters
and a reviewed count. Ambiguous layouts, duplicate keys, changed counts and
missing selected fields fail for review. Tests use invented organizations and
check that private fields do not escape projection.

Contribute corrections with an official league, program, school or operator
source, URL, date/hash and the specific assertion being changed. Keep aliases,
co-ops and source namespaces; do not merge by name, short code or shared pool.
Do not publish personal contacts, swimmer records or raw source databases.
For normalized facility/source supplements, use the [catalog contract](CATALOG.md).
More listings or races alone do not establish national completeness or balanced
same-swimmer cross-course labels. The full collection stays local; model views
and evaluation follow acquisition and coverage review.
