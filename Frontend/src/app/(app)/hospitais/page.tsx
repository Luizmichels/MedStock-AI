"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import PageHeader from "@/components/PageHeader";
import {
  ApiError,
  EmpresaResponse,
  SolicitacaoResponse,
  atualizarEmpresa,
  atualizarSolicitacao,
  esqueciSenha,
  listarEmpresas,
  listarSolicitacoesPendentes,
  reenviarAtivacao,
} from "@/lib/api";

/** Intervalo mínimo (s) entre dois reenvios do e-mail de acesso. */
const ESPERA_REENVIO = 60;

type StatusLinha = "Ativo" | "Inativo" | "Pendente";

interface Linha {
  tipo: "empresa" | "solicitacao";
  id: number;
  resp: string;
  email: string;
  hosp: string;
  status: StatusLinha;
  empresa?: EmpresaResponse;
}

const BADGE: Record<StatusLinha, string> = {
  Ativo: "bg-[#E3F3EA] text-[#1F7A50]",
  Pendente: "bg-[#FDF1DC] text-[#9A6212]",
  Inativo: "bg-[#ECEFF3] text-[#5B6B7E]",
};

function mensagemErro(e: unknown): string {
  if (e instanceof ApiError) return typeof e.detail === "string" ? e.detail : e.message;
  return "Algo deu errado. Tente novamente.";
}

