import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const lumonVersion = readFileSync(resolve(import.meta.dirname, "../VERSION"), "utf8").trim();

export default defineConfig({
  plugins: [react()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
    __LUMON_VERSION__: JSON.stringify(lumonVersion),
  },
  build: {
    emptyOutDir: true,
    outDir: resolve(import.meta.dirname, "../lib/templates/dashboard-app"),
    lib: {
      entry: resolve(import.meta.dirname, "src/main.tsx"),
      formats: ["es"],
      fileName: () => "dashboard.js",
      cssFileName: "dashboard"
    },
    rollupOptions: {
      output: {
        assetFileNames: "[name][extname]"
      }
    }
  }
});
