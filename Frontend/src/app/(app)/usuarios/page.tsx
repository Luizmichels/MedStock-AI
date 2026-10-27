"use client";

import { useCallback, useEffect, useState } from "react";
import Modal from "@/components/Modal";
import PageHeader from "@/components/PageHeader";
import Toast, { useToast } from "@/components/Toast";
import {
  UsuarioResponse,
  UsuarioUpdate,
  atualizarUsuario,
  criarUsuario,
  desativarUsuario,
  listarUsuarios,
} from "@/lib/api";
import { papel, useAuth } from "@/lib/auth";
import { mensagemErro } from "@/lib/erros";

const SENHA_MINIMA = 8;

type PerfilEditavel = "admin" | "usuario";

interface Formulario {
  id: number | null; // null = novo usuário
  nome: string;
  email: string;
  perfil: PerfilEditavel;
  senha: string;
}

const PERFIS: { valor: PerfilEditavel; rotulo: string; descricao: string }[] = [
  { valor: "usuario", rotulo: "Usuário", descricao: "Dashboard, Previsões e Exportar relatório." },
  {
    valor: "admin",
    rotulo: "Administrador",
    descricao: "Acesso completo ao hospital, incluindo Importar dados e Gestão de usuários.",
  },
];

function rotuloPerfil(perfil: string): string {
  return perfil === "admin" ? "Administrador" : perfil === "super_admin" ? "Super Usuário" : "Usuário";
}

