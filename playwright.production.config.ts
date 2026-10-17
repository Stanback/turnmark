import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  outputDir: "test-results-production",
  testDir: "./tests-production",
  workers: 1,
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:4175/turnmark/",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run build && npm run preview -- --host 127.0.0.1 --port 4175",
    url: "http://127.0.0.1:4175/turnmark/",
    reuseExistingServer: false,
  },
});
