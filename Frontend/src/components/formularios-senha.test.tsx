import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import EsqueciSenha from "@/components/EsqueciSenha";
import NovaSenhaForm from "@/components/NovaSenhaForm";
import { mockFetch, resposta } from "@/test/fetch";

const navegacao = vi.hoisted(() => ({ push: vi.fn(), token: "token-do-email" as string | null }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: navegacao.push, replace: navegacao.push }),
  useSearchParams: () => new URLSearchParams(navegacao.token ? { token: navegacao.token } : {}),
}));

beforeEach(() => {
  navegacao.push.mockReset();
  navegacao.token = "token-do-email";
});

describe("EsqueciSenha", () => {
  const campoEmail = () => screen.getByPlaceholderText("nome@hospital.org.br");

  it("recusa e-mail inválido sem chamar a API", async () => {
    const fetchMock = mockFetch(resposta(200, { mensagem: "ok" }));
    render(<EsqueciSenha />);

    await userEvent.type(campoEmail(), "ana@hospital");
    await userEvent.click(screen.getByRole("button", { name: "ENVIAR LINK" }));

    expect(screen.getByText("Informe um e-mail válido.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("chama as duas rotas (redefinir e reativar) e mostra a confirmação", async () => {
    const fetchMock = mockFetch(resposta(200, { mensagem: "ok" }));
    render(<EsqueciSenha emailInicial="  ana@hospital.org.br " />);

    await userEvent.click(screen.getByRole("button", { name: "ENVIAR LINK" }));

    expect(await screen.findByText("Verifique seu e-mail")).toBeInTheDocument();
    const urls = fetchMock.mock.calls.map(([url]) => url);
    expect(urls.some((u) => u.endsWith("/auth/esqueci-senha"))).toBe(true);
    expect(urls.some((u) => u.endsWith("/auth/reenviar-ativacao"))).toBe(true);
    expect(JSON.parse(fetchMock.mock.calls[0][1]!.body as string)).toEqual({ email: "ana@hospital.org.br" });
    expect(screen.getByRole("button", { name: /Reenviar em 0:60/ })).toBeDisabled();
  });

  it("o reenvio libera depois de 60 segundos", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockFetch(resposta(200, { mensagem: "ok" }));
    render(<EsqueciSenha emailInicial="ana@hospital.org.br" />);

    fireEvent.click(screen.getByRole("button", { name: "ENVIAR LINK" }));
    await screen.findByText("Verifique seu e-mail");
    for (let i = 0; i < 60; i++) {
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });
    }

    expect(screen.getByRole("button", { name: "Reenviar e-mail" })).toBeEnabled();
    vi.useRealTimers();
  });

  it("muitas tentativas (429) mostra aviso específico", async () => {
    mockFetch(resposta(429, { detail: "Too Many Requests" }));
    render(<EsqueciSenha emailInicial="ana@hospital.org.br" />);

    await userEvent.click(screen.getByRole("button", { name: "ENVIAR LINK" }));

    expect(await screen.findByText(/Muitas tentativas/)).toBeInTheDocument();
  });

  it("outro erro mostra a mensagem genérica", async () => {
    mockFetch(resposta(500, { detail: "erro" }));
    render(<EsqueciSenha emailInicial="ana@hospital.org.br" />);

    await userEvent.click(screen.getByRole("button", { name: "ENVIAR LINK" }));

    expect(await screen.findByText(/Não foi possível enviar o e-mail/)).toBeInTheDocument();
  });

  it("'Usar outro e-mail' volta ao formulário e 'Voltar' chama o callback", async () => {
    const onVoltar = vi.fn();
    mockFetch(resposta(200, { mensagem: "ok" }));
    render(<EsqueciSenha emailInicial="ana@hospital.org.br" onVoltar={onVoltar} />);

    await userEvent.click(screen.getByRole("button", { name: "ENVIAR LINK" }));
    await userEvent.click(await screen.findByRole("button", { name: "Usar outro e-mail" }));
    expect(screen.getByRole("button", { name: "ENVIAR LINK" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Voltar ao login/ }));
    expect(onVoltar).toHaveBeenCalled();
  });
});

