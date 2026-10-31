"use client";

import Link from "next/link";
import { Icon } from "@/components/Icon";
import { papel, useAuth } from "@/lib/auth";

/**
 * Estado vazio das telas que dependem de dados de consumo (Dashboard, Previsões).
 * Só o admin pode importar, então só ele vê o botão; o usuário comum é orientado
 * a falar com o administrador do hospital.
 */
export default function SemDadosImportados({ descricao }: { descricao: string }) {
  const { usuario } = useAuth();
  const isAdmin = papel(usuario?.perfil ?? "usuario") === "admin";

  return (
    <div className="previa-card flex flex-col items-center gap-2.5 px-6 py-12 text-center">
      <div className="mb-1.5 grid h-14 w-14 place-items-center rounded-full bg-surface-sky text-[#1c4f8a]">
        <svg
          width="26"
          height="26"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M22 12h-6l-2 3h-4l-2-3H2" />
          <path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z" />
        </svg>
      </div>

      <h2 className="text-lg font-bold text-navy">Nenhum dado importado ainda</h2>
      <p className="max-w-[460px] text-sm leading-relaxed text-muted">
        {isAdmin
          ? descricao
          : "O administrador do seu hospital ainda não importou o histórico de consumo. As informações aparecem aqui após a primeira carga."}
      </p>

      {isAdmin && (
        <Link
          href="/importar"
          className="mt-3 inline-flex h-10 items-center gap-2 rounded-full bg-brand px-5 text-[13px] font-bold text-white shadow-[0_6px_14px_rgba(74,168,224,.4)] transition hover:bg-brand-600"
        >
          <Icon name="importar" size={16} />
          Importar dados
        </Link>
      )}
    </div>
  );
}
