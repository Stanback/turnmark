import { hydrate } from "svelte";
import Setup from "./Setup.svelte";

hydrate(Setup, { target: document.getElementById("embed-setup")! });
