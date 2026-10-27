"use client";

import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { MaterialFiltro } from "@/lib/api";
import { fmtCompetencia, somarMeses } from "@/lib/formato";

// ---------------------------------------------------------------------------
// Cascata Grupo / Subgrupo / Classe / Material
// ---------------------------------------------------------------------------

/** Seleção dos filtros de material (lista vazia = todos). */
export interface SelecaoMaterial {
  grupos: string[];
  subgrupos: string[];
  classes: string[];
  materiais: number[];
}

export const SELECAO_VAZIA: SelecaoMaterial = { grupos: [], subgrupos: [], classes: [], materiais: [] };

type Nivel = "grupos" | "subgrupos" | "classes";

const ATRIBUTO: Record<Nivel, "grupo_material" | "subgrupo_material" | "classe_material"> = {
  grupos: "grupo_material",
  subgrupos: "subgrupo_material",
  classes: "classe_material",
};

/** O material atende à seleção dos níveis, ignorando (opcionalmente) um deles. */
function atende(m: MaterialFiltro, sel: SelecaoMaterial, ignorar?: Nivel): boolean {
  return (Object.keys(ATRIBUTO) as Nivel[]).every((nivel) => {
    if (nivel === ignorar || sel[nivel].length === 0) return true;
    const valor = m[ATRIBUTO[nivel]];
    return valor != null && sel[nivel].includes(valor);
  });
}

function distintos(valores: (string | null)[], extras: string[]): string[] {
  const conjunto = new Set<string>(extras);
  for (const v of valores) if (v) conjunto.add(v);
  return Array.from(conjunto).sort((a, b) => a.localeCompare(b, "pt-BR"));
}

/**
 * Opções de cada filtro, filtradas pelos OUTROS níveis (cascata nos dois sentidos):
 * escolher um grupo restringe subgrupo, classe e material; escolher um subgrupo
 * restringe grupo, classe e material; e assim por diante. Valores já marcados
 * continuam na lista, para poderem ser desmarcados.
 */
export function opcoesCascata(materiais: MaterialFiltro[], sel: SelecaoMaterial) {
  const nivel = (n: Nivel) =>
    distintos(
      materiais.filter((m) => atende(m, sel, n)).map((m) => m[ATRIBUTO[n]]),
      sel[n],
    );
  const marcados = new Set(sel.materiais);
  return {
    grupos: nivel("grupos"),
    subgrupos: nivel("subgrupos"),
    classes: nivel("classes"),
    materiais: materiais.filter((m) => marcados.has(m.id) || atende(m, sel)),
  };
}

/** Quantos filtros de material estão ativos. */
export function contarSelecao(sel: SelecaoMaterial): number {
  return [sel.grupos, sel.subgrupos, sel.classes, sel.materiais].filter((l) => l.length > 0).length;
}

/** Os quatro campos de material, na ordem Grupo → Subgrupo → Classe → Material. */
export function CamposMaterial({
  materiais,
  valor,
  onChange,
}: {
  materiais: MaterialFiltro[];
  valor: SelecaoMaterial;
  onChange: (v: SelecaoMaterial) => void;
}) {
  const op = useMemo(() => opcoesCascata(materiais, valor), [materiais, valor]);
  const opcoesMaterial = useMemo(
    () =>
      op.materiais.map((m) => ({
        valor: String(m.id),
        rotulo: m.descricao_item,
        detalhe: m.codigo_item,
      })),
    [op.materiais],
  );

  return (
    <>
      <MultiSelecao
        rotulo="Grupo Material"
        opcoes={op.grupos.map(simples)}
        selecionados={valor.grupos}
        onChange={(grupos) => onChange({ ...valor, grupos })}
      />
      <MultiSelecao
        rotulo="SubGrupo Material"
        opcoes={op.subgrupos.map(simples)}
        selecionados={valor.subgrupos}
        onChange={(subgrupos) => onChange({ ...valor, subgrupos })}
      />
      <MultiSelecao
        rotulo="Classe Material"
        opcoes={op.classes.map(simples)}
        selecionados={valor.classes}
        onChange={(classes) => onChange({ ...valor, classes })}
      />
      <MultiSelecao
        rotulo="Material"
        largura="min-w-[180px] flex-[1.4]"
        opcoes={opcoesMaterial}
        selecionados={valor.materiais.map(String)}
        onChange={(ids) => onChange({ ...valor, materiais: ids.map(Number) })}
        textoBusca="Buscar por código ou descrição"
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// Campo com rótulo no contorno + popover
// ---------------------------------------------------------------------------

/** Fecha o popover ao clicar fora ou apertar Esc. */
function useFecharFora(aberto: boolean, fechar: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!aberto) return;
    function clique(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) fechar();
    }
    function tecla(e: KeyboardEvent) {
      if (e.key === "Escape") fechar();
    }
    document.addEventListener("mousedown", clique);
    document.addEventListener("keydown", tecla);
    return () => {
      document.removeEventListener("mousedown", clique);
      document.removeEventListener("keydown", tecla);
    };
  }, [aberto, fechar]);
  return ref;
}

