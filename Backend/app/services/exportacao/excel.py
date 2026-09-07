"""Geração de relatórios em Excel (openpyxl via pandas)."""

from io import BytesIO

import pandas as pd


def gerar_xlsx(abas: dict[str, pd.DataFrame]) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nome, df in abas.items():
            # nomes de aba do Excel têm no máximo 31 caracteres.
            df.to_excel(writer, sheet_name=nome[:31], index=False)
    return buffer.getvalue()
