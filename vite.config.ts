import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  base: "/",
  server: {
    // Native test/report writers must not reload a running web review.
    watch: {
      ignored: [
        "**/target/**",
        "**/apps/**/build/**",
        "**/packages/**/build/**",
        "**/build/reports/**",
        "**/test-results/**",
        "**/playwright-report/**",
      ],
    },
  },
  build: {
    rolldownOptions: {
      input: [
        "index.html",
        "embed/index.html",
        "embed/v1/index.html",
        "mcp/index.html",
      ],
    },
  },
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
