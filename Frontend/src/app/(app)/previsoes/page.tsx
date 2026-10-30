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
  PrevisaoMensalDetalhe,
  ResumoPrevisaoItem,
  detalheMensal,
  listarItens,
  listarModelos,
  resumoDashboard,
  resumoPrevisoes,
  statusTreino,
  treinarPrevisoes,
} from "@/lib/api";
import { papel, useAuth } from "@/lib/auth";
import { mensagemErro } from "@/lib/erros";
import { esperar, fmtDataHora, fmtMesAno, fmtNumero } from "@/lib/formato";

type Estado = "carregando" | "semDados" | "semPrevisoes" | "pronto" | "erro";

const MESES_HISTORICO = 12;
// Meses previstos pelo modelo (o mesmo horizonte da validação no treino).
const HORIZONTE_MESES = 3;
const POR_PAGINA = 25;
// Colunas: material, curva ABC, unidade, um por mês previsto e total.
const GRADE = "grid-cols-[minmax(220px,2.4fr)_50px_60px_repeat(3,minmax(84px,1fr))_minmax(100px,1fr)]"; // 3 = HORIZONTE_MESES

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

const ROTULO_ALGORITMO: Record<string, string> = {
  sma: "Média móvel (SMA)",
  sarima: "ARIMA",
  holt_winters: "Holt-Winters",
  random_forest: "Random Forest",
  gradient_boosting: "Gradient Boosting",
};

