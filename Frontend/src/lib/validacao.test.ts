import { describe, expect, it } from "vitest";
import { emailValido } from "@/lib/validacao";

describe("emailValido", () => {
  it.each(["ana@hospital.org.br", "a.b-c@x.io", "nome+tag@dominio.com"])("aceita %s", (email) => {
    expect(emailValido(email)).toBe(true);
  });

  it.each([
    "",
    "sem-arroba.com",
    "ana@",
    "ana@dominio",
    "ana@dominio.",
    "ana@.com",
    "ana @dominio.com",
    "ana@@dominio.com",
  ])("recusa %j", (email) => {
    expect(emailValido(email)).toBe(false);
  });

  it("responde rápido mesmo com texto longo e malformado (sem retrocesso exponencial)", () => {
    const texto = "a@" + "b".repeat(50_000) + "!";
    const inicio = performance.now();
    expect(emailValido(texto)).toBe(false);
    expect(performance.now() - inicio).toBeLessThan(200);
  });
});
