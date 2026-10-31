"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Icon";
import IntegracaoApi from "@/components/IntegracaoApi";
import Modal from "@/components/Modal";
import PageHeader from "@/components/PageHeader";
import Toast, { useToast } from "@/components/Toast";
import {
  ImportacaoResponse,
  ModoImportacao,
  buscarImportacao,
  listarImportacoes,
  uploadImportacao,
} from "@/lib/api";
import { papel, useAuth } from "@/lib/auth";
import { mensagemErro } from "@/lib/erros";
import { esperar, fmtDataHora, fmtNumero, fmtTamanhoArquivo } from "@/lib/formato";

const EXTENSOES = ["csv", "xls", "xlsx"];
const COLUNAS = ["codigo_item", "descricao_item", "data", "quantidade", "valor", "setor"];
const COLUNAS_OPCIONAIS = ["grupo_material", "subgrupo_material", "classe_material", "unidade_medida"];
const MAX_ERROS_EXIBIDOS = 15;

const MODOS: { chave: ModoImportacao; rotulo: string; desc: string }[] = [
  {
    chave: "incremental",
    rotulo: "Incremental",
    desc: "Acrescenta as linhas do arquivo à base atual. Nada é apagado.",
  },
  {
    chave: "completa",
    rotulo: "Completa",
    desc: "Substitui toda a base de consumo do hospital pelo conteúdo deste arquivo.",
  },
];

function situacao(i: ImportacaoResponse): { rotulo: string; classe: string } {
  if (i.status === "processando") return { rotulo: "Processando", classe: "bg-[#EAF3FB] text-[#1F5FA0]" };
  if (i.status === "erro") return { rotulo: "Erro", classe: "bg-[#FBE9EC] text-[#B0364A]" };
  if (i.registros_invalidos > 0) return { rotulo: "Concluída com alertas", classe: "bg-[#FDF1DC] text-[#9A6212]" };
  return { rotulo: "Concluída", classe: "bg-[#E3F3EA] text-[#1F7A50]" };
}

