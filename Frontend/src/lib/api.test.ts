import { describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { mockFetch, resposta } from "@/test/fetch";

const BASE = api.URL_API;

/** URL, método e corpo da n-ésima chamada ao fetch. */
function chamada(fetchMock: ReturnType<typeof mockFetch>, n = 0) {
  const [url, init] = fetchMock.mock.calls[n];
  const headers = new Headers(init?.headers);
  return { url, metodo: init?.method ?? "GET", headers, corpo: init?.body };
}

describe("token", () => {
  it("guarda, lê e apaga o token no localStorage", () => {
    expect(api.getToken()).toBeNull();
    api.setToken("abc");
    expect(api.getToken()).toBe("abc");
    api.logout();
    expect(api.getToken()).toBeNull();
  });

  it("não quebra se o localStorage estiver bloqueado", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("bloqueado");
    });
    expect(api.getToken()).toBeNull();
    expect(() => api.setToken("abc")).not.toThrow();
  });
});

describe("apiFetch", () => {
  it("envia JSON e o token Bearer, e devolve o corpo da resposta", async () => {
    api.setToken("tk-123");
    const fetchMock = mockFetch(resposta(200, { ok: true }));

    const dados = await api.apiFetch("/teste", { method: "POST", body: { a: 1 } });

    const c = chamada(fetchMock);
    expect(dados).toEqual({ ok: true });
    expect(c.url).toBe(`${BASE}/teste`);
    expect(c.metodo).toBe("POST");
    expect(c.headers.get("Authorization")).toBe("Bearer tk-123");
    expect(c.headers.get("Content-Type")).toBe("application/json");
    expect(c.corpo).toBe('{"a":1}');
  });

  it("com auth: false, não manda o token", async () => {
    api.setToken("tk-123");
    const fetchMock = mockFetch(resposta(200, {}));
    await api.apiFetch("/publico", { auth: false });
    expect(chamada(fetchMock).headers.has("Authorization")).toBe(false);
  });

  it("FormData vai sem Content-Type (o navegador define o boundary)", async () => {
    const fetchMock = mockFetch(resposta(202, { id: 1 }));
    const arquivo = new File(["codigo;quantidade"], "consumo.csv", { type: "text/csv" });

    await api.uploadImportacao(arquivo, "completa");

    const c = chamada(fetchMock);
    expect(c.url).toBe(`${BASE}/importacoes/upload`);
    expect(c.headers.has("Content-Type")).toBe(false);
    const form = c.corpo as FormData;
    expect((form.get("arquivo") as File).name).toBe("consumo.csv");
    expect(form.get("modo")).toBe("completa");
  });

  it("resposta vazia (204) vira null", async () => {
    mockFetch(resposta(204));
    await expect(api.revogarChaveIntegracao()).resolves.toBeNull();
  });

  it("erro da API vira ApiError com status e detail", async () => {
    mockFetch(resposta(409, { detail: "Já existe um treino em andamento." }));

    const erro = await api.treinarPrevisoes().catch((e) => e);

    expect(erro).toBeInstanceOf(api.ApiError);
    expect(erro.status).toBe(409);
    expect(erro.detail).toBe("Já existe um treino em andamento.");
    expect(erro.message).toBe("Já existe um treino em andamento.");
  });

  it("erro com corpo que não é JSON mantém o texto como detail", async () => {
    mockFetch(resposta(502, "Bad Gateway"));
    const erro = await api.verificarSaude().catch((e) => e);
    expect(erro.status).toBe(502);
    expect(erro.detail).toBe("Bad Gateway");
  });

  it("erro de validação (422) guarda a lista de erros e usa a mensagem genérica", async () => {
    const detalhes = [{ loc: ["body", "email"], msg: "inválido" }];
    mockFetch(resposta(422, { detail: detalhes }));
    const erro = await api.criarUsuario({} as api.UsuarioCreate).catch((e) => e);
    expect(erro.detail).toEqual(detalhes);
    expect(erro.message).toBe("Erro 422");
  });
});

describe("login", () => {
  it("guarda o token recebido", async () => {
    const fetchMock = mockFetch(resposta(200, { access_token: "novo-token", token_type: "bearer" }));

    await api.login("ana@hospital.org.br", "segredo123");

    const c = chamada(fetchMock);
    expect(c.url).toBe(`${BASE}/auth/login`);
    expect(c.headers.has("Authorization")).toBe(false);
    expect(JSON.parse(c.corpo as string)).toEqual({ email: "ana@hospital.org.br", senha: "segredo123" });
    expect(api.getToken()).toBe("novo-token");
  });

  it("credencial errada não guarda token", async () => {
    mockFetch(resposta(401, { detail: "Credenciais inválidas" }));
    await expect(api.login("ana@hospital.org.br", "errada")).rejects.toBeInstanceOf(api.ApiError);
    expect(api.getToken()).toBeNull();
  });
});

