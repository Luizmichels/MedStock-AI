"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BarraFiltros,
  CamposMaterial,
  MultiSelecao,
  SELECAO_VAZIA,
  SelecaoMaterial,
  contarSelecao,
} from "@/components/Filtros";
import PageHeader from "@/components/PageHeader";
import SemDadosImportados from "@/components/SemDadosImportados";
import Toast, { useToast } from "@/components/Toast";
import {
  ItemResponse,
  MaterialFiltro,
  ModeloTreinadoResponse,
  PrevisaoDiariaDetalhe,
  ResumoDiarioItem,
  detalheDiario,
  gerarPrevisaoDiaria,
  listarConsumos,
  listarItens,
  listarModelos,
  resumoDashboard,
  resumoDiario,
  statusTreino,
  treinarPrevisoes,
} from "@/lib/api";
import { papel, useAuth } from "@/lib/auth";
import { mensagemErro } from "@/lib/erros";
import { esperar, fmtData, fmtDataHora, fmtDiaMes, fmtNumero, isoData, lerData, somarDias } from "@/lib/formato";

type Horizonte = 7 | 15 | 30;
type Estado = "carregando" | "semDados" | "semPrevisoes" | "pronto" | "erro";

const HORIZONTES: Horizonte[] = [7, 15, 30];
const DIAS_HISTORICO = 45;
const POR_PAGINA = 25;

const OPCOES_ABC = ["A", "B", "C"].map((c) => ({ valor: c, rotulo: `Curva ${c}` }));

/** Lista vazia = sem filtro; senão o valor precisa estar na lista. */
function contem<T>(lista: T[], valor: T | null | undefined): boolean {
  return lista.length === 0 || (valor != null && lista.includes(valor));
}

const CLASSES: Record<string, [string, string]> = {
  A: ["#1F5FA0", "#fff"],
  B: ["#4AA8E0", "#fff"],
  C: ["#CFE6F7", "#1F5FA0"],
};

function totalNoHorizonte(r: ResumoDiarioItem, h: Horizonte): number {
  return h === 7 ? r.sete_dias : h === 15 ? r.quinze_dias : r.trinta_dias;
}

/** Busca todos os itens (a rota é paginada, no máximo 200 por página). */
async function carregarTodosItens(): Promise<Map<number, ItemResponse>> {
  const primeira = await listarItens({ tamanho: 200, pagina: 1 });
  const paginas = Math.ceil(primeira.total / 200);
  const resto = await Promise.all(
    Array.from({ length: Math.max(paginas - 1, 0) }, (_, i) => listarItens({ tamanho: 200, pagina: i + 2 })),
  );
  const mapa = new Map<number, ItemResponse>();
  for (const p of [primeira, ...resto]) for (const item of p.itens) mapa.set(item.id, item);
  return mapa;
}

/** Consumo diário do item (somado entre setores) nos últimos DIAS_HISTORICO dias até a base. */
async function carregarHistorico(itemId: number, base: Date): Promise<number[]> {
  const inicio = somarDias(base, -(DIAS_HISTORICO - 1));
  const porDia = new Map<string, number>();
  for (let pagina = 1; ; pagina++) {
    const p = await listarConsumos({
      item_id: itemId,
      data_inicio: isoData(inicio),
      data_fim: isoData(base),
      tamanho: 200,
      pagina,
    });
    for (const c of p.itens) porDia.set(c.data, (porDia.get(c.data) ?? 0) + c.quantidade);
    if (pagina * 200 >= p.total || p.itens.length === 0) break;
  }
  return Array.from({ length: DIAS_HISTORICO }, (_, i) => porDia.get(isoData(somarDias(inicio, i))) ?? 0);
}

/** "Impressão digital" do resumo, para perceber quando a geração diária terminou. */
function assinatura(res: ResumoDiarioItem[]): string {
  return `${res.length}|${res[0]?.base ?? ""}|${res.slice(0, 5).map((r) => r.trinta_dias).join(",")}`;
}

