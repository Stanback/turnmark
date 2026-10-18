import { hydrate, mount } from "svelte";
import "@fontsource-variable/manrope";
import "@fontsource-variable/dm-sans";
import "@fontsource/dm-mono/400.css";
import "./app.css";
import "./generated/design-tokens.css";
import "./converter.css";
import App from "./App.svelte";
import { createEngine } from "@turnmark/sdk";
import wasmUrl from "@turnmark/sdk/engine.wasm?url";

const target = document.getElementById("app")!;
// Register caching before awaiting Wasm, so a fast window load cannot skip it.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  const register = () => {
    navigator.serviceWorker
      .register(`${import.meta.env.BASE_URL}sw.js`, {
        scope: import.meta.env.BASE_URL,
      })
      .catch(() => {
        // Online calculations remain usable when a browser blocks offline storage.
      });
  };
  if (document.readyState === "complete") register();
  else window.addEventListener("load", register, { once: true });
}
async function start() {
  target.setAttribute("aria-busy", "true");
  try {
    await createEngine({ wasm: wasmUrl });
    const app = target.hasChildNodes()
      ? hydrate(App, { target })
      : mount(App, { target });
    return app;
  } catch (error) {
    console.error("Turnmark could not initialize", error);
    const message = document.createElement("p");
    message.setAttribute("role", "alert");
    message.textContent =
      "Turnmark couldn’t load. Check your connection and reload the page.";
    target.prepend(message);
  } finally {
    target.removeAttribute("aria-busy");
  }
}
const app = start();
export default app;
