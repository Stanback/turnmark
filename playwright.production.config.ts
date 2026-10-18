import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  outputDir: "test-results-production",
  testDir: "./tests-production",
  workers: 1,
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:4175/",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run build && node deployment/node_modules/wrangler/bin/wrangler.js dev --local --ip 127.0.0.1 --port 4175 --config wrangler.jsonc",
    url: "http://127.0.0.1:4175/",
    reuseExistingServer: false,
  },
});
