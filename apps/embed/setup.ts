import { hydrate } from "svelte";
import "@fontsource-variable/dm-sans";
import "@fontsource/dm-mono/400.css";
import Setup from "./Setup.svelte";

hydrate(Setup, { target: document.getElementById("embed-setup")! });