/** Campo contornado com o rótulo "no entalhe" da borda; abre um popover. */
function CampoContorno({
  rotulo,
  texto,
  vazio,
  aberto,
  setAberto,
  largura = "min-w-[140px] flex-1",
  icone,
  children,
}: {
  rotulo: string;
  texto: string;
  vazio: boolean;
  aberto: boolean;
  setAberto: (v: boolean) => void;
  largura?: string;
  icone: ReactNode;
  children: ReactNode;
}) {
  const fechar = useMemo(() => () => setAberto(false), [setAberto]);
  const ref = useFecharFora(aberto, fechar);
  // Perto da borda direita da tela, o popover abre alinhado à direita do campo.
  const [aDireita, setADireita] = useState(false);
  function alternar() {
    if (!aberto && ref.current) setADireita(ref.current.getBoundingClientRect().left + 320 > window.innerWidth);
    setAberto(!aberto);
  }

  return (
    <div ref={ref} className={`relative ${largura} max-w-full`}>
      <button
        type="button"
        onClick={alternar}
        aria-expanded={aberto}
        className={`flex h-11 w-full items-center gap-2 rounded-md border bg-white pl-3 pr-2.5 text-left text-sm transition ${
          aberto ? "border-brand ring-2 ring-brand/20" : "border-[#B9C6D4] hover:border-[#8494A6]"
        }`}
      >
        <span className={`min-w-0 flex-1 truncate ${vazio ? "text-muted-400" : "font-semibold text-ink"}`}>{texto}</span>
        <span className={`flex-none transition ${aberto ? "text-brand-800" : "text-muted"}`}>{icone}</span>
      </button>
      <span
        className={`pointer-events-none absolute -top-[9px] left-2 max-w-[calc(100%-16px)] truncate bg-white px-1 text-[11.5px] font-semibold leading-[18px] ${
          aberto ? "text-brand-800" : "text-muted"
        }`}
      >
        {rotulo}
      </span>
      {aberto && (
        <div className={`absolute ${aDireita ? "right-0" : "left-0"} top-[calc(100%+6px)] z-30 rounded-lg border border-line bg-white shadow-[0_14px_34px_rgba(10,37,64,.18)]`}>
          {children}
        </div>
      )}
    </div>
  );
}

