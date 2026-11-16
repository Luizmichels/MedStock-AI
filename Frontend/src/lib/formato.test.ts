import { describe, expect, it, vi } from "vitest";
import {
  esperar,
  fmtCompacto,
  fmtCompetencia,
  fmtData,
  fmtDataHora,
  fmtDiaMes,
  fmtMes,
  fmtMesAno,
  fmtMesAnoNumerico,
  fmtMoeda,
  fmtMoedaCurta,
  fmtNumero,
  fmtQuantidade,
  fmtTamanhoArquivo,
  isoData,
  lerData,
  mesDe,
  somarDias,
  somarMeses,
} from "@/lib/formato";

// O Intl separa "R$" do número com espaço não separável; \s cobre os dois.
const SEM_ESPACO_ESPECIAL = (texto: string) => texto.replace(/\s/g, " ");

describe("números e moeda (pt-BR)", () => {
  it("fmtNumero usa ponto no milhar e vírgula nas casas", () => {
    expect(fmtNumero(1234567)).toBe("1.234.567");
    expect(fmtNumero(1234.5, 2)).toBe("1.234,50");
  });

  it("fmtMoedaCurta abrevia milhões e milhares", () => {
    expect(fmtMoedaCurta(2_410_000)).toBe("R$ 2,41 mi");
    expect(fmtMoedaCurta(916_400)).toBe("R$ 916 mil");
    expect(fmtMoedaCurta(850)).toBe("R$ 850");
    expect(fmtMoedaCurta(-1_500_000)).toBe("R$ -1,50 mi");
  });

  it("fmtMoeda mostra o valor completo em reais", () => {
    expect(SEM_ESPACO_ESPECIAL(fmtMoeda(2223698.4))).toBe("R$ 2.223.698,40");
  });

  it("fmtCompacto trunca em vez de arredondar", () => {
    expect(fmtCompacto(38_999)).toBe("38,99 K");
    expect(fmtCompacto(2_229_999)).toBe("2,22 M");
    expect(fmtCompacto(850.4)).toBe("850,40");
  });

  it("fmtCompacto sem `fixo` remove zeros à direita e com `moeda` põe o R$", () => {
    expect(fmtCompacto(10_000, { fixo: false })).toBe("10 K");
    expect(fmtCompacto(1_150, { moeda: true })).toBe("R$ 1,15 K");
  });

  it("fmtQuantidade mostra até 2 casas", () => {
    expect(fmtQuantidade(12345)).toBe("12.345");
    expect(fmtQuantidade(12345.5)).toBe("12.345,5");
    expect(fmtQuantidade(1.239)).toBe("1,24");
  });

  it("fmtTamanhoArquivo usa MB a partir de 1 MB e no mínimo 1 KB", () => {
    expect(fmtTamanhoArquivo(5 * 1024 * 1024)).toBe("5,0 MB");
    expect(fmtTamanhoArquivo(2048)).toBe("2 KB");
    expect(fmtTamanhoArquivo(10)).toBe("1 KB");
  });
});

describe("datas", () => {
  it("lerData lê data pura no fuso local, sem pular de dia", () => {
    const d = lerData("2026-09-01");
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 8, 1]);
  });

  it("lerData trata data-hora sem fuso como UTC", () => {
    expect(lerData("2026-09-01T12:00:00").getTime()).toBe(Date.UTC(2026, 8, 1, 12));
    expect(lerData("2026-09-01T12:00:00Z").getTime()).toBe(Date.UTC(2026, 8, 1, 12));
    expect(lerData("2026-09-01T12:00:00-03:00").getTime()).toBe(Date.UTC(2026, 8, 1, 15));
  });

  it("formata datas de competência", () => {
    expect(fmtData("2026-09-01")).toBe("01/09/2026");
    expect(fmtMesAno("2026-09-01")).toBe("set/26");
    expect(fmtMesAnoNumerico("2026-09-01")).toBe("09/2026");
    expect(fmtMes("2026-12-01")).toBe("dez");
    expect(mesDe("2026-09-15")).toBe("2026-09");
    expect(fmtCompetencia("2026-09")).toBe("09/2026");
  });

  it("somarMeses atravessa a virada do ano nos dois sentidos", () => {
    expect(somarMeses("2026-09", -11)).toBe("2025-10");
    expect(somarMeses("2026-11", 3)).toBe("2027-02");
  });

  it("isoData, fmtDiaMes e somarDias trabalham no fuso local", () => {
    const d = new Date(2026, 0, 31);
    expect(isoData(d)).toBe("2026-01-31");
    expect(fmtDiaMes(d)).toBe("31/01");
    expect(isoData(somarDias(d, 1))).toBe("2026-02-01");
    expect(isoData(d)).toBe("2026-01-31"); // não altera a data original
  });

  it("fmtDataHora junta data e hora", () => {
    expect(fmtDataHora("2026-09-01")).toMatch(/^01\/09\/2026 às \d{2}:\d{2}$/);
  });
});

describe("esperar", () => {
  it("resolve depois do tempo pedido", async () => {
    vi.useFakeTimers();
    let resolvido = false;
    const promessa = esperar(1000).then(() => (resolvido = true));
    await vi.advanceTimersByTimeAsync(999);
    expect(resolvido).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await promessa;
    expect(resolvido).toBe(true);
    vi.useRealTimers();
  });
});
