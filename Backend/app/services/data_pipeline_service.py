import logging
from datetime import date, datetime, timezone
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
    "valor",
    "local_estoque",
}

# Nº de linhas processadas e gravadas por lote.
TAMANHO_LOTE = 15_000
MAX_ERROS_REPORTADOS = 1_000

# Mapeamentos alternativos de nomes de coluna aceitos nos arquivos.
_ALIAS_COLUNAS = {
    "codigo": "codigo_item",
    "cod_item": "codigo_item",
    "cod": "codigo_item",
    "descricao": "descricao_item",
    "desc": "descricao_item",
    "qtd": "quantidade",
    "qtde": "quantidade",
    "quantidade_consumida": "quantidade",
    "valor_total": "valor",
    "valor_consumo": "valor",
    "preco": "valor",
    "preco_total": "valor",
    "local": "local_estoque",
    "setor": "local_estoque",
    "data_consumo": "data",
    "dt_mes": "data",
    "ds_centro_custo": "local_estoque",
    "cd_material": "codigo_item",
    "ds_material": "descricao_item",
    "ds_grupo_material": "grupo_item",
    "ds_subgrupo_material": "subgrupo_item",
    "ds_classe_material": "classe_item",
    "cd_unid": "unidade_medida",
    "qt_consumo": "quantidade",
    "vl_consumo": "valor",
}


def _ler_csv(conteudo: bytes) -> pd.DataFrame:
    """Lê CSV detectando separador (';' ou ',') e codificação (utf-8/latin-1)"""
    ultima_excecao: Exception | None = None
    fallback: pd.DataFrame | None = None
    for encoding in ("utf-8-sig", "latin-1"):
        for sep in (";", ","):
            try:
                df = pd.read_csv(BytesIO(conteudo), sep=sep, encoding=encoding)
            except Exception as exc:
                ultima_excecao = exc
                continue
            if df.shape[1] > 1:
                return df
            if fallback is None:
                fallback = df
    if fallback is not None:
        return fallback
    raise ultima_excecao or ValueError("Não foi possível ler o CSV.")


def _ler_arquivo(conteudo: bytes, nome_arquivo: str) -> pd.DataFrame:
    extensao = nome_arquivo.lower().rsplit(".", 1)[-1]
    if extensao == "csv":
        return _ler_csv(conteudo)
    elif extensao in ("xls", "xlsx"):
        return pd.read_excel(BytesIO(conteudo))
    else:
        raise ValueError(f"Formato não suportado: .{extensao}. Use CSV ou Excel.")


def _detectar_dialeto_csv(conteudo: bytes) -> tuple[str, str]:
    """(separador, encoding) inferidos a partir do início do arquivo, para ler
    o restante em lotes com os mesmos parâmetros."""
    amostra = conteudo[:65536]
    for encoding in ("utf-8-sig", "latin-1"):
        for sep in (";", ","):
            try:
                cabecalho = pd.read_csv(
                    BytesIO(amostra), sep=sep, encoding=encoding, nrows=5
                )
            except Exception:
                continue
            if cabecalho.shape[1] > 1:
                return sep, encoding
    return ";", "utf-8-sig"


def _blocos_dataframe(conteudo: bytes, nome_arquivo: str, tamanho: int):
    """Gera o arquivo em blocos de ``tamanho`` linhas (streaming), evitando
    carregar todo o conteúdo tabulado de uma vez."""
    extensao = nome_arquivo.lower().rsplit(".", 1)[-1]
    if extensao == "csv":
        sep, encoding = _detectar_dialeto_csv(conteudo)
        leitor = pd.read_csv(
            BytesIO(conteudo), sep=sep, encoding=encoding, chunksize=tamanho
        )
        for bloco in leitor:
            yield bloco
    elif extensao in ("xls", "xlsx"):
        # Excel não suporta leitura em chunks; fatiamos o DataFrame já carregado.
        df = pd.read_excel(BytesIO(conteudo))
        for inicio in range(0, len(df), tamanho):
            yield df.iloc[inicio:inicio + tamanho].copy()
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
    formatos = (
        # Datas completas
        "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S",
        # Competências mensais (DT_MES) -> normalizadas para o 1º dia do mês
        "%Y-%m", "%m/%Y", "%Y/%m", "%m-%Y", "%Y%m",
    )
    for fmt in formatos:
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def _numerico(coluna: pd.Series) -> pd.Series:
    """Converte para float aceitando vírgula decimal; inválidos viram NaN."""
    return pd.to_numeric(
        coluna.astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce",
    )