export default function ImportarPage() {
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

  const entrada = useRef<HTMLInputElement>(null);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [arrastando, setArrastando] = useState(false);
  const [erroArquivo, setErroArquivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [modo, setModo] = useState<ModoImportacao>("incremental");
  const [confirmarCompleta, setConfirmarCompleta] = useState(false);
  const [atual, setAtual] = useState<ImportacaoResponse | null>(null);

  const [historico, setHistorico] = useState<ImportacaoResponse[] | null>(null);
  const [erroHistorico, setErroHistorico] = useState("");

  const recarregarHistorico = useCallback(async () => {
    try {
      const lista = await listarImportacoes();
      if (montado.current) {
        setHistorico(lista);
        setErroHistorico("");
      }
    } catch (e) {
      if (montado.current) setErroHistorico(mensagemErro(e, "Não foi possível carregar o histórico."));
    }
  }, []);

  useEffect(() => {
    if (isAdmin) recarregarHistorico();
  }, [isAdmin, recarregarHistorico]);

  function escolher(f: File | undefined) {
    if (!f) return;
    const ext = f.name.split(".").pop()?.toLowerCase() ?? "";
    if (!EXTENSOES.includes(ext)) {
      setArquivo(null);
      setErroArquivo(`Formato .${ext} não suportado. Envie um arquivo CSV ou Excel (.xls, .xlsx).`);
      return;
    }
    setErroArquivo("");
    setArquivo(f);
  }

  /** A importação completa apaga a base atual: pede confirmação antes. */
  function pedirEnvio() {
    if (modo === "completa") setConfirmarCompleta(true);
    else enviar();
  }

  async function enviar() {
    if (!arquivo) return;
    setConfirmarCompleta(false);
    setEnviando(true);
    setErroArquivo("");
    try {
      let imp = await uploadImportacao(arquivo, modo);
      setAtual(imp);
      setArquivo(null);
      if (entrada.current) entrada.current.value = "";
      recarregarHistorico();
      // O processamento é em segundo plano (em lotes): acompanha até terminar.
      while (imp.status === "processando" && montado.current) {
        await esperar(2000);
        imp = await buscarImportacao(imp.id);
        if (montado.current) setAtual(imp);
      }
      if (!montado.current) return;
      recarregarHistorico();
      notificar(
        imp.status === "erro"
          ? "A importação falhou. Veja os detalhes."
          : `Importação concluída · ${fmtNumero(imp.registros_validos)} registros válidos.`,
      );
    } catch (e) {
      if (montado.current) setErroArquivo(mensagemErro(e, "Não foi possível enviar o arquivo."));
    } finally {
      if (montado.current) setEnviando(false);
    }
  }

  if (!isAdmin) {
    return (
      <>
        <PageHeader title="Importar dados" subtitle="Carregue dados de consumo via arquivo CSV ou Excel" />
        <div className="previa-card px-6 py-12 text-center text-sm text-muted">
          Apenas administradores do hospital podem importar dados.
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader title="Importar dados" subtitle="Carregue dados de consumo via arquivo CSV ou Excel" />

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(300px,1fr)]">
        <div className="flex flex-col gap-4">
          {/* Envio */}
          <div className="previa-card flex flex-col gap-4 px-[22px] py-5">
            <h3 className="text-base font-bold">Arquivo de consumo</h3>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setArrastando(true);
              }}
              onDragLeave={() => setArrastando(false)}
              onDrop={(e) => {
                e.preventDefault();
                setArrastando(false);
                escolher(e.dataTransfer.files?.[0]);
              }}
              onClick={() => !enviando && entrada.current?.click()}
              className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-dashed px-5 py-9 text-center transition"
              style={{
                borderColor: arrastando ? "#4AA8E0" : "#B9CCE0",
                background: arrastando ? "#EAF3FB" : "#F7FAFD",
              }}
            >
              <div className="grid h-14 w-14 place-items-center rounded-full bg-white text-[#1c4f8a] shadow-[0_2px_8px_rgba(10,37,64,.08)]">
                <Icon name="importar" size={24} />
              </div>
              <span className="text-[15px] font-bold text-navy">
                {arquivo ? arquivo.name : "Arraste o arquivo aqui ou clique para selecionar"}
              </span>
              <span className="text-[13px] text-muted">
                {arquivo ? fmtTamanhoArquivo(arquivo.size) : "CSV (separado por ; ou ,) ou Excel (.xls, .xlsx)"}
              </span>
            </div>
            {/* Fora da área clicável: o clique programático nele não pode "subir" para ela. */}
            <input
              ref={entrada}
              type="file"
              accept=".csv,.xls,.xlsx"
              className="hidden"
              onChange={(e) => escolher(e.target.files?.[0])}
            />
            <div className="flex flex-col gap-2">
              <span className="text-[13px] font-semibold text-ink">Tipo de importação</span>
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
                {MODOS.map((m) => {
                  const marcado = modo === m.chave;
                  return (
                    <button
                      key={m.chave}
                      type="button"
                      onClick={() => setModo(m.chave)}
                      disabled={enviando}
                      aria-pressed={marcado}
                      className="flex items-start gap-3 rounded-[10px] border-[1.5px] px-3.5 py-3 text-left transition disabled:opacity-60"
                      style={{
                        borderColor: marcado ? (m.chave === "completa" ? "#D9822B" : "#4AA8E0") : "#DCE6F0",
                        background: marcado ? (m.chave === "completa" ? "#FDF6EC" : "#F2F8FD") : "#fff",
                      }}
                    >
                      <span
                        className="mt-0.5 grid h-[18px] w-[18px] flex-none place-items-center rounded-full border-2"
                        style={{ borderColor: marcado ? (m.chave === "completa" ? "#D9822B" : "#4AA8E0") : "#DCE6F0" }}
                      >
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ background: marcado ? (m.chave === "completa" ? "#D9822B" : "#4AA8E0") : "transparent" }}
                        />
                      </span>
                      <span className="flex flex-col gap-0.5">
                        <span className="text-sm font-bold text-ink">{m.rotulo}</span>
                        <span className="text-xs leading-snug text-muted">{m.desc}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
            {erroArquivo && <p className="text-[13px] font-semibold text-[#C23B4E]">{erroArquivo}</p>}
            <div className="flex justify-end gap-2.5">
              {arquivo && !enviando && (
                <button
                  onClick={() => {
                    setArquivo(null);
                    if (entrada.current) entrada.current.value = "";
                  }}
                  className="h-10 rounded-full border border-[#CBD6E2] bg-white px-[18px] text-[13px] font-bold text-ink"
                >
                  Remover
                </button>
              )}
              <button className="previa-btn h-10" onClick={pedirEnvio} disabled={!arquivo || enviando}>
                {enviando ? "ENVIANDO…" : modo === "completa" ? "SUBSTITUIR BASE" : "ENVIAR ARQUIVO"}
              </button>
            </div>
          </div>

          {/* Resultado */}
          {atual && <Resultado importacao={atual} />}
        </div>

        {/* Ajuda */}
        <div className="previa-card flex flex-col gap-3.5 px-[22px] py-5">
          <h3 className="text-base font-bold">Formato esperado</h3>
          <div>
            <span className="text-[13px] font-semibold text-ink">Colunas obrigatórias</span>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {COLUNAS.map((c) => (
                <code key={c} className="rounded-md bg-surface-app px-2 py-0.5 font-mono text-xs text-[#123a66]">
                  {c}
                </code>
              ))}
            </div>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              O <b>setor</b> é o centro de custo do consumo.
            </p>
          </div>
          <div>
            <span className="text-[13px] font-semibold text-ink">Colunas opcionais do material</span>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {COLUNAS_OPCIONAIS.map((c) => (
                <code key={c} className="rounded-md bg-surface-app px-2 py-0.5 font-mono text-xs text-[#123a66]">
                  {c}
                </code>
              ))}
            </div>
            <p className="mt-2 text-xs leading-relaxed text-muted">
              Também são aceitos os nomes do sistema de origem: <code className="font-mono">CD_MATERIAL</code>,{" "}
              <code className="font-mono">DS_MATERIAL</code>, <code className="font-mono">DT_MES</code>,{" "}
              <code className="font-mono">QT_CONSUMO</code>, <code className="font-mono">VL_CONSUMO</code>,{" "}
              <code className="font-mono">DS_CENTRO_CUSTO</code>, <code className="font-mono">DS_GRUPO_MATERIAL</code>,{" "}
              <code className="font-mono">DS_SUBGRUPO_MATERIAL</code>, <code className="font-mono">DS_CLASSE_MATERIAL</code>{" "}
              e <code className="font-mono">CD_UNID</code>.
            </p>
          </div>
          <div className="border-t border-line-200 pt-3.5">
            <span className="text-[13px] font-semibold text-ink">Validações automáticas</span>
            <ul className="mt-2 flex flex-col gap-1.5 text-[13px] text-ink-700">
              {[
                "Campos obrigatórios vazios",
                "Linhas duplicadas",
                "Datas (dd/mm/aaaa, aaaa-mm-dd ou competência mensal)",
                "Quantidade e valor numéricos e maiores que zero",
                "Agregação por mês, material e setor",
              ].map((v) => (
                <li key={v} className="flex items-start gap-2">
                  <span className="mt-[7px] h-1.5 w-1.5 flex-none rounded-full bg-brand" />
                  {v}
                </li>
              ))}
            </ul>
          </div>
          <p className="border-t border-line-200 pt-3.5 text-xs leading-relaxed text-muted">
            Arquivos grandes são processados em lotes. As linhas inválidas são descartadas e listadas no resultado;
            as válidas entram na base. Se a importação falhar, nada do arquivo fica gravado e a base anterior é
            mantida — inclusive na importação completa.
          </p>
        </div>
      </div>

      {/* Integração via API */}
      <IntegracaoApi notificar={notificar} />

      {/* Histórico */}
      <div className="previa-card overflow-hidden p-0">
        <h3 className="px-[22px] py-4 text-base font-bold">Histórico de importações</h3>
        <div className="grid grid-cols-[150px_minmax(180px,2fr)_120px_100px_170px] gap-3 border-y border-line-200 bg-surface-panel px-[22px] py-2.5 text-xs font-bold text-muted">
          <span>Data</span>
          <span>Arquivo</span>
          <span className="text-right">Válidos / total</span>
          <span className="text-right">Inválidos</span>
          <span>Status</span>
        </div>
        {historico === null ? (
          <div className="px-7 py-7 text-center text-sm text-muted">{erroHistorico || "Carregando…"}</div>
        ) : historico.length === 0 ? (
          <div className="px-7 py-7 text-center text-sm text-muted">Nenhuma importação realizada ainda.</div>
        ) : (
          historico.map((h) => {
            const s = situacao(h);
            return (
              <button
                key={h.id}
                onClick={() => setAtual(h)}
                title="Ver detalhes"
                className="grid w-full grid-cols-[150px_minmax(180px,2fr)_120px_100px_170px] items-center gap-3 border-b border-[#F0F4F8] px-[22px] py-3 text-left text-[13px] transition hover:bg-[#F5F9FD]"
                style={{ background: atual?.id === h.id ? "#EAF3FB" : undefined }}
              >
                <span className="text-muted">{fmtDataHora(h.criado_em)}</span>
                <span className="flex min-w-0 flex-col">
                  <span className="truncate font-semibold">{h.nome_arquivo}</span>
                  <span className="text-[11.5px] text-muted-400">
                    {h.tipo === "api" ? "Via API · " : "Arquivo · "}
                    {h.modo === "completa" ? "Completa (substituiu a base)" : "Incremental"}
                  </span>
                </span>
                <span className="text-right">
                  {fmtNumero(h.registros_validos)} / {fmtNumero(h.total_registros)}
                </span>
                <span className="text-right">{fmtNumero(h.registros_invalidos)}</span>
                <span>
                  <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${s.classe}`}>{s.rotulo}</span>
                </span>
              </button>
            );
          })
        )}
      </div>

      {confirmarCompleta && arquivo && (
        <Modal
          titulo="Substituir toda a base de consumo?"
          onFechar={() => setConfirmarCompleta(false)}
          rodape={
            <>
              <button
                onClick={() => setConfirmarCompleta(false)}
                className="h-10 rounded-full border border-[#CBD6E2] bg-white px-[18px] text-[13px] font-bold text-ink"
              >
                Cancelar
              </button>
              <button
                onClick={enviar}
                className="h-10 rounded-full bg-[#C23B4E] px-[22px] text-[13px] font-extrabold tracking-wide text-white transition hover:bg-[#A82F41]"
              >
                SUBSTITUIR BASE
              </button>
            </>
          }
        >
          <p className="text-sm leading-relaxed text-ink-700">
            Todo o consumo já importado deste hospital será apagado e substituído pelo conteúdo de{" "}
            <b className="break-all">{arquivo.name}</b>. Os gráficos, a curva ABC e os relatórios passam a refletir só
            este arquivo.
          </p>
          <p className="text-[13px] leading-relaxed text-muted">
            A troca só acontece se o arquivo for processado com sucesso; se der erro, a base atual é mantida.
          </p>
        </Modal>
      )}

      <Toast mensagem={mensagem} />
    </>
  );
}

function Resultado({ importacao: i }: { importacao: ImportacaoResponse }) {
  const s = situacao(i);
  const erros = i.erros ?? [];
  const processando = i.status === "processando";

  return (
    <div className="previa-card flex flex-col gap-4 px-[22px] py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="text-xs text-muted">Resultado da importação</span>
          <h3 className="truncate text-base font-bold">{i.nome_arquivo}</h3>
        </div>
        <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${s.classe}`}>{s.rotulo}</span>
      </div>

      {processando && (
        <div className="h-1.5 overflow-hidden rounded-full bg-surface-app">
          <div className="h-full w-1/3 animate-pulse rounded-full bg-brand" />
        </div>
      )}

      <div className="grid grid-cols-3 gap-3">
        {[
          { rotulo: processando ? "Linhas lidas até agora" : "Linhas lidas", valor: i.total_registros },
          { rotulo: "Válidas", valor: i.registros_validos },
          { rotulo: "Inválidas", valor: i.registros_invalidos },
        ].map((c) => (
          <div key={c.rotulo} className="rounded-[10px] bg-surface-panel px-3.5 py-2.5">
            <span className="block text-xs text-muted">{c.rotulo}</span>
            <span className="text-lg font-extrabold text-navy">{fmtNumero(c.valor)}</span>
          </div>
        ))}
      </div>

      {!processando &&
        (erros.length > 0 ? (
          <div>
            <span className="text-[13px] font-semibold text-ink">
              {i.status === "erro" ? "Motivo da falha" : "Linhas com problema"}
            </span>
            <ul className="mt-2 flex max-h-[220px] flex-col gap-1 overflow-y-auto rounded-[10px] border border-line-200 px-3.5 py-2.5 font-mono text-xs text-ink-700">
              {erros.slice(0, MAX_ERROS_EXIBIDOS).map((e, k) => (
                <li key={k}>{e}</li>
              ))}
            </ul>
            {erros.length > MAX_ERROS_EXIBIDOS && (
              <p className="mt-1.5 text-xs text-muted">
                Mostrando {MAX_ERROS_EXIBIDOS} de {fmtNumero(erros.length)} mensagens.
              </p>
            )}
          </div>
        ) : (
          <p className="text-[13px] text-[#1F7A50]">Nenhum problema encontrado nas linhas.</p>
        ))}

      {i.status === "concluido" && i.registros_validos > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] bg-surface-sky px-4 py-3 text-[13px] text-[#123a66]">
          <span>
            <b>Dados na base.</b> Próximo passo: gerar as previsões com o histórico atualizado.
          </span>
          <Link href="/previsoes" className="font-bold text-brand-800 hover:underline">
            Ir para Previsões →
          </Link>
        </div>
      )}
    </div>
  );
}
