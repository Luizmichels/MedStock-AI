"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError } from "@/lib/api";
import { papel, useAuth } from "@/lib/auth";
import { enviarSolicitacao } from "@/lib/api";
import Logo from "@/components/Logo";
import EsqueciSenha from "@/components/EsqueciSenha";

type Tela = "login" | "request" | "sent" | "forgot";

const SLIDES = [
  {
    tag: "PREVISÃO DE DEMANDA",
    title: "Antecipe o consumo de cada insumo",
    text: "Modelos preditivos estimam a demanda por material e setor.",
    path: "M20 130 L70 115 L110 120 L150 95",
    dash: "M150 95 L190 80 L240 60",
  },
  {
    tag: "CLASSIFICAÇÃO ABC",
    title: "Foque no que pesa no orçamento",
    text: "Identifique os itens classe A e priorize compras, contratos e controle de estoque.",
    path: "M20 40 L60 110 L110 135 L170 148 L240 152",
    dash: "",
  },
  {
    tag: "DADOS SEMPRE ATUALIZADOS",
    title: "Importação com validação automática",
    text: "Envie CSV com carga validada. Nulos, duplicidades e datas são verificados.",
    path: "M20 50 L70 80 L110 70 L150 110 L200 95 L240 120",
    dash: "",
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { entrar, usuario, carregando } = useAuth();

  const [tela, setTela] = useState<Tela>("login");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [errEmail, setErrEmail] = useState(false);
  const [errSenha, setErrSenha] = useState(false);
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  const [reqResp, setReqResp] = useState("");
  const [reqEmail, setReqEmail] = useState("");
  const [reqHosp, setReqHosp] = useState("");
  const [endereco, setEndereco] = useState("");
  const [cidade, setCidade] = useState("");
  const [uf, setUf] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [enviandoReq, setEnviandoReq] = useState(false);
  const [reqError, setReqError] = useState(false);
  const [reqErro, setReqErro] = useState("");

  const [slide, setSlide] = useState(0);

  useEffect(() => {
    if (!carregando && usuario) {
      router.replace(papel(usuario.perfil) === "super" ? "/hospitais" : "/dashboard");
    }
  }, [carregando, usuario, router]);

  useEffect(() => {
    const t = setInterval(() => setSlide((s) => (s + 1) % SLIDES.length), 5000);
    return () => clearInterval(t);
  }, []);

  const sl = SLIDES[slide];

  async function doLogin() {
    const ee = !email.trim();
    const es = !senha.trim();
    setErrEmail(ee);
    setErrSenha(es);
    setErro("");
    if (ee || es) return;
    setEnviando(true);
    try {
      const u = await entrar(email.trim(), senha);
      router.replace(papel(u.perfil) === "super" ? "/hospitais" : "/dashboard");
    } catch (e) {
      setErro(e instanceof ApiError && e.status === 401 ? "Credenciais inválidas." : "Não foi possível entrar. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  }

  async function submitRequest() {
    if (!reqResp.trim() || !reqEmail.trim() || !reqHosp.trim() ||
      !endereco.trim() || !cidade.trim() || !uf.trim() || !cnpj.trim()) {
      setReqError(true);
      return;
    }
    setReqError(false);
    setReqErro("");
    setEnviandoReq(true);
    try {
      await enviarSolicitacao({
        nome_responsavel: reqResp.trim(),
        email: reqEmail.trim(),
        nome_hospital: reqHosp.trim(),
        endereco: endereco.trim(),
        cidade: cidade.trim(),
        uf: uf.trim(),
        cnpj: cnpj.trim(),
      });
      setTela("sent");
      setReqResp("");
      setReqEmail("");
      setReqHosp("");
      setEndereco("");
      setCidade("");
      setUf("");
      setCnpj("");
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) setReqErro("Muitas tentativas. Tente novamente em instantes.");
      else if (e instanceof ApiError && e.status === 422) setReqErro("Verifique os dados (e-mail inválido ou campos imcompletos).");
      else setReqErro("Não foi possível enviar a solicitação. Tente novamente.");
    } finally {
      setEnviandoReq(false);
    }
  }

  const dots = useMemo(() => SLIDES.map((_, i) => i), []);

  return (
    <div className="flex min-h-screen flex-col bg-navy">
      <header className="flex items-center justify-between px-10 py-5 text-white">
        <div className="flex items-center gap-2.5">
          <Logo dark />
          <span className="ml-1.5 text-[13px] text-muted-300">
            Previsão de consumo de insumos hospitalares
          </span>
        </div>
        <span className="hidden text-[13px] text-muted-300 sm:block">Suporte: medstockai@gmail.com</span>
      </header>

      <main className="flex flex-1 items-center justify-center px-4 pb-12 pt-2 sm:px-8">
        <div className="grid min-h-[540px] w-full max-w-[1140px] grid-cols-1 overflow-hidden rounded-[18px] bg-white shadow-[0_30px_80px_rgba(0,0,0,.35)] md:grid-cols-2">
          {/* Coluna esquerda — formulários */}
          <div className="flex flex-col px-8 py-12 sm:px-[72px] sm:pb-12 sm:pt-16">
            <Logo size="lg" />

            {tela === "login" && (
              <>
                <h1 className="mb-[22px] mt-12 text-xl font-semibold text-ink">Login</h1>
                <div className="flex flex-col gap-[22px]">
                  <Campo label="E-mail" erro={errEmail ? "Por favor, coloque o seu e-mail" : ""}>
                    <input
                      className="previa-input"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        setErrEmail(false);
                      }}
                      onKeyDown={(e) => e.key === "Enter" && doLogin()}
                      autoComplete="username"
                    />
                  </Campo>
                  <Campo label="Senha" erro={errSenha ? "Por favor, coloque sua senha" : ""}>
                    <input
                      type={showPw ? "text" : "password"}
                      className="previa-input pr-11"
                      value={senha}
                      onChange={(e) => {
                        setSenha(e.target.value);
                        setErrSenha(false);
                      }}
                      onKeyDown={(e) => e.key === "Enter" && doLogin()}
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw((v) => !v)}
                      className="absolute right-2 top-2 h-7 px-2 text-xs text-muted"
                    >
                      {showPw ? "Ocultar" : "Mostrar"}
                    </button>
                  </Campo>
                </div>

                {erro && <p className="mt-3 text-sm font-semibold text-[#C23B4E]">{erro}</p>}

                <label className="mt-5 flex cursor-pointer items-center gap-2.5 text-sm text-ink-700">
                  <input type="checkbox" className="h-[17px] w-[17px] accent-brand" />
                  Lembrar de mim
                </label>

                <div className="mt-3.5 flex items-center justify-between">
                  <button type="button" onClick={() => setTela("forgot")} className="text-sm text-ink hover:underline">
                    Esqueceu a senha?
                  </button>
                  <button className="previa-btn min-w-[140px]" onClick={doLogin} disabled={enviando}>
                    {enviando ? "ENTRANDO…" : "ENTRAR"}
                  </button>
                </div>

                <div className="mt-auto flex flex-col gap-3.5 pt-9">
                  <div className="h-px bg-line-200" />
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="text-sm text-muted">Hospital ainda sem acesso?</span>
                    <button
                      onClick={() => setTela("request")}
                      className="h-9 rounded-full border border-brand bg-white px-4 text-[13px] font-bold text-brand-800 transition hover:bg-surface-sky"
                    >
                      Solicitar acesso
                    </button>
                  </div>
                </div>
              </>
            )}

            {tela === "request" && (
              <>
                <button
                  onClick={() => setTela("login")}
                  className="mt-10 self-start text-[13px] font-bold text-brand-800"
                >
                  ← Voltar ao login
                </button>
                <h1 className="mb-1.5 mt-[18px] text-xl font-semibold">Solicitação de acesso</h1>
                <p className="mb-6 text-sm leading-relaxed text-muted">
                  Preencha os dados da sua instituição. Nossa equipe analisa a solicitação e envia as
                  credenciais por e-mail.
                </p>
                <div className="flex flex-col gap-[22px]">
                  <Campo label="Responsável pelo contato">
                    <input
                      className="previa-input"
                      placeholder="Nome completo"
                      value={reqResp}
                      onChange={(e) => setReqResp(e.target.value)}
                    />
                  </Campo>
                  <Campo label="E-mail">
                    <input
                      className="previa-input"
                      placeholder="nome@hospital.org.br"
                      value={reqEmail}
                      onChange={(e) => setReqEmail(e.target.value)}
                    />
                  </Campo>
                  <Campo label="Nome da instituição">
                    <input
                      className="previa-input"
                      placeholder="Hospital, clínica ou rede"
                      value={reqHosp}
                      onChange={(e) => setReqHosp(e.target.value)}
                    />
                  </Campo>
                  <Campo label="CNPJ">
                    <input
                      className="previa-input"
                      placeholder="00.000.000/0000-00"
                      value={cnpj}
                      onChange={(e) => setCnpj(e.target.value)} />
                  </Campo>
                  <Campo label="Endereço">
                    <input className="previa-input" placeholder="Rua, número, bairro"
                      value={endereco} onChange={(e) => setEndereco(e.target.value)} />
                  </Campo>
                  <div className="grid grid-cols-[1fr_90px] gap-3">
                    <Campo label="Cidade">
                      <input className="previa-input" value={cidade} onChange={(e) => setCidade(e.target.value)} />
                    </Campo>
                    <Campo label="UF">
                      <input className="previa-input" maxLength={2}
                        value={uf} onChange={(e) => setUf(e.target.value.toUpperCase())} />
                    </Campo>
                  </div>
                </div>
                {reqErro && <div className="mt-3.5 text-[13px] text-[#C23B4E]">{reqErro}</div>}
                <div className="mt-6 flex justify-end">
                  <button className="previa-btn" onClick={submitRequest} disabled={enviandoReq}>
                    {enviandoReq ? "ENVIANDO…" : "ENVIAR SOLICITAÇÃO"}
                  </button>
                </div>
              </>
            )}

            {tela === "sent" && (
              <div className="mt-14 flex flex-col gap-3.5">
                <div className="grid h-12 w-12 place-items-center rounded-full bg-[#E3F3EA] text-2xl font-extrabold text-[#2E9E6A]">
                  ✓
                </div>
                <h1 className="mt-1.5 text-[22px] font-bold">Solicitação enviada</h1>
                <p className="text-sm leading-relaxed text-muted">
                  Recebemos o seu pedido. Ele está registrado com status{" "}
                  <span className="inline-block rounded-full bg-[#FDF1DC] px-2 py-px text-xs font-bold text-[#9A6212]">
                    Pendente
                  </span>{" "}
                  e será analisado pela equipe MedStock-AI. Você receberá a resposta por e-mail.
                </p>
                <button
                  onClick={() => setTela("login")}
                  className="mt-3 inline-flex h-10 items-center self-start rounded-full bg-brand px-[22px] text-[13px] font-extrabold tracking-wide text-white"
                >
                  VOLTAR AO LOGIN
                </button>
              </div>
            )}

            {tela === "forgot" && (
              <EsqueciSenha emailInicial={email} onVoltar={() => setTela("login")} />
            )}
          </div>

          {/* Coluna direita — slides */}
          <div className="relative hidden flex-col overflow-hidden bg-surface-sky px-16 pb-12 pt-16 md:flex">
            <div className="absolute left-[-60px] top-[260px] h-60 w-60 rounded-full bg-[#DCEAF6]" />
            <div className="relative flex justify-center">
              <svg width="260" height="170" viewBox="0 0 260 170">
                <g stroke="#C9DDF0" strokeWidth="1" fill="none">
                  <rect x="10" y="10" width="240" height="150" />
                  <line x1="70" y1="10" x2="70" y2="160" />
                  <line x1="130" y1="10" x2="130" y2="160" />
                  <line x1="190" y1="10" x2="190" y2="160" />
                  <line x1="10" y1="60" x2="250" y2="60" />
                  <line x1="10" y1="110" x2="250" y2="110" />
                </g>
                <path d={sl.path} fill="none" stroke="#5A8FD0" strokeWidth="2" strokeLinejoin="round" />
                {sl.dash && (
                  <path d={sl.dash} fill="none" stroke="#4AA8E0" strokeWidth="2" strokeDasharray="5 5" />
                )}
              </svg>
            </div>
            <div className="relative mt-auto flex max-w-[340px] flex-col gap-3">
              <span className="self-start rounded-[3px] bg-[#D2E4F5] px-[11px] py-[5px] text-xs font-bold tracking-[0.1em] text-[#1F5FA0]">
                {sl.tag}
              </span>
              <h2 className="text-[22px] font-semibold leading-snug text-ink">{sl.title}</h2>
              <p className="text-sm leading-relaxed text-[#4F79AB]">{sl.text}</p>
              <div className="mt-[18px] flex gap-2">
                {dots.map((i) => (
                  <button
                    key={i}
                    onClick={() => setSlide(i)}
                    aria-label={`Slide ${i + 1}`}
                    className="h-2 w-2 rounded-full"
                    style={{ background: i === slide ? "#1F5FA0" : "#B7D2EA" }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

function Campo({
  label,
  erro,
  children,
}: {
  label: string;
  erro?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative">
      <label className="absolute -top-2 left-3 bg-white px-1 text-[11px] text-muted">{label}</label>
      {children}
      {erro && (
        <div className="absolute left-1/2 top-10 z-[3] -translate-x-1/2 whitespace-nowrap rounded-md border border-brand bg-white px-[18px] py-[9px] text-[13px] text-ink shadow-[0_6px_18px_rgba(10,37,64,.12)]">
          {erro}
        </div>
      )}
    </div>
  );
}
