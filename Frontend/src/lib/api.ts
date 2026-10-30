const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "medstock_token";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown, message?: string) {
    super(message ?? `Erro ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
  }
}

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Quando false, não envia o header Authorization (ex.: login). */
  auth?: boolean;
}

export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { body, auth = true, headers, ...rest } = options;
  const finalHeaders = new Headers(headers);

  if (body !== undefined && !(body instanceof FormData)) {
    finalHeaders.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = getToken();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }

  const resposta = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: finalHeaders,
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });

  const texto = await resposta.text();
  const dados = texto ? safeJson(texto) : null;

  if (!resposta.ok) {
    const detail = (dados as { detail?: unknown } | null)?.detail ?? dados;
    throw new ApiError(resposta.status, detail, typeof detail === "string" ? detail : undefined);
  }
  return dados as T;
}

function safeJson(texto: string): unknown {
  try {
    return JSON.parse(texto);
  } catch {
    return texto;
  }
}

/** Monta a query string ("?a=1&b=2") ignorando valores vazios. */
type ValorQuery = string | number | boolean | null | undefined;

/** Monta "?a=1&b=2". Listas viram o parâmetro repetido: setor=UTI&setor=Farmácia. */
function montarQuery(params: Record<string, ValorQuery | ValorQuery[]>): string {
  const busca = new URLSearchParams();
  for (const [chave, valor] of Object.entries(params)) {
    for (const v of Array.isArray(valor) ? valor : [valor]) {
      if (v !== undefined && v !== null && v !== "") busca.append(chave, String(v));
    }
  }
  const texto = busca.toString();
  return texto ? `?${texto}` : "";
}

/**
 * Download de arquivo (PDF/XLSX). Não usa apiFetch porque a resposta é binária:
 * apiFetch lê a resposta como texto/JSON, o que corromperia o arquivo.
 */
export async function baixarArquivo(path: string): Promise<Blob> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const resposta = await fetch(`${BASE_URL}${path}`, { headers });
  if (!resposta.ok) {
    const texto = await resposta.text();
    const dados = texto ? safeJson(texto) : null;
    const detail = (dados as { detail?: unknown } | null)?.detail ?? dados;
    throw new ApiError(resposta.status, detail, typeof detail === "string" ? detail : undefined);
  }
  return resposta.blob();
}

/**
 * Abre o "salvar arquivo" do navegador. O nome é montado no front porque o back
 * não expõe o header Content-Disposition via CORS (front e API são origens diferentes).
 */
export function salvarArquivo(blob: Blob, nomeArquivo: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = nomeArquivo;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

// Tipos comuns

export interface TokenResponse {
  access_token: string;
  token_type?: string;
}

export interface MensagemResponse { mensagem: string; }

/** Resposta das rotas que disparam processamento em segundo plano (HTTP 202). */
export interface DetalheResponse { detail: string; }

/** Envelope das respostas paginadas do back (schemas/comuns.py → Pagina). */
export interface Pagina<T> {
  itens: T[];
  total: number;
  pagina: number;
  tamanho: number;
}

// Sistema

// GET - /health  (público)
export function verificarSaude(): Promise<{ status: string; database?: string }> {
  return apiFetch<{ status: string; database?: string }>("/health", { auth: false });
}

// Autenticação

// POST - /auth/login
export async function login(email: string, senha: string): Promise<TokenResponse> {
  const token = await apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    auth: false,
    body: { email, senha },
  });
  setToken(token.access_token);
  return token;
}

// POST - /auth/definir-senha
export async function definirSenha(token: string, senha: string): Promise<MensagemResponse> {
  return apiFetch<MensagemResponse>("/auth/definir-senha", {
    method: "POST",
    auth: false,
    body: { token, senha },
  });
}

// POST - /auth/esqueci-senha
export async function esqueciSenha(email: string): Promise<MensagemResponse> {
  return apiFetch<MensagemResponse>("/auth/esqueci-senha", {
    method: "POST",
    auth: false,
    body: { email },
  });
}

// POST - /auth/redefinir-senha
export async function redefinirSenha(token: string, senha: string): Promise<MensagemResponse> {
  return apiFetch<MensagemResponse>("/auth/redefinir-senha", {
    method: "POST",
    auth: false,
    body: { token, senha },
  });
}

// POST - /auth/reenviar-ativacao
export async function reenviarAtivacao(email: string): Promise<MensagemResponse> {
  return apiFetch<MensagemResponse>("/auth/reenviar-ativacao", {
    method: "POST",
    auth: false,
    body: { email },
  });
}

export function logout(): void {
  setToken(null);
}

// Usuários

export interface UsuarioResponse {
  id: number;
  nome: string;
  email: string;
  perfil: string;
  ativo: boolean;
}

export interface UsuarioCreate {
  nome: string;
  email: string;
  senha: string;
  perfil: "admin" | "usuario";
}

export interface UsuarioUpdate {
  nome?: string;
  email?: string;
  senha?: string;
  perfil?: "admin" | "usuario";
  ativo?: boolean;
}

// GET - /usuarios/me
export function usuarioLogado(): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>("/usuarios/me");
}

// PATCH - /usuarios/me  (o próprio usuário; trocar o e-mail exige senha_atual)
export interface MeuPerfilUpdate {
  nome?: string;
  email?: string;
  senha_atual?: string;
}
export function atualizarMeuPerfil(dados: MeuPerfilUpdate): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>("/usuarios/me", { method: "PATCH", body: dados });
}

// POST - /usuarios/me/senha  (nova_senha: mínimo de 8 caracteres)
export function trocarMinhaSenha(senha_atual: string, nova_senha: string): Promise<MensagemResponse> {
  return apiFetch<MensagemResponse>("/usuarios/me/senha", {
    method: "POST",
    body: { senha_atual, nova_senha },
  });
}

// GET - /usuarios/listar/usuarios  (admin)
export function listarUsuarios(): Promise<UsuarioResponse[]> {
  return apiFetch<UsuarioResponse[]>("/usuarios/listar/usuarios");
}

// GET - /usuarios/buscar/usuario/{usuario_id}  (admin)
export function buscarUsuario(usuarioId: number): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>(`/usuarios/buscar/usuario/${usuarioId}`);
}

// POST - /usuarios/criar/usuario  (admin)
export function criarUsuario(dados: UsuarioCreate): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>("/usuarios/criar/usuario", { method: "POST", body: dados });
}

// PATCH - /usuarios/atualizar/usuario/{usuario_id}  (admin)
export function atualizarUsuario(id: number, dados: UsuarioUpdate): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>(`/usuarios/atualizar/usuario/${id}`, { method: "PATCH", body: dados });
}

// DELETE - /usuarios/desativar/usuario/{usuario_id}  (admin)
export function desativarUsuario(usuarioId: number): Promise<UsuarioResponse> {
  return apiFetch<UsuarioResponse>(`/usuarios/desativar/usuario/${usuarioId}`, {
    method: "DELETE",
  });
}

// Empresa  (todas as rotas, exceto enviar solicitação, são do super admin)

export interface EmpresaCreate {
  nome: string
  cnpj?: string | null
  email_responsavel: string
  nome_responsavel: string
  endereco: string
  cidade: string
  uf: string
}

// PATCH = atualização parcial: no back todos os campos são Optional.
export interface EmpresaUpdate {
  nome?: string
  cnpj?: string
  email_responsavel?: string
  nome_responsavel?: string
  ativa?: boolean
  endereco?: string
  uf?: string
  cidade?: string
}

export interface EmpresaResponse {
  id: number
  nome: string
  cnpj: string | null
  email_responsavel: string
  nome_responsavel: string
  ativa: boolean
  endereco: string
  uf: string
  cidade: string
  criado_em: string // datas chegam como texto ISO no JSON
}

export interface SolicitacaoCreate {
  nome_responsavel: string;
  email: string;
  nome_hospital: string;
  // ATENÇÃO: o back ainda NÃO tem cnpj em SolicitacaoCreate, então hoje este
  // campo é enviado mas descartado. Precisa ser incluído no back para ser salvo.
  cnpj?: string;
  endereco: string;
  uf: string;
  cidade: string;
}

export interface SolicitacaoResponse {
  id: number;
  nome_responsavel: string;
  email: string;
  nome_hospital: string;
  endereco: string;
  uf: string;
  cidade: string;
  status: string;
  criado_em: string;
}

// GET - /empresas/listar/empresas
export function listarEmpresas(): Promise<EmpresaResponse[]> {
  return apiFetch<EmpresaResponse[]>("/empresas/listar/empresas");
}

// GET - /empresas/buscar/empresa/{empresa_id}
export function buscarEmpresa(empresaId: number): Promise<EmpresaResponse> {
  return apiFetch<EmpresaResponse>(`/empresas/buscar/empresa/${empresaId}`);
}

// POST - /empresas/criar/empresa
export function criarEmpresa(dados: EmpresaCreate): Promise<EmpresaResponse> {
  return apiFetch<EmpresaResponse>("/empresas/criar/empresa", { method: "POST", body: dados });
}

// PATCH - /empresas/atualizar/empresa/{empresa_id}
export function atualizarEmpresa(id: number, dados: EmpresaUpdate): Promise<EmpresaResponse> {
  return apiFetch<EmpresaResponse>(`/empresas/atualizar/empresa/${id}`, { method: "PATCH", body: dados });
}

// PATCH - /empresas/desativar/empresa/{empresa_id}  (sem corpo: o back só lê o id)
export function desativarEmpresa(empresaId: number): Promise<EmpresaResponse> {
  return apiFetch<EmpresaResponse>(`/empresas/desativar/empresa/${empresaId}`, { method: "PATCH" });
}

// POST - /empresas/enviar/solicitacao  (público, com rate limit)
export function enviarSolicitacao(dados: SolicitacaoCreate): Promise<SolicitacaoResponse> {
  return apiFetch<SolicitacaoResponse>("/empresas/enviar/solicitacao", {
    method: "POST",
    auth: false,
    body: dados,
  });
}

// GET - /empresas/solicitacoes/pendentes
export function listarSolicitacoesPendentes(): Promise<SolicitacaoResponse[]> {
  return apiFetch<SolicitacaoResponse[]>("/empresas/solicitacoes/pendentes");
}

// PATCH - /empresas/solicitacoes/{solicitacao_id}  (aprovar cria empresa + admin e envia e-mail)
export function atualizarSolicitacao(
  solicitacaoId: number,
  status: "aprovado" | "rejeitado",
): Promise<SolicitacaoResponse> {
  return apiFetch<SolicitacaoResponse>(`/empresas/solicitacoes/${solicitacaoId}`, {
    method: "PATCH",
    body: { status },
  });
}

// Importações

export interface ImportacaoResponse {
  id: number;
  nome_arquivo: string;
  tipo: string; // "csv" | "excel" | "api"
  status: string; // "processando" | "concluido" | "erro"
  modo: ModoImportacao;
  total_registros: number;
  registros_validos: number;
  registros_invalidos: number;
  erros: string[] | null;
  criado_em: string;
  concluido_em: string | null;
}

/**
 * "incremental": só acrescenta as linhas do arquivo.
 * "completa": ao concluir, substitui toda a base de consumo do hospital por este arquivo.
 */
export type ModoImportacao = "incremental" | "completa";

// POST - /importacoes/upload  (admin; multipart com os campos "arquivo" e "modo"; processa em segundo plano)
export function uploadImportacao(arquivo: File, modo: ModoImportacao = "incremental"): Promise<ImportacaoResponse> {
  const formData = new FormData();
  formData.append("arquivo", arquivo);
  formData.append("modo", modo);
  return apiFetch<ImportacaoResponse>("/importacoes/upload", {
    method: "POST",
    body: formData,
  });
}

// GET - /importacoes/  (importações da empresa do usuário logado, mais recentes primeiro)
export function listarImportacoes(): Promise<ImportacaoResponse[]> {
  return apiFetch<ImportacaoResponse[]>("/importacoes/");
}

// GET - /importacoes/{importacao_id}
export function buscarImportacao(importacaoId: number): Promise<ImportacaoResponse> {
  return apiFetch<ImportacaoResponse>(`/importacoes/${importacaoId}`);
}

// Integração via API  (o sistema do hospital envia o consumo com o cabeçalho X-API-Key)

export interface ChaveIntegracaoStatus {
  prefixo: string; // início da chave, para identificá-la
  criado_em: string;
  ultimo_uso_em: string | null;
}

/** A chave completa só vem na geração — depois disso não dá para consultá-la. */
export interface ChaveIntegracaoGerada extends ChaveIntegracaoStatus {
  chave: string;
}

// GET - /integracoes/chave  (admin; null se não houver chave ativa)
export function consultarChaveIntegracao(): Promise<ChaveIntegracaoStatus | null> {
  return apiFetch<ChaveIntegracaoStatus | null>("/integracoes/chave");
}

// POST - /integracoes/chave  (admin; a chave anterior deixa de funcionar)
export function gerarChaveIntegracao(): Promise<ChaveIntegracaoGerada> {
  return apiFetch<ChaveIntegracaoGerada>("/integracoes/chave", { method: "POST" });
}

// DELETE - /integracoes/chave  (admin)
export function revogarChaveIntegracao(): Promise<void> {
  return apiFetch<void>("/integracoes/chave", { method: "DELETE" });
}

/** URL base da API, para montar o exemplo de chamada na tela. */
export const URL_API = BASE_URL;

// Itens

export interface ItemResponse {
  id: number;
  codigo_item: string;
  descricao_item: string;
  unidade_medida: string | null;
  grupo_material: string | null;
  subgrupo_material: string | null;
  classe_material: string | null;
  ativo: boolean;
  classe_abc: string | null;
}

export interface ItemDetalheResponse extends ItemResponse {
  meses_de_historico: number;
}

export type FiltrosItens = {
  busca?: string;
  classe_abc?: string;
  grupo_material?: string;
  subgrupo_material?: string;
  classe_material?: string;
  pagina?: number;
  tamanho?: number; // máx. 200
};

// GET - /itens/  (paginado)
export function listarItens(filtros: FiltrosItens = {}): Promise<Pagina<ItemResponse>> {
  return apiFetch<Pagina<ItemResponse>>(`/itens/${montarQuery(filtros)}`);
}

// GET - /itens/{item_id}
export function buscarItem(itemId: number): Promise<ItemDetalheResponse> {
  return apiFetch<ItemDetalheResponse>(`/itens/${itemId}`);
}

// Consumos

export interface ConsumoResponse {
  id: number;
  item_id: number;
  data: string;
  quantidade: number;
  valor: number;
  setor: string | null; // setor = centro de custo
}

/** Um ponto da série MENSAL agregada de um item (base dos gráficos). */
export interface PontoSerie {
  periodo: string;
  quantidade_total: number;
  valor_total: number;
}

export type FiltrosConsumos = {
  item_id?: number;
  data_inicio?: string; // "AAAA-MM-DD"
  data_fim?: string; // "AAAA-MM-DD"
  setor?: string;
  pagina?: number;
  tamanho?: number; // máx. 200
};

// GET - /consumos/  (paginado; para os consumos de um item, passe item_id)
export function listarConsumos(filtros: FiltrosConsumos = {}): Promise<Pagina<ConsumoResponse>> {
  return apiFetch<Pagina<ConsumoResponse>>(`/consumos/${montarQuery(filtros)}`);
}

// GET - /consumos/serie/{item_id}
export function serieConsumo(itemId: number): Promise<PontoSerie[]> {
  return apiFetch<PontoSerie[]>(`/consumos/serie/${itemId}`);
}

// Previsões

export interface ModeloTreinadoResponse {
  id: number;
  algoritmo: string;
  rmse: number | null;
  mae: number | null;
  mape: number | null;
  ativo: boolean;
  treinado_em: string;
}

export interface PrevisaoResponse {
  id: number;
  item_id: number;
  modelo_id: number;
  periodo: string;
  quantidade_prevista: number;
  intervalo_inferior: number | null;
  intervalo_superior: number | null;
}

export type FiltrosPrevisoes = {
  item_id?: number;
  periodo_inicio?: string; // "AAAA-MM-DD"
  periodo_fim?: string; // "AAAA-MM-DD"
  classe_abc?: string;
  pagina?: number;
  tamanho?: number; // máx. 200
};

export interface ItemOmitidoResponse {
  item_id: number;
  meses_disponiveis: number;
  motivo: string;
}

export interface StatusTreinoResponse {
  em_andamento: boolean;
  ultimo_modelo: ModeloTreinadoResponse | null;
}

export interface PontoHistoricoMensal {
  periodo: string; // 1º dia do mês, "AAAA-MM-DD"
  quantidade: number;
}

export interface PrevisaoMensalDetalhe {
  item_id: number;
  algoritmo: string | null; // escolhido para o item no treino; null sem modelo treinado
  mae: number | null;
  rmse: number | null;
  mape: number | null;
  historico: PontoHistoricoMensal[];
  previsoes: PrevisaoResponse[];
}

export interface ResumoPrevisaoItem {
  item_id: number;
  algoritmo: string; // escolhido para o item no treino
  mae: number | null;
  mape: number | null;
  previsoes: PrevisaoResponse[]; // os meses do horizonte, em ordem
  total: number;
}

export interface ResumoPrevisoesResponse {
  referencia: string | null; // último mês com dados; a previsão começa no seguinte
  treinado_em: string | null;
  itens: ResumoPrevisaoItem[];
}

export interface ResumoDiarioItem {
  item_id: number;
  metodo: string; // "croston_sba" | "media_movel_sazonal"
  base: string;
  proximo_dia: number;
  sete_dias: number;
  quinze_dias: number;
  trinta_dias: number;
}

export interface PontoDiario {
  data: string;
  quantidade_prevista: number;
}

export interface HorizontesDiarios {
  proximo_dia: number;
  sete_dias: number;
  quinze_dias: number;
  trinta_dias: number;
}

export interface PrevisaoDiariaDetalhe {
  item_id: number;
  metodo: string;
  base: string;
  horizontes: HorizontesDiarios;
  dias: PontoDiario[];
}

export interface IntermitenciaItemResponse {
  item_id: number;
  dias_totais: number;
  dias_com_demanda: number;
  densidade: number;
  adi: number | null;
  cv2: number | null;
  classe: string; // "suave" | "intermitente" | "erratico" | "lumpy" | "sem_dados"
  adequado_diario: boolean;
}

export interface ResumoIntermitencia {
  total_itens: number;
  por_classe: Record<string, number>;
  itens_adequados_ao_diario: number;
  percentual_adequado_ao_diario: number;
}

export interface AnaliseIntermitenciaResponse {
  resumo: ResumoIntermitencia;
  itens: IntermitenciaItemResponse[];
}

// POST - /previsoes/treinar  (admin; 202, roda em segundo plano; 409 se já houver treino)
export function treinarPrevisoes(): Promise<DetalheResponse> {
  return apiFetch<DetalheResponse>("/previsoes/treinar", { method: "POST" });
}

// GET - /previsoes/modelos
export function listarModelos(): Promise<ModeloTreinadoResponse[]> {
  return apiFetch<ModeloTreinadoResponse[]>("/previsoes/modelos");
}

// POST - /previsoes/modelos/{modelo_id}/ativar  (admin)
export function ativarModelo(modeloId: number): Promise<ModeloTreinadoResponse> {
  return apiFetch<ModeloTreinadoResponse>(`/previsoes/modelos/${modeloId}/ativar`, { method: "POST" });
}

// GET - /previsoes/  (previsões mensais, paginado)
export function listarPrevisoes(filtros: FiltrosPrevisoes = {}): Promise<Pagina<PrevisaoResponse>> {
  return apiFetch<Pagina<PrevisaoResponse>>(`/previsoes/${montarQuery(filtros)}`);
}

// GET - /previsoes/resumo  (previsões do modelo ativo agrupadas por item)
export function resumoPrevisoes(): Promise<ResumoPrevisoesResponse> {
  return apiFetch<ResumoPrevisoesResponse>("/previsoes/resumo");
}

// GET - /previsoes/mensal/{item_id}  (histórico + próximos meses do modelo ativo; 404 sem consumo)
export function detalheMensal(itemId: number): Promise<PrevisaoMensalDetalhe> {
  return apiFetch<PrevisaoMensalDetalhe>(`/previsoes/mensal/${itemId}`);
}

// GET - /previsoes/itens-omitidos
export function listarItensOmitidos(): Promise<ItemOmitidoResponse[]> {
  return apiFetch<ItemOmitidoResponse[]>("/previsoes/itens-omitidos");
}

// GET - /previsoes/status-treino  (admin)
export function statusTreino(): Promise<StatusTreinoResponse> {
  return apiFetch<StatusTreinoResponse>("/previsoes/status-treino");
}

// POST - /previsoes/diaria/gerar  (admin; 202, roda em segundo plano; 409 se já estiver gerando)
export function gerarPrevisaoDiaria(): Promise<DetalheResponse> {
  return apiFetch<DetalheResponse>("/previsoes/diaria/gerar", { method: "POST" });
}

// GET - /previsoes/diaria/resumo
export function resumoDiario(itemId?: number): Promise<ResumoDiarioItem[]> {
  return apiFetch<ResumoDiarioItem[]>(`/previsoes/diaria/resumo${montarQuery({ item_id: itemId })}`);
}

// GET - /previsoes/diaria/{item_id}  (404 se o item não tiver previsão diária)
export function detalheDiario(itemId: number): Promise<PrevisaoDiariaDetalhe> {
  return apiFetch<PrevisaoDiariaDetalhe>(`/previsoes/diaria/${itemId}`);
}

// GET - /previsoes/analise-intermitencia
export function analiseIntermitencia(): Promise<AnaliseIntermitenciaResponse> {
  return apiFetch<AnaliseIntermitenciaResponse>("/previsoes/analise-intermitencia");
}

// Dashboard

export interface KpisResponse {
  total_itens_ativos: number;
  valor_total_consumido: number;
  numero_importacoes: number;
  itens_classe_a: number;
  cobertura_previsao: number; // % do valor consumido (todo o histórico) de itens com previsão diária
}

/** Espelha ResumoResponse do back. */
export interface ResumoDashboardResponse {
  possui_dados: boolean;
  kpis: KpisResponse;
  ultima_importacao: string | null;
}

export interface PontoMensal {
  periodo: string;
  quantidade_total: number;
  valor_total: number;
}

export interface ConsumoSetor {
  setor: string | null;
  quantidade_total: number;
  valor_total: number;
}

/**
 * Filtros aceitos pelas rotas do dashboard. Competência = mês ("AAAA-MM-01").
 * Os demais aceitam vários valores (lista vazia ou ausente = sem filtro).
 */
export type FiltrosDashboard = {
  data_inicio?: string;
  data_fim?: string;
  item_id?: number[];
  grupo_material?: string[];
  subgrupo_material?: string[];
  classe_material?: string[];
  setor?: string[];
};

/** Uma combinação existente de grupo / subgrupo / classe do material. */
export interface HierarquiaMaterial {
  grupo_material: string | null;
  subgrupo_material: string | null;
  classe_material: string | null;
}

/** Material com seus atributos (usado na cascata dos filtros). */
export interface MaterialFiltro extends HierarquiaMaterial {
  id: number;
  codigo_item: string;
  descricao_item: string;
}

export interface OpcoesFiltroResponse {
  hierarquia: HierarquiaMaterial[];
  materiais: MaterialFiltro[];
  setores: string[];
  periodo_inicio: string | null;
  periodo_fim: string | null;
}

export interface DistribuicaoABC {
  classe: string;
  quantidade_itens: number;
  valor_total: number;
}

export interface ItemRanking {
  item_id: number;
  codigo_item: string;
  descricao_item: string;
  quantidade_total: number;
  valor_total: number;
}

// GET - /dashboard/resumo
export function resumoDashboard(): Promise<ResumoDashboardResponse> {
  return apiFetch<ResumoDashboardResponse>("/dashboard/resumo");
}

// GET - /dashboard/opcoes-filtro  (valores para popular os filtros)
export function opcoesFiltro(): Promise<OpcoesFiltroResponse> {
  return apiFetch<OpcoesFiltroResponse>("/dashboard/opcoes-filtro");
}

// GET - /dashboard/consumo-mensal
// Sem competência nos filtros: os `meses` (1 a 60) que terminam no último mês com dados.
export function consumoMensal(meses = 12, filtros: FiltrosDashboard = {}): Promise<PontoMensal[]> {
  return apiFetch<PontoMensal[]>(`/dashboard/consumo-mensal${montarQuery({ meses, ...filtros })}`);
}

// GET - /dashboard/consumo-por-setor
export function consumoSetor(filtros: FiltrosDashboard = {}): Promise<ConsumoSetor[]> {
  return apiFetch<ConsumoSetor[]>(`/dashboard/consumo-por-setor${montarQuery(filtros)}`);
}

/** Parcela do consumo (no filtro) de itens com previsão diária gerada. */
export interface CoberturaPrevisao {
  itens_consumidos: number;
  itens_com_previsao: number;
  valor_total: number;
  valor_coberto: number;
  percentual_valor: number; // meta: 80%
  percentual_itens: number;
}

// GET - /dashboard/cobertura-previsao
export function coberturaPrevisao(filtros: FiltrosDashboard = {}): Promise<CoberturaPrevisao> {
  return apiFetch<CoberturaPrevisao>(`/dashboard/cobertura-previsao${montarQuery(filtros)}`);
}

/** Previsão do próximo mês pelo modelo mensal ativo (a previsão é por material: setor e competência não se aplicam). */
export interface PrevisaoProximoMes {
  mes: string | null; // 1º dia do mês previsto; null sem modelo treinado
  quantidade_prevista: number;
  valor_estimado: number; // quantidade prevista x preço médio histórico de cada material
  itens_com_previsao: number;
}

// GET - /dashboard/previsao-proximo-mes
export function previsaoProximoMes(filtros: FiltrosDashboard = {}): Promise<PrevisaoProximoMes> {
  return apiFetch<PrevisaoProximoMes>(`/dashboard/previsao-proximo-mes${montarQuery(filtros)}`);
}

// GET - /dashboard/classificacao-abc  (nº de itens distintos e valor por classe)
export function classificacaoAbc(filtros: FiltrosDashboard = {}): Promise<DistribuicaoABC[]> {
  return apiFetch<DistribuicaoABC[]>(`/dashboard/classificacao-abc${montarQuery(filtros)}`);
}

// GET - /dashboard/abc-xyz  (contagem de itens por classe combinada, ex.: { "AX": 12 })
export function matrizAbcXyz(): Promise<Record<string, number>> {
  return apiFetch<Record<string, number>>("/dashboard/abc-xyz");
}

// GET - /dashboard/top-itens  (limite: 1 a 50)
export function topItens(
  limite = 10,
  por: "valor" | "quantidade" = "valor",
  filtros: FiltrosDashboard = {},
): Promise<ItemRanking[]> {
  return apiFetch<ItemRanking[]>(`/dashboard/top-itens${montarQuery({ limite, por, ...filtros })}`);
}

// Exportações  (devolvem ARQUIVO, não JSON → use salvarArquivo(blob, "nome.ext"))

export type FormatoExportacao = "pdf" | "xlsx";

// GET - /exportacoes/previsoes
export function exportarPrevisoes(formato: FormatoExportacao = "pdf"): Promise<Blob> {
  return baixarArquivo(`/exportacoes/previsoes${montarQuery({ formato })}`);
}

// GET - /exportacoes/consumo
export function exportarConsumo(
  formato: FormatoExportacao = "pdf",
  periodo: { data_inicio?: string; data_fim?: string } = {},
): Promise<Blob> {
  return baixarArquivo(`/exportacoes/consumo${montarQuery({ formato, ...periodo })}`);
}

