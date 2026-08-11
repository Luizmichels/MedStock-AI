"""
Pipeline de validação e tratamento dos dados de consumo importados.
Executado automaticamente após cada importação.
"""

import logging
from datetime import date, datetime
from io import BytesIO
from typing import BinaryIO, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from app.models.consumo import Consumo
from app.models.consumo_tratado import ConsumoTratado
from app.models.importacoes import Importacao
from app.models.itens import Item

logger = logging.getLogger(__name__)

COLUNAS_OBRIGATORIAS = {
    "codigo_item",
    "descricao_item",
    "data",
    "quantidade",
    "local_estoque",
}

# Mapeamentos alternativos de nomes de coluna aceitos nos arquivos
_ALIAS_COLUNAS = {
    "codigo": "codigo_item",
    "cod_item": "codigo_item",
    "cod": "codigo_item",
    "descricao": "descricao_item",
    "desc": "descricao_item",
    "qtd": "quantidade",
    "qtde": "quantidade",
    "quantidade_consumida": "quantidade",
    "local": "local_estoque",
    "setor": "local_estoque",
    "data_consumo": "data",
}


def _ler_arquivo(conteudo: bytes, nome_arquivo: str) -> pd.DataFrame:
    extensao = nome_arquivo.lower().rsplit(".", 1)[-1]
    if extensao == "csv":
        try:
            return pd.read_csv(BytesIO(conteudo), sep=";", encoding="utf-8")
        except Exception:
            return pd.read_csv(BytesIO(conteudo), sep=",", encoding="latin-1")
    elif extensao in ("xls", "xlsx"):
        return pd.read_excel(BytesIO(conteudo))
    else:
        raise ValueError(f"Formato não suportado: .{extensao}. Use CSV ou Excel.")


def _normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df.rename(columns=_ALIAS_COLUNAS, inplace=True)
    return df


def _validar_colunas(df: pd.DataFrame) -> None:
    faltando = COLUNAS_OBRIGATORIAS - set(df.columns)
    if faltando:
        raise ValueError(
            f"Colunas obrigatórias ausentes: {', '.join(sorted(faltando))}. "
            "O arquivo deve conter: codigo_item, descricao_item, data, quantidade, local_estoque."
        )


