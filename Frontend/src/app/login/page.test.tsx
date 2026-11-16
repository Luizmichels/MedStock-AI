import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "@/app/login/page";
import { getToken } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import { mockFetch, resposta, tokenFalso } from "@/test/fetch";

const navegacao = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navegacao.replace, push: navegacao.replace }),
  useSearchParams: () => new URLSearchParams(),
}));

beforeEach(() => navegacao.replace.mockReset());

function abrirLogin() {
  render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>,
  );
}

const campo = (autocomplete: string) =>
  document.querySelector<HTMLInputElement>(`input[autocomplete="${autocomplete}"]`)!;

async function entrarCom(email: string, senha: string) {
  await userEvent.type(campo("username"), email);
  await userEvent.type(campo("current-password"), senha);
  await userEvent.click(screen.getByRole("button", { name: "ENTRAR" }));
}

describe("Login", () => {
  it("exige e-mail e senha antes de chamar a API", async () => {
    const fetchMock = mockFetch(resposta(200, {}));
    abrirLogin();

    await userEvent.click(await screen.findByRole("button", { name: "ENTRAR" }));

    expect(screen.getByText("Por favor, coloque o seu e-mail")).toBeInTheDocument();
    expect(screen.getByText("Por favor, coloque sua senha")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("admin entra e vai para o dashboard", async () => {
    const token = tokenFalso({ sub: "12", perfil: "admin", empresa_id: 3 });
    mockFetch(
      resposta(200, { access_token: token }),
      resposta(200, { id: 12, nome: "Ana", email: "ana@hospital.org.br", perfil: "admin", ativo: true }),
    );
    abrirLogin();

    await entrarCom("ana@hospital.org.br", "segredo123");

    await vi.waitFor(() => expect(navegacao.replace).toHaveBeenCalledWith("/dashboard"));
    expect(getToken()).toBe(token);
  });

  it("super admin vai para a gestão de hospitais", async () => {
    const token = tokenFalso({ sub: "1", perfil: "super_admin" });
    mockFetch(resposta(200, { access_token: token }), resposta(200, { id: 1, nome: "Root", email: "r@x.com" }));
    abrirLogin();

    await entrarCom("r@x.com", "segredo123");

    await vi.waitFor(() => expect(navegacao.replace).toHaveBeenCalledWith("/hospitais"));
  });

  it("credenciais erradas mostram aviso e não navegam", async () => {
    mockFetch(resposta(401, { detail: "Credenciais inválidas" }));
    abrirLogin();

    await entrarCom("ana@hospital.org.br", "errada");

    expect(await screen.findByText("Credenciais inválidas.")).toBeInTheDocument();
    expect(navegacao.replace).not.toHaveBeenCalled();
  });

  it("falha de rede mostra a mensagem genérica", async () => {
    mockFetch(resposta(500, {}));
    abrirLogin();

    await entrarCom("ana@hospital.org.br", "segredo123");

    expect(await screen.findByText("Não foi possível entrar. Tente novamente.")).toBeInTheDocument();
  });

  it("'Mostrar' revela a senha e os pontos trocam o slide", async () => {
    mockFetch(resposta(200, {}));
    abrirLogin();

    await userEvent.click(await screen.findByRole("button", { name: "Mostrar" }));
    expect(campo("current-password")).toHaveAttribute("type", "text");

    await userEvent.click(screen.getByRole("button", { name: "Slide 2" }));
    expect(screen.getByText("Foque no que pesa no orçamento")).toBeInTheDocument();
  });

  it("'Esqueceu a senha?' abre a recuperação com o e-mail já digitado", async () => {
    mockFetch(resposta(200, {}));
    abrirLogin();

    await userEvent.type(campo("username"), "ana@hospital.org.br");
    await userEvent.click(screen.getByRole("button", { name: "Esqueceu a senha?" }));

    expect(screen.getByPlaceholderText("nome@hospital.org.br")).toHaveValue("ana@hospital.org.br");
    await userEvent.click(screen.getByRole("button", { name: /Voltar ao login/ }));
    expect(screen.getByRole("button", { name: "ENTRAR" })).toBeInTheDocument();
  });
});

describe("Solicitação de acesso", () => {
  async function abrirSolicitacao() {
    abrirLogin();
    await userEvent.click(await screen.findByRole("button", { name: "Solicitar acesso" }));
  }

  function preencherTudo() {
    const valores: Record<string, string> = {
      "Nome completo": "Ana Souza",
      "nome@hospital.org.br": "ana@hospital.org.br",
      "Hospital, clínica ou rede": "Hospital Central",
      "00.000.000/0000-00": "12.345.678/0001-90",
      "Rua, número, bairro": "Rua A, 10, Centro",
    };
    for (const [placeholder, valor] of Object.entries(valores)) {
      fireEvent.change(screen.getByPlaceholderText(placeholder), { target: { value: valor } });
    }
    const [cidade, uf] = Array.from(document.querySelectorAll<HTMLInputElement>("input:not([placeholder])"));
    fireEvent.change(cidade, { target: { value: "Joinville" } });
    fireEvent.change(uf, { target: { value: "sc" } });
  }

  it("campos vazios não enviam nada", async () => {
    const fetchMock = mockFetch(resposta(200, {}));
    await abrirSolicitacao();

    await userEvent.click(screen.getByRole("button", { name: "ENVIAR SOLICITAÇÃO" }));

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("envia os dados (UF em maiúsculas) e mostra a confirmação", async () => {
    const fetchMock = mockFetch(resposta(201, { id: 1, status: "pendente" }));
    await abrirSolicitacao();

    preencherTudo();
    await userEvent.click(screen.getByRole("button", { name: "ENVIAR SOLICITAÇÃO" }));

    expect(await screen.findByText("Solicitação enviada")).toBeInTheDocument();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/empresas\/enviar\/solicitacao$/);
    expect(JSON.parse(init!.body as string)).toMatchObject({ uf: "SC", cidade: "Joinville", nome_hospital: "Hospital Central" });

    await userEvent.click(screen.getByRole("button", { name: "VOLTAR AO LOGIN" }));
    expect(screen.getByRole("button", { name: "ENTRAR" })).toBeInTheDocument();
  });

  it.each([
    [429, /Muitas tentativas/],
    [422, /Verifique os dados/],
    [500, /Não foi possível enviar a solicitação/],
  ])("erro %i mostra o aviso certo", async (status, aviso) => {
    mockFetch(resposta(status, { detail: "erro" }));
    await abrirSolicitacao();

    preencherTudo();
    await userEvent.click(screen.getByRole("button", { name: "ENVIAR SOLICITAÇÃO" }));

    expect(await screen.findByText(aviso)).toBeInTheDocument();
  });
});
