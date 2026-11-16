import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api";
import { mensagemErro } from "@/lib/erros";

describe("mensagemErro", () => {
  it("usa o detail da API quando é texto", () => {
    expect(mensagemErro(new ApiError(409, "Já existe um treino em andamento."))).toBe(
      "Já existe um treino em andamento.",
    );
  });

  it.each([
    [401, "Sua sessão expirou. Entre novamente."],
    [403, "Você não tem permissão para esta ação."],
    [422, "Dados inválidos. Confira os campos."],
  ])("traduz o status %i quando o detail não é texto", (status, esperado) => {
    expect(mensagemErro(new ApiError(status, [{ loc: ["body"], msg: "x" }]))).toBe(esperado);
  });

  it("cai na mensagem padrão para outros erros", () => {
    expect(mensagemErro(new ApiError(500, null))).toBe("Algo deu errado. Tente novamente.");
    expect(mensagemErro(new Error("falha de rede"), "Sem conexão.")).toBe("Sem conexão.");
    expect(mensagemErro("qualquer coisa")).toBe("Algo deu errado. Tente novamente.");
  });
});