export default function UsuariosPage() {
  const { usuario } = useAuth();
  const isAdmin = papel(usuario?.perfil ?? "usuario") === "admin";
  const { mensagem, notificar } = useToast();

  const [usuarios, setUsuarios] = useState<UsuarioResponse[] | null>(null);
  const [erro, setErro] = useState("");
  const [processandoId, setProcessandoId] = useState<number | null>(null);

  const [form, setForm] = useState<Formulario | null>(null);
  const [erroForm, setErroForm] = useState("");
  const [salvando, setSalvando] = useState(false);

  const carregar = useCallback(async () => {
    try {
      const lista = await listarUsuarios();
      // Ativos primeiro, depois por nome.
      lista.sort((a, b) => Number(b.ativo) - Number(a.ativo) || a.nome.localeCompare(b.nome, "pt-BR"));
      setUsuarios(lista);
      setErro("");
    } catch (e) {
      setErro(mensagemErro(e, "Não foi possível carregar os usuários."));
    }
  }, []);

  useEffect(() => {
    if (isAdmin) carregar();
  }, [isAdmin, carregar]);

  const ehVoce = (u: UsuarioResponse) => String(u.id) === usuario?.id;

  async function alternarStatus(u: UsuarioResponse) {
    setProcessandoId(u.id);
    try {
      if (u.ativo) await desativarUsuario(u.id);
      else await atualizarUsuario(u.id, { ativo: true });
      notificar(`${u.nome} foi ${u.ativo ? "inativado" : "reativado"}.`);
      await carregar();
    } catch (e) {
      notificar(mensagemErro(e));
    } finally {
      setProcessandoId(null);
    }
  }

  function abrirNovo() {
    setErroForm("");
    setForm({ id: null, nome: "", email: "", perfil: "usuario", senha: "" });
  }

  function abrirEdicao(u: UsuarioResponse) {
    setErroForm("");
    setForm({
      id: u.id,
      nome: u.nome,
      email: u.email,
      perfil: u.perfil === "admin" ? "admin" : "usuario",
      senha: "",
    });
  }

  async function salvar() {
    if (!form) return;
    const nome = form.nome.trim();
    const email = form.email.trim();
    const novo = form.id === null;
    if (!nome) return setErroForm("Informe o nome.");
    if (!/^\S+@\S+\.\S+$/.test(email)) return setErroForm("Informe um e-mail válido.");
    if (novo && form.senha.length < SENHA_MINIMA)
      return setErroForm(`A senha inicial deve ter pelo menos ${SENHA_MINIMA} caracteres.`);
    if (!novo && form.senha && form.senha.length < SENHA_MINIMA)
      return setErroForm(`A nova senha deve ter pelo menos ${SENHA_MINIMA} caracteres.`);

    setSalvando(true);
    setErroForm("");
    try {
      if (novo) {
        await criarUsuario({ nome, email, perfil: form.perfil, senha: form.senha });
        notificar(`${nome} foi cadastrado. Repasse a senha inicial a ele.`);
      } else {
        const dados: UsuarioUpdate = { nome, email, perfil: form.perfil };
        if (form.senha) dados.senha = form.senha;
        await atualizarUsuario(form.id as number, dados);
        notificar("Usuário atualizado.");
      }
      setForm(null);
      await carregar();
    } catch (e) {
      setErroForm(mensagemErro(e, "Não foi possível salvar o usuário."));
    } finally {
      setSalvando(false);
    }
  }

  if (!isAdmin) {
    return (
      <>
        <PageHeader title="Gestão de usuários" subtitle="Cadastre usuários e defina o perfil de acesso" />
        <div className="previa-card px-6 py-12 text-center text-sm text-muted">
          Apenas administradores do hospital podem gerenciar usuários.
        </div>
      </>
    );
  }

  const editandoVoce = form?.id != null && String(form.id) === usuario?.id;

  return (
    <>
      <PageHeader title="Gestão de usuários" subtitle="Cadastre usuários e defina o perfil de acesso" />

      <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-4">
        {PERFIS.map((p) => (
          <div key={p.valor} className="previa-card flex flex-col gap-1 px-5 py-4">
            <span className="font-bold">{p.rotulo}</span>
            <span className="text-[13px] leading-relaxed text-muted">{p.descricao}</span>
          </div>
        ))}
      </div>

      <div className="previa-card overflow-hidden p-0">
        <div className="flex flex-wrap items-center justify-between gap-3 px-[22px] py-4">
          <h3 className="text-base font-bold">
            {usuarios ? `${usuarios.length} ${usuarios.length === 1 ? "usuário cadastrado" : "usuários cadastrados"}` : "Usuários"}
          </h3>
          <button
            onClick={abrirNovo}
            className="h-[38px] rounded-full bg-brand px-5 text-[13px] font-extrabold tracking-wide text-white transition hover:bg-brand-600"
          >
            + NOVO USUÁRIO
          </button>
        </div>
        <div className="grid grid-cols-[minmax(170px,1.4fr)_minmax(200px,1.6fr)_130px_100px_190px] gap-3 border-y border-line-200 bg-surface-panel px-[22px] py-2.5 text-xs font-bold text-muted">
          <span>Nome</span>
          <span>E-mail</span>
          <span>Perfil</span>
          <span>Status</span>
          <span className="text-right">Ações</span>
        </div>

        {usuarios === null ? (
          <div className="px-7 py-7 text-center text-sm text-muted">{erro || "Carregando…"}</div>
        ) : usuarios.length === 0 ? (
          <div className="px-7 py-7 text-center text-sm text-muted">Nenhum usuário cadastrado.</div>
        ) : (
          usuarios.map((u) => {
            const voce = ehVoce(u);
            // Conta da plataforma: o perfil super_admin não existe no formulário, e
            // editá-la aqui rebaixaria o super usuário. Fica fora do alcance desta tela.
            const plataforma = u.perfil === "super_admin";
            return (
              <div
                key={u.id}
                className="grid grid-cols-[minmax(170px,1.4fr)_minmax(200px,1.6fr)_130px_100px_190px] items-center gap-3 border-b border-[#F0F4F8] px-[22px] py-3 text-[13px]"
                style={{ opacity: u.ativo ? 1 : 0.65 }}
              >
                <span className="truncate font-semibold">
                  {u.nome}
                  {voce && <span className="ml-1.5 font-normal text-muted-400">(você)</span>}
                </span>
                <span className="truncate text-ink-700">{u.email}</span>
                <span>{rotuloPerfil(u.perfil)}</span>
                <span>
                  <span
                    className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-bold ${
                      u.ativo ? "bg-[#E3F3EA] text-[#1F7A50]" : "bg-[#ECEFF3] text-[#5B6B7E]"
                    }`}
                  >
                    {u.ativo ? "Ativo" : "Inativo"}
                  </span>
                </span>
                <span className="flex justify-end gap-2">
                  {plataforma ? (
                    <span className="text-xs text-muted-400">Gerenciado pela plataforma</span>
                  ) : (
                  <>
                  <button
                    onClick={() => abrirEdicao(u)}
                    className="h-[30px] rounded-full border border-[#CBD6E2] bg-white px-3 text-xs font-bold text-ink transition hover:border-brand"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => alternarStatus(u)}
                    disabled={voce || processandoId === u.id}
                    title={voce ? "Você não pode inativar a própria conta" : undefined}
                    className="h-[30px] rounded-full border border-[#CBD6E2] bg-white px-3 text-xs font-bold text-ink transition hover:border-brand disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-[#CBD6E2]"
                  >
                    {processandoId === u.id ? "…" : u.ativo ? "Inativar" : "Reativar"}
                  </button>
                  </>
                  )}
                </span>
              </div>
            );
          })
        )}
      </div>

      {form && (
        <Modal
          titulo={form.id === null ? "Novo usuário" : "Editar usuário"}
          onFechar={() => setForm(null)}
          rodape={
            <>
              <button
                onClick={() => setForm(null)}
                className="h-10 rounded-full border border-[#CBD6E2] bg-white px-[18px] text-[13px] font-bold text-ink"
              >
                Cancelar
              </button>
              <button
                onClick={salvar}
                disabled={salvando}
                className="h-10 rounded-full bg-brand px-[22px] text-[13px] font-extrabold tracking-wide text-white transition hover:bg-brand-600 disabled:opacity-60"
              >
                {salvando ? "SALVANDO…" : "SALVAR"}
              </button>
            </>
          }
        >
          <CampoTexto rotulo="Nome completo" valor={form.nome} onChange={(v) => setForm({ ...form, nome: v })} />
          <CampoTexto
            rotulo="E-mail"
            tipo="email"
            valor={form.email}
            onChange={(v) => setForm({ ...form, email: v })}
          />

          <div className="flex flex-col gap-1.5 text-[13px] text-muted">
            Perfil de acesso
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {PERFIS.map((p) => {
                const marcado = form.perfil === p.valor;
                return (
                  <label
                    key={p.valor}
                    className={`flex cursor-pointer items-start gap-2.5 rounded-[10px] border p-3 transition ${
                      marcado ? "border-brand bg-surface-sky" : "border-line"
                    } ${editandoVoce ? "cursor-not-allowed opacity-60" : ""}`}
                  >
                    <input
                      type="radio"
                      name="perfil"
                      checked={marcado}
                      disabled={editandoVoce}
                      onChange={() => setForm({ ...form, perfil: p.valor })}
                      className="mt-[3px] accent-[#3B97CF]"
                    />
                    <span>
                      <b className="block text-[13.5px] text-ink">{p.rotulo}</b>
                      <span className="text-xs leading-snug text-muted">{p.descricao}</span>
                    </span>
                  </label>
                );
              })}
            </div>
            {editandoVoce && (
              <span className="text-xs text-muted-400">Você não pode alterar o próprio perfil de acesso.</span>
            )}
          </div>

          <CampoTexto
            rotulo={form.id === null ? "Senha inicial" : "Nova senha (opcional)"}
            tipo="password"
            valor={form.senha}
            onChange={(v) => setForm({ ...form, senha: v })}
            ajuda={
              form.id === null
                ? `Mínimo de ${SENHA_MINIMA} caracteres. Repasse ao usuário; ele pode trocá-la em "Esqueceu a senha?".`
                : "Deixe em branco para manter a senha atual."
            }
          />

          {erroForm && <p className="text-[13px] font-semibold text-[#C23B4E]">{erroForm}</p>}
        </Modal>
      )}

      <Toast mensagem={mensagem} />
    </>
  );
}

function CampoTexto({
  rotulo,
  valor,
  onChange,
  tipo = "text",
  ajuda,
}: {
  rotulo: string;
  valor: string;
  onChange: (v: string) => void;
  tipo?: string;
  ajuda?: string;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-[13px] text-muted">
      {rotulo}
      <input
        type={tipo}
        value={valor}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={tipo === "password" ? "new-password" : "off"}
        className="h-10 rounded-lg border border-[#CBD6E2] px-3 text-sm text-ink outline-none focus:border-brand focus:ring-4 focus:ring-brand/20"
      />
      {ajuda && <span className="text-xs text-muted-400">{ajuda}</span>}
    </label>
  );
}
