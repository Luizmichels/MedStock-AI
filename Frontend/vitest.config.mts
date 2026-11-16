import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

// Testes do frontend: Vitest + Testing Library num DOM simulado (jsdom).
// A cobertura (v8) é medida sobre todo o src/, não só sobre os arquivos testados,
// e o mínimo de 25% faz o `npm run test:coverage` (e o CI) falhar abaixo disso.
export default defineConfig({
  // O tsconfig usa "jsx": "preserve" (quem compila é o Next); nos testes, o
  // esbuild do Vitest transforma o JSX com o runtime automático do React.
  esbuild: { jsx: "automatic" },
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/test/**"],
      reporter: ["text-summary", "html", "lcov"],
      thresholds: { statements: 25, lines: 25 },
    },
  },
});