function rotuloAlgoritmo(algoritmo: string): string {
  return ROTULO_ALGORITMO[algoritmo] ?? algoritmo;
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
  const [resumo, setResumo] = useState<ResumoPrevisaoItem[]>([]);
  const [itens, setItens] = useState<Map<number, ItemResponse>>(new Map());
  const [modelo, setModelo] = useState<ModeloTreinadoResponse | null>(null);

  const [material, setMaterial] = useState<SelecaoMaterial>(SELECAO_VAZIA);
  const [abc, setAbc] = useState<string[]>([]);
  const [pagina, setPagina] = useState(1);
  const [selecionado, setSelecionado] = useState<number | null>(null);

  const [mensal, setMensal] = useState<PrevisaoMensalDetalhe | null>(null);
  const [carregandoMensal, setCarregandoMensal] = useState(false);

  const [treinando, setTreinando] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const [res, dash, modelos] = await Promise.all([resumoPrevisoes(), resumoDashboard(), listarModelos()]);
      if (!montado.current) return;
      setModelo(modelos.find((m) => m.ativo) ?? modelos[0] ?? null);
      if (!dash.possui_dados) {
        setEstado("semDados");
        return;
      }
      if (res.itens.length === 0) {
        setResumo([]);
        setEstado("semPrevisoes");
        return;
      }
      const mapa = await carregarTodosItens();
      if (!montado.current) return;
      setItens(mapa);
      setResumo(res.itens);
      setEstado("pronto");
    } catch {
      if (montado.current) setEstado("erro");
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  // Todos os itens partem da mesma referência, então os meses são os mesmos.
  const meses = useMemo(
    () => resumo[0]?.previsoes.slice(0, HORIZONTE_MESES).map((p) => p.periodo) ?? [],
    [resumo],
  );

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
      .sort((a, b) => b.r.total - a.r.total);
  }, [resumo, itens, material, abc]);

  useEffect(() => setPagina(1), [material, abc]);

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

  // Gráfico do material selecionado: histórico mensal + previsão do modelo ativo.
  useEffect(() => {
    if (selecionado == null) return;
    let ativo = true;
    setCarregandoMensal(true);
    detalheMensal(selecionado)
      .then((d) => ativo && setMensal(d))
      .catch(() => ativo && setMensal(null))
      .finally(() => ativo && setCarregandoMensal(false));
    return () => {
      ativo = false;
    };
  }, [selecionado, resumo]);

  async function treinar() {
    setTreinando(true);
    try {
      const anterior = modelo?.id ?? null;
      await treinarPrevisoes();
      notificar("Treinando os modelos e atualizando as previsões. Pode levar alguns minutos.");
      for (let i = 0; i < 200 && montado.current; i++) {
        await esperar(3000);
        const st = await statusTreino();
        if (st.em_andamento) continue;
        setModelo(st.ultimo_modelo);
        await carregar();
        notificar(
          st.ultimo_modelo && st.ultimo_modelo.id !== anterior
            ? "Modelos treinados e previsões atualizadas."
            : "O treino terminou sem gerar um modelo novo. É preciso ter materiais com pelo menos 3 meses de histórico.",
        );
        break;
      }
    } catch (e) {
      notificar(mensagemErro(e, "Não foi possível treinar os modelos."));
    } finally {
      if (montado.current) setTreinando(false);
    }
  }

  const acoesAdmin = isAdmin && (estado === "pronto" || estado === "semPrevisoes") && (
    <button
      onClick={treinar}
      disabled={treinando}
      className="h-9 rounded-full bg-brand px-4 text-[13px] font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {treinando ? "Treinando…" : "Treinar modelos"}
    </button>
  );

  const selecionadoLinha = linhas.find((l) => l.r.item_id === selecionado) ?? null;
  const inicioPagina = (pagina - 1) * POR_PAGINA;
  const paginaAtual = linhas.slice(inicioPagina, inicioPagina + POR_PAGINA);
  const totalPaginas = Math.max(Math.ceil(linhas.length / POR_PAGINA), 1);

  return (
    <>
      <PageHeader
        title="Previsões"
        subtitle={`Consumo previsto por material para os próximos ${HORIZONTE_MESES} meses`}
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
        <SemDadosImportados descricao="As previsões aparecem depois da primeira importação de consumo. Importe o histórico e treine os modelos para ver as previsões." />
      )}
      {estado === "semPrevisoes" && (
        <div className="previa-card flex flex-col items-center gap-2.5 px-6 py-12 text-center">
          <h2 className="text-lg font-bold text-navy">As previsões ainda não foram geradas</h2>
          <p className="max-w-[460px] text-sm leading-relaxed text-muted">
            {isAdmin
              ? "Os dados de consumo já estão na base. Treine os modelos para ver a previsão dos próximos 3 meses por material."
              : "Os dados já foram importados, mas o administrador ainda não treinou os modelos."}
          </p>
          {isAdmin && (
            <button onClick={treinar} disabled={treinando} className="previa-btn mt-3">
              {treinando ? "TREINANDO…" : "TREINAR MODELOS"}
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
                <span className="text-xs text-muted">Modelos</span>
                <span className="text-[13px] font-bold text-navy">
                  {modelo ? `Treinados em ${fmtDataHora(modelo.treinado_em)}` : "Ainda não treinados"}
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
            <CartaoGrafico linha={selecionadoLinha} mensal={mensal} carregando={carregandoMensal} />
          )}

          {/* Tabela */}
          {/* Em telas estreitas a tabela rola na horizontal (senão o Total é cortado). */}
          <div className="previa-card overflow-x-auto p-0">
            <div className="flex flex-wrap items-baseline justify-between gap-3 px-[22px] py-4">
              <h3 className="text-base font-bold">Materiais e previsões estimadas</h3>
              <span className="text-xs text-muted">
                {fmtNumero(linhas.length)} de {fmtNumero(resumo.length)} materiais · clique para ver no gráfico
              </span>
            </div>
            <div className={`grid ${GRADE} gap-3 border-y border-line-200 bg-surface-panel px-[22px] py-2.5 text-xs font-bold text-muted`}>
              <span>Material</span>
              <span className="text-center">ABC</span>
              <span>Unid.</span>
              {meses.map((m) => (
                <span key={m} className="text-right">
                  {fmtMesAno(m)}
                </span>
              ))}
              <span className="text-right">Total {HORIZONTE_MESES} meses</span>
            </div>
            {paginaAtual.length === 0 ? (
              <div className="px-7 py-7 text-center text-sm text-muted">Nenhum material encontrado.</div>
            ) : (
              paginaAtual.map(({ r, item }) => {
                const cls = item?.classe_abc ?? null;
                return (
                  <button
                    key={r.item_id}
                    onClick={() => setSelecionado(r.item_id)}
                    className={`grid w-full ${GRADE} items-center gap-3 border-b border-[#F0F4F8] px-[22px] py-3 text-left text-[13px] transition hover:bg-[#F5F9FD]`}
                    style={{ background: r.item_id === selecionado ? "#EAF3FB" : undefined }}
                  >
                    <span className="flex min-w-0 flex-col">
                      <span className="truncate font-semibold">{item?.descricao_item ?? `Item ${r.item_id}`}</span>
                      <span className="font-mono text-[11px] text-muted-400">{item?.codigo_item ?? "—"}</span>
                    </span>
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
                    <span className="text-muted">{item?.unidade_medida || "—"}</span>
                    {meses.map((m) => {
                      const p = r.previsoes.find((x) => x.periodo === m);
                      return (
                        <span key={m} className="text-right">
                          {p ? fmtNumero(p.quantidade_prevista, 1) : "—"}
                        </span>
                      );
                    })}
                    <span className="text-right font-bold text-navy">{fmtNumero(r.total, 1)}</span>
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
  mensal,
  carregando,
}: {
  linha: { r: ResumoPrevisaoItem; item?: ItemResponse };
  mensal: PrevisaoMensalDetalhe | null;
  carregando: boolean;
}) {
  const { r, item } = linha;
  const unidade = item?.unidade_medida || "unid.";
  const proximo = r.previsoes[0];
  const pronto = !carregando && mensal && mensal.item_id === r.item_id;

  return (
    <div className="previa-card px-[22px] py-5">
      <div className="min-w-0">
        <span className="text-xs text-muted">
          Consumo mensal · {unidade}
          {item?.codigo_item && <span className="font-mono"> · {item.codigo_item}</span>}
        </span>
        <h3 className="mt-0.5 truncate text-lg font-bold">{item?.descricao_item ?? `Item ${r.item_id}`}</h3>
      </div>

      <div className="mt-4 flex flex-wrap gap-7">
        {proximo && (
          <Estatistica
            rotulo={`Previsão ${fmtMesAno(proximo.periodo)}`}
            valor={`${fmtNumero(proximo.quantidade_prevista, 1)} ${unidade}`}
          />
        )}
        <Estatistica rotulo={`Próximos ${r.previsoes.length} meses`} valor={fmtNumero(r.total, 1)} />
        <Estatistica rotulo="Modelo escolhido" valor={rotuloAlgoritmo(r.algoritmo)} />
        {r.mae != null && (
          <Estatistica
            rotulo="Erro médio na validação (MAE)"
            valor={`${fmtNumero(r.mae, 1)} ${unidade}`}
            dica={r.mape != null ? `MAPE ${fmtNumero(r.mape, 1)}%` : undefined}
          />
        )}
      </div>
      <p className="mt-2 text-[12px] text-muted">
        O modelo foi escolhido para este material entre 5 algoritmos, pelo menor erro ao prever até 3 meses à frente na
        validação. A faixa mostra a margem de incerteza de ±20%.
      </p>

      {pronto ? (
        <GraficoMensal
          historico={mensal.historico.slice(-MESES_HISTORICO)}
          previsoes={mensal.previsoes.slice(0, HORIZONTE_MESES)}
          unidade={unidade}
        />
      ) : (
        <div className="mt-[18px] grid h-[300px] place-items-center text-sm text-muted">
          {carregando ? "Carregando gráfico…" : "Não foi possível carregar o gráfico deste material."}
        </div>
      )}
      <Legenda faixa />
    </div>
  );
}

function Legenda({ faixa }: { faixa: boolean }) {
  return (
    <div className="mt-4 flex flex-wrap gap-5 text-xs text-muted">
      <span className="flex items-center gap-1.5">
        <span className="h-[3px] w-[18px] bg-[#1F5FA0]" />
        Consumo realizado
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-0 w-[18px] border-t-[3px] border-dashed border-brand" />
        Previsão
      </span>
      {faixa && (
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-[18px] rounded-sm bg-[#4AA8E0]/20" />
          Faixa de incerteza
        </span>
      )}
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

function GraficoMensal({
  historico,
  previsoes,
  unidade,
}: {
  historico: PrevisaoMensalDetalhe["historico"];
  previsoes: PrevisaoMensalDetalhe["previsoes"];
  unidade: string;
}) {
  const [ativo, setAtivo] = useState<number | null>(null);

  const nHist = historico.length;
  const n = nHist + previsoes.length;
  const valores = [
    ...historico.map((h) => h.quantidade),
    ...previsoes.map((p) => p.intervalo_superior ?? p.quantidade_prevista),
  ];
  const maximo = Math.max(...valores, 1) * 1.1;
  const X = (i: number) => (n > 1 ? (i / (n - 1)) * 840 : 420);
  const Y = (v: number) => 260 - (v / maximo) * 240;

  const caminhoHist = historico
    .map((h, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(h.quantidade).toFixed(1)}`)
    .join(" ");
  const ultimo = historico[nHist - 1]?.quantidade ?? 0;
  const inicio = `M${X(nHist - 1).toFixed(1)} ${Y(ultimo).toFixed(1)} `;
  const caminhoPrev =
    inicio + previsoes.map((p, k) => `L${X(nHist + k).toFixed(1)} ${Y(p.quantidade_prevista).toFixed(1)}`).join(" ");
  // Faixa: sobe pelo limite superior e volta pelo inferior, partindo do último mês real.
  const faixa =
    previsoes.length > 0
      ? inicio +
      previsoes
        .map((p, k) => `L${X(nHist + k).toFixed(1)} ${Y(p.intervalo_superior ?? p.quantidade_prevista).toFixed(1)}`)
        .join(" ") +
      " " +
      [...previsoes]
        .map((p, k) => ({ p, k }))
        .reverse()
        .map(({ p, k }) => `L${X(nHist + k).toFixed(1)} ${Y(p.intervalo_inferior ?? p.quantidade_prevista).toFixed(1)}`)
        .join(" ") +
      " Z"
      : "";
  const xBase = X(nHist - 1);

  // Um ponto por mês, para a dica ao passar o mouse.
  const pontos = [
    ...historico.map((h) => ({ periodo: h.periodo, valor: h.quantidade, previsto: false, inferior: null, superior: null })),
    ...previsoes.map((p) => ({
      periodo: p.periodo,
      valor: p.quantidade_prevista,
      previsto: true,
      inferior: p.intervalo_inferior,
      superior: p.intervalo_superior,
    })),
  ];
  const largura = n > 1 ? 840 / (n - 1) : 840; // área de captura do mouse de cada mês
  const pct = (x: number) => `${(x / 840) * 100}%`;
  const ponto = ativo != null ? pontos[ativo] : null;

  // Com muitos meses, rótulo sim/não alternado; o 1º mês previsto sempre aparece.
  const passo = n > 12 ? 2 : 1;
  const rotulos = pontos
    .map((p, i) => ({ i, periodo: p.periodo }))
    .filter(({ i }) => i === nHist || (i - nHist) % passo === 0);

  return (
    <div className="mt-[18px] flex gap-2.5">
      <div className="flex h-[280px] w-12 flex-col justify-between py-2.5 text-right text-[11px] text-muted-400">
        <span>{fmtNumero(maximo)}</span>
        <span>{fmtNumero(maximo / 2)}</span>
        <span>0</span>
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="relative h-[280px]" onMouseLeave={() => setAtivo(null)}>
          <svg viewBox="0 0 840 280" preserveAspectRatio="none" className="block h-[280px] w-full" aria-hidden="true">
            <g stroke="#E4EBF2" strokeWidth="1">
              <line x1="0" y1="20" x2="840" y2="20" vectorEffect="non-scaling-stroke" />
              <line x1="0" y1="140" x2="840" y2="140" vectorEffect="non-scaling-stroke" />
              <line x1="0" y1="260" x2="840" y2="260" vectorEffect="non-scaling-stroke" />
            </g>
            {previsoes.length > 0 && (
              <>
                <rect x={xBase} y="0" width={840 - xBase} height="280" fill="#F4F9FD" />
                <path d={faixa} fill="#4AA8E0" fillOpacity="0.18" stroke="none" />
              </>
            )}
            <path d={caminhoHist} fill="none" stroke="#1F5FA0" strokeWidth="2.5" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
            {previsoes.length > 0 && (
              <>
                <path d={caminhoPrev} fill="none" stroke="#4AA8E0" strokeWidth="2.5" strokeDasharray="6 5" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                <line x1={xBase} y1="0" x2={xBase} y2="280" stroke="#9FB6CE" strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
              </>
            )}
          </svg>

          {/* Um marcador por mês. Fica em HTML (e não no SVG) porque o SVG é
              esticado (preserveAspectRatio="none") e deformaria os círculos. */}
          {pontos.map((p, i) => (
            <div
              key={`ponto-${p.periodo}`}
              className="pointer-events-none absolute h-[9px] w-[9px] -translate-x-1/2 -translate-y-1/2 rounded-full border-2"
              style={{
                left: pct(X(i)),
                top: Y(p.valor),
                borderColor: p.previsto ? "#4AA8E0" : "#1F5FA0",
                background: p.previsto ? "#fff" : "#1F5FA0",
              }}
            />
          ))}

          {/* Áreas de captura: uma por mês, centrada no ponto. */}
          {pontos.map((p, i) => (
            <div
              key={p.periodo}
              className="absolute inset-y-0 cursor-crosshair"
              style={{ left: pct(X(i) - largura / 2), width: pct(largura) }}
              onMouseEnter={() => setAtivo(i)}
            />
          ))}

          {ponto && ativo != null && (
            <>
              <div
                className="pointer-events-none absolute inset-y-0 w-px bg-[#9FB6CE]"
                style={{ left: pct(X(ativo)) }}
              />
              <div
                className="pointer-events-none absolute h-[13px] w-[13px] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow"
                style={{ left: pct(X(ativo)), top: Y(ponto.valor), background: ponto.previsto ? "#4AA8E0" : "#1F5FA0" }}
              />
              <div
                className="pointer-events-none absolute top-2 z-10 min-w-[150px] rounded-lg bg-navy px-3 py-2 text-xs text-white shadow-lg"
                style={
                  ativo > n / 2
                    ? { right: `calc(${100 - (X(ativo) / 840) * 100}% + 10px)` }
                    : { left: `calc(${pct(X(ativo))} + 10px)` }
                }
              >
                <div className="font-bold capitalize">{fmtMesAno(ponto.periodo)}</div>
                <div className="mt-0.5 text-[#D6E7F6]">{ponto.previsto ? "Previsão" : "Consumo realizado"}</div>
                <div className="text-[15px] font-extrabold">
                  {fmtNumero(ponto.valor, 1)} <span className="text-xs font-semibold">{unidade}</span>
                </div>
                {ponto.previsto && ponto.inferior != null && ponto.superior != null && (
                  <div className="mt-0.5 text-[11px] text-[#D6E7F6]">
                    Faixa: {fmtNumero(ponto.inferior, 1)} a {fmtNumero(ponto.superior, 1)}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
        <div className="relative h-4">
          {rotulos.map(({ i, periodo }) => (
            <span
              key={periodo}
              className="absolute -translate-x-1/2 whitespace-nowrap text-[10.5px]"
              style={{ left: pct(X(i)), color: i >= nHist ? "#2F8FD0" : "#8494A6" }}
            >
              {fmtMesAno(periodo)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
