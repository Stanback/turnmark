import { mount } from "svelte";
import "@fontsource-variable/manrope";
import "@fontsource-variable/dm-sans";
import "@fontsource/dm-mono/400.css";
import "./app.css";
import App from "./App.svelte";

const app = mount(App, { target: document.getElementById("app")! });
export default app;
