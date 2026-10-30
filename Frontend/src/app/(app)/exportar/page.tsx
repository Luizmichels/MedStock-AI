"use client";

import { useEffect, useState } from "react";
import { Icon, IconName } from "@/components/Icon";
import PageHeader from "@/components/PageHeader";
import SemDadosImportados from "@/components/SemDadosImportados";
import Toast, { useToast } from "@/components/Toast";
import {
  FormatoExportacao,
  consumoMensal,
  exportarConsumo,
  exportarPrevisoes,
  resumoDashboard,
  resumoPrevisoes,
  salvarArquivo,
} from "@/lib/api";
import { mensagemErro } from "@/lib/erros";
import { isoData } from "@/lib/formato";

type ChaveRelatorio = "previsoes" | "consumo";
type ChavePeriodo = "tudo" | "12" | "6" | "1" | "custom";

const RELATORIOS: {
  chave: ChaveRelatorio;
  nome: string;
  desc: string;
  icone: IconName;
  exigePrevisao: boolean;
}[] = [
  {
    chave: "previsoes",
    nome: "Previsão de consumo por material",
    desc: "Uma linha por material com a previsão de cada um dos próximos 3 meses e o total, ordenada pela curva ABC. No Excel, uma aba extra traz o detalhe mês a mês com o modelo escolhido, a faixa de incerteza e o erro da validação.",
    icone: "previsoes",
    exigePrevisao: true,
  },
  {
    chave: "consumo",
    nome: "Consumo consolidado do período",
    desc: "Indicadores do período, consumo por setor e o total por material (quantidade, valor e % do valor). No Excel, também o detalhe mês a mês.",
    icone: "dashboard",
    exigePrevisao: false,
  },
];

const PERIODOS: { chave: ChavePeriodo; rotulo: string }[] = [
  { chave: "tudo", rotulo: "Todo o histórico" },
  { chave: "12", rotulo: "Últimos 12 meses" },
  { chave: "6", rotulo: "Últimos 6 meses" },
  { chave: "1", rotulo: "Último mês" },
  { chave: "custom", rotulo: "Personalizado" },
];

const FORMATOS: { chave: FormatoExportacao; rotulo: string; sub: string }[] = [
  { chave: "pdf", rotulo: "PDF", sub: "Leitura e impressão" },
  { chave: "xlsx", rotulo: "Excel", sub: ".xlsx · planilha" },
];

