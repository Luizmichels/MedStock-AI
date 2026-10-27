import Logo from "@/components/Logo";

/** Moldura das páginas públicas acessadas pelo link do e-mail (sem sidebar). */
export default function AuthCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-navy">
      <header className="flex items-center justify-between px-10 py-5 text-white">
        <Logo dark />
        <span className="hidden text-[13px] text-muted-300 sm:block">Suporte: medstockai@gmail.com</span>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 pb-12 pt-2">
        <div className="flex w-full max-w-[480px] flex-col rounded-[18px] bg-white px-8 py-10 shadow-[0_30px_80px_rgba(0,0,0,.35)] sm:px-12">
          <Logo size="lg" />
          {children}
        </div>
      </main>
    </div>
  );
}
