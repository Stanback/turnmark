<script lang="ts">
  import { onMount } from "svelte";
  import Icon from "./Icon.svelte";
  interface InstallEvent extends Event {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
  }
  let installEvent = $state<InstallEvent | null>(null);
  let installed = $state(false);
  let help: HTMLDialogElement;
  let requesting = $state(false);
  onMount(() => {
    const standalone = window.matchMedia("(display-mode: standalone)");
    const checkInstalled = () =>
      (installed =
        standalone.matches ||
        !!(navigator as Navigator & { standalone?: boolean }).standalone);
    checkInstalled();
    const available = (event: Event) => {
      event.preventDefault();
      installEvent = event as InstallEvent;
    };
    const didInstall = () => {
      installed = true;
      installEvent = null;
      help?.close();
    };
    window.addEventListener("beforeinstallprompt", available);
    window.addEventListener("appinstalled", didInstall);
    standalone.addEventListener("change", checkInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", available);
      window.removeEventListener("appinstalled", didInstall);
      standalone.removeEventListener("change", checkInstalled);
    };
  });
  async function install() {
    if (!installEvent) {
      help.showModal();
      return;
    }
    requesting = true;
    try {
      await installEvent.prompt();
      await installEvent.userChoice;
      installEvent = null;
    } catch {
      help.showModal();
    } finally {
      requesting = false;
    }
  }
</script>

{#if !installed}<button
    class="install-button"
    onclick={install}
    disabled={requesting}
    ><Icon name="download" size={15} /><span>Install app</span></button
  >{/if}
<dialog class="install-dialog" bind:this={help} aria-labelledby="install-title">
  <div class="install-dialog-heading">
    <span class="brand-icon"><Icon name="wave" size={24} /></span><button
      class="icon-button"
      onclick={() => help.close()}
      aria-label="Close installation instructions"
      ><Icon name="close" size={21} /></button
    >
  </div>
  <h2 id="install-title">Install Turnmark</h2>
  <p>
    Open the converter in its own window, with an app icon on your desktop or
    home screen.
  </p>
  <h3>Chrome or Edge</h3>
  <p>
    Use the install icon in the address bar or the browser menu’s install
    option. If it isn’t available yet, keep the page open while the browser
    checks installation support.
  </p>
  <h3>iPhone or iPad</h3>
  <p>Open this page in Safari, tap Share, then Add to Home Screen.</p>
  <p class="install-offline">
    <Icon name="info" size={17} />After the first online visit finishes caching,
    the converter and its bundled tables work offline. Saved swims stay on this
    device.
  </p>
  <button class="primary-button" onclick={() => help.close()}>Got it</button>
</dialog>
