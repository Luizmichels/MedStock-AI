"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Icon, IconName } from "@/components/Icon";
import Logo from "@/components/Logo";
import { resumoDashboard } from "@/lib/api";
import { papel, useAuth } from "@/lib/auth";
import { fmtDataHora } from "@/lib/formato";

interface ItemNav {
  href: string;
  label: string;
  icon: IconName;
}

const NAV_PRINCIPAL: ItemNav[] = [
  { href: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { href: "/previsoes", label: "Previsões", icon: "previsoes" },
  { href: "/exportar", label: "Exportar relatório", icon: "exportar" },
];

const NAV_ADMIN: ItemNav[] = [
  { href: "/importar", label: "Importar dados", icon: "importar" },
  { href: "/usuarios", label: "Gestão de usuários", icon: "usuarios" },
];

const NAV_SUPER: ItemNav[] = [
  { href: "/hospitais", label: "Gestão de hospitais", icon: "hospitais" },
];

const ROTULO_PAPEL = {
  usuario: "Usuário",
  admin: "Administrador",
  super: "Super Usuário",
} as const;

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { usuario, sair } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const perfil = papel(usuario?.perfil ?? "usuario");
  const isAdmin = perfil === "admin";
  const isSuper = perfil === "super";

  const navPrincipal = isSuper ? NAV_SUPER : NAV_PRINCIPAL;
  const nomeExibicao = usuario?.nome || usuario?.email?.split("@")[0] || "Usuário";
  const iniciais =
    nomeExibicao
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0])
      .join("")
      .toUpperCase() || "U";
  // A API ainda não expõe o nome da empresa do usuário logado; por isso um rótulo genérico.
  const orgName = isSuper ? "Painel da plataforma" : "Gestão de insumos hospitalares";

  // "Última carga de dados" (não se aplica ao super admin). Recarrega ao trocar de
  // tela, para refletir uma importação recém-concluída.
  const [ultimaCarga, setUltimaCarga] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    if (isSuper) return;
    let ativo = true;
    resumoDashboard()
      .then((r) => ativo && setUltimaCarga(r.ultima_importacao))
      .catch(() => ativo && setUltimaCarga(undefined));
    return () => {
      ativo = false;
    };
  }, [isSuper, pathname]);

  function logout() {
    sair();
    router.replace("/login");
  }

  return (
    <div className="flex min-h-screen flex-col bg-navy">
      <header className="flex items-center justify-between gap-4 border-b border-white/[0.07] px-7 py-3.5 text-white">
        <div className="flex items-center gap-2.5">
          <Logo dark />
          <span className="mx-2.5 h-[22px] w-px bg-white/15" />
          <span className="text-sm text-[#C9D8E8]">{orgName}</span>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <nav className="sticky top-0 flex h-[calc(100vh-60px)] w-[232px] flex-none flex-col gap-1 self-start px-3.5 pb-[18px] pt-[22px]">
          <span className="px-3 pb-2 font-mono text-[10.5px] uppercase tracking-[0.1em] text-[#6F8FB0]">
            {isSuper ? "Plataforma" : "Menu"}
          </span>
          {navPrincipal.map((n) => (
            <LinkNav key={n.href} item={n} ativo={pathname === n.href} />
          ))}

          {isAdmin && (
            <>
              <span className="px-3 pb-2 pt-[22px] font-mono text-[10.5px] uppercase tracking-[0.1em] text-[#6F8FB0]">
                Administração
              </span>
              {NAV_ADMIN.map((n) => (
                <LinkNav key={n.href} item={n} ativo={pathname === n.href} />
              ))}
            </>
          )}

          {!isSuper && (
            <div className="mt-auto flex flex-col gap-1 rounded-[10px] bg-navy-700 px-3.5 py-3">
              <span className="text-xs text-[#8FB0CF]">Última carga de dados</span>
              <span className="text-[13px] font-bold text-white">
                {ultimaCarga === undefined ? "—" : ultimaCarga ? fmtDataHora(ultimaCarga) : "Nenhuma carga"}
              </span>
            </div>
          )}

          <div
            className={`flex items-center gap-2.5 border-t border-white/[0.08] px-1.5 pt-3.5 ${isSuper ? "mt-auto" : "mt-3"}`}
          >
            <Link
              href="/configuracoes"
              title="Minha conta"
              className="flex min-w-0 flex-1 items-center gap-2.5 rounded-lg transition hover:opacity-90"
            >
              <div className="grid h-9 w-9 flex-none place-items-center rounded-full bg-brand text-[13px] font-extrabold text-navy">
                {iniciais}
              </div>
              <div className="flex min-w-0 flex-1 flex-col leading-tight">
                <span className="truncate text-sm font-bold text-white">{nomeExibicao}</span>
                <span className="text-xs text-[#8FB0CF]">{ROTULO_PAPEL[perfil]}</span>
              </div>
            </Link>
            <Link
              href="/configuracoes"
              title="Minha conta"
              className="grid h-[34px] w-[34px] flex-none place-items-center rounded-lg transition hover:bg-white/10 hover:text-white"
              style={{ color: pathname === "/configuracoes" ? "#fff" : "#B7CBE0", background: pathname === "/configuracoes" ? "#16426B" : undefined }}
            >
              <Icon name="configuracoes" />
            </Link>
            <button
              onClick={logout}
              title="Sair"
              className="grid h-[34px] w-[34px] flex-none place-items-center rounded-lg bg-transparent text-[#B7CBE0] transition hover:bg-white/10 hover:text-white"
            >
              <Icon name="logout" />
            </button>
          </div>
        </nav>

        <main className="flex min-w-0 flex-1 flex-col gap-[22px] rounded-tl-[20px] bg-surface-app px-9 pb-10 pt-[30px]">
          {children}
        </main>
      </div>
    </div>
  );
}

function LinkNav({ item, ativo }: { item: ItemNav; ativo: boolean }) {
  return (
    <Link
      href={item.href}
      className="flex h-[42px] items-center gap-3 rounded-[9px] px-3 text-sm font-semibold transition"
      style={{
        background: ativo ? "#16426B" : "transparent",
        color: ativo ? "#fff" : "#B7CBE0",
      }}
    >
      <Icon name={item.icon} className="flex-none" />
      <span className="flex-1">{item.label}</span>
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ background: ativo ? "#4AA8E0" : "transparent" }}
      />
    </Link>
  );
}
