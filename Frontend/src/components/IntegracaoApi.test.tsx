import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import IntegracaoApi from "@/components/IntegracaoApi";
import { mockFetch, resposta } from "@/test/fetch";

const CHAVE_ATIVA = { prefixo: "msk_ab12", criado_em: "2026-11-01T10:00:00Z", ultimo_uso_em: null };
const CHAVE_GERADA = { ...CHAVE_ATIVA, prefixo: "msk_cd34", chave: "msk_cd34_chave_completa_secreta" };

function renderizar() {
  const notificar = vi.fn();
  render(<IntegracaoApi notificar={notificar} />);
  return notificar;
}

/** Área de transferência controlada (o jsdom não tem uma). */
function mockClipboard(falhar = false) {
  const writeText = falhar ? vi.fn().mockRejectedValue(new Error("negado")) : vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  return writeText;
}

describe("IntegracaoApi", () => {
  it("sem chave ativa, convida a gerar uma", async () => {
    mockFetch(resposta(200, null));
    renderizar();
    expect(await screen.findByText(/Nenhuma chave ativa/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "GERAR CHAVE" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Revogar chave" })).toBeNull();
  });

  it("com chave ativa, mostra só o prefixo e que nunca foi usada", async () => {
    mockFetch(resposta(200, CHAVE_ATIVA));
    renderizar();
    expect(await screen.findByText("msk_ab12…")).toBeInTheDocument();
    expect(screen.getByText("Nunca usada")).toBeInTheDocument();
  });

  it("gerar a primeira chave mostra a chave completa uma única vez e permite copiar", async () => {
    const fetchMock = mockFetch(resposta(200, null), resposta(201, CHAVE_GERADA));
    const writeText = mockClipboard();
    const notificar = renderizar();

    fireEvent.click(await screen.findByRole("button", { name: "GERAR CHAVE" }));

    expect(await screen.findByText(CHAVE_GERADA.chave)).toBeInTheDocument();
    expect(screen.getByText(/ela não será mostrada de novo/)).toBeInTheDocument();
    expect(fetchMock.mock.calls[1][1]?.method).toBe("POST");
    // o exemplo de curl passa a usar a chave real
    expect(screen.getByText(/X-API-Key: msk_cd34_chave_completa_secreta/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Copiar chave" }));
    await waitFor(() => expect(notificar).toHaveBeenCalledWith("Chave copiada."));
    expect(writeText).toHaveBeenCalledWith(CHAVE_GERADA.chave);
  });

  it("gerar nova chave com uma ativa pede confirmação antes", async () => {
    const fetchMock = mockFetch(resposta(200, CHAVE_ATIVA), resposta(201, CHAVE_GERADA));
    renderizar();

    fireEvent.click(await screen.findByRole("button", { name: "GERAR NOVA CHAVE" }));
    expect(screen.getByRole("dialog", { name: "Gerar uma nova chave?" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const dialogo = screen.getByRole("dialog");
    fireEvent.click(dialogo.querySelector("button.bg-\\[\\#C23B4E\\]")!);

    expect(await screen.findByText(CHAVE_GERADA.chave)).toBeInTheDocument();
  });

  it("cancelar a confirmação não chama a API", async () => {
    const fetchMock = mockFetch(resposta(200, CHAVE_ATIVA));
    renderizar();

    fireEvent.click(await screen.findByRole("button", { name: "Revogar chave" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("revogar apaga a chave e avisa", async () => {
    const fetchMock = mockFetch(resposta(200, CHAVE_ATIVA), resposta(204));
    const notificar = renderizar();

    fireEvent.click(await screen.findByRole("button", { name: "Revogar chave" }));
    fireEvent.click(screen.getByRole("button", { name: "REVOGAR" }));

    expect(await screen.findByText(/Nenhuma chave ativa/)).toBeInTheDocument();
    expect(fetchMock.mock.calls[1][1]?.method).toBe("DELETE");
    expect(notificar).toHaveBeenCalledWith(expect.stringContaining("Chave revogada"));
  });

  it("erros da API aparecem na tela", async () => {
    mockFetch(resposta(500, null));
    renderizar();
    expect(await screen.findByText("Não foi possível consultar a chave de integração.")).toBeInTheDocument();
  });

  it("falha ao gerar e ao revogar mostra o motivo", async () => {
    mockFetch(resposta(200, CHAVE_ATIVA), resposta(403, { detail: "Apenas administradores." }));
    renderizar();

    fireEvent.click(await screen.findByRole("button", { name: "Revogar chave" }));
    fireEvent.click(screen.getByRole("button", { name: "REVOGAR" }));
    expect(await screen.findByText("Apenas administradores.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "GERAR NOVA CHAVE" }));
    fireEvent.click(screen.getAllByRole("button", { name: "GERAR NOVA CHAVE" }).at(-1)!);
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(await screen.findByText("Apenas administradores.")).toBeInTheDocument();
  });

  it("se a cópia falhar, orienta a copiar manualmente", async () => {
    mockFetch(resposta(200, null));
    mockClipboard(true);
    const notificar = renderizar();

    fireEvent.click(await screen.findByRole("button", { name: "Copiar exemplo" }));

    await waitFor(() => expect(notificar).toHaveBeenCalledWith(expect.stringContaining("copie manualmente")));
  });
});
