# Shared swim glyphs

`swim-icons.json` owns the eight small vector glyphs: the five supported strokes,
distance, course equivalents and the Log swim stopwatch-plus. The generator also derives a tightly framed
toolbar wave from the existing `wave.svg` brand geometry. The swim glyphs
accompany readable labels, never replace
event names or imply additional engine coverage. System navigation, sharing and
overflow actions continue to use platform icons.

Web, widget and MCP Apps inline the same paths with `currentColor`. Native
controls use generated Android VectorDrawables and iOS template PDF assets,
keeping menus and scaled displays vector-based. Their tint comes from existing
semantic tokens or the native control environment.

```sh
node design/generate-icons.mjs
node design/generate-icons.mjs --check
```

The generator deliberately supports only absolute move, line, cubic and close
commands in a 24-unit viewbox. It is not a general SVG/PDF converter. Edit the
canonical paths and regenerate; do not edit `design/icons`, `ic_swim_*.xml` or
the `Swim-*.imageset` exports independently. Native wrappers and the design
contract tests check these committed exports for drift.
