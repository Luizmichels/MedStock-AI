"use client";

import { useEffect } from "react";

/** Janela modal com cabeçalho, corpo e rodapé de ações. Fecha com Esc ou clique fora. */
export default function Modal({
  titulo,
  onFechar,
  rodape,
  children,
}: {
  titulo: string;
  onFechar: () => void;
  rodape: React.ReactNode;
  children: React.ReactNode;
}) {
  useEffect(() => {
    const aoTeclar = (e: KeyboardEvent) => e.key === "Escape" && onFechar();
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [onFechar]);

  return (
    <div onClick={onFechar} className="fixed inset-0 z-40 grid place-items-center bg-[rgba(7,26,46,.55)] p-5">
      <div
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[520px] overflow-hidden rounded-2xl bg-white shadow-[0_30px_80px_rgba(0,0,0,.35)]"
      >
        <div className="flex items-center justify-between border-b border-line-200 px-6 py-4">
          <h3 className="text-base font-bold text-ink">{titulo}</h3>
          <button
            onClick={onFechar}
            title="Fechar"
            className="grid h-8 w-8 place-items-center rounded-lg text-muted transition hover:bg-surface-app hover:text-ink"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <div className="flex flex-col gap-[18px] px-6 py-5">{children}</div>
        <div className="flex justify-end gap-2.5 border-t border-line-200 px-6 py-3.5">{rodape}</div>
      </div>
    </div>
  );
}
