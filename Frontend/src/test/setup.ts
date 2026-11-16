// Matchers do DOM (toBeInTheDocument, toBeDisabled...) e limpeza entre testes.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});
