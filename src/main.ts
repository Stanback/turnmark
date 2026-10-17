import { hydrate, mount } from "svelte";
import "@fontsource-variable/manrope";
import "@fontsource-variable/dm-sans";
import "@fontsource/dm-mono/400.css";
import "./app.css";
import App from "./App.svelte";

const target = document.getElementById("app")!;
const app = target.hasChildNodes()
  ? hydrate(App, { target })
  : mount(App, { target });
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register(`${import.meta.env.BASE_URL}sw.js`, {
        scope: import.meta.env.BASE_URL,
      })
      .catch(() => {
        // Online calculations remain usable when a browser blocks offline storage.
      });
  });
}
export default app;
