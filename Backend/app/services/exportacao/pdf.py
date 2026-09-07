"""Geração de relatórios em PDF (reportlab)."""

from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def gerar_pdf(df: pd.DataFrame, titulo: str, subtitulo: str = "") -> bytes:
    buffer = BytesIO()
    documento = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    estilos = getSampleStyleSheet()

    elementos = [Paragraph(titulo, estilos["Title"])]
    if subtitulo:
        elementos.append(Paragraph(subtitulo, estilos["Normal"]))
    elementos.append(Spacer(1, 12))

    if df.empty:
        elementos.append(Paragraph("Nenhum dado disponível para o período.", estilos["Normal"]))
    else:
        dados = [list(df.columns)] + df.astype(str).values.tolist()
        tabela = Table(dados, repeatRows=1)
        tabela.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ])
        )
        elementos.append(tabela)

    documento.build(elementos)
    return buffer.getvalue()