describe("NovaSenhaForm", () => {
  function preencher(senha: string, confirma = senha) {
    const [campoSenha, campoConfirma] = document.querySelectorAll<HTMLInputElement>('input[autocomplete="new-password"]');
    fireEvent.change(campoSenha, { target: { value: senha } });
    fireEvent.change(campoConfirma, { target: { value: confirma } });
  }

  it("valida o tamanho mínimo e a confirmação antes de enviar", async () => {
    const fetchMock = mockFetch(resposta(200, { mensagem: "ok" }));
    render(<NovaSenhaForm modo="definir" />);

    preencher("curta");
    await userEvent.click(screen.getByRole("button", { name: "CRIAR SENHA" }));
    expect(screen.getByText("A senha deve ter pelo menos 8 caracteres.")).toBeInTheDocument();

    preencher("senhaforte1", "senhaforte2");
    await userEvent.click(screen.getByRole("button", { name: "CRIAR SENHA" }));
    expect(screen.getByText("As senhas não conferem.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("definir: envia token e senha e mostra o sucesso", async () => {
    const fetchMock = mockFetch(resposta(200, { mensagem: "ok" }));
    render(<NovaSenhaForm modo="definir" />);

    preencher("senhaforte1");
    await userEvent.click(screen.getByRole("button", { name: "CRIAR SENHA" }));

    expect(await screen.findByText("Senha criada! Sua conta está ativa.")).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/auth\/definir-senha$/);
    expect(JSON.parse(init!.body as string)).toEqual({ token: "token-do-email", senha: "senhaforte1" });

    await userEvent.click(screen.getByRole("button", { name: "IR PARA O LOGIN" }));
    expect(navegacao.push).toHaveBeenCalledWith("/login");
  });

  it("redefinir: usa a rota de redefinição (Enter também envia)", async () => {
    const fetchMock = mockFetch(resposta(200, { mensagem: "ok" }));
    render(<NovaSenhaForm modo="redefinir" />);

    preencher("senhaforte1");
    const [, campoConfirma] = document.querySelectorAll('input[autocomplete="new-password"]');
    fireEvent.keyDown(campoConfirma, { key: "Enter" });

    expect(await screen.findByText("Senha redefinida com sucesso.")).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/auth\/redefinir-senha$/);
  });

  it("mostrar/ocultar alterna o tipo do campo", async () => {
    render(<NovaSenhaForm modo="definir" />);
    const campo = document.querySelector('input[autocomplete="new-password"]')!;
    expect(campo).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: "Mostrar" }));
    expect(campo).toHaveAttribute("type", "text");
  });

  it("link expirado (401) troca para o pedido de novo link", async () => {
    mockFetch(resposta(401, { detail: "Token inválido ou expirado" }));
    render(<NovaSenhaForm modo="definir" />);

    preencher("senhaforte1");
    await userEvent.click(screen.getByRole("button", { name: "CRIAR SENHA" }));

    expect(await screen.findByText("Link inválido ou expirado")).toBeInTheDocument();
  });

  it("conta já ativa (400) avisa e leva ao login", async () => {
    mockFetch(resposta(400, { detail: "Conta já ativa" }));
    render(<NovaSenhaForm modo="definir" />);

    preencher("senhaforte1");
    await userEvent.click(screen.getByRole("button", { name: "CRIAR SENHA" }));

    expect(await screen.findByText("Esta conta já está ativa.")).toBeInTheDocument();
  });

  it("erro inesperado mantém o formulário com aviso", async () => {
    mockFetch(resposta(500, { detail: "erro" }));
    render(<NovaSenhaForm modo="definir" />);

    preencher("senhaforte1");
    await userEvent.click(screen.getByRole("button", { name: "CRIAR SENHA" }));

    await waitFor(() =>
      expect(screen.getByText("Não foi possível salvar a senha. Tente novamente.")).toBeInTheDocument(),
    );
  });

  it("sem token no link, vai direto para o pedido de novo link", async () => {
    navegacao.token = null;
    render(<NovaSenhaForm modo="definir" />);

    expect(screen.getByText("Link inválido ou expirado")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Voltar ao login/ }));
    expect(navegacao.push).toHaveBeenCalledWith("/login");
  });
});