def _parsear_data(valor: str | date) -> date | None:
    if isinstance(valor, (date, datetime)):
        return valor if isinstance(valor, date) else valor.date()
    valor = str(valor).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def _limpar_dados(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    erros = []
    df = df.drop_duplicates()

    linhas_invalidas = []
    for idx, row in df.iterrows():
        linha_erros = []

        # Nulos em campos obrigatórios
        for col in COLUNAS_OBRIGATORIAS:
            if pd.isna(row.get(col)) or str(row.get(col, "")).strip() == "":
                linha_erros.append(f"linha {idx + 2}: campo '{col}' nulo")

        # Data
        data_parsed = _parsear_data(row.get("data"))
        if data_parsed is None:
            linha_erros.append(f"linha {idx + 2}: data inválida '{row.get('data')}'")
        else:
            df.at[idx, "data"] = data_parsed

        # Quantidade
        try:
            qtd = float(str(row.get("quantidade", "")).replace(",", "."))
            if qtd <= 0:
                linha_erros.append(
                    f"linha {idx + 2}: quantidade deve ser positiva (encontrado: {qtd})"
                )
            else:
                df.at[idx, "quantidade"] = qtd
        except (ValueError, TypeError):
            linha_erros.append(
                f"linha {idx + 2}: quantidade inválida '{row.get('quantidade')}'"
            )

        if linha_erros:
            erros.extend(linha_erros)
            linhas_invalidas.append(idx)

    df_valido = df.drop(index=linhas_invalidas).reset_index(drop=True)
    return df_valido, erros


def _upsert_item(db: Session, empresa_id: int, codigo: str, descricao: str) -> Item:
    item = db.query(Item).filter(
        Item.empresa_id == empresa_id,
        Item.codigo_item == str(codigo).strip(),
    ).first()
    if not item:
        item = Item(
            empresa_id=empresa_id,
            codigo_item=str(codigo).strip(),
            descricao_item=str(descricao).strip(),
        )
        db.add(item)
        db.flush()
    return item


def _salvar_consumos_brutos(
    db: Session, df: pd.DataFrame, empresa_id: int, importacao_id: int
) -> None:
    for _, row in df.iterrows():
        item = _upsert_item(db, empresa_id, row["codigo_item"], row["descricao_item"])
        consumo = Consumo(
            empresa_id=empresa_id,
            importacao_id=importacao_id,
            item_id=item.id,
            data=row["data"],
            quantidade=float(row["quantidade"]),
            local_estoque=str(row.get("local_estoque", "")).strip() or None,
        )
        db.add(consumo)


def _agregar_consumos_tratados(db: Session, empresa_id: int) -> None:
    """Agrega consumos brutos por item + mês e faz upsert em consumos_tratados."""
    consumos = (
        db.query(Consumo)
        .filter(Consumo.empresa_id == empresa_id)
        .all()
    )
    if not consumos:
        return

    registros = [
        {
            "item_id": c.item_id,
            "periodo": c.data.replace(day=1),
            "quantidade": c.quantidade,
            "local_estoque": c.local_estoque,
        }
        for c in consumos
    ]
    df = pd.DataFrame(registros)
    agregado = (
        df.groupby(["item_id", "periodo", "local_estoque"])["quantidade"]
        .sum()
        .reset_index()
        .rename(columns={"quantidade": "quantidade_total"})
    )

    # Remove tratados antigos e recria (estratégia simples para recalculo completo)
    db.query(ConsumoTratado).filter(ConsumoTratado.empresa_id == empresa_id).delete()
    for _, row in agregado.iterrows():
        tratado = ConsumoTratado(
            empresa_id=empresa_id,
            item_id=int(row["item_id"]),
            periodo=row["periodo"],
            quantidade_total=float(row["quantidade_total"]),
            local_estoque=row["local_estoque"] if pd.notna(row["local_estoque"]) else None,
        )
        db.add(tratado)


def processar_arquivo(
    db: Session,
    conteudo: bytes,
    nome_arquivo: str,
    empresa_id: int,
    usuario_id: int,
) -> Importacao:
    """
    Ponto de entrada do pipeline. Retorna o registro de Importacao criado.
    """
    extensao = nome_arquivo.lower().rsplit(".", 1)[-1]
    tipo = "excel" if extensao in ("xls", "xlsx") else "csv"

    importacao = Importacao(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        nome_arquivo=nome_arquivo,
        tipo=tipo,
        status="processando",
    )
    db.add(importacao)
    db.flush()

    try:
        logger.info("Iniciando pipeline de importação id=%s empresa=%s", importacao.id, empresa_id)

        df_raw = _ler_arquivo(conteudo, nome_arquivo)
        df_raw = _normalizar_colunas(df_raw)
        _validar_colunas(df_raw)

        df_valido, erros = _limpar_dados(df_raw)

        importacao.total_registros = len(df_raw)
        importacao.registros_validos = len(df_valido)
        importacao.registros_invalidos = len(df_raw) - len(df_valido)
        importacao.erros = erros or None

        if not df_valido.empty:
            _salvar_consumos_brutos(db, df_valido, empresa_id, importacao.id)
            _agregar_consumos_tratados(db, empresa_id)

        importacao.status = "concluido"
        importacao.concluido_em = datetime.utcnow()
        logger.info(
            "Pipeline concluído id=%s válidos=%s inválidos=%s",
            importacao.id, importacao.registros_validos, importacao.registros_invalidos,
        )

    except Exception as exc:
        importacao.status = "erro"
        importacao.erros = [str(exc)]
        importacao.concluido_em = datetime.utcnow()
        logger.error("Erro na importação id=%s: %s", importacao.id, exc, exc_info=True)

    db.commit()
    db.refresh(importacao)
    return importacao
