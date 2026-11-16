import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ConfiguracoesPage from "@/app/(app)/configuracoes/page";
import type { Usuario } from "@/lib/auth";
import { mockFetch, resposta } from "@/test/fetch";

const sessao = vi.hoisted(() => ({
  usuario: null as Usuario | null,
  atualizarUsuario: vi.fn(),
}));
vi.mock("@/lib/auth", async (original) => ({
  ...(await original<typeof import("@/lib/auth")>()),
  useAuth: () => sessao,
}));

beforeEach(() => {
  sessao.usuario = { id: "1", nome: "Ana Souza", email: "ana@hospital.org.br", perfil: "admin", empresaId: 3 };
  sessao.atualizarUsuario.mockReset();
});

const campo = (autocomplete: string, indice = 0) =>
  document.querySelectorAll<HTMLInputElement>(`input[autocomplete="${autocomplete}"]`)[indice];
const digitar = (el: HTMLInputElement, valor: string) => fireEvent.change(el, { target: { value: valor } });
const botao = (nome: string) => screen.getByRole("button", { name: nome });

describe("Minha conta: dados pessoais", () => {
  it("começa com os dados do usuário e o botão desabilitado sem mudanças", () => {
    mockFetch(resposta(200, {}));
    render(<ConfiguracoesPage />);
    expect(campo("name")).toHaveValue("Ana Souza");
    expect(campo("email")).toHaveValue("ana@hospital.org.br");
    expect(botao("SALVAR DADOS")).toBeDisabled();
  });

  it("trocar só o nome não pede senha e atualiza o menu", async () => {
    const fetchMock = mockFetch(resposta(200, { nome: "Ana S.", email: "ana@hospital.org.br" }));
    render(<ConfiguracoesPage />);

    digitar(campo("name"), "  Ana S. ");
    fireEvent.click(botao("SALVAR DADOS"));

    expect(await screen.findByRole("status")).toHaveTextContent("Dados salvos.");
    expect(JSON.parse(fetchMock.mock.calls[0][1]!.body as string)).toEqual({ nome: "Ana S." });
    expect(sessao.atualizarUsuario).toHaveBeenCalledWith({ nome: "Ana S.", email: "ana@hospital.org.br" });
  });

  it("trocar o e-mail exige a senha atual", async () => {
    const fetchMock = mockFetch(resposta(200, { nome: "Ana Souza", email: "nova@hospital.org.br" }));
    render(<ConfiguracoesPage />);

    digitar(campo("email"), "Nova@Hospital.org.br");
    fireEvent.click(botao("SALVAR DADOS"));
    expect(screen.getByText("Para trocar o e-mail, confirme a sua senha atual.")).toBeInTheDocument();

    digitar(campo("current-password"), "segredo123");
    fireEvent.keyDown(campo("current-password"), { key: "Enter" });

    expect(await screen.findByRole("status")).toHaveTextContent("Use o novo e-mail no próximo login.");
    expect(JSON.parse(fetchMock.mock.calls[0][1]!.body as string)).toEqual({
      email: "nova@hospital.org.br",
      senha_atual: "segredo123",
    });
  });

  it("valida nome vazio e e-mail inválido", () => {
    mockFetch(resposta(200, {}));
    render(<ConfiguracoesPage />);

    digitar(campo("name"), "   ");
    fireEvent.click(botao("SALVAR DADOS"));
    expect(screen.getByText("Informe o seu nome.")).toBeInTheDocument();

    digitar(campo("name"), "Ana");
    digitar(campo("email"), "ana@");
    fireEvent.click(botao("SALVAR DADOS"));
    expect(screen.getByText("Informe um e-mail válido.")).toBeInTheDocument();
  });

  it("mostra o erro da API (ex.: e-mail já usado)", async () => {
    mockFetch(resposta(409, { detail: "E-mail já cadastrado." }));
    render(<ConfiguracoesPage />);

    digitar(campo("name"), "Ana S.");
    fireEvent.click(botao("SALVAR DADOS"));

    expect(await screen.findByText("E-mail já cadastrado.")).toBeInTheDocument();
  });
});

describe("Minha conta: trocar senha", () => {
  // na tela: [0] senha atual da troca de senha; new-password: [0] nova, [1] confirmação
  function preencher(atual: string, nova: string, confirma = nova) {
    digitar(campo("current-password"), atual);
    digitar(campo("new-password", 0), nova);
    digitar(campo("new-password", 1), confirma);
  }

  it.each([
    ["segredo123", "curta", "curta", "A nova senha deve ter pelo menos 8 caracteres."],
    ["segredo123", "novasenha1", "novasenha2", "As senhas não conferem."],
    ["segredo123", "segredo123", "segredo123", "A nova senha deve ser diferente da atual."],
  ])("recusa: atual=%s nova=%s confirma=%s", (atual, nova, confirma, aviso) => {
    const fetchMock = mockFetch(resposta(200, {}));
    render(<ConfiguracoesPage />);

    preencher(atual, nova, confirma);
    fireEvent.click(botao("ALTERAR SENHA"));

    expect(screen.getByText(aviso)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("troca a senha, limpa os campos e avisa", async () => {
    const fetchMock = mockFetch(resposta(200, { mensagem: "ok" }));
    render(<ConfiguracoesPage />);

    preencher("segredo123", "novasenha1");
    fireEvent.click(botao("Mostrar"));
    fireEvent.keyDown(campo("new-password", 1), { key: "Enter" });

    expect(await screen.findByRole("status")).toHaveTextContent("Senha alterada com sucesso.");
    expect(campo("new-password", 0)).toHaveValue("");
    expect(JSON.parse(fetchMock.mock.calls[0][1]!.body as string)).toEqual({
      senha_atual: "segredo123",
      nova_senha: "novasenha1",
    });
  });

  it("senha atual errada mostra o erro da API", async () => {
    mockFetch(resposta(400, { detail: "Senha atual incorreta." }));
    render(<ConfiguracoesPage />);

    preencher("errada123", "novasenha1");
    fireEvent.click(botao("ALTERAR SENHA"));

    expect(await screen.findByText("Senha atual incorreta.")).toBeInTheDocument();
  });
});
