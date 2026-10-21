import { mount } from "svelte";
import "@fontsource-variable/dm-sans";
import "@fontsource/dm-mono/400.css";
import { createConverter } from "@turnmark/sdk/converter";
import wasmUrl from "@turnmark/sdk/converter.wasm?url";
import "../../src/generated/design-tokens.css";
import Widget from "./Widget.svelte";
import { announceEmbedHeight } from "./resize";

// The widget does not read/write app preferences, history, cookies or storage,
// register a service worker, receive parent commands, or load publisher scripts.
// Its optional parent-facing layout signal contains only content height.
const theme = new URLSearchParams(location.search).get("theme");
if (theme === "light" || theme === "dark")
  document.documentElement.dataset.theme = theme;
const target = document.getElementById("widget")!;
try {
  const converter = await createConverter({ wasm: wasmUrl });
  target.replaceChildren();
  mount(Widget, { target, props: { converter } });
} catch {
  target.replaceChildren();
  const error = document.createElement("p");
  error.setAttribute("role", "alert");
  error.textContent =
    "The converter couldn’t load. Please reload or open turnmark.app.";
  target.append(error);
} finally {
  announceEmbedHeight(target);
}
