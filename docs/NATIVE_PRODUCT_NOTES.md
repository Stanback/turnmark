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
**Log swim** opens a confirmation/editor for an actual swim. From Convert it
prefills the entered swim; from My times the time starts empty, while retaining
useful event/course context. The optional meet and date can be confirmed there.
The single confirmation writes the original performance, never the estimate.
Web’s **Save comparison** bookmarks its conversion setup; it does not write a
native performance record. Keep labels aligned with these distinct actions.

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

## Native standards and points

Native Standards & points includes USA Swimming motivational standards
(including AAAA), USMS targets and World Aquatics points.
The native screens now consume the shared Rust lookups and benchmark assessment
through generated Swift/Kotlin APIs. Open contextual Standards & points
from the entered/recorded performance with age-group controls, source editions,
coverage states and the achieved course visible. Compare actual performances,
not converted estimates. Missing source data stays unavailable. This is a contextual
feature, separate from course conversion and recorded-performance storage.

Use one view/component per platform, accessible from both My times and Convert.
Carry the actual swim's time/event/course into it. Lead with the useful benchmark
or points result, progressively reveal controls, coverage and source details,
and avoid another main navigation destination. Persist the last standard type,
separate youth/Masters age groups and published category locally across launches.
An existing record retains its own category; preferences are defaults, not edits
to history. Converted estimates remain explicitly separate from the achieved
performance.

## README showcase

The README now includes actual web, iOS and Android captures after completing
and visually reviewing native Standards & points. Native screenshots are
clearly labeled development previews, with links to the live widget/MCP setup
and detailed [standards review](NATIVE_STANDARDS_REVIEW.md).

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

### Implemented comparison defaults

Both native apps reuse one contextual Standards & points sheet from Convert and
recorded-swim detail. The sheet uses the original time, event, course and category;
category follows that swim, and the converter's existing saved draft retains its
category across launches. Standard type, youth age, Masters age and comparison
mode are stored locally and do not edit history. Comparison settings start
expanded for first use and remain available behind a labeled disclosure. No
profile inference or age-at-meet eligibility check is added.

The sheet's presentation state lives above adaptive pane branches. Rotation or
fold changes retain its original input. Sources and coverage are progressively
available, while missing targets are explained in the result itself. Source
links require connectivity; lookups and preferences work offline.

## October 19 converter alignment

On phones, show editable swim inputs first, followed by all course equivalents.
A fresh draft is blank, with direct time entry. Preserve the draft on
relaunch; reset clears the time without changing the swimmer's chosen context.
A user can scroll directly to results after valid entry. Wider workspaces keep
independent input/result panes and preserve active entry through layout changes.

The selected row focuses the main comparison. Keep one Standards & points entry
point and the explicit Log swim action below the results. Calculation details
compare NCAA and Colorado for the same destination, label their gap a method
difference, and distinguish source formula inputs from personal physiology.
Keep NCAA as default. The [altitude parity follow-up](ALTITUDE.md) provides an
independent USA Swimming / NCAA altitude policy without changing original swims.
