import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    css: false,
    // Count every source file, not only the ones a test happens to import: without `include` an
    // untested page is invisible and the number reads 70% for a 31% suite.
    coverage: {
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/types/**", "src/**/*.test.*", "src/components/ui/**"],
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});