import { defineConfig } from "vitest/config";
export default defineConfig({
  test: {
    include: ["src/**/*.test.ts", "packages/*/test/**/*.test.ts"],
    setupFiles: ["packages/sdk/test/setup.ts"],
  },
});
