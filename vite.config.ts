import vinext from "vinext";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    vinext(),
  ],

  build: {
    outDir: "dist",
  },

  server: {
    host: "0.0.0.0",
  },
});
