import { ApiError } from "@/lib/api";

/** Mensagem amigável para exibir a partir de um erro da API. */
export function mensagemErro(e: unknown, padrao = "Algo deu errado. Tente novamente."): string {
  if (e instanceof ApiError) {
    if (typeof e.detail === "string") return e.detail;
    if (e.status === 401) return "Sua sessão expirou. Entre novamente.";
    if (e.status === 403) return "Você não tem permissão para esta ação.";
    if (e.status === 422) return "Dados inválidos. Confira os campos.";
  }
  return padrao;
}
