"""Geração de relatórios em PDF (reportlab).

Layout: cabeçalho com a logo em todas as páginas; na primeira página, um bloco
com hospital, quem gerou e quando, seguido dos indicadores e das tabelas. O
rodapé numera as páginas ("Página 2 de 5"). A tabela principal é limitada a
``LIMITE_LINHAS_PDF`` linhas — a lista completa vai no Excel — para o PDF
continuar curto e legível.
"""

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.exportacao.dados import (
    CASAS_DECIMAIS,
    COLUNAS_MOEDA,
    Relatorio,
    fmt_moeda,
    fmt_numero,
)

LOGO_PATH = Path(__file__).resolve().parents[3] / "imagens" / "MedStockAi-logo.png"
LIMITE_LINHAS_PDF = 100
LIMITE_LINHAS_SECAO = 15

NAVY = colors.HexColor("#0A2540")
AZUL = colors.HexColor("#1F5FA0")
CINZA = colors.HexColor("#5B6B7E")
LINHA = colors.HexColor("#DCE6F0")
FUNDO = colors.HexColor("#F5F8FC")

MARGEM = 16 * mm
ALTURA_CABECALHO = 20 * mm

_ESTILO_TITULO = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=NAVY)
_ESTILO_SUB = ParagraphStyle("sub", fontName="Helvetica", fontSize=9, leading=12, textColor=CINZA)
_ESTILO_SECAO = ParagraphStyle(
    "secao", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=NAVY, spaceBefore=6, spaceAfter=4
)
_ESTILO_CELULA = ParagraphStyle("celula", fontName="Helvetica", fontSize=7.5, leading=9, textColor=NAVY)
_ESTILO_CELULA_DIR = ParagraphStyle("celula_dir", parent=_ESTILO_CELULA, alignment=2)
_ESTILO_CABECALHO = ParagraphStyle("cabecalho", parent=_ESTILO_CELULA, fontName="Helvetica-Bold", textColor=colors.white)
_ESTILO_CABECALHO_DIR = ParagraphStyle("cabecalho_dir", parent=_ESTILO_CABECALHO, alignment=2)
_ESTILO_ROTULO = ParagraphStyle("rotulo", fontName="Helvetica", fontSize=7.5, leading=9, textColor=CINZA)
_ESTILO_VALOR = ParagraphStyle("valor", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=NAVY)
_ESTILO_NOTA = ParagraphStyle("nota", fontName="Helvetica-Oblique", fontSize=8, leading=10, textColor=CINZA)

# Larguras fixas (pt); a coluna "Descrição" ocupa o restante.
_LARGURAS = {
    "Código": 58, "Unid.": 34, "Curva ABC": 50, "Grupo": 78,
    "Competência": 56,
}
_LARGURA_NUMERICA = 60


@dataclass
class ContextoExportacao:
    hospital: str
    usuario: str
    gerado_em: datetime


def _fmt_celula(coluna: str, valor) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    if coluna in COLUNAS_MOEDA:
        return fmt_moeda(float(valor))
    if coluna in CASAS_DECIMAIS:
        texto = fmt_numero(float(valor), CASAS_DECIMAIS[coluna])
        return f"{texto}%" if coluna.startswith("%") else texto
    return escape(str(valor))


def _tabela(df: pd.DataFrame, largura_util: float) -> Table:
    colunas = list(df.columns)
    numericas = [c in CASAS_DECIMAIS for c in colunas]
    fixas = [
        _LARGURAS.get(c, _LARGURA_NUMERICA if numericas[i] else 0) for i, c in enumerate(colunas)
    ]
    livres = [i for i, w in enumerate(fixas) if w == 0]
    sobra = max(largura_util - sum(fixas), 80)
    larguras = [w if w else sobra / len(livres) for w in fixas]

    cabecalho = [
        Paragraph(escape(c), _ESTILO_CABECALHO_DIR if numericas[i] else _ESTILO_CABECALHO)
        for i, c in enumerate(colunas)
    ]
    linhas = [cabecalho]
    for registro in df.itertuples(index=False):
        linhas.append([
            Paragraph(_fmt_celula(c, v), _ESTILO_CELULA_DIR if numericas[i] else _ESTILO_CELULA)
            for i, (c, v) in enumerate(zip(colunas, registro))
        ])

    tabela = Table(linhas, colWidths=larguras, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FUNDO]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINHA),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabela


def _bloco_informacoes(contexto: ContextoExportacao, largura_util: float) -> Table:
    celulas = [
        [Paragraph("Hospital", _ESTILO_ROTULO), Paragraph("Gerado por", _ESTILO_ROTULO), Paragraph("Data de geração", _ESTILO_ROTULO)],
        [
            Paragraph(f"<b>{escape(contexto.hospital)}</b>", _ESTILO_CELULA),
            Paragraph(f"<b>{escape(contexto.usuario)}</b>", _ESTILO_CELULA),
            Paragraph(f"<b>{contexto.gerado_em.strftime('%d/%m/%Y às %H:%M')}</b>", _ESTILO_CELULA),
        ],
    ]
    tabela = Table(celulas, colWidths=[largura_util * 0.44, largura_util * 0.32, largura_util * 0.24])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), FUNDO),
        ("BOX", (0, 0), (-1, -1), 0.5, LINHA),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tabela


