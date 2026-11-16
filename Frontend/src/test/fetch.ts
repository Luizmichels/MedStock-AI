import { vi } from "vitest";

/** Resposta HTTP falsa com corpo JSON (ou vazia, com `corpo` undefined). */
export function resposta(status: number, corpo?: unknown): Response {
  const texto = corpo === undefined ? null : typeof corpo === "string" ? corpo : JSON.stringify(corpo);
  return new Response(texto, { status });
}

/**
 * Substitui o fetch global. Cada chamada devolve a próxima resposta da lista
 * (a última se repete); o retorno permite conferir URL, método e corpo enviados.
 */
export function mockFetch(...respostas: Response[]) {
  const fila = [...respostas];
  const fn = vi.fn(async (_url: string, _init?: RequestInit) => {
    const proxima = fila.length > 1 ? fila.shift()! : fila[0];
    return proxima.clone();
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

/** JWT falso (sem assinatura válida): o front só lê o payload. */
export function tokenFalso(payload: Record<string, unknown>): string {
  const base64url = (obj: unknown) =>
    btoa(JSON.stringify(obj)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${base64url({ alg: "HS256", typ: "JWT" })}.${base64url(payload)}.assinatura`;
}