describe("rotas da API", () => {
  // [descrição, chamada, método, caminho esperado]
  const casos: [string, () => Promise<unknown>, string, string][] = [
    ["definirSenha", () => api.definirSenha("t", "s"), "POST", "/auth/definir-senha"],
    ["esqueciSenha", () => api.esqueciSenha("a@b.com"), "POST", "/auth/esqueci-senha"],
    ["redefinirSenha", () => api.redefinirSenha("t", "s"), "POST", "/auth/redefinir-senha"],
    ["reenviarAtivacao", () => api.reenviarAtivacao("a@b.com"), "POST", "/auth/reenviar-ativacao"],
    ["usuarioLogado", () => api.usuarioLogado(), "GET", "/usuarios/me"],
    ["atualizarMeuPerfil", () => api.atualizarMeuPerfil({} as api.MeuPerfilUpdate), "PATCH", "/usuarios/me"],
    ["trocarMinhaSenha", () => api.trocarMinhaSenha("a", "b"), "POST", "/usuarios/me/senha"],
    ["listarUsuarios", () => api.listarUsuarios(), "GET", "/usuarios/listar/usuarios"],
    ["buscarUsuario", () => api.buscarUsuario(7), "GET", "/usuarios/buscar/usuario/7"],
    ["criarUsuario", () => api.criarUsuario({} as api.UsuarioCreate), "POST", "/usuarios/criar/usuario"],
    ["atualizarUsuario", () => api.atualizarUsuario(7, {} as api.UsuarioUpdate), "PATCH", "/usuarios/atualizar/usuario/7"],
    ["desativarUsuario", () => api.desativarUsuario(7), "DELETE", "/usuarios/desativar/usuario/7"],
    ["listarEmpresas", () => api.listarEmpresas(), "GET", "/empresas/listar/empresas"],
    ["buscarEmpresa", () => api.buscarEmpresa(3), "GET", "/empresas/buscar/empresa/3"],
    ["criarEmpresa", () => api.criarEmpresa({} as api.EmpresaCreate), "POST", "/empresas/criar/empresa"],
    ["atualizarEmpresa", () => api.atualizarEmpresa(3, {} as api.EmpresaUpdate), "PATCH", "/empresas/atualizar/empresa/3"],
    ["desativarEmpresa", () => api.desativarEmpresa(3), "PATCH", "/empresas/desativar/empresa/3"],
    ["enviarSolicitacao", () => api.enviarSolicitacao({} as api.SolicitacaoCreate), "POST", "/empresas/enviar/solicitacao"],
    ["listarSolicitacoesPendentes", () => api.listarSolicitacoesPendentes(), "GET", "/empresas/solicitacoes/pendentes"],
    ["atualizarSolicitacao", () => api.atualizarSolicitacao(9, "aprovado"), "PATCH", "/empresas/solicitacoes/9"],
    ["listarImportacoes", () => api.listarImportacoes(), "GET", "/importacoes/"],
    ["buscarImportacao", () => api.buscarImportacao(5), "GET", "/importacoes/5"],
    ["consultarChaveIntegracao", () => api.consultarChaveIntegracao(), "GET", "/integracoes/chave"],
    ["gerarChaveIntegracao", () => api.gerarChaveIntegracao(), "POST", "/integracoes/chave"],
    ["revogarChaveIntegracao", () => api.revogarChaveIntegracao(), "DELETE", "/integracoes/chave"],
    ["listarItens", () => api.listarItens({ busca: "luva", pagina: 2 }), "GET", "/itens/?busca=luva&pagina=2"],
    ["buscarItem", () => api.buscarItem(4), "GET", "/itens/4"],
    ["listarConsumos", () => api.listarConsumos({ item_id: 4, setor: "" }), "GET", "/consumos/?item_id=4"],
    ["serieConsumo", () => api.serieConsumo(4), "GET", "/consumos/serie/4"],
    ["treinarPrevisoes", () => api.treinarPrevisoes(), "POST", "/previsoes/treinar"],
    ["listarModelos", () => api.listarModelos(), "GET", "/previsoes/modelos"],
    ["ativarModelo", () => api.ativarModelo(2), "POST", "/previsoes/modelos/2/ativar"],
    ["listarPrevisoes", () => api.listarPrevisoes({ classe_abc: "A" }), "GET", "/previsoes/?classe_abc=A"],
    ["resumoPrevisoes", () => api.resumoPrevisoes(), "GET", "/previsoes/resumo"],
    ["detalheMensal", () => api.detalheMensal(4), "GET", "/previsoes/mensal/4"],
    ["listarItensOmitidos", () => api.listarItensOmitidos(), "GET", "/previsoes/itens-omitidos"],
    ["statusTreino", () => api.statusTreino(), "GET", "/previsoes/status-treino"],
    ["gerarPrevisaoDiaria", () => api.gerarPrevisaoDiaria(), "POST", "/previsoes/diaria/gerar"],
    ["resumoDiario sem item", () => api.resumoDiario(), "GET", "/previsoes/diaria/resumo"],
    ["resumoDiario com item", () => api.resumoDiario(4), "GET", "/previsoes/diaria/resumo?item_id=4"],
    ["detalheDiario", () => api.detalheDiario(4), "GET", "/previsoes/diaria/4"],
    ["analiseIntermitencia", () => api.analiseIntermitencia(), "GET", "/previsoes/analise-intermitencia"],
    ["resumoDashboard", () => api.resumoDashboard(), "GET", "/dashboard/resumo"],
    ["opcoesFiltro", () => api.opcoesFiltro(), "GET", "/dashboard/opcoes-filtro"],
    ["consumoMensal", () => api.consumoMensal(), "GET", "/dashboard/consumo-mensal?meses=12"],
    [
      "consumoSetor com listas",
      () => api.consumoSetor({ setor: ["UTI", "Farmácia"] }),
      "GET",
      "/dashboard/consumo-por-setor?setor=UTI&setor=Farm%C3%A1cia",
    ],
    ["coberturaPrevisao", () => api.coberturaPrevisao(), "GET", "/dashboard/cobertura-previsao"],
    ["previsaoProximoMes", () => api.previsaoProximoMes(), "GET", "/dashboard/previsao-proximo-mes"],
    ["classificacaoAbc", () => api.classificacaoAbc(), "GET", "/dashboard/classificacao-abc"],
    ["matrizAbcXyz", () => api.matrizAbcXyz(), "GET", "/dashboard/abc-xyz"],
    ["topItens", () => api.topItens(5, "quantidade"), "GET", "/dashboard/top-itens?limite=5&por=quantidade"],
  ];

  it.each(casos)("%s", async (_nome, chamar, metodo, caminho) => {
    const fetchMock = mockFetch(resposta(200, {}));
    await chamar();
    const c = chamada(fetchMock);
    expect(c.metodo).toBe(metodo);
    expect(c.url).toBe(`${BASE}${caminho}`);
  });
});

