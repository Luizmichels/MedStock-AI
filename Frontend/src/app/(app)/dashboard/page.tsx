"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BarraFiltros,
  CamposMaterial,
  Competencia,
  Medida,
  MultiSelecao,
  ROTULO_MEDIDA,
  SELECAO_VAZIA,
  SeletorCompetencia,
  SeletorMedida,
  SelecaoMaterial,
  contarSelecao,
} from "@/components/Filtros";
import PageHeader from "@/components/PageHeader";
import SemDadosImportados from "@/components/SemDadosImportados";
import {
  ConsumoSetor,
  DistribuicaoABC,
  FiltrosDashboard,
  KpisResponse,
  OpcoesFiltroResponse,
  PontoMensal,
  PrevisaoProximosDias,
  classificacaoAbc,
  consumoMensal,
  consumoSetor,
  previsaoProximosDias,
  opcoesFiltro,
  resumoDashboard,
} from "@/lib/api";
import {
  fmtCompacto,
  fmtCompetencia,
  fmtData,
  fmtMesAnoNumerico,
  fmtMoeda,
  fmtNumero,
  fmtQuantidade,
  mesDe,
  somarMeses,
} from "@/lib/formato";

type Estado = "carregando" | "vazio" | "comDados" | "erro";

interface Dados {
  mensal: PontoMensal[];
  /** Mesma quantidade de meses, imediatamente antes da competência escolhida. */
  anterior: PontoMensal[];
  setores: ConsumoSetor[];
  abc: DistribuicaoABC[];
  previsao: PrevisaoProximosDias;
}

/** Nº de meses do intervalo "AAAA-MM" a "AAAA-MM", contando as pontas. */
function mesesNoIntervalo(c: Competencia): number {
  const [ai, mi] = c.inicio.split("-").map(Number);
  const [af, mf] = c.fim.split("-").map(Number);
  return (af - ai) * 12 + (mf - mi) + 1;
}

/** O período de mesmo tamanho logo antes da competência (ex.: 05–09/2026 -> 12/2025–04/2026). */
function periodoAnterior(c: Competencia): Competencia {
  const n = mesesNoIntervalo(c);
  return { inicio: somarMeses(c.inicio, -n), fim: somarMeses(c.inicio, -1) };
}

/**
 * Faixas da curva ABC pelo valor acumulado (do item mais caro para o mais barato).
 * Mesmos cortes do backend (abc_service): A até 70%, B de 70% a 90%, C acima de 90%.
 */
const CLASSES: Record<string, { bg: string; fg: string; desc: string; corte: string }> = {
  A: { bg: "#1F5FA0", fg: "#fff", desc: "Alto valor · controle rigoroso e compra frequente", corte: "até 70%" },
  B: { bg: "#4AA8E0", fg: "#fff", desc: "Valor intermediário · revisão periódica", corte: "de 70% a 90%" },
  C: { bg: "#CFE6F7", fg: "#1F5FA0", desc: "Baixo valor · reposição simplificada", corte: "de 90% a 100%" },
};

/** Espera após a última mudança de filtro antes de consultar a API. */
const ATRASO_FILTRO_MS = 300;

const valorDe = (p: { valor_total: number; quantidade_total: number }, m: Medida) =>
  m === "valor" ? p.valor_total : p.quantidade_total;

/**
 * Rótulo do gráfico. Valor: abreviado (M/K) e truncado em 2 casas ("R$ 37,48 K").
 * Quantidade: número completo, sem abreviação nem "R$" ("12.161").
 */
const fmtMedida = (v: number, m: Medida) => (m === "valor" ? fmtCompacto(v, { moeda: true }) : fmtQuantidade(v));

/** Valor completo, para a dica ao passar o mouse. */
const fmtMedidaCompleta = (v: number, m: Medida) => (m === "valor" ? fmtMoeda(v) : fmtQuantidade(v));

