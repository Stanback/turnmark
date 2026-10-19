# Converter layout exploration

This follow-up explores a calmer web converter layout. It is a draft design
study, separate from conversion-model research. No redesigned UI has been
implemented or accepted yet.

## Direction

Bring the editable swim and its three course equivalents into one visual group.
Make the original time, destination event/course and derived estimate easy to
scan. Explore a compact next-target summary using the existing published
standards, with the full standards/points view still reachable. Keep the navy,
cyan and lime identity and generated semantic tokens.

Keep water artwork behind the content, restrained border highlights and subtle
button hover feedback. Preserve readable surfaces, focus visibility, reduced
motion and light/dark appearances. Decorative branching light trails, miniature
swimmers and invented probability/confidence graphics are outside this study.

NCAA stays the default. The alternative conversion method stays a quiet setting;
its selected source and original-swim benchmark distinction remain accessible.
Native controls remain platform-owned; this web study does not imply a shared
web/native layout or a native redesign.

## README screenshots are part of this PR

Before this draft is ready, update the root README's images from the actual
running builds after the explored layout settles. Do not use the supplied
concept art as a screenshot of implemented behavior.

- Lead with the main converter: a readable original swim, editable time/event
  and SCY/SCM/LCM results. Avoid a hero-heavy crop that cuts off the converter.
- Keep the paired iOS and Android previews on their normal Convert/home view,
  using the same sample swim. Show enough input and converted result context;
  standards and points sheets belong in the detailed review.
- Make the NCAA/Colorado capability discoverable where shown, with a compact
  supplementary actual-build capture if opening settings would obscure the
  main comparison. Keep the lead screenshot representative of the NCAA default.
- Review existing widget/MCP images where this PR touches their presentation.
  Distinguish published npm behavior from newer source-only UI.
- Use sample data only. Check both appearances and narrow/large-text layouts in
  the detailed review; keep the README's gallery small, legible and current.
- Update image paths, alt text and captions together. Record source revision,
  method, sample event/time, viewport/device and capture procedure in the review.

The current README images remain until their replacements exist. Screenshot
refresh is an acceptance item for this PR, not a later documentation chore.

## Completion checks

- Confirm which layout to keep through actual desktop/mobile browser previews.
- Keep calculations, unsupported/invalid states, offline behavior, shared links,
  keyboard access and original-swim standards/points semantics intact.
- Run web type/unit/browser/production checks for implemented layout changes.
  Exercise widget/MCP or native consumers only if this study changes them.
- Inspect the replacement README images at their rendered GitHub size and verify
  their relative links. Do not mark this draft ready with stale screenshots.
