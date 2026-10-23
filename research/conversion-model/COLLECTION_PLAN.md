# Collection priorities after the million-race checkpoint

The [result-source review](RESULT_SOURCES.md) separates documented provider
workflows from unverified feed/API assumptions and records the next qualified
regional acquisition leads. Use it with the directory coverage audit when
choosing batches.

The next acquisition checkpoint is **five million deduplicated actual races**,
followed by a coverage-led expansion that could reach **10–30 million** as
accessible sources and useful history allow. Five million is not a cap, and the
larger range is not a promised obtainable total or a reason to duplicate races.
First expand the [organizational directory](DIRECTORY_PLAN.md); then collect a
broader source mix and balance the training cohorts after acquisition. Keep
coverage counts during acquisition so five million does not simply reproduce
the same regional concentration. Do not discard the naturally distributed raw
corpus to force balanced training counts.

The [aggregate receipt](checkpoint-summary.json) describes the initial frozen private
checkpoint: 1,024,845 distinct actual individual races, 57,780 source-scoped
swimmers and 685 meets. The [latest acquisition receipt](acquisition-checkpoint-06.json)
advances the local corpus past the five-million target to **5,690,964** distinct
actual individual races, **193,429** source-scoped swimmers and **4,194** meets
across nine regional LSC archives (`Pacific`: `1,427,491`, `North Carolina`:
`1,406,162`, `Southeastern`: `1,011,729`, `Michigan`: `862,281`, `Adirondack`:
`610,386`, `Potomac Valley`: `170,493`, `South Dakota`: `107,421`, `Midwestern`:
`93,821`, and `South Texas`: `1,180`). This is a collection milestone, not a
balanced national sample. No swimmer-level records or identity keys are published.

Only 337,471 races meet the first pilot's SCY/LCM 50/100/200 freestyle scope.
Matching within 30 days yields **5,655 pairs from 2,577 swimmers**, including
760 test pairs from 358 held-out swimmers. Men/women pair counts are close to
even, but **5,267 pairs (93.1%) come from Pacific Swimming's archive**. The other
archives contribute 174 Potomac Valley, 111 Midwestern and 103 Southeastern
pairs. Archive region identifies the publishing archive, not every swimmer's
home geography.

The raw race count is even less informative about model readiness: SCM has only
2,508 rows, and the whole dataset has only 10,221 age-19+ races. The first pilot
excludes SCM and other strokes/distances; adding them requires a separate
coverage/evaluation decision. The public directory's team count is independent
of these race and matching counts.

## Acquisition order

1. Add paired short/long-course seasons from additional official regional
   archives, and first find out why existing non-Pacific archives produce so
   few nearby-date pairs. Track eligible pairs and independent swimmers per
   source alongside raw race counts. Avoid expanding already dominant archives
   merely to reach five million faster.
2. Include ordinary local meets and slower performance bands, not only large
   championships. Sample meet/season/course strata before looking at swimmer
   outcomes. A directory listing helps locate archives; it is not permission to
   assume every source exposes a reusable complete results feed.
3. Broaden adolescent age bands and geography within the pilot, then assess
   whether masters, collegiate and school sources have stable published IDs and
   enough independent cross-course matches. Keep ID namespaces and formats
   explicit. No cross-provider identity joins by swimmer name.
4. Report missing/ambiguous identities and course/event anomalies by adapter.
   Preserve suspect source records locally for review; they must not silently
   enter a training cohort. Source membership, incomplete exports and ID changes
   can create selection bias even when parsing succeeds.
5. Compare 14/30/60-day matching as documented research variants if needed. The
   current checkpoint remains the frozen 30-day pilot. Longer gaps can reflect
   training, growth and taper; more pairs do not automatically improve labels.

## Balance and evaluation

Use cohort-specific swimmer/meet counts, not a promise that all course/age/event
cells should have equal populations. Preserve a natural-frequency evaluation
set and report a separate macro/cohort-balanced metric. Fit any sample weights,
performance quantiles or sampling caps on training data only. A few dominant
meets/swimmers must not manufacture apparent independent coverage.

The existing swimmer-disjoint 70/15/15 split prevents one swimmer crossing those
partitions. A separate later-meet/season and region holdout is still needed;
the current test set is not proof of temporal or national generalization.
Compare NCAA, documented Colorado and simple statistical baselines before a
bounded XGBoost run. No calibrated prediction interval, physiological claim or
product-model approval follows from this checkpoint.

## Directory sources

The [public organizational catalog](team-directory/README.md) and
[source catalog](team-directory/source-catalog.csv) distinguish imported listings,
partial searches and unimported candidates. Masters/workout groups, varsity,
school and independent-program coverage remain explicit gaps. Summer-league
coverage is an optional extra, not a completeness requirement.
The source-specific collectors keep cache, pacing, request budgets and cooldowns
local. Access challenges stop a source; they are not a reason to bypass controls.

## Broader collection readiness

Keep directory breadth first: review swimming-specific school sources across the
50 states and D.C., reconcile national club listings against LSC directories,
and cross-check the national masters finder against LMSC clubs and workout
groups. Record source universes, actual imported counts, seasons and remaining
gaps. A public finder response or authority homepage does not establish all
active teams. Independent-school associations, YMCA, college
club/varsity and middle-school programs where published remain separate scopes.

Then acquire linked public result archives in resumable regional/seasonal
batches, retaining full supported actual-finish history rather than only the
first freestyle model pilot. Prefer broad archives over fetching individual
swimmer profiles. Keep per-origin pacing, finite budgets, caching/backoff,
source receipts and parser rejection counts as volume grows. Stop on access
challenges; source access is not an entitlement to a bulk feed.

The natural-frequency deduplicated archive remains local. Apply balancing only
to derived training views/weights, and preserve independent swimmer, later-season
and region/venue evaluation. Track valid pairs, source breadth and event/course/
age/performance coverage alongside the headline race total. Ten million badly
concentrated or mismatched rows would not improve the research automatically.
