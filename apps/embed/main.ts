import { mount } from "svelte";
import "@fontsource-variable/dm-sans";
import "@fontsource/dm-mono/400.css";
import { createEngine } from "@turnmark/sdk";
import wasmUrl from "@turnmark/sdk/engine.wasm?url";
import Widget from "./Widget.svelte";

// The widget does not read/write app preferences, history, cookies or storage,
// register a service worker, message its parent, or load publisher scripts.
const theme = new URLSearchParams(location.search).get("theme");
if (theme === "light" || theme === "dark")
  document.documentElement.dataset.theme = theme;
const target = document.getElementById("widget")!;
try {
  await createEngine({ wasm: wasmUrl });
  target.replaceChildren();
  mount(Widget, { target });
} catch {
  target.replaceChildren();
  const error = document.createElement("p");
  error.setAttribute("role", "alert");
  error.textContent =
    "The converter couldn’t load. Please reload or open turnmark.app.";
  target.append(error);
}
