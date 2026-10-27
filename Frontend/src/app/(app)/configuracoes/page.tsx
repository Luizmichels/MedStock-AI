"use client";

import { useEffect, useState } from "react";
import Campo from "@/components/Campo";
import PageHeader from "@/components/PageHeader";
import Toast, { useToast } from "@/components/Toast";
import { atualizarMeuPerfil, trocarMinhaSenha } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { mensagemErro } from "@/lib/erros";

const TAMANHO_MINIMO = 8;
const EMAIL_VALIDO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ConfiguracoesPage() {
  const { mensagem, notificar } = useToast();
  return (
    <>
      <PageHeader title="Minha conta" subtitle="Altere seu nome, e-mail de acesso e senha" />
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2">
        <DadosPessoais notificar={notificar} />
        <TrocarSenha notificar={notificar} />
      </div>
      <Toast mensagem={mensagem} />
    </>
  );
}

function DadosPessoais({ notificar }: { notificar: (m: string) => void }) {
  const { usuario, atualizarUsuario } = useAuth();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senhaAtual, setSenhaAtual] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    setNome(usuario?.nome ?? "");
    setEmail(usuario?.email ?? "");
  }, [usuario?.nome, usuario?.email]);

  const nomeLimpo = nome.trim();
  const emailLimpo = email.trim().toLowerCase();
  const mudouNome = nomeLimpo !== (usuario?.nome ?? "");
  const mudouEmail = emailLimpo !== (usuario?.email ?? "").toLowerCase();

  async function salvar() {
    if (!nomeLimpo) return setErro("Informe o seu nome.");
    if (!EMAIL_VALIDO.test(emailLimpo)) return setErro("Informe um e-mail válido.");
    if (mudouEmail && !senhaAtual) return setErro("Para trocar o e-mail, confirme a sua senha atual.");
    setSalvando(true);
    setErro("");
    try {
      const atualizado = await atualizarMeuPerfil({
        ...(mudouNome ? { nome: nomeLimpo } : {}),
        ...(mudouEmail ? { email: emailLimpo, senha_atual: senhaAtual } : {}),
      });
      atualizarUsuario({ nome: atualizado.nome, email: atualizado.email });
      setSenhaAtual("");
      notificar(mudouEmail ? "Dados salvos. Use o novo e-mail no próximo login." : "Dados salvos.");
    } catch (e) {
      setErro(mensagemErro(e, "Não foi possível salvar os dados."));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="previa-card flex flex-col gap-[22px] px-[22px] py-5">
      <div>
        <h3 className="text-base font-bold">Dados pessoais</h3>
        <p className="mt-0.5 text-xs text-muted">O e-mail é o seu login na plataforma.</p>
      </div>
      <Campo label="Nome">
        <input
          className="previa-input"
          value={nome}
          onChange={(e) => {
            setNome(e.target.value);
            setErro("");
          }}
          autoComplete="name"
        />
      </Campo>
      <Campo label="E-mail">
        <input
          type="email"
          className="previa-input"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            setErro("");
          }}
          autoComplete="email"
        />
      </Campo>
      {mudouEmail && (
        <Campo label="Senha atual (para confirmar a troca do e-mail)">
          <input
            type="password"
            className="previa-input"
            value={senhaAtual}
            onChange={(e) => {
              setSenhaAtual(e.target.value);
              setErro("");
            }}
            onKeyDown={(e) => e.key === "Enter" && salvar()}
            autoComplete="current-password"
          />
        </Campo>
      )}
      {erro && <p className="-mt-2 text-[13px] font-semibold text-[#C23B4E]">{erro}</p>}
      <div className="flex justify-end">
        <button className="previa-btn h-10" onClick={salvar} disabled={salvando || (!mudouNome && !mudouEmail)}>
          {salvando ? "SALVANDO…" : "SALVAR DADOS"}
        </button>
      </div>
    </div>
  );
}

function TrocarSenha({ notificar }: { notificar: (m: string) => void }) {
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [confirma, setConfirma] = useState("");
  const [mostrar, setMostrar] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  function mudar(setter: (v: string) => void) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setter(e.target.value);
      setErro("");
    };
  }

  async function salvar() {
    if (!atual) return setErro("Informe a sua senha atual.");
    if (nova.length < TAMANHO_MINIMO) return setErro(`A nova senha deve ter pelo menos ${TAMANHO_MINIMO} caracteres.`);
    if (nova !== confirma) return setErro("As senhas não conferem.");
    if (nova === atual) return setErro("A nova senha deve ser diferente da atual.");
    setSalvando(true);
    setErro("");
    try {
      await trocarMinhaSenha(atual, nova);
      setAtual("");
      setNova("");
      setConfirma("");
      notificar("Senha alterada com sucesso.");
    } catch (e) {
      setErro(mensagemErro(e, "Não foi possível alterar a senha."));
    } finally {
      setSalvando(false);
    }
  }

  const tipo = mostrar ? "text" : "password";
  return (
    <div className="previa-card flex flex-col gap-[22px] px-[22px] py-5">
      <div>
        <h3 className="text-base font-bold">Trocar senha</h3>
        <p className="mt-0.5 text-xs text-muted">Mínimo de {TAMANHO_MINIMO} caracteres.</p>
      </div>
      <Campo label="Senha atual">
        <input
          type={tipo}
          className="previa-input pr-[72px]"
          value={atual}
          onChange={mudar(setAtual)}
          autoComplete="current-password"
        />
        <button
          type="button"
          onClick={() => setMostrar((v) => !v)}
          className="absolute right-2 top-2 h-7 px-2 text-xs text-muted"
        >
          {mostrar ? "Ocultar" : "Mostrar"}
        </button>
      </Campo>
      <Campo label="Nova senha">
        <input type={tipo} className="previa-input" value={nova} onChange={mudar(setNova)} autoComplete="new-password" />
      </Campo>
      <Campo label="Confirmar nova senha">
        <input
          type={tipo}
          className="previa-input"
          value={confirma}
          onChange={mudar(setConfirma)}
          onKeyDown={(e) => e.key === "Enter" && salvar()}
          autoComplete="new-password"
        />
      </Campo>
      {erro && <p className="-mt-2 text-[13px] font-semibold text-[#C23B4E]">{erro}</p>}
      <div className="flex justify-end">
        <button className="previa-btn h-10" onClick={salvar} disabled={salvando || !atual || !nova || !confirma}>
          {salvando ? "SALVANDO…" : "ALTERAR SENHA"}
        </button>
      </div>
    </div>
  );
}
