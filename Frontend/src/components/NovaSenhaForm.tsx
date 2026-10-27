"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, definirSenha, redefinirSenha } from "@/lib/api";
import Campo from "@/components/Campo";
import EsqueciSenha from "@/components/EsqueciSenha";

const TAMANHO_MINIMO = 8;

type Estado = "form" | "ok" | "expirado" | "jaAtiva";

const TEXTOS = {
  definir: {
    titulo: "Crie sua senha",
    sub: "Defina a senha de acesso para ativar sua conta.",
    botao: "CRIAR SENHA",
    ok: "Senha criada! Sua conta está ativa.",
  },
  redefinir: {
    titulo: "Redefinir senha",
    sub: "Escolha uma nova senha para a sua conta.",
    botao: "SALVAR NOVA SENHA",
    ok: "Senha redefinida com sucesso.",
  },
} as const;

/**
 * Formulário das páginas abertas pelo link do e-mail.
 * - "definir"   → /definir-senha   (ativação da conta)  → POST /auth/definir-senha
 * - "redefinir" → /redefinir-senha (esqueci a senha)    → POST /auth/redefinir-senha
 */
export default function NovaSenhaForm({ modo }: { modo: "definir" | "redefinir" }) {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const t = TEXTOS[modo];

  const [estado, setEstado] = useState<Estado>(token ? "form" : "expirado");
  const [senha, setSenha] = useState("");
  const [confirma, setConfirma] = useState("");
  const [mostrar, setMostrar] = useState(false);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function salvar() {
    if (senha.length < TAMANHO_MINIMO) {
      setErro(`A senha deve ter pelo menos ${TAMANHO_MINIMO} caracteres.`);
      return;
    }
    if (senha !== confirma) {
      setErro("As senhas não conferem.");
      return;
    }
    setErro("");
    setEnviando(true);
    try {
      if (modo === "definir") await definirSenha(token, senha);
      else await redefinirSenha(token, senha);
      setEstado("ok");
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 404)) setEstado("expirado");
      else if (e instanceof ApiError && e.status === 400) setEstado("jaAtiva");
      else setErro("Não foi possível salvar a senha. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  }

  if (estado === "expirado") {
    return (
      <EsqueciSenha
        titulo="Link inválido ou expirado"
        descricao="Os links de acesso valem 48 horas. Informe seu e-mail para receber um novo."
        onVoltar={() => router.push("/login")}
      />
    );
  }

  if (estado === "ok" || estado === "jaAtiva") {
    return (
      <div className="mt-10 flex flex-col gap-3">
        <div className="grid h-12 w-12 place-items-center rounded-full bg-[#E3F3EA] text-2xl font-extrabold text-[#2E9E6A]">
          ✓
        </div>
        <h1 className="mt-1 text-[22px] font-bold text-ink">
          {estado === "ok" ? t.ok : "Esta conta já está ativa."}
        </h1>
        <p className="text-sm leading-relaxed text-muted">
          {estado === "ok"
            ? "Agora é só entrar com o seu e-mail e a nova senha."
            : "Entre com o seu e-mail e senha. Se não lembrar a senha, use “Esqueceu a senha?” no login."}
        </p>
        <button className="previa-btn mt-3 self-start" onClick={() => router.push("/login")}>
          IR PARA O LOGIN
        </button>
      </div>
    );
  }

  return (
    <>
      <h1 className="mb-1.5 mt-10 text-xl font-semibold text-ink">{t.titulo}</h1>
      <p className="mb-6 text-sm leading-relaxed text-muted">{t.sub}</p>

      <div className="flex flex-col gap-[22px]">
        <Campo label="Nova senha">
          <input
            type={mostrar ? "text" : "password"}
            className="previa-input pr-[72px]"
            value={senha}
            onChange={(e) => {
              setSenha(e.target.value);
              setErro("");
            }}
            autoComplete="new-password"
          />
          <button
            type="button"
            onClick={() => setMostrar((v) => !v)}
            className="absolute right-2 top-2 h-7 px-2 text-xs text-muted"
          >
            {mostrar ? "Ocultar" : "Mostrar"}
          </button>
        </Campo>
        <Campo label="Confirmar nova senha">
          <input
            type={mostrar ? "text" : "password"}
            className="previa-input"
            value={confirma}
            onChange={(e) => {
              setConfirma(e.target.value);
              setErro("");
            }}
            onKeyDown={(e) => e.key === "Enter" && salvar()}
            autoComplete="new-password"
          />
        </Campo>
      </div>

      <p className="mt-3 text-xs text-muted-400">Mínimo de {TAMANHO_MINIMO} caracteres.</p>
      {erro && <p className="mt-2 text-[13px] font-semibold text-[#C23B4E]">{erro}</p>}

      <div className="mt-6 flex justify-end">
        <button className="previa-btn" onClick={salvar} disabled={enviando}>
          {enviando ? "SALVANDO…" : t.botao}
        </button>
      </div>
    </>
  );
}
