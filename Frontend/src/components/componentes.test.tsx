import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import AuthCard from "@/components/AuthCard";
import Campo from "@/components/Campo";
import { Icon } from "@/components/Icon";
import Logo from "@/components/Logo";
import Modal from "@/components/Modal";
import PageHeader from "@/components/PageHeader";
import SemDadosImportados from "@/components/SemDadosImportados";
import Toast, { useToast } from "@/components/Toast";
import type { Perfil } from "@/lib/auth";

// O <Link> do Next precisa do roteador do App Router; nos testes basta um <a>.
vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const perfilAtual: { perfil: Perfil | null } = { perfil: null };
vi.mock("@/lib/auth", async (original) => ({
  ...(await original<typeof import("@/lib/auth")>()),
  useAuth: () => ({ usuario: perfilAtual.perfil ? { perfil: perfilAtual.perfil } : null }),
}));

describe("Campo", () => {
  it("mostra o rótulo e o erro só quando existe", () => {
    const { rerender } = render(
      <Campo label="E-mail">
        <input />
      </Campo>,
    );
    expect(screen.getByText("E-mail")).toBeInTheDocument();
    expect(screen.queryByText("Informe um e-mail válido.")).toBeNull();

    rerender(
      <Campo label="E-mail" erro="Informe um e-mail válido.">
        <input />
      </Campo>,
    );
    expect(screen.getByText("Informe um e-mail válido.")).toBeInTheDocument();
  });
});

describe("Modal", () => {
  function abrir(onFechar = vi.fn()) {
    render(
      <Modal titulo="Novo usuário" onFechar={onFechar} rodape={<button>Salvar</button>}>
        <p>conteúdo</p>
      </Modal>,
    );
    return onFechar;
  }

  it("mostra título, corpo e rodapé como diálogo acessível", () => {
    abrir();
    expect(screen.getByRole("dialog", { name: "Novo usuário" })).toBeInTheDocument();
    expect(screen.getByText("conteúdo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar" })).toBeInTheDocument();
  });

  it("fecha com Esc, com o X e com clique no fundo", async () => {
    const onFechar = abrir();
    fireEvent.keyDown(window, { key: "Escape" });
    await userEvent.click(screen.getByTitle("Fechar"));
    await userEvent.click(screen.getByRole("presentation"));
    expect(onFechar).toHaveBeenCalledTimes(3);
  });

  it("clique dentro da janela não fecha", async () => {
    const onFechar = abrir();
    await userEvent.click(screen.getByText("conteúdo"));
    fireEvent.keyDown(window, { key: "Enter" });
    expect(onFechar).not.toHaveBeenCalled();
  });
});

describe("Toast e useToast", () => {
  it("não renderiza nada sem mensagem", () => {
    const { container } = render(<Toast mensagem="" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("mostra a mensagem como status", () => {
    render(<Toast mensagem="Usuário criado." />);
    expect(screen.getByRole("status")).toHaveTextContent("Usuário criado.");
  });

  it("a mensagem some depois do tempo, e uma nova reinicia a contagem", () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useToast(1000));

    act(() => result.current.notificar("Primeira"));
    act(() => vi.advanceTimersByTime(800));
    act(() => result.current.notificar("Segunda"));
    act(() => vi.advanceTimersByTime(800));
    expect(result.current.mensagem).toBe("Segunda");

    act(() => vi.advanceTimersByTime(200));
    expect(result.current.mensagem).toBe("");
    vi.useRealTimers();
  });
});

describe("cabeçalhos e marca", () => {
  it("PageHeader mostra título, subtítulo e ações", () => {
    render(<PageHeader title="Previsões" subtitle="Próximos meses" acoes={<button>Treinar</button>} />);
    expect(screen.getByRole("heading", { name: "Previsões" })).toBeInTheDocument();
    expect(screen.getByText("Próximos meses")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Treinar" })).toBeInTheDocument();
  });

  it("AuthCard envolve o conteúdo com a marca e o suporte", () => {
    render(
      <AuthCard>
        <p>formulário</p>
      </AuthCard>,
    );
    expect(screen.getByText("formulário")).toBeInTheDocument();
    expect(screen.getByText(/Suporte:/)).toBeInTheDocument();
  });

  it.each([{}, { size: "lg" as const }, { dark: true }])("Logo renderiza a variante %j", (props) => {
    const { container } = render(<Logo {...props} />);
    expect(container.querySelector("svg")).not.toBeNull();
  });

  it("Icon desenha o caminho do ícone pedido", () => {
    const { container } = render(<Icon name="importar" size={16} />);
    expect(container.querySelector("svg")).toHaveAttribute("width", "16");
  });
});

describe("SemDadosImportados", () => {
  it("admin vê a descrição e o botão de importar", () => {
    perfilAtual.perfil = "admin";
    render(<SemDadosImportados descricao="Importe o histórico para ver o dashboard." />);
    expect(screen.getByText("Importe o histórico para ver o dashboard.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Importar dados/ })).toHaveAttribute("href", "/importar");
  });

  it("usuário comum é orientado a falar com o administrador, sem botão", () => {
    perfilAtual.perfil = "usuario";
    render(<SemDadosImportados descricao="Importe o histórico para ver o dashboard." />);
    expect(screen.getByText(/O administrador do seu hospital/)).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });
});