export default function DashboardPage() {
  const [estado, setEstado] = useState<Estado>("carregando");
  const [kpis, setKpis] = useState<KpisResponse | null>(null);
  const [opcoes, setOpcoes] = useState<OpcoesFiltroResponse | null>(null);
  const [competencia, setCompetencia] = useState<Competencia | null>(null);
  const [material, setMaterial] = useState<SelecaoMaterial>(SELECAO_VAZIA);
  const [setores, setSetores] = useState<string[]>([]);
  const [dados, setDados] = useState<Dados | null>(null);
  const [carregandoDados, setCarregandoDados] = useState(false);
  const [erroDados, setErroDados] = useState(false);

  useEffect(() => {
    let ativo = true;
    (async () => {
      try {
        const resumo = await resumoDashboard();
        if (!ativo) return;
        if (!resumo.possui_dados) {
          setEstado("vazio");
          return;
        }
        const op = await opcoesFiltro();
        if (!ativo) return;
        // Competência padrão: os últimos 12 meses com dados.
        const fim = mesDe(op.periodo_fim ?? new Date().toISOString());
        const primeiro = op.periodo_inicio ? mesDe(op.periodo_inicio) : fim;
        const inicio = somarMeses(fim, -11) < primeiro ? primeiro : somarMeses(fim, -11);
        setKpis(resumo.kpis);
        setOpcoes(op);
        setCompetencia({ inicio, fim });
        setEstado("comDados");
      } catch {
        if (ativo) setEstado("erro");
      }
    })();
    return () => {
      ativo = false;
    };
  }, []);

  // Recarrega os gráficos quando a competência ou os filtros mudam, com um pequeno
  // atraso para não consultar a API a cada caixa marcada.
  const primeiraCarga = dados === null;
  useEffect(() => {
    if (estado !== "comDados" || !competencia) return;
    let ativo = true;
    const params: FiltrosDashboard = {
      data_inicio: `${competencia.inicio}-01`,
      data_fim: `${competencia.fim}-01`,
      item_id: material.materiais,
      grupo_material: material.grupos,
      subgrupo_material: material.subgrupos,
      classe_material: material.classes,
      setor: setores,
    };
    setCarregandoDados(true);
    const t = setTimeout(
      () => {
        setErroDados(false);
        const anterior = periodoAnterior(competencia);
        Promise.all([
          consumoMensal(12, params),
          consumoMensal(12, { ...params, data_inicio: `${anterior.inicio}-01`, data_fim: `${anterior.fim}-01` }),
          consumoSetor(params),
          classificacaoAbc(params),
          previsaoProximosDias(params, 30),
        ])
          .then(
            ([mensal, mensalAnterior, porSetor, abc, previsao]) =>
              ativo && setDados({ mensal, anterior: mensalAnterior, setores: porSetor, abc, previsao }),
          )
          .catch(() => ativo && setErroDados(true))
          .finally(() => ativo && setCarregandoDados(false));
      },
      primeiraCarga ? 0 : ATRASO_FILTRO_MS,
    );
    return () => {
      ativo = false;
      clearTimeout(t);
    };
    // `primeiraCarga` só decide o atraso; mudar para false não deve consultar de novo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado, competencia, material, setores]);

  const temFiltro = contarSelecao(material) > 0 || setores.length > 0;
  const opcoesSetor = useMemo(() => (opcoes?.setores ?? []).map((s) => ({ valor: s, rotulo: s })), [opcoes]);

  return (
    <>
      <PageHeader title="Dashboard" subtitle="Visão geral do consumo de insumos do hospital" />

      {estado === "carregando" && (
        <div className="previa-card px-6 py-12 text-center text-sm text-muted">Carregando…</div>
      )}
      {estado === "erro" && (
        <div className="previa-card px-6 py-12 text-center text-sm text-[#C23B4E]">
          Não foi possível carregar o dashboard. Tente novamente em instantes.
        </div>
      )}
      {estado === "vazio" && (
        <SemDadosImportados descricao="O dashboard é carregado automaticamente após a primeira importação de consumo — por arquivo CSV ou integração via API. Então aparecem os KPIs, o consumo mensal, o consumo por setor e a classificação ABC." />
      )}

      {estado === "comDados" && kpis && competencia && opcoes && (
        <>
          <BarraFiltros
            onLimpar={
              temFiltro
                ? () => {
                    setMaterial(SELECAO_VAZIA);
                    setSetores([]);
                  }
                : undefined
            }
          >
            <SeletorCompetencia
              valor={competencia}
              limiteInicio={opcoes.periodo_inicio ? mesDe(opcoes.periodo_inicio) : competencia.inicio}
              limiteFim={opcoes.periodo_fim ? mesDe(opcoes.periodo_fim) : competencia.fim}
              onChange={setCompetencia}
            />
            <CamposMaterial materiais={opcoes.materiais} valor={material} onChange={setMaterial} />
            <MultiSelecao rotulo="Setor" opcoes={opcoesSetor} selecionados={setores} onChange={setSetores} />
          </BarraFiltros>

          {erroDados ? (
            <div className="previa-card px-6 py-12 text-center text-sm text-[#C23B4E]">
              Não foi possível aplicar os filtros. Tente novamente.
            </div>
          ) : !dados ? (
            <div className="previa-card px-6 py-12 text-center text-sm text-muted">Carregando…</div>
          ) : (
            <div className={`flex flex-col gap-[22px] transition-opacity ${carregandoDados ? "opacity-60" : ""}`}>
              <Kpis dados={dados} competencia={competencia} filtroSetor={setores.length > 0} />
              <GraficoMensal mensal={dados.mensal} />
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.5fr)]">
                <CurvaAbc abc={dados.abc} />
                <ConsumoPorSetor setores={dados.setores} />
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}

/** Título do card + grandeza exibida (alternável ou fixa). */
function CabecalhoGrafico({
  titulo,
  medida,
  onMedida,
}: {
  titulo: string;
  medida: Medida;
  onMedida?: (m: Medida) => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="text-base font-bold">{titulo}</h3>
      {onMedida ? (
        <SeletorMedida valor={medida} onChange={onMedida} />
      ) : (
        <span className="rounded-full bg-surface-app px-3 py-1 text-xs font-bold text-navy">{ROTULO_MEDIDA[medida]}</span>
      )}
    </div>
  );
}

function Kpis({
  dados,
  competencia,
  filtroSetor,
}: {
  dados: Dados;
  competencia: Competencia;
  filtroSetor: boolean;
}) {
  const valorPeriodo = dados.mensal.reduce((s, p) => s + p.valor_total, 0);
  const quantidadePeriodo = dados.mensal.reduce((s, p) => s + p.quantidade_total, 0);
  const valorAnterior = dados.anterior.reduce((s, p) => s + p.valor_total, 0);
  const periodo = `${fmtCompetencia(competencia.inicio)} a ${fmtCompetencia(competencia.fim)}`;
  const anterior = periodoAnterior(competencia);
  const rotuloAnterior = `${fmtCompetencia(anterior.inicio)} a ${fmtCompetencia(anterior.fim)}`;

  // Variação do valor consumido. Consumo maior = custo maior, por isso a alta fica em vermelho.
  const variacao = valorAnterior > 0 ? ((valorPeriodo - valorAnterior) / valorAnterior) * 100 : null;
  const corVariacao = variacao == null ? "#0A2540" : variacao > 0 ? "#C23B4E" : variacao < 0 ? "#1F7A50" : "#0A2540";

  const { previsao } = dados;
  const temPrevisao = previsao.itens_com_previsao > 0;

  const cards = [
    {
      label: "Valor consumido no período",
      valor: fmtCompacto(valorPeriodo, { moeda: true }),
      dica: fmtMoeda(valorPeriodo),
      nota: periodo,
    },
    {
      label: "Quantidade de itens consumidos",
      valor: fmtQuantidade(quantidadePeriodo),
      dica: "Soma das quantidades consumidas no período, com os filtros aplicados.",
      nota: `unidades somadas · ${periodo}`,
    },
    {
      label: "Variação vs. período anterior",
      valor: variacao == null ? "—" : `${variacao > 0 ? "+" : ""}${fmtNumero(variacao, 1)}%`,
      cor: corVariacao,
      dica:
        "Variação do valor consumido em relação ao mesmo número de meses imediatamente antes da competência." +
        (valorAnterior > 0 ? ` Período anterior: ${fmtMoeda(valorAnterior)}.` : ""),
      nota:
        valorAnterior > 0
          ? `vs ${rotuloAnterior} (${fmtCompacto(valorAnterior, { moeda: true })})`
          : `sem consumo em ${rotuloAnterior}`,
    },
    {
      label: "Previsão dos próximos 30 dias",
      valor: temPrevisao ? fmtCompacto(previsao.valor_estimado, { moeda: true }) : "—",
      dica:
        "Previsão diária somada dos próximos 30 dias. O valor é estimado pelo preço médio histórico de cada material." +
        (temPrevisao ? ` Quantidade prevista: ${fmtQuantidade(previsao.quantidade_prevista)}.` : ""),
      nota: !temPrevisao
        ? "previsões diárias ainda não geradas"
        : `${fmtQuantidade(Math.round(previsao.quantidade_prevista))} unidades` +
          (previsao.base ? ` · a partir de ${fmtData(previsao.base)}` : "") +
          (filtroSetor ? " · não filtra por setor" : ""),
    },
  ];

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
      {cards.map((k) => (
        <div key={k.label} title={k.dica} className="previa-card flex flex-col gap-1.5 px-5 py-[18px]">
          <span className="text-[13px] text-muted">{k.label}</span>
          <span className="text-[28px] font-extrabold -tracking-[0.02em]" style={{ color: k.cor ?? "#0A2540" }}>
            {k.valor}
          </span>
          <span className="text-xs font-semibold text-muted">{k.nota}</span>
        </div>
      ))}
    </div>
  );
}

/** Topo "redondo" da escala do eixo (ex.: 37.200 -> 40.000). */
function topoEscala(valor: number): number {
  if (valor <= 0) return 1;
  const potencia = 10 ** Math.floor(Math.log10(valor));
  const n = valor / potencia;
  const passo = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
  return passo * potencia;
}

/** Número do eixo. Valor: abreviado (M/K), sem zeros à direita ("10 K"). Quantidade: completo ("12.500"). */
const fmtTick = (v: number, m: Medida) => (m === "valor" ? fmtCompacto(v, { fixo: false }) : fmtQuantidade(v));

function GraficoMensal({ mensal }: { mensal: PontoMensal[] }) {
  const [medida, setMedida] = useState<Medida>("valor");
  const ALTURA = 230;
  const valores = mensal.map((p) => valorDe(p, medida));
  const topo = topoEscala(Math.max(...valores, 0));
  const tituloEixo = ROTULO_MEDIDA[medida];
  const ticks = [1, 0.75, 0.5, 0.25, 0];
  const passoRotulo = mensal.length > 12 ? 2 : 1;
  const semConsumo = valores.every((v) => v === 0);

  return (
    <div className="previa-card px-[22px] py-5">
      <CabecalhoGrafico titulo="Consumo mensal" medida={medida} onMedida={setMedida} />

      {mensal.length === 0 || semConsumo ? (
        <div className="grid h-[262px] place-items-center text-sm text-muted">
          Nenhum consumo encontrado para os filtros escolhidos.
        </div>
      ) : (
        <div className="mt-[18px] flex gap-2">
          {/* Título e escala do eixo Y */}
          <div className="flex flex-none items-center" style={{ height: ALTURA }}>
            <span className="rotate-180 whitespace-nowrap text-[11px] font-bold text-muted [writing-mode:vertical-rl]">
              {tituloEixo}
            </span>
          </div>
          <div className="relative w-11 flex-none" style={{ height: ALTURA }}>
            {ticks.map((t) => (
              <span
                key={t}
                className="absolute right-1 -translate-y-1/2 text-[10.5px] text-muted-400"
                style={{ top: `${(1 - t) * 100}%` }}
              >
                {fmtTick(topo * t, medida)}
              </span>
            ))}
          </div>

          <div className="min-w-0 flex-1">
            <div className="relative border-b border-l border-line" style={{ height: ALTURA }}>
              {ticks.slice(0, -1).map((t) => (
                <div
                  key={t}
                  className="absolute left-0 right-0 border-t border-dashed border-line-200"
                  style={{ top: `${(1 - t) * 100}%` }}
                />
              ))}
              <div className="absolute inset-0 flex items-end gap-1.5 px-1.5 sm:gap-2.5">
                {mensal.map((p, i) => {
                  const v = valores[i];
                  return (
                    <div
                      key={p.periodo}
                      title={`${fmtMesAnoNumerico(p.periodo)}: ${fmtMedidaCompleta(v, medida)}`}
                      className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1"
                    >
                      {passoRotulo === 1 && v > 0 && (
                        <span className="whitespace-nowrap text-[10.5px] font-semibold text-muted">
                          {medida === "valor" ? fmtCompacto(v) : fmtQuantidade(v)}
                        </span>
                      )}
                      <div
                        className="w-full max-w-[38px] rounded-t-[5px]"
                        style={{
                          height: `${(v / topo) * 100}%`,
                          minHeight: v > 0 ? 2 : 0,
                          background: i === mensal.length - 1 ? "#4AA8E0" : "#1F5FA0",
                        }}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="mt-2 flex gap-1.5 px-1.5 sm:gap-2.5">
              {mensal.map((p, i) => (
                <span key={p.periodo} className="min-w-0 flex-1 text-center text-[11px] text-muted-400">
                  {i % passoRotulo === 0 ? fmtMesAnoNumerico(p.periodo) : ""}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Largura reservada à direita das barras para o rótulo de valor ("R$ 999,99 K"). */
const ESPACO_ROTULO = 92;
/** Coluna dos nomes de setor (a mesma no eixo de valores, para alinhar). */
const COLUNA_NOMES = "w-[36%] max-w-[210px] flex-none";

function ConsumoPorSetor({ setores }: { setores: ConsumoSetor[] }) {
  const [medida, setMedida] = useState<Medida>("valor");
  const linhas = useMemo(
    () =>
      setores
        .map((s) => ({ nome: s.setor || "Setor não informado", valor: valorDe(s, medida) }))
        .sort((a, b) => b.valor - a.valor),
    [setores, medida],
  );
  const topo = topoEscala(Math.max(...linhas.map((l) => l.valor), 0));
  const ticks = [0, 0.2, 0.4, 0.6, 0.8, 1];

  return (
    <div className="previa-card flex flex-col px-[22px] py-5">
      <CabecalhoGrafico titulo="Consumo por setor" medida={medida} onMedida={setMedida} />
      {linhas.length === 0 ? (
        <p className="mt-6 text-sm text-muted">Nenhum consumo por setor para os filtros escolhidos.</p>
      ) : (
        <>
          <div className="mt-4 max-h-[420px] overflow-y-auto pr-1">
            <div className="flex">
              {/* Nomes dos setores */}
              <div className={`${COLUNA_NOMES} pr-3`}>
                {linhas.map((l) => (
                  <div key={l.nome} className="flex h-8 items-center justify-end">
                    <span
                      title={l.nome}
                      className="truncate text-[12.5px] font-bold text-ink underline decoration-[#9FB6CE] underline-offset-2"
                    >
                      {l.nome}
                    </span>
                  </div>
                ))}
              </div>
              {/* Barras */}
              <div className="relative min-w-0 flex-1 border-l border-[#9FB6CE]">
                <div className="absolute inset-y-0 left-0" style={{ right: ESPACO_ROTULO }}>
                  {ticks.slice(1).map((t) => (
                    <div
                      key={t}
                      className="absolute inset-y-0 border-l border-dashed border-line-200"
                      style={{ left: `${t * 100}%` }}
                    />
                  ))}
                </div>
                <div className="relative" style={{ marginRight: ESPACO_ROTULO }}>
                  {linhas.map((l, i) => {
                    const pct = (l.valor / topo) * 100;
                    return (
                      <div key={l.nome} className="relative h-8" title={`${l.nome}: ${fmtMedidaCompleta(l.valor, medida)}`}>
                        <div
                          className="absolute left-0 top-1/2 h-[18px] -translate-y-1/2 rounded-r-[4px]"
                          style={{
                            width: `${pct}%`,
                            minWidth: l.valor > 0 ? 2 : 0,
                            background: i === 0 ? "#4AA8E0" : "#1F5FA0",
                          }}
                        />
                        <span
                          className="absolute top-1/2 -translate-y-1/2 whitespace-nowrap pl-1.5 text-[11.5px] font-semibold text-ink-700"
                          style={{ left: `${pct}%` }}
                        >
                          {fmtMedida(l.valor, medida)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          {/* Eixo de valores (rótulos inclinados) */}
          <div className="flex pr-1">
            <div className={COLUNA_NOMES} />
            <div className="min-w-0 flex-1">
              <div className="relative h-[58px] border-t border-[#9FB6CE]" style={{ marginRight: ESPACO_ROTULO }}>
                {ticks.map((t) => (
                  <span key={t} className="absolute top-0" style={{ left: `${t * 100}%` }}>
                    <span className="absolute left-0 top-0 h-1.5 border-l border-[#9FB6CE]" />
                    <span
                      className="absolute right-0 top-2 origin-top-right whitespace-nowrap text-[10.5px] text-muted"
                      style={{ transform: "rotate(-40deg)" }}
                    >
                      {fmtTick(topo * t, medida)}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          </div>
          <p className="text-center text-xs font-bold text-muted">{ROTULO_MEDIDA[medida]}</p>
        </>
      )}
    </div>
  );
}

function CurvaAbc({ abc }: { abc: DistribuicaoABC[] }) {
  const fatias = ["A", "B", "C"].map((cls) => {
    const d = abc.find((a) => a.classe === cls);
    return { cls, valor: d?.valor_total ?? 0, itens: d?.quantidade_itens ?? 0 };
  });
  const total = fatias.reduce((s, f) => s + f.valor, 0);

  return (
    <div className="previa-card flex flex-col px-[22px] py-5">
      <CabecalhoGrafico titulo="Classificação ABC dos itens" medida="valor" />
      {total <= 0 ? (
        <p className="mt-6 text-sm text-muted">Sem consumo classificado para os filtros escolhidos.</p>
      ) : (
        <>
          <div className="mt-4 flex justify-center">
            <Pizza fatias={fatias} total={total} />
          </div>
          <div className="mt-4 flex flex-col">
            {fatias.map((f) => (
              <div key={f.cls} className="flex items-center gap-3 border-b border-[#F0F4F8] py-2.5 text-[13px] last:border-0">
                <span
                  className="grid h-[26px] w-[26px] flex-none place-items-center rounded-md font-extrabold"
                  style={{ background: CLASSES[f.cls].bg, color: CLASSES[f.cls].fg }}
                >
                  {f.cls}
                </span>
                <span className="min-w-0 flex-1 text-ink-700">
                  {CLASSES[f.cls].desc}
                  <span className="block text-xs text-muted-400">
                    Corte: {CLASSES[f.cls].corte} do valor acumulado · {fmtNumero(f.itens)} itens ·{" "}
                    {fmtCompacto(f.valor, { moeda: true })}
                  </span>
                </span>
                <span className="font-bold">{fmtNumero((f.valor / total) * 100, 1)}%</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Pizza({ fatias, total }: { fatias: { cls: string; valor: number }[]; total: number }) {
  const C = 110;
  const R = 100;
  const visiveis = fatias.filter((f) => f.valor > 0);
  let angulo = -Math.PI / 2;

  return (
    <svg viewBox="0 0 220 220" className="h-[220px] w-[220px]" role="img" aria-label="Participação das classes ABC no valor consumido">
      {visiveis.length === 1 ? (
        <>
          <circle cx={C} cy={C} r={R} fill={CLASSES[visiveis[0].cls].bg} />
          <text x={C} y={C} textAnchor="middle" dominantBaseline="middle" fontSize="16" fontWeight="800" fill={CLASSES[visiveis[0].cls].fg}>
            {visiveis[0].cls} 100%
          </text>
        </>
      ) : (
        visiveis.map((f) => {
          const fracao = f.valor / total;
          const a0 = angulo;
          const a1 = angulo + fracao * 2 * Math.PI;
          angulo = a1;
          const x0 = C + R * Math.cos(a0);
          const y0 = C + R * Math.sin(a0);
          const x1 = C + R * Math.cos(a1);
          const y1 = C + R * Math.sin(a1);
          const meio = (a0 + a1) / 2;
          return (
            <g key={f.cls}>
              <path
                d={`M ${C} ${C} L ${x0} ${y0} A ${R} ${R} 0 ${fracao > 0.5 ? 1 : 0} 1 ${x1} ${y1} Z`}
                fill={CLASSES[f.cls].bg}
                stroke="#fff"
                strokeWidth="2"
              />
              {fracao >= 0.06 && (
                <text
                  x={C + R * 0.62 * Math.cos(meio)}
                  y={C + R * 0.62 * Math.sin(meio)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="13"
                  fontWeight="800"
                  fill={CLASSES[f.cls].fg}
                >
                  {f.cls} {fmtNumero(fracao * 100)}%
                </text>
              )}
            </g>
          );
        })
      )}
    </svg>
  );
}
