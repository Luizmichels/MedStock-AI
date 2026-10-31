"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Aviso rápido no canto da tela: const { mensagem, notificar } = useToast(). */
export function useToast(duracaoMs = 3500) {
  const [mensagem, setMensagem] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const notificar = useCallback(
    (texto: string) => {
      setMensagem(texto);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setMensagem(""), duracaoMs);
    },
    [duracaoMs],
  );

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  return { mensagem, notificar };
}

export default function Toast({ mensagem }: { mensagem: string }) {
  if (!mensagem) return null;
  return (
    <div
      role="status"
      className="fixed bottom-6 right-6 z-50 flex max-w-[420px] items-center gap-2.5 rounded-xl border border-navy-600 bg-navy px-[18px] py-3.5 text-sm text-white shadow-[0_12px_30px_rgba(0,0,0,.3)]"
    >
      <span className="h-2 w-2 flex-none rounded-full bg-brand" />
      {mensagem}
    </div>
  );
}