export default function PrevisoesPage() {
  const { usuario } = useAuth();
  const isAdmin = papel(usuario?.perfil ?? "usuario") === "admin";
  const { mensagem, notificar } = useToast();
  // Precisa voltar a true no corpo do efeito: em desenvolvimento o StrictMode
  // monta, desmonta e remonta o componente.
  const montado = useRef(true);
  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  const [estado, setEstado] = useState<Estado>("carregando");
  const [resumo, setResumo] = useState<ResumoDiarioItem[]>([]);
  const [itens, setItens] = useState<Map<number, ItemResponse>>(new Map());
  const [modelo, setModelo] = useState<ModeloTreinadoResponse | null>(null);

  const [horizonte, setHorizonte] = useState<Horizonte>(30);
  const [material, setMaterial] = useState<SelecaoMaterial>(SELECAO_VAZIA);
  const [abc, setAbc] = useState<string[]>([]);
  const [pagina, setPagina] = useState(1);
  const [selecionado, setSelecionado] = useState<number | null>(null);

  const [detalhe, setDetalhe] = useState<PrevisaoDiariaDetalhe | null>(null);
  const [historico, setHistorico] = useState<number[] | null>(null);
  const [carregandoGrafico, setCarregandoGrafico] = useState(false);

  const [gerando, setGerando] = useState(false);
  const [treinando, setTreinando] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const [res, dash, modelos] = await Promise.all([resumoDiario(), resumoDashboard(), listarModelos()]);
      if (!montado.current) return;
      setModelo(modelos.find((m) => m.ativo) ?? modelos[0] ?? null);
      if (!dash.possui_dados) {
        setEstado("semDados");
        return;
      }
      if (res.length === 0) {
        setResumo([]);
        setEstado("semPrevisoes");
        return;
      }
      const mapa = await carregarTodosItens();
      if (!montado.current) return;
      setItens(mapa);
      setResumo(res);
      setEstado("pronto");
    } catch {
      if (montado.current) setEstado("erro");
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const linhas = useMemo(() => {
    return resumo
      .map((r) => ({ r, item: itens.get(r.item_id) }))
      .filter(
        ({ r, item }) =>
          contem(material.materiais, r.item_id) &&
          contem(material.grupos, item?.grupo_material) &&
          contem(material.subgrupos, item?.subgrupo_material) &&
          contem(material.classes, item?.classe_material) &&
          contem(abc, item?.classe_abc),
      )
      .sort((a, b) => totalNoHorizonte(b.r, horizonte) - totalNoHorizonte(a.r, horizonte));
  }, [resumo, itens, material, abc, horizonte]);

  useEffect(() => setPagina(1), [material, abc, horizonte]);

  // Materiais do filtro: só os que têm previsão, com os atributos para a cascata.
  const materiaisFiltro = useMemo<MaterialFiltro[]>(
    () =>
      resumo
        .map((r) => itens.get(r.item_id))
        .filter((i): i is ItemResponse => i !== undefined)
        .map((i) => ({
          id: i.id,
          codigo_item: i.codigo_item,
          descricao_item: i.descricao_item,
          grupo_material: i.grupo_material,
          subgrupo_material: i.subgrupo_material,
          classe_material: i.classe_material,
        }))
        .sort((a, b) => a.descricao_item.localeCompare(b.descricao_item, "pt-BR")),
    [resumo, itens],
  );

  // Mantém sempre um material selecionado entre os visíveis.
  useEffect(() => {
    if (linhas.length === 0) return;
    if (selecionado == null || !linhas.some((l) => l.r.item_id === selecionado)) {
      setSelecionado(linhas[0].r.item_id);
    }
  }, [linhas, selecionado]);

  // Gráfico do material selecionado: histórico diário + previsão diária.
  useEffect(() => {
    if (selecionado == null) return;
    const r = resumo.find((x) => x.item_id === selecionado);
    if (!r) return;
    let ativo = true;
    setCarregandoGrafico(true);
    Promise.all([detalheDiario(selecionado), carregarHistorico(selecionado, lerData(r.base))])
      .then(([d, h]) => {
        if (!ativo) return;
        setDetalhe(d);
        setHistorico(h);
      })
      .catch(() => {
        if (!ativo) return;
        setDetalhe(null);
        setHistorico(null);
      })
      .finally(() => ativo && setCarregandoGrafico(false));
    return () => {
      ativo = false;
    };
  }, [selecionado, resumo]);

  async function gerar() {
    setGerando(true);
    try {
      const antes = assinatura(resumo);
      await gerarPrevisaoDiaria();
      notificar("Gerando as previsões diárias… a tela atualiza sozinha ao terminar.");
      // Não há rota de status para a geração diária: consulta até o resultado mudar (máx. ~1 min).
      for (let i = 0; i < 20 && montado.current; i++) {
        await esperar(3000);
        const res = await resumoDiario();
        if (res.length > 0 && assinatura(res) !== antes) break;
      }
      if (!montado.current) return;
      await carregar();
      notificar("Previsões diárias atualizadas.");
    } catch (e) {
      notificar(mensagemErro(e, "Não foi possível gerar as previsões."));
    } finally {
      if (montado.current) setGerando(false);
    }
  }

  async function treinar() {
    setTreinando(true);
    try {
      const anterior = modelo?.id ?? null;
      await treinarPrevisoes();
      notificar("Treinamento do modelo mensal iniciado. Pode levar alguns minutos.");
      for (let i = 0; i < 200 && montado.current; i++) {
        await esperar(3000);
        const st = await statusTreino();
        if (st.em_andamento) continue;
        setModelo(st.ultimo_modelo);
        notificar(
          st.ultimo_modelo && st.ultimo_modelo.id !== anterior
            ? "Modelo mensal treinado com sucesso."
            : "O treino terminou sem gerar um modelo novo (há itens com histórico suficiente?).",
        );
        break;
      }
    } catch (e) {
      notificar(mensagemErro(e, "Não foi possível treinar o modelo."));
    } finally {
      if (montado.current) setTreinando(false);
    }
  }

  const acoesAdmin = isAdmin && (estado === "pronto" || estado === "semPrevisoes") && (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={treinar}
        disabled={treinando}
        className="h-9 rounded-full border border-brand bg-white px-4 text-[13px] font-bold text-brand-800 transition hover:bg-surface-sky disabled:cursor-not-allowed disabled:opacity-60"
      >
        {treinando ? "Treinando…" : "Treinar modelo mensal"}
      </button>
      <button
        onClick={gerar}
        disabled={gerando}
        className="h-9 rounded-full bg-brand px-4 text-[13px] font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {gerando ? "Gerando…" : "Gerar previsões diárias"}
      </button>
    </div>
  );

  const selecionadoLinha = linhas.find((l) => l.r.item_id === selecionado) ?? null;
  const inicioPagina = (pagina - 1) * POR_PAGINA;
  const paginaAtual = linhas.slice(inicioPagina, inicioPagina + POR_PAGINA);
  const totalPaginas = Math.max(Math.ceil(linhas.length / POR_PAGINA), 1);

  return (
    <>
      <PageHeader
        title="Previsões"
        subtitle="Consumo previsto para os próximos 7, 15 ou 30 dias, por material"
        acoes={acoesAdmin || undefined}
      />

      {estado === "carregando" && (
        <div className="previa-card px-6 py-12 text-center text-sm text-muted">Carregando previsões…</div>
      )}
      {estado === "erro" && (
        <div className="previa-card px-6 py-12 text-center text-sm text-[#C23B4E]">
          Não foi possível carregar as previsões. Tente novamente em instantes.
        </div>
      )}
      {estado === "semDados" && (
        <SemDadosImportados descricao="As previsões aparecem depois da primeira importação de consumo. Importe o histórico e gere as previsões diárias para ver os horizontes de 7, 15 e 30 dias." />
      )}
      {estado === "semPrevisoes" && (
        <div className="previa-card flex flex-col items-center gap-2.5 px-6 py-12 text-center">
          <h2 className="text-lg font-bold text-navy">As previsões ainda não foram geradas</h2>
          <p className="max-w-[460px] text-sm leading-relaxed text-muted">
            {isAdmin
              ? "Os dados de consumo já estão na base. Gere as previsões diárias para ver os horizontes de 7, 15 e 30 dias por material."
              : "Os dados já foram importados, mas o administrador ainda não gerou as previsões."}
          </p>
          {isAdmin && (
            <button onClick={gerar} disabled={gerando} className="previa-btn mt-3">
              {gerando ? "GERANDO…" : "GERAR PREVISÕES AGORA"}
            </button>
          )}
        </div>
      )}

      {estado === "pronto" && (
        <>
          {/* Filtros */}
          <BarraFiltros>
            <CamposMaterial materiais={materiaisFiltro} valor={material} onChange={setMaterial} />
            <MultiSelecao rotulo="Curva ABC" largura="min-w-[120px] flex-[0.7]" opcoes={OPCOES_ABC} selecionados={abc} onChange={setAbc} />
            <div className="relative flex h-11 flex-none items-center rounded-md border border-[#B9C6D4] bg-white px-[3px]">
              <span className="pointer-events-none absolute -top-[9px] left-2 bg-white px-1 text-[11.5px] font-semibold leading-[18px] text-muted">
                Horizonte
              </span>
              {HORIZONTES.map((h) => (
                <button
                  key={h}
                  onClick={() => setHorizonte(h)}
                  className="h-[34px] rounded px-3.5 text-[13px] font-bold transition"
                  style={{
                    background: horizonte === h ? "#0A2540" : "transparent",
                    color: horizonte === h ? "#fff" : "#5B6B7E",
                  }}
                >
                  {h} dias
                </button>
              ))}
            </div>
            {(contarSelecao(material) > 0 || abc.length > 0) && (
              <button
                onClick={() => {
                  setMaterial(SELECAO_VAZIA);
                  setAbc([]);
                }}
                className="h-11 px-1 text-[13px] font-bold text-brand-800 hover:underline"
              >
                Limpar filtros
              </button>
            )}
            <div className="ml-auto flex items-center gap-2.5 rounded-[10px] bg-surface-panel px-3.5 py-2">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2F8FD0" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 7v5l3 2" />
              </svg>
              <div className="flex flex-col leading-snug">
                <span className="text-xs text-muted">Modelo mensal</span>
                <span className="text-[13px] font-bold text-navy">
                  {modelo ? `Treinado em ${fmtDataHora(modelo.treinado_em)}` : "Ainda não treinado"}
                </span>
                {modelo?.mae != null && (
                  <span className="text-[11.5px] text-muted-400">
                    Erro médio (MAE mediano): {fmtNumero(modelo.mae, 1)}
                  </span>
                )}
              </div>
            </div>
          </BarraFiltros>

          {/* Gráfico do material selecionado */}
          {selecionadoLinha && (
            <CartaoGrafico
              linha={selecionadoLinha}
              horizonte={horizonte}
              detalhe={detalhe}
              historico={historico}
              carregando={carregandoGrafico}
            />
          )}

          {/* Tabela */}
          <div className="previa-card overflow-hidden p-0">
            <div className="flex flex-wrap items-baseline justify-between gap-3 px-[22px] py-4">
              <h3 className="text-base font-bold">Materiais e previsões estimadas</h3>
              <span className="text-xs text-muted">
                {fmtNumero(linhas.length)} de {fmtNumero(resumo.length)} materiais · clique para ver no gráfico
              </span>
            </div>
            <div className="grid grid-cols-[minmax(220px,2.6fr)_70px_minmax(100px,1fr)_minmax(120px,1fr)_50px] gap-3 border-y border-line-200 bg-surface-panel px-[22px] py-2.5 text-xs font-bold text-muted">
              <span>Material</span>
              <span>Unid.</span>
              <span className="text-right">Média diária</span>
              <span className="text-right">Previsão {horizonte} dias</span>
              <span className="text-center">ABC</span>
            </div>
            {paginaAtual.length === 0 ? (
              <div className="px-7 py-7 text-center text-sm text-muted">Nenhum material encontrado.</div>
            ) : (
              paginaAtual.map(({ r, item }) => {
                const total = totalNoHorizonte(r, horizonte);
                const cls = item?.classe_abc ?? null;
                return (
                  <button
                    key={r.item_id}
                    onClick={() => setSelecionado(r.item_id)}
                    className="grid w-full grid-cols-[minmax(220px,2.6fr)_70px_minmax(100px,1fr)_minmax(120px,1fr)_50px] items-center gap-3 border-b border-[#F0F4F8] px-[22px] py-3 text-left text-[13px] transition hover:bg-[#F5F9FD]"
                    style={{ background: r.item_id === selecionado ? "#EAF3FB" : undefined }}
                  >
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate font-semibold">{item?.descricao_item ?? `Item ${r.item_id}`}</span>
                      <span className="font-mono text-[11px] text-muted-400">{item?.codigo_item ?? "—"}</span>
                    </span>
                    <span className="text-muted">{item?.unidade_medida || "—"}</span>
                    <span className="text-right">{fmtNumero(total / horizonte, 1)}</span>
                    <span className="text-right font-bold text-navy">{fmtNumero(total, 1)}</span>
                    <span className="flex justify-center">
                      {cls && CLASSES[cls] ? (
                        <span
                          className="grid h-6 w-6 place-items-center rounded-md text-xs font-extrabold"
                          style={{ background: CLASSES[cls][0], color: CLASSES[cls][1] }}
                        >
                          {cls}
                        </span>
                      ) : (
                        <span className="text-muted-400">—</span>
                      )}
                    </span>
                  </button>
                );
              })
            )}
            {linhas.length > POR_PAGINA && (
              <div className="flex items-center justify-between gap-3 px-[22px] py-3 text-xs text-muted">
                <span>
                  Mostrando {fmtNumero(inicioPagina + 1)}–{fmtNumero(Math.min(inicioPagina + POR_PAGINA, linhas.length))} de{" "}
                  {fmtNumero(linhas.length)}
                </span>
                <span className="flex gap-2">
                  <button
                    onClick={() => setPagina((p) => Math.max(p - 1, 1))}
                    disabled={pagina === 1}
                    className="h-8 rounded-full border border-[#CBD6E2] bg-white px-3 font-bold text-ink disabled:opacity-40"
                  >
                    Anterior
                  </button>
                  <button
                    onClick={() => setPagina((p) => Math.min(p + 1, totalPaginas))}
                    disabled={pagina === totalPaginas}
                    className="h-8 rounded-full border border-[#CBD6E2] bg-white px-3 font-bold text-ink disabled:opacity-40"
                  >
                    Próxima
                  </button>
                </span>
              </div>
            )}
          </div>
        </>
      )}

      <Toast mensagem={mensagem} />
    </>
  );
}