function Chevron({ aberto }: { aberto: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`transition-transform ${aberto ? "rotate-180" : ""}`}
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

function Caixa({ marcada }: { marcada: boolean }) {
  return (
    <span
      className={`grid h-4 w-4 flex-none place-items-center rounded-[4px] border transition ${
        marcada ? "border-navy bg-navy text-white" : "border-[#9FB0C2] bg-white"
      }`}
      aria-hidden="true"
    >
      {marcada && (
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M5 12l5 5 9-10" />
        </svg>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Seleção múltipla com busca e "Todos"
// ---------------------------------------------------------------------------

export interface OpcaoSelecao {
  valor: string;
  rotulo: string;
  detalhe?: string;
}

const simples = (v: string): OpcaoSelecao => ({ valor: v, rotulo: v });

/** Máximo de opções desenhadas de uma vez (listas de material podem ser enormes). */
const MAX_VISIVEIS = 300;

export function MultiSelecao({
  rotulo,
  opcoes,
  selecionados,
  onChange,
  largura,
  textoBusca = "Buscar",
}: {
  rotulo: string;
  opcoes: OpcaoSelecao[];
  selecionados: string[];
  onChange: (v: string[]) => void;
  largura?: string;
  textoBusca?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const [busca, setBusca] = useState("");
  useEffect(() => {
    if (!aberto) setBusca("");
  }, [aberto]);

  const marcados = useMemo(() => new Set(selecionados), [selecionados]);
  const filtradas = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    if (!termo) return opcoes;
    return opcoes.filter((o) => `${o.rotulo} ${o.detalhe ?? ""}`.toLowerCase().includes(termo));
  }, [opcoes, busca]);
  const visiveis = filtradas.slice(0, MAX_VISIVEIS);

  const texto =
    selecionados.length === 0
      ? "Selecione"
      : selecionados.length === 1
        ? (opcoes.find((o) => o.valor === selecionados[0])?.rotulo ?? "1 selecionado")
        : `${selecionados.length} selecionados`;

  function alternar(valor: string) {
    onChange(marcados.has(valor) ? selecionados.filter((v) => v !== valor) : [...selecionados, valor]);
  }

  // Sem busca, "Todos" = sem filtro. Com busca, marca/desmarca todos os resultados.
  const comBusca = busca.trim() !== "";
  const todosMarcado = comBusca
    ? filtradas.length > 0 && filtradas.every((o) => marcados.has(o.valor))
    : selecionados.length === 0;
  function alternarTodos() {
    if (!comBusca) return onChange([]);
    const resultado = new Set(filtradas.map((o) => o.valor));
    onChange(
      todosMarcado
        ? selecionados.filter((v) => !resultado.has(v))
        : Array.from(new Set([...selecionados, ...resultado])),
    );
  }

  return (
    <CampoContorno
      rotulo={rotulo}
      texto={texto}
      vazio={selecionados.length === 0}
      aberto={aberto}
      setAberto={setAberto}
      largura={largura}
      icone={<Chevron aberto={aberto} />}
    >
      <div className="flex w-[300px] max-w-[calc(100vw-48px)] flex-col">
        <div className="border-b border-line-200 p-2">
          <div className="flex h-9 items-center gap-2 rounded-md border border-[#CBD6E2] px-2.5 focus-within:border-brand">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#8494A6" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
            <input
              autoFocus
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder={textoBusca}
              className="min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-muted-400"
            />
          </div>
        </div>
        <div className="max-h-[300px] overflow-y-auto py-1">
          <button
            type="button"
            onClick={alternarTodos}
            disabled={comBusca && filtradas.length === 0}
            className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-[13px] font-bold text-ink hover:bg-surface-sky disabled:opacity-50"
          >
            <Caixa marcada={todosMarcado} />
            {comBusca ? `Todos os resultados (${filtradas.length})` : "Todos"}
          </button>
          {visiveis.length === 0 ? (
            <p className="px-3 py-2.5 text-[13px] text-muted">
              {opcoes.length === 0 ? "Sem opções para os filtros escolhidos." : "Nada encontrado."}
            </p>
          ) : (
            visiveis.map((o) => (
              <button
                key={o.valor}
                type="button"
                onClick={() => alternar(o.valor)}
                title={o.detalhe ? `${o.detalhe} · ${o.rotulo}` : o.rotulo}
                className="flex w-full items-center gap-2.5 px-3 py-[7px] text-left hover:bg-surface-sky"
              >
                <Caixa marcada={marcados.has(o.valor)} />
                <span className="flex min-w-0 flex-col">
                  <span className="truncate text-[13px] text-ink">{o.rotulo}</span>
                  {o.detalhe && <span className="font-mono text-[10.5px] text-muted-400">{o.detalhe}</span>}
                </span>
              </button>
            ))
          )}
          {filtradas.length > MAX_VISIVEIS && (
            <p className="px-3 py-2 text-[11.5px] text-muted-400">
              Mostrando {MAX_VISIVEIS} de {filtradas.length.toLocaleString("pt-BR")}. Digite para refinar.
            </p>
          )}
        </div>
      </div>
    </CampoContorno>
  );
}

// ---------------------------------------------------------------------------
// Competência: intervalo de meses
// ---------------------------------------------------------------------------

/** Intervalo de competência ("AAAA-MM"). */
export interface Competencia {
  inicio: string;
  fim: string;
}

const NOMES_MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export function SeletorCompetencia({
  valor,
  limiteInicio,
  limiteFim,
  onChange,
}: {
  valor: Competencia;
  limiteInicio: string;
  limiteFim: string;
  onChange: (c: Competencia) => void;
}) {
  const [aberto, setAberto] = useState(false);
  const [ano, setAno] = useState(Number(valor.fim.slice(0, 4)));
  // Primeiro clique escolhe uma ponta; o segundo fecha o intervalo.
  const [pendente, setPendente] = useState<string | null>(null);
  const [sobre, setSobre] = useState<string | null>(null);

  useEffect(() => {
    if (aberto) setAno(Number(valor.fim.slice(0, 4)));
    else {
      setPendente(null);
      setSobre(null);
    }
  }, [aberto, valor.fim]);

  const anoMin = Number(limiteInicio.slice(0, 4));
  const anoMax = Number(limiteFim.slice(0, 4));

  // Intervalo destacado: o escolhido ou, durante a seleção, o que está sob o mouse.
  const [ini, fim] = pendente
    ? [pendente, sobre ?? pendente].sort()
    : [valor.inicio, valor.fim];

  function escolher(mes: string) {
    if (!pendente) {
      setPendente(mes);
      return;
    }
    const [a, b] = [pendente, mes].sort();
    onChange({ inicio: a, fim: b });
    setAberto(false);
  }

  function atalho(c: Competencia) {
    onChange(c);
    setAberto(false);
  }
  const ultimos12 = somarMeses(limiteFim, -11);

  return (
    <CampoContorno
      rotulo="Competência"
      texto={`${fmtCompetencia(valor.inicio)} - ${fmtCompetencia(valor.fim)}`}
      vazio={false}
      aberto={aberto}
      setAberto={setAberto}
      largura="w-[190px] flex-none"
      icone={
        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="3" y="5" width="18" height="16" rx="2" />
          <path d="M3 10h18M8 3v4M16 3v4" />
        </svg>
      }
    >
      <div className="w-[288px] p-3.5" onMouseLeave={() => setSobre(null)}>
        <div className="mb-3 flex items-center justify-between">
          <BotaoAno direcao="anterior" disabled={ano <= anoMin} onClick={() => setAno(ano - 1)} />
          <span className="text-[15px] font-extrabold text-navy">{ano}</span>
          <BotaoAno direcao="proximo" disabled={ano >= anoMax} onClick={() => setAno(ano + 1)} />
        </div>
        <div className="grid grid-cols-3 gap-x-1 gap-y-2">
          {NOMES_MESES.map((nome, i) => {
            const mes = `${ano}-${String(i + 1).padStart(2, "0")}`;
            const indisponivel = mes < limiteInicio || mes > limiteFim;
            const ponta = mes === ini || mes === fim;
            const dentro = mes > ini && mes < fim;
            return (
              <button
                key={mes}
                type="button"
                disabled={indisponivel}
                onClick={() => escolher(mes)}
                onMouseEnter={() => setSobre(mes)}
                className={`h-9 rounded-full text-[13px] font-semibold transition ${
                  indisponivel
                    ? "cursor-not-allowed text-[#B8C4D0]"
                    : ponta
                      ? "bg-navy text-white"
                      : dentro
                        ? "bg-[#D6E7F6] text-navy"
                        : "text-ink hover:bg-surface-sky"
                }`}
              >
                {nome}
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-[11.5px] text-muted">
          {pendente
            ? `Início em ${fmtCompetencia(pendente)} — escolha o mês final.`
            : "Clique no mês inicial e depois no mês final."}
        </p>
        <div className="mt-2.5 flex gap-3 border-t border-line-200 pt-2.5 text-[12px] font-bold text-brand-800">
          <button type="button" onClick={() => atalho({ inicio: ultimos12 < limiteInicio ? limiteInicio : ultimos12, fim: limiteFim })} className="hover:underline">
            Últimos 12 meses
          </button>
          <button type="button" onClick={() => atalho({ inicio: limiteInicio, fim: limiteFim })} className="hover:underline">
            Todo o período
          </button>
        </div>
      </div>
    </CampoContorno>
  );
}

function BotaoAno({ direcao, disabled, onClick }: { direcao: "anterior" | "proximo"; disabled: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={direcao === "anterior" ? "Ano anterior" : "Próximo ano"}
      className="grid h-8 w-8 place-items-center rounded-full text-navy transition hover:bg-surface-sky disabled:cursor-not-allowed disabled:text-[#C7D1DC] disabled:hover:bg-transparent"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d={direcao === "anterior" ? "M15 6l-6 6 6 6" : "M9 6l6 6-6 6"} />
      </svg>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Barra de filtros e alternância de grandeza
// ---------------------------------------------------------------------------

/** Card branco com os filtros lado a lado. */
export function BarraFiltros({ children, onLimpar }: { children: ReactNode; onLimpar?: () => void }) {
  return (
    <div className="previa-card flex flex-wrap items-center gap-x-3 gap-y-4 px-5 pb-4 pt-5">
      {children}
      {onLimpar && (
        <button type="button" onClick={onLimpar} className="h-11 px-1 text-[13px] font-bold text-brand-800 hover:underline">
          Limpar filtros
        </button>
      )}
    </div>
  );
}

export type Medida = "valor" | "quantidade";

export const ROTULO_MEDIDA: Record<Medida, string> = { valor: "Valor (R$)", quantidade: "Quantidade" };

/** Alterna a grandeza exibida no gráfico (e deixa explícita qual é). */
export function SeletorMedida({ valor, onChange }: { valor: Medida; onChange: (m: Medida) => void }) {
  return (
    <div className="flex h-8 items-center rounded-full bg-surface-app p-[3px]" role="group" aria-label="Grandeza exibida">
      {(Object.keys(ROTULO_MEDIDA) as Medida[]).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onChange(m)}
          aria-pressed={valor === m}
          className="h-[26px] rounded-full px-3 text-xs font-bold transition"
          style={{
            background: valor === m ? "#fff" : "transparent",
            color: valor === m ? "#0A2540" : "#5B6B7E",
            boxShadow: valor === m ? "0 1px 3px rgba(10,37,64,.15)" : "none",
          }}
        >
          {ROTULO_MEDIDA[m]}
        </button>
      ))}
    </div>
  );
}
