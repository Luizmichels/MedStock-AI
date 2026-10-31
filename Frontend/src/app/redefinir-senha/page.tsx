import { Suspense } from "react";
import AuthCard from "@/components/AuthCard";
import NovaSenhaForm from "@/components/NovaSenhaForm";

// Destino do link do e-mail de "esqueci a senha".
export default function RedefinirSenhaPage() {
  return (
    <AuthCard>
      <Suspense fallback={<p className="mt-10 text-sm text-muted">Carregando…</p>}>
        <NovaSenhaForm modo="redefinir" />
      </Suspense>
    </AuthCard>
  );
}
