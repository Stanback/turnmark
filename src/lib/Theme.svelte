<script lang="ts">
  import { onMount } from "svelte";
  type Preference = "auto" | "light" | "dark";
  let preference = $state<Preference>("auto");
  function apply(next: Preference) {
    preference = next;
    const dark =
      next === "dark" ||
      (next === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    document.documentElement.dataset.themePreference = next;
    const canvas = getComputedStyle(document.documentElement)
      .getPropertyValue("--tm-color-canvas")
      .trim();
    if (canvas)
      document
        .querySelector('meta[name="theme-color"]')
        ?.setAttribute("content", canvas);
  }
  function choose(next: Preference) {
    apply(next);
    try {
      localStorage.setItem("turnmark-theme", next);
    } catch {
      /* The current tab still follows the chosen theme. */
    }
  }
  onMount(() => {
    const initial = document.documentElement.dataset.themePreference;
    apply(initial === "light" || initial === "dark" ? initial : "auto");
    const media = matchMedia("(prefers-color-scheme: dark)");
    const changed = () => {
      if (preference === "auto") apply("auto");
    };
    media.addEventListener("change", changed);
    return () => media.removeEventListener("change", changed);
  });
</script>

<div class="theme-control">
  <span>Appearance</span>
  <div role="group" aria-label="Appearance">
    {#each ["auto", "light", "dark"] as mode}<button
        class:active={preference === mode}
        aria-pressed={preference === mode}
        onclick={() => choose(mode as Preference)}
        >{mode[0].toUpperCase() + mode.slice(1)}</button
      >{/each}
  </div>
</div>
