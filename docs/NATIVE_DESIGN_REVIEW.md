# Native header and launch review

Historical header/launch research, reviewed October 17, 2026 (U.S. charts).
See [Native visual review](NATIVE_VISUAL_REVIEW.md) for the current implemented UI.

## Scope

A snapshot of the first ten free iPhone apps on [Apple’s chart](https://apps.apple.com/us/iphone/charts/36?chart=top-free)
and the first ten Android apps in [Applyra’s U.S. Google Play chart](https://www.applyra.io/tools/top-charts/google-play/us/overall/free).
Google Play’s public top-chart endpoint was unavailable to the research client,
so the Android ranking is explicitly a third-party snapshot. The app images
reviewed come from the linked official store listings. Rankings can change even
between requests; they are sampling inputs, not design-quality scores.

This reviews published store screenshots, not installed-app sessions or measured
cold starts. Marketing headlines outside device frames are not app headers.
Additional iPhone images were inspected for Vinted, PineDrama and Kalshi because
their first panels mostly advertise the product. No inference about launch-screen
behavior is made from these store images.

## iPhone snapshot

| Position | Official listing                                                                                        | Observation in the reviewed view                                         |
| -------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 1        | [KICK - Live Streaming](https://apps.apple.com/us/app/kick-live-streaming/id6446202561)                 | Small wordmark above a content feed.                                     |
| 2        | [Muse from Meta](https://apps.apple.com/us/app/muse-from-meta/id6760173601)                             | Agent avatar/name identifies the current conversation.                   |
| 3        | [Vinted: Pre-loved marketplace](https://apps.apple.com/us/app/vinted-pre-loved-marketplace/id632064380) | The selling workflow uses a task title, not the app name (second image). |
| 4        | [ChatGPT](https://apps.apple.com/us/app/chatgpt/id6448311069)                                           | Conversation, controls and composer lead; no large app-name heading.     |
| 5        | [TikTok Pro - Events](https://apps.apple.com/us/app/tiktok-pro-events/id6741796873)                     | Feed/category navigation and media lead.                                 |
| 6        | [McDonald's](https://apps.apple.com/us/app/mcdonalds/id922103212)                                       | Compact brand/rewards identity; most space goes to account and offers.   |
| 7        | [PineDrama - Short Dramas](https://apps.apple.com/us/app/pinedrama-short-dramas/id6754134922)           | Video fills the task view without a brand header (second image).         |
| 8        | [Kalshi: Trade Football & more](https://apps.apple.com/us/app/kalshi-trade-football-more/id1632713844)  | Small wordmark above market content (second image).                      |
| 9        | [Threads](https://apps.apple.com/us/app/threads/id6446901002)                                           | Compact symbol above the feed.                                           |
| 10       | [CapCut: Photo & Video Editor](https://apps.apple.com/us/app/capcut-photo-video-editor/id1500855883)    | Content categories and editing/navigation tools lead.                    |

## Android snapshot

| Position | Official listing                                                                                         | Observation in the reviewed view                                         |
| -------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 1        | [Muse from Meta](https://play.google.com/store/apps/details?id=com.facebook.aura&gl=us)                  | Agent avatar/name above a conversation.                                  |
| 2        | [ChatGPT](https://play.google.com/store/apps/details?id=com.openai.chatgpt&gl=us)                        | Conversation and composer lead.                                          |
| 3        | [Settings Home](https://play.google.com/store/apps/details?id=com.eet.settings.launcher&gl=us)           | Dashboard/search and device controls lead.                               |
| 4        | [TikTok Pro - Events](https://play.google.com/store/apps/details?id=com.ss.android.ugc.tiktok.pro&gl=us) | Shopping search, navigation and offers lead.                             |
| 5        | [WhatsApp Messenger](https://play.google.com/store/apps/details?id=com.whatsapp&gl=us)                   | Compact app-name header above chats.                                     |
| 6        | [TikTok](https://play.google.com/store/apps/details?id=com.zhiliaoapp.musically&gl=us)                   | Feed/category navigation over full-screen media.                         |
| 7        | [GPS Location Tracker Ultra](https://play.google.com/store/apps/details?id=com.locc.trak.ult&gl=us)      | Map/task view retains an identifying title.                              |
| 8        | [Vinted](https://play.google.com/store/apps/details?id=fr.vinted&gl=us)                                  | First panel is promotional; no in-app header conclusion from that panel. |
| 9        | [DealSeek](https://play.google.com/store/apps/details?id=com.dealseekorg.dealseek&gl=us)                 | First panel is promotional; no in-app header conclusion from that panel. |
| 10       | [McDonald’s](https://play.google.com/store/apps/details?id=com.mcdonalds.app&gl=us)                      | Location selection uses a functional header above the map.               |

## Earlier Turnmark decision

The sample is mixed: some feeds retain a small wordmark, some use an icon, and
focused workflows often show actions or task context. It does not establish a
rule that successful apps omit branding. For Turnmark’s short calculation flow,
the input labels and selected bottom tab already explain the screen. Removing
the logo/name bar and “Convert a swim” heading puts the time field first and
makes room for Save/Share. Saved and Method keep useful page titles. The saved
result card also drops its decorative wave.

The launcher icon keeps the shared wave identity. Android 12+ uses that icon in
its system splash, with a background matching the app’s light/dark appearance.
There is no extra splash activity, timer or loading animation. On iOS, a launch
background matching the first screen leads straight into the converter, without
an additional logo screen.

The later native visual direction restores a compact **turnmark + wave** on
the same native toolbar row as the overflow menu on both apps. This supersedes
the intermediate large “Swim converter” title. The menu exposes About and
published methodology; at larger text sizes the wordmark can yield to the wave.
An additional app-name banner stays out of the converter;
the current [visual review](NATIVE_VISUAL_REVIEW.md) and default phone captures
supersede the earlier header-free presentation.

This follows [Apple’s launch guidance](https://developer.apple.com/design/human-interface-guidelines/launching),
which favors immediate interaction, matching the first screen and avoiding
standalone launch branding, and [Android’s splash-screen guidance](https://developer.android.com/develop/ui/views/launch/splash-screen),
which provides the launcher-icon splash and dismisses it when the first frame is
ready. System Liquid Glass navigation and action buttons stay in use on iOS.

## Result context

The persistent result leads with its destination event, actual distance and
units, course and category. The time remains prominent, with the
entered/published/derived label and original swim nearby. Use the SDK's returned
event rather than copying the input distance: 400 metres can compare with 500
yards. Both apps expose a native Details sheet with the original/result pair,
the SDK's multiplier and source edition. This keeps provenance available while
giving the answer more space than a repeated source title.

Input controls have explicit stroke, distance and published-category labels;
distance choices include yards or metres. Save/Share follow the inputs. The
next [offline history workflow](MEET_HISTORY.md) prioritizes actual performances
and meet/date context, keeping converted estimates out of personal bests.
