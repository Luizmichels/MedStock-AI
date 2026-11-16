import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AppLayout from "@/app/(app)/layout";
import AppShell from "@/components/AppShell";
import type { Usuario } from "@/lib/auth";
import { mockFetch, resposta } from "@/test/fetch";

const navegacao = vi.hoisted(() => ({ replace: vi.fn(), caminho: "/dashboard" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navegacao.replace, push: navegacao.replace }),
  usePathname: () => navegacao.caminho,
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const sessao = vi.hoisted(() => ({
  usuario: null as Usuario | null,
  carregando: false,
  sair: vi.fn(),
}));
vi.mock("@/lib/auth", async (original) => ({
  ...(await original<typeof import("@/lib/auth")>()),
  useAuth: () => sessao,
}));

function usuario(perfil: Usuario["perfil"], nome = "Ana Souza"): Usuario {
  return { id: "1", nome, email: "ana.souza@hospital.org.br", perfil, empresaId: 3 };
}

beforeEach(() => {
  navegacao.replace.mockReset();
  navegacao.caminho = "/dashboard";
  sessao.sair.mockReset();
  sessao.carregando = false;
});

describe("AppShell (menu lateral)", () => {
  it("usuário comum vê só o menu principal e a última carga", async () => {
    sessao.usuario = usuario("usuario");
    mockFetch(resposta(200, { ultima_importacao: "2026-11-10" }));
    render(<AppShell>conteúdo</AppShell>);

    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/dashboard");
    expect(screen.queryByRole("link", { name: "Importar dados" })).toBeNull();
    expect(screen.getByText("AS")).toBeInTheDocument(); // iniciais
    expect(screen.getByText("Usuário")).toBeInTheDocument();
    expect(await screen.findByText(/10\/11\/2026 às/)).toBeInTheDocument();
  });

  it("admin vê também a administração (importar e usuários)", async () => {
    sessao.usuario = usuario("admin");
    mockFetch(resposta(200, { ultima_importacao: null }));
    render(<AppShell>conteúdo</AppShell>);

    expect(screen.getByRole("link", { name: "Importar dados" })).toHaveAttribute("href", "/importar");
    expect(screen.getByRole("link", { name: "Gestão de usuários" })).toBeInTheDocument();
    expect(screen.getByText("Administrador")).toBeInTheDocument();
    expect(await screen.findByText("Nenhuma carga")).toBeInTheDocument();
  });

  it("super admin vê só a gestão de hospitais e não consulta a última carga", () => {
    sessao.usuario = usuario("super_admin", "");
    navegacao.caminho = "/hospitais";
    const fetchMock = mockFetch(resposta(200, {}));
    render(<AppShell>conteúdo</AppShell>);

    expect(screen.getByRole("link", { name: "Gestão de hospitais" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Dashboard" })).toBeNull();
    expect(screen.getByText("ana.souza")).toBeInTheDocument(); // sem nome, usa o e-mail
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("se a API falhar, a última carga fica com traço", async () => {
    sessao.usuario = usuario("usuario");
    mockFetch(resposta(500, null));
    render(<AppShell>conteúdo</AppShell>);
    await waitFor(() => expect(screen.getByText("—")).toBeInTheDocument());
  });

  it("Sair encerra a sessão e volta ao login", async () => {
    sessao.usuario = usuario("usuario");
    mockFetch(resposta(200, { ultima_importacao: null }));
    render(<AppShell>conteúdo</AppShell>);

    await userEvent.click(screen.getByTitle("Sair"));

    expect(sessao.sair).toHaveBeenCalled();
    expect(navegacao.replace).toHaveBeenCalledWith("/login");
  });
});

describe("layout das telas logadas", () => {
  it("sem sessão, manda para o login", async () => {
    sessao.usuario = null;
    render(<AppLayout>conteúdo protegido</AppLayout>);

    expect(screen.getByText("Carregando…")).toBeInTheDocument();
    expect(screen.queryByText("conteúdo protegido")).toBeNull();
    await waitFor(() => expect(navegacao.replace).toHaveBeenCalledWith("/login"));
  });

  it("enquanto carrega, não redireciona", () => {
    sessao.usuario = null;
    sessao.carregando = true;
    render(<AppLayout>conteúdo protegido</AppLayout>);
    expect(navegacao.replace).not.toHaveBeenCalled();
  });

  it("com sessão, mostra o conteúdo dentro do menu", () => {
    sessao.usuario = usuario("usuario");
    mockFetch(resposta(200, { ultima_importacao: null }));
    render(<AppLayout>conteúdo protegido</AppLayout>);
    expect(screen.getByText("conteúdo protegido")).toBeInTheDocument();
  });
});
