# Result acquisition: evidence and practical route

Reviewed October 21, 2026. This is a source-access reference for local model
training and evaluation. It does not propose a hosted results service. Real
result files, source-specific collectors, identity keys and per-race datasets
remain ignored local files. Public organizational provenance is a separate
deliverable; a directory listing does not establish result availability.

## Decision

Use official regional meet-result archives as the primary acquisition route.
Prefer published SDIF/CL2 result exports over scraping swimmer profile pages.
Qualify each archive with a small historical/course sample, then collect in
bounded, resumable batches. Preserve the directory-first order in
[the collection plan](COLLECTION_PLAN.md) and use its coverage priorities before
expanding a region that already dominates the corpus.

An approved federation integration or contributed export could supplement that
route later. Neither is a prerequisite for this experiment, and no vendor
application, paid access or external outreach has been initiated.

## Official governing-body interfaces and interchange formats

| Source or format | Verified scope | Research implication |
| --- | --- | --- |
| [Official USA Swimming API program](https://www.usaswimming.org/about-usas/resources/stakeholder-engagement/usa-swimming-api) | The published vendor program requires formal onboarding. It describes team-management tiers and a $25,000/year times/member-verification tier whose club endpoints are scoped to an authenticated vendor's associated clubs. | The published verification API does not provide an open bulk historical research export. Regional LSC result archives remain the primary public data source. |
| USA Swimming LSC & USMS LMSC result archives | Regional governing bodies publish seasonal meet-result indexes linking to downloadable Hy-Tek Meet Manager `.zip` packages, raw SDIF (`.sd3`, `.cl2`) files, and HTML/PDF summaries. | Archive-level `.zip` and SDIF downloads provide complete meet results per file with structured event, course, team, and B1 venue/altitude headers. |
| SDIF v3 (`.sd3` / `.cl2`) and Hy-Tek `.hy3` | Standard swimming interchange formats containing `B1` meet/altitude headers, `C1` team records, and `D0`/`D3` individual result records with swimmer registration IDs and whole-year ages. | Parse official result files directly; exclude event-setup exports (`meet-events-*.zip`), entry files, relay splits, and proprietary database backups. |

## Qualified regional archive inventory

Source discovery and cached sample validation support the following regional
archives. Candidate totals are index discovery counts, not deduplicated race
counts or additions to the frozen checkpoint.

| Archive | Reviewed discovery | Next action |
| --- | --- | --- |
| [North Carolina Swimming](https://www.swimnc.com/swimnc_meets/events_view.php) | Index inventory identifies 3,066 past meet record IDs with result-ZIP titles. Independent parsing of three cached samples from 2014, 2024 and 2026 accepts 214, 2,199 and 1,485 finishes respectively. One older titled file returned 404. | Preserve observed IDs and receipts; qualify historical availability and sample course/season strata before a bounded import. Do not estimate total race yield from three samples. |
| [Midwestern Swimming](https://www.mwswim.org/page/meets/results-archive) | Offline index replay discovers 137 candidate exports across current and historical archive pages, including result links alongside standard label patterns. | Validate against fixture and cached-corpus checks; reconcile HTTP budgets and receipts before collecting additional files. |
| [Potomac Valley Swimming](https://files.pvswim.org/hsresults.html) | Index inventory identifies 59 recent school-result candidates alongside club archives. Legacy club links include sampled 404s; those samples do not establish that every historical file is absent. | Keep school results separate from club-source expectations, measure stable-ID coverage, and probe historical availability sparingly. |
| [Michigan Swimming](https://www.miswim.org/page/events/2025-2026-sc-info--results) | Custom domain serves `/page/...` directly over HTTPS (`HTTP 200`, tenant `milsc`). Verified 166 Hy-Tek TM Results `.zip` links across the 3 latest seasonal indexes (`2025–26 SC`: 115, `2026 LC`: 41, `2026–27 SC`: 10) plus multi-year archive indexes back to 2006. | Filter out `meet-events-*.zip` setup files; sample and qualify `.zip` SDIF/HY3 contents in bounded batches. |
| [South Texas Swimming](https://www.stswim.org/page/events/2014-22-meet-results) | Custom domain serves `/page/...` directly over HTTPS (`HTTP 200`). Verified 453 meet links across 2014–2026+ plus observed UIL meets with Hy-Tek `.zip` downloads. | Sample seasonal `.zip` exports and verify SDIF registration ID stability before bounded collection. |
| [Adirondack Swimming](https://www.adirondackswimming.org/schedule.html) | Independent static Apache server (`HTTP 200`) with 17 seasonal result indexes (`2010–2027`), 38 `Meet Results-*.zip` SDIF archives in `2025–26` alone, and 2 official LSC pool depth/geometry certification PDFs. | Sample 2025–26 `Meet Results-*.zip` files and link certified pool geometry metadata to `pool_basins.csv` where supported. |
| High-Altitude LSCs ([New Mexico](https://www.gomotionapp.com/team/nmlsc/page/meets-info/meet-results), [Utah](https://www.gomotionapp.com/team/lscuts/page/meets/meet-results), [Snake River](https://www.gomotionapp.com/team/wzsrslsc/page/meets/meets-info--results), [Border](https://www.gomotionapp.com/team/szguslsc/page/times/meet-results), [Montana](https://www.gomotionapp.com/team/mtslsc/page/meets/upcoming-meets), [Sierra Nevada](https://www.gomotionapp.com/team/snslsc/page/meets-events/meet-schedule), [Arizona](https://azswimming.org/events/meets/)) | Survey across all 9 Mountain West / High-Altitude LSCs (`2,650–7,320 ft`) identified public Hy-Tek `.zip` SDIF/CL2 archives with B1 altitude headers and explicit `Altitude` meet flags, plus a geocoded Arizona pools map at `azswimming.org/about-azs/pools/`. | Prioritize these high-altitude LSCs for balanced elevation strata (`3,000–5,500 ft` and `>5,500 ft`) alongside sea-level and mid-elevation cohorts. |
| USMS SCM Archives ([Colonies Zone](https://www.colonieszone.org/results/), [Virginia LMSC](https://www.vaswim.org/results/)) | Static Apache indexes (`HTTP 200`) publishing 26 years (`1999–2025`) of Colonies Zone Short Course Meters (`SCM`) Championship results and 28 annual pages (`1999–2026`) of Virginia LMSC SCY/LCM/SCM results. | Qualify export formats and swimmer identity keys to expand `SCM` and adult/masters `19+` cohorts. |

The three North Carolina samples pass the existing SDIF parser without changing
identity, result-status or course rules. They were checked using a disposable
validation key and were not added to the shared corpus. Across sources, ZIPs
containing event setup, entries or proprietary Meet Manager backups must not
be mistaken for normalized result exports.

## Evidence needed before scaling

For each source and season, retain index URL/hash, the observed export link,
retrieval receipt, format, actual course/event fields and parser exclusions.
Report valid finishes, independent swimmers, missing ages/IDs, usable cross-course
pairs and venue coverage. Missing age stays missing; decimal age cannot be
reconstructed from a whole-year source field. Do not guess identity from names.

Keep public school/masters results in the general archive when supported, while
explicitly excluding records without usable identity or covariates from models
that require them. Measure those exclusions so a clean-looking training table
does not conceal selection bias. Facilities require separately sourced race-venue
and pool-configuration evidence; a team's practice address is not sufficient.

Use one paced collector per origin with persistent cache, request budgets and
cooldowns. Preserve per-origin HTTP status history and respect robots directives.
Review redirects and stop on rate-limit or access challenges. A visible public
page or API schema does not establish an unrestricted bulk-data feed.
