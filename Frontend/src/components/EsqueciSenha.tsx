"use client";

import { useEffect, useState } from "react";
import { ApiError, esqueciSenha, reenviarAtivacao } from "@/lib/api";
import Campo from "@/components/Campo";

/** Tempo mínimo (s) entre dois envios — as rotas de auth não têm rate limit no back. */
const ESPERA_REENVIO = 60;

export default function EsqueciSenha({
  emailInicial = "",
  titulo = "Esqueceu a senha?",
  descricao = "Informe o e-mail cadastrado. Enviaremos um link para você criar uma nova senha.",
  onVoltar,
}: {
  emailInicial?: string;
  titulo?: string;
  descricao?: string;
  onVoltar?: () => void;
}) {
  const [email, setEmail] = useState(emailInicial);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [espera, setEspera] = useState(0);
  const [erro, setErro] = useState("");

  useEffect(() => {
    if (espera <= 0) return;
    const t = setTimeout(() => setEspera((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [espera]);

  async function enviar() {
    const alvo = email.trim();
    if (!/^\S+@\S+\.\S+$/.test(alvo)) {
      setErro("Informe um e-mail válido.");
      return;
    }
    setErro("");
    setEnviando(true);
    try {
      // O back separa por estado da conta: ativa -> link de redefinição;
      // ainda não ativada -> link de ativação. As duas rotas respondem de forma
      // genérica (sem revelar se o e-mail existe), então chamamos ambas: os filtros
      // são excludentes, logo no máximo uma delas envia e-mail.
      await Promise.all([esqueciSenha(alvo), reenviarAtivacao(alvo)]);
      setEnviado(true);
      setEspera(ESPERA_REENVIO);
    } catch (e) {
      setErro(
        e instanceof ApiError && e.status === 429
          ? "Muitas tentativas. Aguarde um pouco e tente de novo."
          : "Não foi possível enviar o e-mail. Tente novamente em instantes.",
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      {onVoltar && (
        <button onClick={onVoltar} className="mt-10 self-start text-[13px] font-bold text-brand-800">
          ← Voltar ao login
        </button>
      )}

      {!enviado ? (
        <>
          <h1 className="mb-1.5 mt-[18px] text-xl font-semibold text-ink">{titulo}</h1>
          <p className="mb-6 text-sm leading-relaxed text-muted">{descricao}</p>
          <Campo label="E-mail" erro={erro}>
            <input
              className="previa-input"
              type="email"
              placeholder="nome@hospital.org.br"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setErro("");
              }}
              onKeyDown={(e) => e.key === "Enter" && enviar()}
              autoComplete="email"
            />
          </Campo>
          <div className="mt-8 flex justify-end">
            <button className="previa-btn" onClick={enviar} disabled={enviando}>
              {enviando ? "ENVIANDO…" : "ENVIAR LINK"}
            </button>
          </div>
        </>
      ) : (
        <div className="mt-8 flex flex-col gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-full bg-[#E3F3EA] text-2xl font-extrabold text-[#2E9E6A]">
            ✓
          </div>
          <h1 className="mt-1 text-[22px] font-bold text-ink">Verifique seu e-mail</h1>
          <p className="text-sm leading-relaxed text-muted">
            Se houver uma conta com <b className="text-ink">{email.trim()}</b>, enviamos um link para
            você acessar. Ele vale por <b className="text-ink">48 horas</b>.
          </p>
          <p className="text-[13px] text-muted-400">Não chegou? Confira a caixa de spam ou reenvie.</p>

          {erro && <p className="text-[13px] font-semibold text-[#C23B4E]">{erro}</p>}

          <div className="mt-2 flex flex-wrap items-center gap-4">
            <button
              onClick={enviar}
              disabled={enviando || espera > 0}
              className="h-10 rounded-full border border-brand bg-white px-5 text-[13px] font-bold text-brand-800 transition hover:bg-surface-sky disabled:cursor-not-allowed disabled:border-line disabled:text-muted-400 disabled:hover:bg-white"
            >
              {enviando
                ? "Reenviando…"
                : espera > 0
                  ? `Reenviar em 0:${String(espera).padStart(2, "0")}`
                  : "Reenviar e-mail"}
            </button>
            <button
              onClick={() => {
                setEnviado(false);
                setEspera(0);
              }}
              className="text-[13px] font-bold text-ink-700 hover:underline"
            >
              Usar outro e-mail
            </button>
          </div>
        </div>
      )}
    </>
  );
}