function CartaoGrafico({
  linha,
  horizonte,
  detalhe,
  historico,
  carregando,
}: {
  linha: { r: ResumoDiarioItem; item?: ItemResponse };
  horizonte: Horizonte;
  detalhe: PrevisaoDiariaDetalhe | null;
  historico: number[] | null;
  carregando: boolean;
}) {
  const { r, item } = linha;
  const total = totalNoHorizonte(r, horizonte);
  const unidade = item?.unidade_medida || "unid.";
  const pronto = !carregando && detalhe && historico && detalhe.item_id === r.item_id;

  return (
    <div className="previa-card px-[22px] py-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <span className="text-xs text-muted">Consumo diário · {unidade}</span>
          <h3 className="mt-0.5 truncate text-lg font-bold">{item?.descricao_item ?? `Item ${r.item_id}`}</h3>
        </div>
        <span className="pt-1 font-mono text-xs text-muted">{item?.codigo_item}</span>
      </div>

      <div className="mt-4 flex flex-wrap gap-7">
        <Estatistica rotulo={`Previsão próximos ${horizonte} dias`} valor={`${fmtNumero(total, 1)} ${unidade}`} />
        <Estatistica rotulo="Média diária prevista" valor={fmtNumero(total / horizonte, 1)} />
        <Estatistica rotulo="Último dado de consumo" valor={fmtData(r.base)} />
      </div>

      {pronto ? (
        <Grafico
          historico={historico}
          previsao={detalhe.dias.slice(0, horizonte).map((d) => d.quantidade_prevista)}
          base={lerData(r.base)}
        />
      ) : (
        <div className="mt-[18px] grid h-[300px] place-items-center text-sm text-muted">
          {carregando ? "Carregando gráfico…" : "Não foi possível carregar o gráfico deste material."}
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-5 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-[3px] w-[18px] bg-[#1F5FA0]" />
          Consumo realizado
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0 w-[18px] border-t-[3px] border-dashed border-brand" />
          Previsão
        </span>
      </div>
    </div>
  );
}

function Estatistica({ rotulo, valor, dica }: { rotulo: string; valor: string; dica?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-muted">{rotulo}</span>
      <span className="text-[22px] font-extrabold text-navy">{valor}</span>
      {dica && <span className="text-[11.5px] text-muted-400">{dica}</span>}
    </div>
  );
}

function Grafico({ historico, previsao, base }: { historico: number[]; previsao: number[]; base: Date }) {
  const nHist = historico.length;
  const n = nHist + previsao.length;
  const maximo = Math.max(...historico, ...previsao, 1) * 1.1;
  const X = (i: number) => (i / (n - 1)) * 840;
  const Y = (v: number) => 260 - (v / maximo) * 240;

  const caminhoHist = historico.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join(" ");
  const caminhoPrev =
    `M${X(nHist - 1).toFixed(1)} ${Y(historico[nHist - 1]).toFixed(1)} ` +
    previsao.map((v, k) => `L${X(nHist + k).toFixed(1)} ${Y(v).toFixed(1)}`).join(" ");
  const xBase = X(nHist - 1);

  const rotulos = Array.from({ length: n }, (_, i) => {
    const deslocamento = i - (nHist - 1);
    // Um rótulo por semana; o último dia só aparece se não colar no rótulo anterior.
    const mostrar = deslocamento % 7 === 0 || (i === n - 1 && deslocamento % 7 >= 4);
    return {
      i,
      texto: mostrar ? fmtDiaMes(somarDias(base, deslocamento)) : "",
      cor: deslocamento > 0 ? "#2F8FD0" : deslocamento === 0 ? "#0A2540" : "#8494A6",
    };
  }).filter((r) => r.texto);

  return (
    <div className="mt-[18px] flex gap-2.5">
      <div className="flex h-[280px] w-12 flex-col justify-between py-2.5 text-right text-[11px] text-muted-400">
        <span>{fmtNumero(maximo)}</span>
        <span>{fmtNumero(maximo / 2)}</span>
        <span>0</span>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <svg viewBox="0 0 840 280" preserveAspectRatio="none" className="block h-[280px] w-full" aria-hidden="true">
          <g stroke="#E4EBF2" strokeWidth="1">
            <line x1="0" y1="20" x2="840" y2="20" vectorEffect="non-scaling-stroke" />
            <line x1="0" y1="140" x2="840" y2="140" vectorEffect="non-scaling-stroke" />
            <line x1="0" y1="260" x2="840" y2="260" vectorEffect="non-scaling-stroke" />
          </g>
          <rect x={xBase} y="0" width={840 - xBase} height="280" fill="#F4F9FD" />
          <path d={caminhoHist} fill="none" stroke="#1F5FA0" strokeWidth="2.5" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          <path d={caminhoPrev} fill="none" stroke="#4AA8E0" strokeWidth="2.5" strokeDasharray="6 5" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          <line x1={xBase} y1="0" x2={xBase} y2="280" stroke="#9FB6CE" strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
        </svg>
        <div className="relative h-4">
          {rotulos.map((r) => (
            <span
              key={r.i}
              className="absolute -translate-x-1/2 whitespace-nowrap text-[10.5px]"
              style={{ left: `${(X(r.i) / 840) * 100}%`, color: r.cor }}
            >
              {r.texto}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