describe("exportações (arquivo binário)", () => {
  it("baixa o arquivo como Blob, com o token", async () => {
    api.setToken("tk-123");
    const fetchMock = mockFetch(new Response("%PDF-1.7", { status: 200 }));

    const blob = await api.exportarConsumo("xlsx", { data_inicio: "2026-01-01" });

    const c = chamada(fetchMock);
    expect(c.url).toBe(`${BASE}/exportacoes/consumo?formato=xlsx&data_inicio=2026-01-01`);
    expect(c.headers.get("Authorization")).toBe("Bearer tk-123");
    expect(blob.size).toBe("%PDF-1.7".length);
  });

  it("erro no download vira ApiError", async () => {
    mockFetch(resposta(404, { detail: "Sem previsões para exportar." }));
    const erro = await api.exportarPrevisoes().catch((e) => e);
    expect(erro).toBeInstanceOf(api.ApiError);
    expect(erro.detail).toBe("Sem previsões para exportar.");
  });

  it("salvarArquivo cria um link de download e o remove", () => {
    vi.useFakeTimers();
    const criar = vi.fn(() => "blob:fake");
    const revogar = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL: criar, revokeObjectURL: revogar });
    const clique = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    api.salvarArquivo(new Blob(["x"]), "previsoes.pdf");

    expect(clique).toHaveBeenCalledOnce();
    expect(document.querySelector("a[download]")).toBeNull();
    vi.runAllTimers();
    expect(revogar).toHaveBeenCalledWith("blob:fake");
    vi.useRealTimers();
  });
});
