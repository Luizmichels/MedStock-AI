/** Formatação pt-BR e utilidades de data usadas pelas telas. */

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

export function fmtNumero(n: number, casas = 0): string {
  return n.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

/** Valor monetário abreviado: "R$ 2,41 mi", "R$ 916 mil", "R$ 850". */
export function fmtMoedaCurta(valor: number): string {
  const abs = Math.abs(valor);
  if (abs >= 1_000_000) return `R$ ${fmtNumero(valor / 1_000_000, 2)} mi`;
  if (abs >= 1_000) return `R$ ${fmtNumero(valor / 1_000, 0)} mil`;
  return `R$ ${fmtNumero(valor, 0)}`;
}

/** Valor monetário completo: "R$ 2.223.698,40". */
export function fmtMoeda(valor: number): string {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/** Trunca (não arredonda) em `casas` decimais: 38,999 -> 38,99. */
function truncar(valor: number, casas: number): number {
  const fator = 10 ** casas;
  // O epsilon evita que 1,15 vire 1,14 por erro de ponto flutuante.
  return Math.trunc(valor * fator + Math.sign(valor) * 1e-9) / fator;
}

/**
 * Número abreviado para gráficos e KPIs, truncado em 2 casas:
 * milhões "2,22 M", milhares "38,99 K"; abaixo de mil não abrevia ("850,40").
 * `fixo` = sempre 2 casas (rótulos); sem ele, zeros à direita somem (eixos: "10 K").
 */
export function fmtCompacto(valor: number, { moeda = false, fixo = true } = {}): string {
  const abs = Math.abs(valor);
  const [divisor, sufixo] = abs >= 1_000_000 ? [1_000_000, " M"] : abs >= 1_000 ? [1_000, " K"] : [1, ""];
  const numero = truncar(valor / divisor, 2).toLocaleString("pt-BR", {
    minimumFractionDigits: fixo ? 2 : 0,
    maximumFractionDigits: 2,
  });
  return `${moeda ? "R$ " : ""}${numero}${sufixo}`;
}

/** Quantidade com até 2 casas: "12.345", "12.345,5". */
export function fmtQuantidade(valor: number): string {
  return valor.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
}

/**
 * Converte o texto de data vindo da API em Date.
 * - "AAAA-MM-DD" (data pura) é lida no fuso local, sem pular de dia.
 * - Data-hora sem fuso é tratada como UTC (o Postgres do container grava em UTC).
 */
export function lerData(texto: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(texto)) {
    const [a, m, d] = texto.split("-").map(Number);
    return new Date(a, m - 1, d);
  }
  const temFuso = /([zZ]|[+-]\d{2}:?\d{2})$/.test(texto);
  return new Date(temFuso ? texto : `${texto}Z`);
}

export function fmtData(texto: string): string {
  return lerData(texto).toLocaleDateString("pt-BR");
}

export function fmtDataHora(texto: string): string {
  const d = lerData(texto);
  const hora = d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return `${d.toLocaleDateString("pt-BR")} às ${hora}`;
}

/** "2026-09-01" -> "set/26" */
export function fmtMesAno(texto: string): string {
  const d = lerData(texto);
  return `${MESES[d.getMonth()]}/${String(d.getFullYear()).slice(2)}`;
}

/** "2026-09-01" -> "09/2026" */
export function fmtMesAnoNumerico(texto: string): string {
  const d = lerData(texto);
  return `${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}

// --- Competência (mês) no formato "AAAA-MM", o mesmo do <input type="month"> ---

/** "2026-09-01" -> "2026-09" */
export function mesDe(texto: string): string {
  return texto.slice(0, 7);
}

/** "2026-09" + (-11) -> "2025-10" */
export function somarMeses(mes: string, quantidade: number): string {
  const [ano, m] = mes.split("-").map(Number);
  const d = new Date(ano, m - 1 + quantidade, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/** "2026-09" -> "09/2026" */
export function fmtCompetencia(mes: string): string {
  const [ano, m] = mes.split("-");
  return `${m}/${ano}`;
}

/** "2026-09-01" -> "set" */
export function fmtMes(texto: string): string {
  return MESES[lerData(texto).getMonth()];
}

/** Date -> "dd/mm" */
export function fmtDiaMes(d: Date): string {
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/** Date -> "AAAA-MM-DD" (no fuso local), formato aceito pela API. */
export function isoData(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function somarDias(d: Date, dias: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + dias);
  return r;
}

export function fmtTamanhoArquivo(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${fmtNumero(bytes / (1024 * 1024), 1)} MB`;
  return `${fmtNumero(Math.max(bytes / 1024, 1), 0)} KB`;
}

export function esperar(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
