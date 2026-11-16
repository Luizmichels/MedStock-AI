import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DefinirSenhaPage from "@/app/definir-senha/page";
import Home from "@/app/page";
import RedefinirSenhaPage from "@/app/redefinir-senha/page";

const navegacao = vi.hoisted(() => ({ redirect: vi.fn() }));
vi.mock("next/navigation", () => ({
  redirect: navegacao.redirect,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams({ token: "token-do-email" }),
}));

describe("páginas públicas", () => {
  it("a raiz do site redireciona para o dashboard", () => {
    Home();
    expect(navegacao.redirect).toHaveBeenCalledWith("/dashboard");
  });

  it("/definir-senha mostra o formulário de criar senha", () => {
    render(<DefinirSenhaPage />);
    expect(screen.getByRole("heading", { name: "Crie sua senha" })).toBeInTheDocument();
  });

  it("/redefinir-senha mostra o formulário de nova senha", () => {
    render(<RedefinirSenhaPage />);
    expect(screen.getByRole("heading", { name: "Redefinir senha" })).toBeInTheDocument();
  });
});