def _limpar_dados(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    df = df.drop_duplicates().copy()  # mantém o índice original para o número da linha
    erros: list[str] = []
    invalidas = pd.Series(False, index=df.index)

    def _linha(idx) -> int:
        return int(idx) + 2

    # Nulos em campos obrigatórios
    for col in COLUNAS_OBRIGATORIAS:
        coluna = df[col]
        nulo = coluna.isna() | (coluna.astype(str).str.strip() == "")
        for idx in df.index[nulo]:
            erros.append(f"linha {_linha(idx)}: campo '{col}' nulo")
        invalidas |= nulo

    # Data
    datas = df["data"].apply(_parsear_data)
    data_invalida = datas.isna()
    for idx in df.index[data_invalida]:
        erros.append(f"linha {_linha(idx)}: data inválida '{df.at[idx, 'data']}'")
    df["data"] = datas
    invalidas |= data_invalida

    # Quantidade e Valor (mesma regra: numérico e estritamente positivo)
    for col in ("quantidade", "valor"):
        numerico = _numerico(df[col])
        invalido = numerico.isna()
        nao_positivo = (~invalido) & (numerico <= 0)
        for idx in df.index[invalido]:
            erros.append(f"linha {_linha(idx)}: {col} inválid{'a' if col == 'quantidade' else 'o'} '{df.at[idx, col]}'")
        for idx in df.index[nao_positivo]:
            erros.append(
                f"linha {_linha(idx)}: {col} deve ser positiv{'a' if col == 'quantidade' else 'o'} "
                f"(encontrado: {numerico[idx]})"
            )
        df[col] = numerico
        invalidas |= invalido | nao_positivo

    df_valido = df[~invalidas].reset_index(drop=True)
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
            valor=float(row["valor"]),
            local_estoque=str(row.get("local_estoque", "")).strip() or None,
        )
        db.add(consumo)


def _resolver_item_id(
    db: Session, empresa_id: int, codigo, descricao, cache: dict[str, int]
) -> int:
    """id do item, usando um cache em memória para evitar um SELECT por linha.
    Cria o item na primeira vez que o código aparece."""
    codigo = str(codigo).strip()
    if codigo in cache:
        return cache[codigo]
    item = db.query(Item).filter(
        Item.empresa_id == empresa_id, Item.codigo_item == codigo
    ).first()
    if item is None:
        item = Item(
            empresa_id=empresa_id,
            codigo_item=codigo,
            descricao_item=str(descricao).strip(),
        )
        db.add(item)
        db.flush()
    cache[codigo] = item.id
    return item.id


def _salvar_bloco(
    db: Session, df: pd.DataFrame, empresa_id: int, importacao_id: int,
    cache: dict[str, int],
) -> None:
    """Insere um lote de consumos em bulk, resolvendo item_id via cache."""
    registros = []
    for _, row in df.iterrows():
        item_id = _resolver_item_id(
            db, empresa_id, row["codigo_item"], row["descricao_item"], cache
        )
        registros.append({
            "empresa_id": empresa_id,
            "importacao_id": importacao_id,
            "item_id": item_id,
            "data": row["data"],
            "quantidade": float(row["quantidade"]),
            "valor": float(row["valor"]),
            "local_estoque": str(row.get("local_estoque", "")).strip() or None,
        })
    if registros:
        db.bulk_insert_mappings(Consumo, registros)


def _agregar_consumos_tratados(db: Session, empresa_id: int) -> None:
    """Agrega consumos brutos por item + mês (+ local) e recria consumos_tratados.

    Percorre os consumos em streaming (``yield_per``) acumulando apenas os grupos
    (item, mês, local) — o uso de memória fica proporcional ao número de grupos,
    não ao total de linhas.
    """
    agregados: dict[tuple, dict] = {}
    consulta = (
        db.query(
            Consumo.item_id, Consumo.data, Consumo.quantidade,
            Consumo.valor, Consumo.local_estoque,
        )
        .filter(Consumo.empresa_id == empresa_id)
        .yield_per(10_000)
    )
    for item_id, data, quantidade, valor, local in consulta:
        chave = (item_id, data.replace(day=1), local)
        acc = agregados.get(chave)
        if acc is None:
            agregados[chave] = {"quantidade": float(quantidade), "valor": float(valor)}
        else:
            acc["quantidade"] += float(quantidade)
            acc["valor"] += float(valor)

    # Remove tratados antigos e recria (recálculo completo).
    db.query(ConsumoTratado).filter(ConsumoTratado.empresa_id == empresa_id).delete()
    if not agregados:
        return
    registros = [
        {
            "empresa_id": empresa_id,
            "item_id": item_id,
            "periodo": periodo,
            "quantidade_total": valores["quantidade"],
            "valor_total": valores["valor"],
            "local_estoque": local,
        }
        for (item_id, periodo, local), valores in agregados.items()
    ]
    db.bulk_insert_mappings(ConsumoTratado, registros)