def _indicadores(pares: list[tuple[str, str]], largura_util: float) -> Table:
    tabela = Table(
        [[Paragraph(escape(r), _ESTILO_ROTULO) for r, _ in pares], [Paragraph(escape(v), _ESTILO_VALOR) for _, v in pares]],
        colWidths=[largura_util / len(pares)] * len(pares),
    )
    tabela.setStyle(TableStyle([
        ("LINEBEFORE", (1, 0), (-1, -1), 0.5, LINHA),
        ("LINEABOVE", (0, 0), (-1, 0), 2, AZUL),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tabela


def _canvas_numerado(titulo: str, contexto: ContextoExportacao):
    """Canvas que desenha cabeçalho e rodapé em todas as páginas, com "Página X de Y"."""

    class CanvasNumerado(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._paginas = []

        def showPage(self):
            self._paginas.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._paginas)
            for estado in self._paginas:
                self.__dict__.update(estado)
                self._decorar(total)
                super().showPage()
            super().save()

        def _decorar(self, total: int) -> None:
            largura, altura = A4
            topo = altura - MARGEM
            if LOGO_PATH.exists():
                logo = ImageReader(str(LOGO_PATH))
                lw, lh = logo.getSize()
                h = 9 * mm
                self.drawImage(logo, MARGEM, topo - h, width=h * lw / lh, height=h, mask="auto")
            self.setFont("Helvetica-Bold", 9)
            self.setFillColor(NAVY)
            self.drawRightString(largura - MARGEM, topo - 3.5 * mm, titulo)
            self.setFont("Helvetica", 8)
            self.setFillColor(CINZA)
            self.drawRightString(largura - MARGEM, topo - 7.5 * mm, contexto.hospital)
            self.setStrokeColor(LINHA)
            self.setLineWidth(0.8)
            self.line(MARGEM, topo - 12 * mm, largura - MARGEM, topo - 12 * mm)

            self.line(MARGEM, MARGEM, largura - MARGEM, MARGEM)
            self.setFont("Helvetica", 7.5)
            self.drawString(
                MARGEM, MARGEM - 4 * mm,
                f"MedStock AI · gerado por {contexto.usuario} em {contexto.gerado_em.strftime('%d/%m/%Y %H:%M')}",
            )
            self.drawRightString(largura - MARGEM, MARGEM - 4 * mm, f"Página {self._pageNumber} de {total}")

    return CanvasNumerado


def gerar_pdf(relatorio: Relatorio, contexto: ContextoExportacao) -> bytes:
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGEM,
        rightMargin=MARGEM,
        topMargin=MARGEM + ALTURA_CABECALHO - 4 * mm,
        bottomMargin=MARGEM + 4 * mm,
        title=relatorio.titulo,
        author=contexto.usuario,
    )
    largura_util = A4[0] - 2 * MARGEM

    elementos = [Paragraph(escape(relatorio.titulo), _ESTILO_TITULO)]
    if relatorio.referencia:
        elementos.append(Paragraph(escape(relatorio.referencia), _ESTILO_SUB))
    elementos += [Spacer(1, 8), _bloco_informacoes(contexto, largura_util), Spacer(1, 10)]
    if relatorio.indicadores:
        elementos += [_indicadores(relatorio.indicadores, largura_util), Spacer(1, 12)]

    for nome, df in relatorio.secoes.items():
        if df.empty:
            continue
        bloco = [Paragraph(escape(nome), _ESTILO_SECAO), _tabela(df.head(LIMITE_LINHAS_SECAO), largura_util)]
        if len(df) > LIMITE_LINHAS_SECAO:
            bloco.append(Paragraph(
                f"Exibindo {LIMITE_LINHAS_SECAO} de {fmt_numero(len(df))} linhas; as demais estão no Excel.",
                _ESTILO_NOTA,
            ))
        elementos += [KeepTogether(bloco), Spacer(1, 10)]

    tabela = relatorio.tabela
    elementos.append(Paragraph(relatorio.nome_tabela, _ESTILO_SECAO))
    if tabela.empty:
        elementos.append(Paragraph("Nenhum dado disponível para este relatório.", _ESTILO_NOTA))
    else:
        elementos.append(_tabela(tabela.head(LIMITE_LINHAS_PDF), largura_util))
        if len(tabela) > LIMITE_LINHAS_PDF:
            elementos += [
                Spacer(1, 6),
                Paragraph(
                    f"Exibindo os {LIMITE_LINHAS_PDF} materiais mais relevantes de {fmt_numero(len(tabela))}. "
                    "A lista completa está na exportação em Excel.",
                    _ESTILO_NOTA,
                ),
            ]

    documento.build(elementos, canvasmaker=_canvas_numerado(relatorio.titulo, contexto))
    return buffer.getvalue()