export default function HospitaisPage() {
  const [empresas, setEmpresas] = useState<EmpresaResponse[]>([]);
  const [solicitacoes, setSolicitacoes] = useState<SolicitacaoResponse[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");

  const [busca, setBusca] = useState("");
  const [filtro, setFiltro] = useState<"Todos" | StatusLinha>("Todos");

  const [toast, setToast] = useState("");
  const [processando, setProcessando] = useState<string | null>(null); // "tipo-id"
  const [reprovarId, setReprovarId] = useState<number | null>(null);
  const [editar, setEditar] = useState<EmpresaResponse | null>(null);

  const recarregar = useCallback(async () => {
    setErro("");
    try {
      const [emp, sol] = await Promise.all([listarEmpresas(), listarSolicitacoesPendentes()]);
      setEmpresas(emp);
      setSolicitacoes(sol);
    } catch (e) {
      setErro(mensagemErro(e));
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    recarregar();
  }, [recarregar]);

  function notificar(msg: string) {
    setToast(msg);
    window.setTimeout(() => setToast(""), 3500);
  }

  // Monta a tabela única: pendentes primeiro, depois instituições.
  const linhas = useMemo<Linha[]>(() => {
    const dePendentes: Linha[] = solicitacoes.map((s) => ({
      tipo: "solicitacao",
      id: s.id,
      resp: s.nome_responsavel,
      email: s.email,
      hosp: s.nome_hospital,
      status: "Pendente",
    }));
    const deEmpresas: Linha[] = empresas.map((e) => ({
      tipo: "empresa",
      id: e.id,
      resp: e.nome_responsavel,
      email: e.email_responsavel,
      hosp: e.nome,
      status: e.ativa ? "Ativo" : "Inativo",
      empresa: e,
    }));
    return [...dePendentes, ...deEmpresas];
  }, [empresas, solicitacoes]);

  const linhasFiltradas = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return linhas.filter(
      (l) =>
        (filtro === "Todos" || l.status === filtro) &&
        (!q || `${l.hosp} ${l.resp} ${l.email}`.toLowerCase().includes(q)),
    );
  }, [linhas, busca, filtro]);

  const kpis = useMemo(
    () => [
      { label: "Instituições ativas", valor: empresas.filter((e) => e.ativa).length, dot: "#2E9E6A" },
      { label: "Solicitações pendentes", valor: solicitacoes.length, dot: "#D9962B" },
      { label: "Instituições inativas", valor: empresas.filter((e) => !e.ativa).length, dot: "#9AA8B8" },
      { label: "Total cadastrado", valor: empresas.length, dot: "#4AA8E0" },
    ],
    [empresas, solicitacoes],
  );

  async function aprovar(id: number) {
    setProcessando(`sol-${id}`);
    try {
      await atualizarSolicitacao(id, "aprovado");
      notificar("Solicitação aprovada. Credenciais enviadas por e-mail.");
      await recarregar();
    } catch (e) {
      notificar(mensagemErro(e));
    } finally {
      setProcessando(null);
    }
  }

  async function confirmarReprovar() {
    if (reprovarId == null) return;
    const id = reprovarId;
    setReprovarId(null);
    setProcessando(`sol-${id}`);
    try {
      await atualizarSolicitacao(id, "rejeitado");
      notificar("Solicitação reprovada. O responsável foi avisado por e-mail.");
      await recarregar();
    } catch (e) {
      notificar(mensagemErro(e));
    } finally {
      setProcessando(null);
    }
  }

  async function salvarEdicao(dados: {
    nome: string;
    nome_responsavel: string;
    email_responsavel: string;
    ativa: boolean;
  }) {
    if (!editar) return;
    setProcessando(`emp-${editar.id}`);
    try {
      await atualizarEmpresa(editar.id, dados);
      notificar("Instituição atualizada.");
      setEditar(null);
      await recarregar();
    } catch (e) {
      notificar(mensagemErro(e));
    } finally {
      setProcessando(null);
    }
  }

  const reprovarAlvo = solicitacoes.find((s) => s.id === reprovarId) || null;

  return (
    <>
      <PageHeader
        title="Gestão de hospitais"
        subtitle="Instituições cadastradas e solicitações de acesso"
      />

      {/* KPIs */}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-4">
        {kpis.map((k) => (
          <div key={k.label} className="previa-card flex flex-col gap-1.5 px-5 py-[18px]">
            <span className="flex items-center gap-2 text-[13px] text-muted">
              <span className="h-2 w-2 rounded-full" style={{ background: k.dot }} />
              {k.label}
            </span>
            <span className="text-[30px] font-extrabold text-navy">
              {carregando ? "—" : k.valor}
            </span>
          </div>
        ))}
      </div>

      {/* Tabela */}
      <div className="previa-card overflow-hidden p-0">
        <div className="flex flex-wrap items-center justify-between gap-3 px-[22px] py-4">
          <h3 className="text-base font-bold">Instituições</h3>
          <div className="flex flex-wrap gap-2.5">
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar hospital"
              className="h-9 w-60 rounded-lg border border-[#CBD6E2] px-3 text-[13px] outline-none focus:border-brand"
            />
            <select
              value={filtro}
              onChange={(e) => setFiltro(e.target.value as typeof filtro)}
              className="h-9 rounded-lg border border-[#CBD6E2] bg-white px-2.5 text-[13px] text-ink"
            >
              <option value="Todos">Todos os status</option>
              <option value="Ativo">Ativo</option>
              <option value="Pendente">Pendente</option>
              <option value="Inativo">Inativo</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-[minmax(160px,1.2fr)_minmax(200px,1.5fr)_minmax(200px,1.6fr)_110px_200px] gap-3 border-y border-line-200 bg-surface-panel px-[22px] py-2.5 text-xs font-bold text-muted">
          <span>Responsável</span>
          <span>E-mail</span>
          <span>Hospital</span>
          <span>Status</span>
          <span className="text-right">Ações</span>
        </div>

        {carregando ? (
          <div className="px-[22px] py-8 text-center text-sm text-muted">Carregando…</div>
        ) : erro ? (
          <div className="px-[22px] py-8 text-center text-sm text-[#C23B4E]">{erro}</div>
        ) : linhasFiltradas.length === 0 ? (
          <div className="px-[22px] py-8 text-center text-sm text-muted">
            Nenhuma instituição encontrada.
          </div>
        ) : (
          linhasFiltradas.map((l) => {
            const ocupado = processando === `${l.tipo === "solicitacao" ? "sol" : "emp"}-${l.id}`;
            return (
              <div
                key={`${l.tipo}-${l.id}`}
                className="grid grid-cols-[minmax(160px,1.2fr)_minmax(200px,1.5fr)_minmax(200px,1.6fr)_110px_200px] items-center gap-3 border-b border-[#F0F4F8] px-[22px] py-3 text-[13px]"
                style={{ background: l.status === "Pendente" ? "#FFFCF5" : "#fff" }}
              >
                <span className="font-semibold">{l.resp}</span>
                <span className="text-ink-700">{l.email}</span>
                <span>{l.hosp}</span>
                <span>
                  <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${BADGE[l.status]}`}>
                    {l.status}
                  </span>
                </span>
                <span className="flex justify-end gap-2">
                  {l.tipo === "solicitacao" ? (
                    <>
                      <button
                        onClick={() => aprovar(l.id)}
                        disabled={ocupado}
                        className="h-[30px] rounded-full bg-[#2E9E6A] px-3.5 text-xs font-bold text-white disabled:opacity-50"
                      >
                        {ocupado ? "…" : "Aprovar"}
                      </button>
                      <button
                        onClick={() => setReprovarId(l.id)}
                        disabled={ocupado}
                        className="h-[30px] rounded-full border border-[#E3B3BB] bg-white px-3.5 text-xs font-bold text-[#B0364A] disabled:opacity-50"
                      >
                        Reprovar
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => l.empresa && setEditar(l.empresa)}
                      className="h-[30px] rounded-full border border-[#CBD6E2] bg-white px-3.5 text-xs font-bold text-ink hover:border-brand"
                    >
                      Editar
                    </button>
                  )}
                </span>
              </div>
            );
          })
        )}
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 z-30 flex items-center gap-2.5 rounded-xl border border-navy-600 bg-navy px-[18px] py-3.5 text-sm text-white shadow-[0_12px_30px_rgba(0,0,0,.3)]">
          <span className="h-2 w-2 rounded-full bg-brand" />
          {toast}
        </div>
      )}

      {reprovarAlvo && (
        <ConfirmarReprovar
          alvo={reprovarAlvo}
          onCancelar={() => setReprovarId(null)}
          onConfirmar={confirmarReprovar}
        />
      )}

      {editar && (
        <ModalEditar empresa={editar} onFechar={() => setEditar(null)} onSalvar={salvarEdicao} />
      )}
    </>
  );
}

function ConfirmarReprovar({
  alvo,
  onCancelar,
  onConfirmar,
}: {
  alvo: SolicitacaoResponse;
  onCancelar: () => void;
  onConfirmar: () => void;
}) {
  return (
    <div
      onClick={onCancelar}
      className="fixed inset-0 z-40 grid place-items-center bg-[rgba(7,26,46,.55)] p-5"
    >
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-[440px] overflow-hidden rounded-2xl bg-white shadow-[0_30px_80px_rgba(0,0,0,.35)]">
        <div className="border-b border-line-200 px-5 py-4">
          <h3 className="text-base font-bold text-ink">Reprovar solicitação</h3>
        </div>
        <p className="px-5 py-5 text-sm leading-relaxed text-ink-700">
          Reprovar a solicitação de acesso de <b className="text-ink">{alvo.nome_hospital}</b>?{" "}
          {alvo.nome_responsavel} será avisado(a) por e-mail em <b className="text-ink">{alvo.email}</b>.
        </p>
        <div className="flex justify-end gap-2.5 border-t border-line-200 px-5 py-3.5">
          <button onClick={onCancelar} className="h-9 rounded-lg px-4 text-[13px] font-semibold text-ink-700 hover:bg-surface-app">
            Cancelar
          </button>
          <button
            onClick={onConfirmar}
            className="h-9 rounded-lg border border-[#E3B3BB] bg-white px-4 text-[13px] font-bold text-[#B0364A] hover:bg-[#FDF2F4]"
          >
            Reprovar
          </button>
        </div>
      </div>
    </div>
  );
}

function ModalEditar({
  empresa,
  onFechar,
  onSalvar,
}: {
  empresa: EmpresaResponse;
  onFechar: () => void;
  onSalvar: (dados: {
    nome: string;
    nome_responsavel: string;
    email_responsavel: string;
    ativa: boolean;
  }) => void;
}) {
  const [nome, setNome] = useState(empresa.nome);
  const [resp, setResp] = useState(empresa.nome_responsavel);
  const [email, setEmail] = useState(empresa.email_responsavel);
  const [status, setStatus] = useState<"Ativo" | "Inativo">(empresa.ativa ? "Ativo" : "Inativo");

  const [reenviando, setReenviando] = useState(false);
  const [espera, setEspera] = useState(0);
  const [retornoReenvio, setRetornoReenvio] = useState<{ ok: boolean; texto: string } | null>(null);

  useEffect(() => {
    if (espera <= 0) return;
    const t = setTimeout(() => setEspera((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [espera]);

  async function reenviarAcesso() {
    // Usa o e-mail SALVO (o usuário admin foi criado com ele na aprovação),
    // não o que estiver sendo editado no campo acima.
    const destino = empresa.email_responsavel;
    setReenviando(true);
    setRetornoReenvio(null);
    try {
      // Nunca ativou -> link de definir senha; já ativou -> link de redefinir.
      // As rotas são excludentes, então sai no máximo um e-mail.
      await Promise.all([esqueciSenha(destino), reenviarAtivacao(destino)]);
      setRetornoReenvio({ ok: true, texto: "Pedido enviado. Se houver um usuário com este e-mail, o link chega em instantes." });
      setEspera(ESPERA_REENVIO);
    } catch (e) {
      setRetornoReenvio({ ok: false, texto: mensagemErro(e) });
    } finally {
      setReenviando(false);
    }
  }

  return (
    <div onClick={onFechar} className="fixed inset-0 z-40 grid place-items-center bg-[rgba(7,26,46,.55)] p-5">
      <div onClick={(e) => e.stopPropagation()} className="flex w-full max-w-[460px] flex-col gap-4 rounded-2xl bg-white px-7 py-6 shadow-[0_30px_80px_rgba(0,0,0,.35)]">
        <h3 className="text-lg font-extrabold text-navy">Editar instituição</h3>

        <CampoModal label="Hospital" value={nome} onChange={setNome} />
        <CampoModal label="Responsável" value={resp} onChange={setResp} />
        <CampoModal label="E-mail" value={email} onChange={setEmail} />

        <label className="flex flex-col gap-1.5 text-[13px] text-muted">
          Status
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as "Ativo" | "Inativo")}
            className="h-10 rounded-lg border border-[#CBD6E2] bg-white px-2.5 text-sm text-ink"
          >
            <option value="Ativo">Ativo</option>
            <option value="Inativo">Inativo</option>
          </select>
        </label>

        <div className="flex flex-col gap-2 rounded-xl border border-line bg-surface-panel px-4 py-3">
          <span className="text-[13px] font-bold text-ink">Acesso do responsável</span>
          <span className="text-xs leading-relaxed text-muted">
            Reenvia para <b className="text-ink">{empresa.email_responsavel}</b> o link para criar a senha
            (primeiro acesso) ou redefini-la.
          </span>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={reenviarAcesso}
              disabled={reenviando || espera > 0}
              className="h-9 rounded-full border border-brand bg-white px-4 text-[13px] font-bold text-brand-800 transition hover:bg-surface-sky disabled:cursor-not-allowed disabled:border-line disabled:text-muted-400 disabled:hover:bg-white"
            >
              {reenviando
                ? "Enviando…"
                : espera > 0
                  ? `Reenviar em 0:${String(espera).padStart(2, "0")}`
                  : "Reenviar e-mail de acesso"}
            </button>
          </div>
          {retornoReenvio && (
            <span
              className={`text-[12.5px] font-semibold ${retornoReenvio.ok ? "text-[#1F7A50]" : "text-[#C23B4E]"}`}
            >
              {retornoReenvio.texto}
            </span>
          )}
        </div>

        <div className="mt-1.5 flex justify-end gap-2.5">
          <button onClick={onFechar} className="h-10 rounded-full border border-[#CBD6E2] bg-white px-[18px] text-[13px] font-bold text-ink">
            Cancelar
          </button>
          <button
            onClick={() =>
              onSalvar({
                nome: nome.trim(),
                nome_responsavel: resp.trim(),
                email_responsavel: email.trim(),
                ativa: status === "Ativo",
              })
            }
            className="h-10 rounded-full bg-brand px-[22px] text-[13px] font-extrabold tracking-wide text-white hover:bg-brand-600"
          >
            SALVAR
          </button>
        </div>
      </div>
    </div>
  );
}

function CampoModal({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-[13px] text-muted">
      {label}
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-10 rounded-lg border border-[#CBD6E2] px-3 text-sm text-ink outline-none focus:border-brand"
      />
    </label>
  );
}
