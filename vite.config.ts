import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  base: "/turnmark/",
  ssr: {
    external: [
      "@turnmark/sdk",
      "@turnmark/sdk/compat",
      "@turnmark/sdk/compat/masters",
      "@turnmark/sdk/compat/points",
      "@turnmark/sdk/conversion",
      "@turnmark/sdk/youth",
    ],
  },
});
