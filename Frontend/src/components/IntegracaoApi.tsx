"use client";

import { useEffect, useState } from "react";
import Modal from "@/components/Modal";
import {
  ChaveIntegracaoStatus,
  URL_API,
  consultarChaveIntegracao,
  gerarChaveIntegracao,
  revogarChaveIntegracao,
} from "@/lib/api";
import { mensagemErro } from "@/lib/erros";
import { fmtDataHora } from "@/lib/formato";

/** Exemplo de chamada mostrado na tela (com a chave real só logo após gerar). */
function exemploCurl(chave: string): string {
  return [
    `curl -X POST ${URL_API}/integracoes/consumos \\`,
    `  -H "X-API-Key: ${chave}" \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -d '{"registros": [{"codigo_item": "MED-01544", "descricao_item": "Dipirona 500 mg/mL",`,
    `       "data": "2026-10-20", "quantidade": 12, "valor": 30.50, "setor": "UTI Adulto",`,
    `       "grupo_material": "Medicamentos"}]}'`,
  ].join("\n");
}

/**
 * Integração via API: o sistema do hospital (ERP/estoque) envia o consumo sem
 * login, usando uma chave gerada aqui. A chave completa aparece uma única vez.
 */
export default function IntegracaoApi({ notificar }: { notificar: (m: string) => void }) {
  const [status, setStatus] = useState<ChaveIntegracaoStatus | null | undefined>(undefined);
  const [chaveNova, setChaveNova] = useState<string | null>(null);
  const [confirmar, setConfirmar] = useState<"gerar" | "revogar" | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    consultarChaveIntegracao()
      .then(setStatus)
      .catch((e) => {
        setStatus(null);
        setErro(mensagemErro(e, "Não foi possível consultar a chave de integração."));
      });
  }, []);

  async function gerar() {
    setConfirmar(null);
    setOcupado(true);
    setErro("");
    try {
      const gerada = await gerarChaveIntegracao();
      setChaveNova(gerada.chave);
      setStatus({ prefixo: gerada.prefixo, criado_em: gerada.criado_em, ultimo_uso_em: gerada.ultimo_uso_em });
    } catch (e) {
      setErro(mensagemErro(e, "Não foi possível gerar a chave."));
    } finally {
      setOcupado(false);
    }
  }

  async function revogar() {
    setConfirmar(null);
    setOcupado(true);
    setErro("");
    try {
      await revogarChaveIntegracao();
      setStatus(null);
      setChaveNova(null);
      notificar("Chave revogada. O sistema do hospital não consegue mais enviar dados com ela.");
    } catch (e) {
      setErro(mensagemErro(e, "Não foi possível revogar a chave."));
    } finally {
      setOcupado(false);
    }
  }

  async function copiar(texto: string, aviso: string) {
    try {
      await navigator.clipboard.writeText(texto);
      notificar(aviso);
    } catch {
      notificar("Não foi possível copiar. Selecione o texto e copie manualmente.");
    }
  }

  return (
    <div className="previa-card flex flex-col gap-4 px-[22px] py-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-bold">Integração via API</h3>
          <p className="mt-0.5 max-w-[640px] text-[13px] leading-relaxed text-muted">
            Para o sistema do hospital (ERP ou estoque) enviar o consumo automaticamente, sem arquivo. Os envios
            são sempre <b>incrementais</b>, em lotes de até 15.000 registros, e aparecem no histórico abaixo. Para
            substituir toda a base, use a importação completa por arquivo.
          </p>
        </div>
        {status !== undefined && (
          <div className="flex gap-2">
            {status && (
              <button
                onClick={() => setConfirmar("revogar")}
                disabled={ocupado}
                className="h-10 rounded-full border border-[#CBD6E2] bg-white px-[18px] text-[13px] font-bold text-[#C23B4E] disabled:opacity-60"
              >
                Revogar chave
              </button>
            )}
            <button
              className="previa-btn h-10"
              onClick={() => (status ? setConfirmar("gerar") : gerar())}
              disabled={ocupado}
            >
              {ocupado ? "AGUARDE…" : status ? "GERAR NOVA CHAVE" : "GERAR CHAVE"}
            </button>
          </div>
        )}
      </div>

      {/* Situação da chave */}
      <div className="flex flex-wrap gap-x-8 gap-y-2 rounded-[10px] bg-surface-panel px-4 py-3 text-[13px]">
        {status === undefined ? (
          <span className="text-muted">Carregando…</span>
        ) : status === null ? (
          <span className="text-muted">Nenhuma chave ativa. Gere uma para liberar a integração.</span>
        ) : (
          <>
            <span className="flex flex-col">
              <span className="text-xs text-muted-400">Chave ativa</span>
              <span className="font-mono font-bold text-navy">{status.prefixo}…</span>
            </span>
            <span className="flex flex-col">
              <span className="text-xs text-muted-400">Criada em</span>
              <span className="font-bold text-navy">{fmtDataHora(status.criado_em)}</span>
            </span>
            <span className="flex flex-col">
              <span className="text-xs text-muted-400">Último envio</span>
              <span className="font-bold text-navy">
                {status.ultimo_uso_em ? fmtDataHora(status.ultimo_uso_em) : "Nunca usada"}
              </span>
            </span>
          </>
        )}
      </div>

      {/* A chave completa: só agora */}
      {chaveNova && (
        <div className="flex flex-col gap-2 rounded-[10px] border-[1.5px] border-[#D9822B] bg-[#FDF6EC] px-4 py-3">
          <span className="text-[13px] font-bold text-[#9A6212]">
            Copie a chave agora: por segurança, ela não será mostrada de novo.
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 break-all rounded-md bg-white px-3 py-2 font-mono text-xs text-ink">
              {chaveNova}
            </code>
            <button
              onClick={() => copiar(chaveNova, "Chave copiada.")}
              className="h-9 rounded-full bg-[#D9822B] px-4 text-[13px] font-bold text-white"
            >
              Copiar chave
            </button>
          </div>
        </div>
      )}

      {/* Como usar */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[13px] font-semibold text-ink">Exemplo de envio</span>
            <button
              onClick={() => copiar(exemploCurl(chaveNova ?? "SUA_CHAVE"), "Exemplo copiado.")}
              className="text-xs font-bold text-brand-800 hover:underline"
            >
              Copiar exemplo
            </button>
          </div>
          <pre className="overflow-x-auto rounded-[10px] bg-navy px-4 py-3 font-mono text-[11.5px] leading-relaxed text-[#D6E7F6]">
            {exemploCurl(chaveNova ?? "SUA_CHAVE")}
          </pre>
        </div>
        <ul className="flex flex-col gap-1.5 text-[13px] text-ink-700">
          {[
            <>
              <code className="font-mono text-xs">POST /integracoes/consumos</code> com a chave no cabeçalho{" "}
              <code className="font-mono text-xs">X-API-Key</code>.
            </>,
            <>Mesmos campos do arquivo; grupo, subgrupo, classe e unidade são opcionais.</>,
            <>
              A resposta traz o <code className="font-mono text-xs">id</code> do envio; o resultado sai em{" "}
              <code className="font-mono text-xs">GET /integracoes/importacoes/&#123;id&#125;</code>.
            </>,
            <>Registros inválidos são listados no resultado (ex.: &quot;linha 3&quot; = 3º registro do envio).</>,
            <>
              Documentação completa em <code className="font-mono text-xs">{URL_API}/docs</code>.
            </>,
          ].map((item, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="mt-[7px] h-1.5 w-1.5 flex-none rounded-full bg-brand" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      {erro && <p className="text-[13px] font-semibold text-[#C23B4E]">{erro}</p>}

      {confirmar && (
        <Modal
          titulo={confirmar === "gerar" ? "Gerar uma nova chave?" : "Revogar a chave?"}
          onFechar={() => setConfirmar(null)}
          rodape={
            <>
              <button
                onClick={() => setConfirmar(null)}
                className="h-10 rounded-full border border-[#CBD6E2] bg-white px-[18px] text-[13px] font-bold text-ink"
              >
                Cancelar
              </button>
              <button
                onClick={confirmar === "gerar" ? gerar : revogar}
                className="h-10 rounded-full bg-[#C23B4E] px-[22px] text-[13px] font-extrabold tracking-wide text-white transition hover:bg-[#A82F41]"
              >
                {confirmar === "gerar" ? "GERAR NOVA CHAVE" : "REVOGAR"}
              </button>
            </>
          }
        >
          <p className="text-sm leading-relaxed text-ink-700">
            {confirmar === "gerar"
              ? "A chave atual para de funcionar na hora. O sistema do hospital precisará ser configurado com a nova chave."
              : "O sistema do hospital não conseguirá mais enviar dados até que uma nova chave seja gerada."}
          </p>
        </Modal>
      )}
    </div>
  );
}
