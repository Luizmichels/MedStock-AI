import { Suspense } from "react";
import AuthCard from "@/components/AuthCard";
import NovaSenhaForm from "@/components/NovaSenhaForm";

// Destino do link do e-mail de ativação (conta recém-aprovada ou criada pelo admin).
export default function DefinirSenhaPage() {
  return (
    <AuthCard>
      <Suspense fallback={<p className="mt-10 text-sm text-muted">Carregando…</p>}>
        <NovaSenhaForm modo="definir" />
      </Suspense>
    </AuthCard>
  );
}
