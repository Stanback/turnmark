# Native jobs and navigation

Research checked October 18, 2026. These sources support the workflow patterns;
they do not validate demand for Turnmark or establish that a label will test well.

## The jobs

1. Before a meet, find a previous performance and compare courses while preparing
   entry information. Keep the original event, course, date and meet available.
2. After a race or timed practice swim, record the actual performance quickly.
   This job starts directly in My times; it does not require doing a conversion.
3. Over time, retrieve a recent swim or the best recorded time for a matching
   event, course and category, then reopen its course comparison when useful.

**Convert** contains the temporary comparison, provenance and sharing.
**My times** contains actual performances, with Recent and Best times views.
**Record time** opens a confirmation/editor for an actual swim. From Convert it
prefills the entered swim; from My times the time starts empty, while retaining
useful event/course context. The optional meet and date can be confirmed there.
The single confirmation writes the original performance, never the estimate.

The Best times view considers this device's recorded data. Importing or editing
records can change it. It does not claim verification against an official results
database. Existing comparison bookmarks remain available as Previous comparisons
inside My times until explicitly removed; they never enter its performance list.

Recent comparisons may later help someone resume an interrupted calculation.
That is a convenience within Convert, not another main destination or an actual
performance record. This PR retains the current draft and does not add a new
comparison-history store. Native methodology remains contextual under Details
and About.

## Evidence and implications

[Swimmingly's entry-time workflow](https://support.swimmingly.app/options-for-event-entry-times)
lets a coach choose a swimmer's previous time or supply another entry time.
Its [best-time guidance](https://support.swimmingly.app/where-can-i-see-the-fastest-times-for-each-swimmer-on-my-team)
also exposes historical performances while preparing entries and distinguishes
season-best from all-time-best policies. This supports making recorded times
retrievable and reusable, without treating one lifetime best as appropriate for
every meet.

[Swimcloud's entry documentation](https://support.swimcloud.com/hc/en-us/articles/44662821873683-Meet-Entries-in-Swimcloud-Free-vs-Pro)
connects recorded best times with meet entry and describes when automatic seed
selection is available. Its
[improvement definitions](https://support.swimcloud.com/hc/en-us/articles/53882057150355-Understanding-Improvement-Calculations)
distinguish individual races, event entries, personal bests and season bests.
Turnmark's simpler local record should preserve each actual swim rather than
merge repeated races or overwrite a previous performance when comparing courses.

[Meet Mobile](https://www.activenetwork.com/more-solutions/meet-mobile)
centers live results, schedules and following swimmers/teams. That is a different
job from an offline personal record. Turnmark does not need to reproduce a meet
results network or registration system to support its two main workflows.

A [2026 meet listing published by USMS](https://www.usms.org/events/events/speed-lake-city-2026-a1jpo00000aebvx2ab)
requires entry times in their achieved course and explicitly disallows converted
times. Therefore Turnmark must not automatically call an estimate an approved
entry time or promise registration eligibility. The meet's rules, accepted
sources, qualifying window and course policy remain authoritative.

## What still needs validation

Try the flow with swimmers preparing for a meet and recording results afterward.
Check whether they can find a suitable prior time, distinguish actual and
estimated values, and record a race without encountering conversion controls.
Manual data entry is a real cost; observe that friction before expanding into
accounts, automatic imports, coach tools or meet management. JSON import/export
already provides a local backup and transfer route; additional import formats
and agent integrations remain separate work. See the [SDIF/LENEX interchange notes](MEET_HISTORY.md#standard-interchange-follow-up)
for primary specifications, adapter boundaries and validation requirements.

## Next native feature: standards and points

After this visual/adaptive pass, expose USA Swimming motivational standards
(including AAAA), USMS targets and World Aquatics points before localization.
The shared Rust SDK and generated Swift/Kotlin APIs already expose these lookups;
the native screens do not yet consume them. Add contextual Standards & points
from the entered/recorded performance with age-group controls, source editions,
coverage states and the achieved course visible. Compare actual performances,
not converted estimates. Missing source data stays unavailable. This is planned
native feature work, separate from the current UI adoption.

Use one view/component per platform, accessible from both My times and Convert.
Carry the actual swim's time/event/course into it. Lead with the useful benchmark
or points result, progressively reveal controls, coverage and source details,
and avoid another main navigation destination. Persist the last standard type,
separate youth/Masters age groups and published category locally across launches.
An existing record retains its own category; preferences are defaults, not edits
to history. Converted estimates remain explicitly separate from the achieved
performance.

## README showcase after standards

Once the native standards/points workflow is implemented and visually reviewed,
add a small README gallery using actual web, iOS and Android captures. Include a
useful benchmark result and native compact/expanded examples, with concise links
to the live widget and MCP setup. Keep development previews distinct from store
releases and avoid mockups or a screenshot for every form. Capture the completed
workflow before choosing the gallery; the current redesign images are review
evidence, not a substitute for that later showcase.

## Localization follow-up

Start with English, Spanish, Brazilian Portuguese and French; consider German
next. This is a proposed sequence, not shipped language support. Keep a shared
message/key inventory and swimming glossary across web, widget and native apps,
while emitting/using platform-native resource formats. Apple's
[String Catalogs](https://developer.apple.com/documentation/xcode/localizing-and-varying-text-with-a-string-catalog)
and Android's [string resources](https://developer.android.com/guide/topics/resources/localization)
provide native lookup, substitution and plural support; Android also documents
[per-app language preferences](https://developer.android.com/guide/topics/resources/app-languages).

Translate UI, accessibility labels, errors and sharing together. Review swimming
terminology with speakers, test expanded text, localized dates and decimal-comma
time entry, and preserve the canonical clock/event/storage contract at the SDK
boundary. Source editions and numerical rules stay unchanged by a display locale.
The current English compact stroke label is IM, with Individual medley in the
selection menu, full event context and accessible value. Each future locale
needs its own reviewed equivalent rather than blindly copying that abbreviation.