export default function ExportarPage() {
  const { mensagem, notificar } = useToast();

  const [estado, setEstado] = useState<"carregando" | "vazio" | "pronto">("carregando");
  const [temPrevisao, setTemPrevisao] = useState(true);

  const [relatorio, setRelatorio] = useState<ChaveRelatorio>("previsoes");
  const [periodo, setPeriodo] = useState<ChavePeriodo>("12");
  const [mesInicio, setMesInicio] = useState("");
  const [mesFim, setMesFim] = useState("");
  const [formato, setFormato] = useState<FormatoExportacao>("pdf");
  const [exportando, setExportando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    Promise.all([resumoDashboard(), resumoPrevisoes()])
      .then(([r, previsoes]) => {
        setTemPrevisao(previsoes.itens.length > 0);
        setEstado(r.possui_dados ? "pronto" : "vazio");
      })
      .catch(() => setEstado("pronto")); // na dúvida, deixa exportar
  }, []);

  const atual = RELATORIOS.find((r) => r.chave === relatorio)!;
  const nomeArquivo = `${relatorio}_${isoData(new Date())}.${formato}`;
  const avisoPrevisao = atual.exigePrevisao && !temPrevisao;

  /**
   * Intervalo do relatório de consumo. "Últimos N meses" conta a partir do
   * último mês COM DADOS (não da data de hoje), para nunca sair vazio quando o
   * histórico importado é antigo.
   */
  async function intervaloConsumo(): Promise<{ data_inicio?: string; data_fim?: string }> {
    if (periodo === "tudo") return {};
    if (periodo === "custom") {
      return {
        data_inicio: mesInicio ? `${mesInicio}-01` : undefined,
        data_fim: mesFim ? `${mesFim}-01` : undefined,
      };
    }
    const pontos = await consumoMensal(Number(periodo));
    if (pontos.length === 0) return {};
    return { data_inicio: pontos[0].periodo, data_fim: pontos[pontos.length - 1].periodo };
  }

  async function exportar() {
    if (relatorio === "consumo" && periodo === "custom" && mesInicio && mesFim && mesInicio > mesFim) {
      setErro("O mês inicial não pode ser depois do mês final.");
      return;
    }
    setExportando(true);
    setErro("");
    try {
      const blob =
        relatorio === "previsoes"
          ? await exportarPrevisoes(formato)
          : await exportarConsumo(formato, await intervaloConsumo());
      salvarArquivo(blob, nomeArquivo);
      notificar(`${nomeArquivo} gerado e baixado.`);
    } catch (e) {
      setErro(mensagemErro(e, "Não foi possível gerar o relatório."));
    } finally {
      setExportando(false);
    }
  }

  return (
    <>
      <PageHeader title="Exportar relatório" subtitle="Selecione o relatório e o formato de exportação" />

      {estado === "carregando" && (
        <div className="previa-card px-6 py-12 text-center text-sm text-muted">Carregando…</div>
      )}
      {estado === "vazio" && (
        <SemDadosImportados descricao="Os relatórios ficam disponíveis depois da primeira importação de consumo." />
      )}

      {estado === "pronto" && (
        <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(300px,1fr)]">
          <div className="previa-card flex flex-col gap-3 px-[22px] py-5">
            <h3 className="mb-1 text-base font-bold">1. Tipo de relatório</h3>
            {RELATORIOS.map((r) => {
              const marcado = relatorio === r.chave;
              return (
                <button
                  key={r.chave}
                  onClick={() => setRelatorio(r.chave)}
                  className="flex items-start gap-3.5 rounded-[10px] border-[1.5px] px-4 py-3.5 text-left transition"
                  style={{
                    borderColor: marcado ? "#4AA8E0" : "#DCE6F0",
                    background: marcado ? "#F2F8FD" : "#fff",
                  }}
                >
                  <span
                    className="grid h-10 w-10 flex-none place-items-center rounded-[10px]"
                    style={{ background: marcado ? "#4AA8E0" : "#EAF3FB", color: marcado ? "#fff" : "#1c4f8a" }}
                  >
                    <Icon name={r.icone} size={18} />
                  </span>
                  <span className="flex flex-1 flex-col gap-0.5">
                    <span className="text-sm font-bold text-ink">{r.nome}</span>
                    <span className="text-[13px] leading-snug text-muted">{r.desc}</span>
                  </span>
                  <span
                    className="mt-0.5 grid h-[18px] w-[18px] flex-none place-items-center rounded-full border-2"
                    style={{ borderColor: marcado ? "#4AA8E0" : "#DCE6F0" }}
                  >
                    <span className="h-2 w-2 rounded-full" style={{ background: marcado ? "#4AA8E0" : "transparent" }} />
                  </span>
                </button>
              );
            })}
          </div>

          <div className="previa-card flex flex-col gap-4 px-[22px] py-5">
            <h3 className="text-base font-bold">2. Parâmetros</h3>

            {relatorio === "consumo" ? (
              <div className="flex flex-col gap-2.5">
                <label className="flex flex-col gap-1.5 text-[13px] text-muted">
                  Período
                  <select
                    value={periodo}
                    onChange={(e) => setPeriodo(e.target.value as ChavePeriodo)}
                    className="h-10 rounded-lg border border-[#CBD6E2] bg-white px-2.5 text-sm text-ink"
                  >
                    {PERIODOS.map((p) => (
                      <option key={p.chave} value={p.chave}>
                        {p.rotulo}
                      </option>
                    ))}
                  </select>
                </label>
                {periodo === "custom" && (
                  <div className="grid grid-cols-2 gap-2.5">
                    <label className="flex flex-col gap-1.5 text-xs text-muted">
                      De
                      <input
                        type="month"
                        value={mesInicio}
                        onChange={(e) => setMesInicio(e.target.value)}
                        className="h-10 rounded-lg border border-[#CBD6E2] px-2.5 text-sm text-ink"
                      />
                    </label>
                    <label className="flex flex-col gap-1.5 text-xs text-muted">
                      Até
                      <input
                        type="month"
                        value={mesFim}
                        onChange={(e) => setMesFim(e.target.value)}
                        className="h-10 rounded-lg border border-[#CBD6E2] px-2.5 text-sm text-ink"
                      />
                    </label>
                  </div>
                )}
              </div>
            ) : (
              <p className="rounded-[10px] bg-surface-panel px-3.5 py-2.5 text-[13px] text-ink-700">
                Este relatório não tem filtro de período: usa as previsões diárias mais recentes de cada material.
              </p>
            )}

            <div className="flex flex-col gap-1.5 text-[13px] text-muted">
              Formato
              <div className="grid grid-cols-2 gap-2.5">
                {FORMATOS.map((f) => {
                  const marcado = formato === f.chave;
                  return (
                    <button
                      key={f.chave}
                      onClick={() => setFormato(f.chave)}
                      className="flex h-14 flex-col items-center justify-center gap-0.5 rounded-[10px] border-[1.5px] text-ink transition"
                      style={{
                        borderColor: marcado ? "#4AA8E0" : "#DCE6F0",
                        background: marcado ? "#F2F8FD" : "#fff",
                      }}
                    >
                      <span className="text-[15px] font-extrabold">{f.rotulo}</span>
                      <span className="text-[11px] text-muted">{f.sub}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col gap-0.5 rounded-[10px] bg-surface-panel px-3.5 py-3 text-[13px] text-ink-700">
              <span className="text-xs text-muted-400">Arquivo</span>
              <span className="break-all font-mono text-xs">{nomeArquivo}</span>
            </div>

            {formato === "pdf" && (
              <p className="text-xs leading-relaxed text-muted">
                O PDF traz um cabeçalho com o hospital, quem gerou e a data, e lista os 100 materiais mais relevantes. A
                lista completa fica no Excel.
              </p>
            )}
            {avisoPrevisao && (
              <p className="rounded-[10px] bg-[#FDF1DC] px-3.5 py-2.5 text-[13px] text-[#9A6212]">
                Ainda não há previsões geradas, então este relatório sairá vazio. Treine os modelos na tela de
                Previsões.
              </p>
            )}
            {erro && <p className="text-[13px] font-semibold text-[#C23B4E]">{erro}</p>}

            <button className="previa-btn h-11 w-full" onClick={exportar} disabled={exportando}>
              {exportando ? "GERANDO…" : formato === "pdf" ? "EXPORTAR PDF" : "EXPORTAR EXCEL"}
            </button>
          </div>
        </div>
      )}

      <Toast mensagem={mensagem} />
    </>
  );
}
