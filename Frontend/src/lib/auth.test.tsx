import { act, render, renderHook, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { getToken, setToken } from "@/lib/api";
import { AuthProvider, papel, useAuth } from "@/lib/auth";
import { mockFetch, resposta, tokenFalso } from "@/test/fetch";

const TOKEN_ADMIN = tokenFalso({ sub: "12", perfil: "admin", empresa_id: 3 });
const ME = { id: 12, nome: "Ana Souza", email: "ana@hospital.org.br", perfil: "admin", ativo: true };

/** Mostra o estado do contexto na tela, para os testes lerem. */
function Sonda() {
  const { usuario, carregando } = useAuth();
  if (carregando) return <p>carregando</p>;
  return <p>{usuario ? `${usuario.nome}|${usuario.perfil}|${usuario.empresaId}` : "anonimo"}</p>;
}

function renderizar() {
  return render(
    <AuthProvider>
      <Sonda />
    </AuthProvider>,
  );
}

describe("AuthProvider: sessão salva", () => {
  it("sem token, termina anônimo e não chama a API", async () => {
    const fetchMock = mockFetch(resposta(200, ME));
    renderizar();
    expect(await screen.findByText("anonimo")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("com token válido, completa nome e e-mail em /usuarios/me", async () => {
    setToken(TOKEN_ADMIN);
    mockFetch(resposta(200, ME));
    renderizar();
    expect(await screen.findByText("Ana Souza|admin|3")).toBeInTheDocument();
  });

  it("token expirado (401) encerra a sessão e apaga o token", async () => {
    setToken(TOKEN_ADMIN);
    mockFetch(resposta(401, { detail: "Token inválido ou expirado" }));
    renderizar();
    expect(await screen.findByText("anonimo")).toBeInTheDocument();
    expect(getToken()).toBeNull();
  });

  it("API fora do ar mantém a sessão com os dados do token", async () => {
    setToken(TOKEN_ADMIN);
    mockFetch(resposta(503, { status: "degraded" }));
    renderizar();
    expect(await screen.findByText("|admin|3")).toBeInTheDocument();
    expect(getToken()).toBe(TOKEN_ADMIN);
  });

  it("token corrompido é ignorado", async () => {
    setToken("nao-e-um-jwt");
    const fetchMock = mockFetch(resposta(200, ME));
    renderizar();
    expect(await screen.findByText("anonimo")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("useAuth: entrar, atualizar e sair", () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => <AuthProvider>{children}</AuthProvider>;

  it("entrar faz login, lê o perfil do token e completa com /usuarios/me", async () => {
    mockFetch(resposta(200, { access_token: TOKEN_ADMIN }), resposta(200, ME));
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.carregando).toBe(false));

    let usuario;
    await act(async () => {
      usuario = await result.current.entrar("ana@hospital.org.br", "segredo123");
    });

    expect(usuario).toMatchObject({ id: "12", perfil: "admin", empresaId: 3, nome: "Ana Souza" });
    expect(result.current.usuario?.nome).toBe("Ana Souza");

    act(() => result.current.atualizarUsuario({ nome: "Ana S." }));
    expect(result.current.usuario?.nome).toBe("Ana S.");

    act(() => result.current.sair());
    expect(result.current.usuario).toBeNull();
    expect(getToken()).toBeNull();
  });

  it("entrar recusa um token que não é JWT", async () => {
    mockFetch(resposta(200, { access_token: "lixo" }));
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.carregando).toBe(false));

    await expect(result.current.entrar("a@b.com", "x")).rejects.toThrow("Token inválido");
    expect(getToken()).toBeNull();
  });

  it("useAuth fora do provider explica o erro", () => {
    vi.spyOn(console, "error").mockImplementation(() => {}); // o React registra o erro esperado
    expect(() => renderHook(() => useAuth())).toThrow("dentro de <AuthProvider>");
  });
});

describe("papel", () => {
  it("traduz super_admin para o vocabulário das telas", () => {
    expect(papel("super_admin")).toBe("super");
    expect(papel("admin")).toBe("admin");
    expect(papel("usuario")).toBe("usuario");
  });
});