def criar_importacao_processando(
    db: Session, nome_arquivo: str, empresa_id: int, usuario_id: int
) -> Importacao:
    """Cria o registro de importação com status 'processando' (persistido)."""
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
    db.commit()
    db.refresh(importacao)
    return importacao


def executar_pipeline(
    db: Session, importacao: Importacao, conteudo: bytes, nome_arquivo: str, empresa_id: int
) -> Importacao:
    """Processa o arquivo dentro de uma importação já criada e atualiza seu status.

    A leitura, limpeza e gravação são feitas em lotes de ``TAMANHO_LOTE`` linhas,
    com commit por lote, para manter o uso de memória constante e permitir
    acompanhar o progresso em arquivos grandes (o `registros_validos` sobe a cada
    lote). A agregação de `consumos_tratados` roda uma vez ao final.
    """
    importacao_id = importacao.id
    try:
        logger.info("Iniciando pipeline de importação id=%s empresa=%s", importacao_id, empresa_id)

        cache_itens: dict[str, int] = {}
        total = validos = invalidos = 0
        erros: list[str] = []
        colunas_validadas = False

        for bloco in _blocos_dataframe(conteudo, nome_arquivo, TAMANHO_LOTE):
            bloco = _normalizar_colunas(bloco)
            if not colunas_validadas:
                _validar_colunas(bloco)  # cabeçalho basta ser checado uma vez
                colunas_validadas = True

            df_valido, erros_bloco = _limpar_dados(bloco)
            total += len(bloco)
            validos += len(df_valido)
            invalidos += len(bloco) - len(df_valido)
            if len(erros) < MAX_ERROS_REPORTADOS and erros_bloco:
                erros.extend(erros_bloco[: MAX_ERROS_REPORTADOS - len(erros)])

            if not df_valido.empty:
                _salvar_bloco(db, df_valido, empresa_id, importacao_id, cache_itens)

            # Progresso incremental persistido (visível via GET /importacoes/{id}).
            importacao.total_registros = total
            importacao.registros_validos = validos
            importacao.registros_invalidos = invalidos
            db.commit()

        if validos:
            _agregar_consumos_tratados(db, empresa_id)

        if len(erros) >= MAX_ERROS_REPORTADOS:
            erros.append(
                f"... lista truncada em {MAX_ERROS_REPORTADOS} mensagens "
                f"(total de linhas inválidas: {invalidos})."
            )
        importacao.erros = erros or None
        importacao.status = "concluido"
        importacao.concluido_em = datetime.now(timezone.utc)
        logger.info(
            "Pipeline concluído id=%s válidos=%s inválidos=%s",
            importacao_id, validos, invalidos,
        )

    except Exception as exc:
        importacao.status = "erro"
        importacao.erros = [str(exc)]
        importacao.concluido_em = datetime.now(timezone.utc)
        logger.error("Erro na importação id=%s: %s", importacao.id, exc, exc_info=True)

    db.commit()
    db.refresh(importacao)

    from app.services import log_service

    if importacao.status == "concluido":
        log_service.registrar(
            db, "importacao", "info",
            f"Importação {importacao.id} concluída",
            empresa_id=empresa_id,
            contexto={
                "arquivo": nome_arquivo,
                "validos": importacao.registros_validos,
                "invalidos": importacao.registros_invalidos,
            },
        )
    else:
        log_service.registrar(
            db, "importacao", "erro",
            f"Importação {importacao.id} falhou",
            empresa_id=empresa_id,
            contexto={"arquivo": nome_arquivo, "erros": importacao.erros},
        )

    return importacao


def processar_arquivo(
    db: Session,
    conteudo: bytes,
    nome_arquivo: str,
    empresa_id: int,
    usuario_id: int,
) -> Importacao:
    """Ponto de entrada síncrono do pipeline: cria a importação e a processa."""
    importacao = criar_importacao_processando(db, nome_arquivo, empresa_id, usuario_id)
    return executar_pipeline(db, importacao, conteudo, nome_arquivo, empresa_id)
