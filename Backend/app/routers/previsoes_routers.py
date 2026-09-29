import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user, require_admin
from app.models.classificacao_abc import ClassificacaoABC
from app.models.modelo_treinado import ModeloTreinado
from app.models.previsoes import Previsao
from app.schemas.comuns import Pagina
from app.schemas.previsao_schemas import (
    ItemOmitidoResponse,
    ModeloTreinadoResponse,
    PrevisaoResponse,
    StatusTreinoResponse,
)
from app.models.usuario import Usuario
from app.services.ml.elegibilidade import separar_elegiveis
from app.services.ml.predicao import gerar_previsoes
from app.services.ml.treinamento import carregar_series_por_item, treinar_empresa
from app.services.ml.intermitencia import analisar_empresa, resumir
from app.services.ml import previsao_diaria as diaria
from app.models.previsao_diaria import PrevisaoDiaria
from app.schemas.intermitencia_schemas import (
    AnaliseIntermitenciaResponse,
    IntermitenciaItemResponse,
)
from app.schemas.previsao_diaria_schemas import (
    HorizontesDiarios,
    PontoDiario,
    PrevisaoDiariaDetalhe,
    ResumoDiarioItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/previsoes", tags=["Previsões"])

# Estado em memória dos treinos em andamento (processo único — TCC).
_TREINOS_EM_ANDAMENTO: set[int] = set()
_DIARIOS_EM_ANDAMENTO: set[int] = set()


def _executar_treino(empresa_id: int) -> None:
    db = SessionLocal()
    try:
        modelo = treinar_empresa(db, empresa_id)
        gerar_previsoes(db, empresa_id, modelo)
    except Exception:  # pragma: no cover - proteção do worker de background
        logger.exception("Falha no treino em background empresa=%s", empresa_id)
    finally:
        _TREINOS_EM_ANDAMENTO.discard(empresa_id)
        db.close()


@router.post("/treinar", status_code=202)
def treinar(
    tarefas: BackgroundTasks,
    current_user: Usuario = Depends(require_admin),
):
    empresa_id = current_user.empresa_id
    if empresa_id in _TREINOS_EM_ANDAMENTO:
        raise HTTPException(status_code=409, detail="Já há um treino em andamento para esta empresa.")
    _TREINOS_EM_ANDAMENTO.add(empresa_id)
    tarefas.add_task(_executar_treino, empresa_id)
    return {"detail": "Treinamento iniciado."}


@router.get("/modelos", response_model=list[ModeloTreinadoResponse])
def listar_modelos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return (
        db.query(ModeloTreinado)
        .filter(ModeloTreinado.empresa_id == current_user.empresa_id)
        .order_by(ModeloTreinado.treinado_em.desc())
        .all()
    )


@router.post("/modelos/{modelo_id}/ativar", response_model=ModeloTreinadoResponse)
def ativar(
    modelo_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    from app.services.ml.treinamento import ativar_modelo

    modelo = ativar_modelo(db, current_user.empresa_id, modelo_id)
    if not modelo:
        raise HTTPException(status_code=404, detail="Modelo não encontrado")
    return modelo


@router.get("/", response_model=Pagina[PrevisaoResponse])
def listar_previsoes(
    item_id: int | None = Query(None),
    periodo_inicio: date | None = Query(None),
    periodo_fim: date | None = Query(None),
    classe_abc: str | None = Query(None),
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = db.query(Previsao).filter(Previsao.empresa_id == current_user.empresa_id)
    if item_id is not None:
        query = query.filter(Previsao.item_id == item_id)
    if periodo_inicio is not None:
        query = query.filter(Previsao.periodo >= periodo_inicio)
    if periodo_fim is not None:
        query = query.filter(Previsao.periodo <= periodo_fim)
    if classe_abc:
        ids_classe = (
            db.query(ClassificacaoABC.item_id)
            .filter(
                ClassificacaoABC.empresa_id == current_user.empresa_id,
                ClassificacaoABC.classe == classe_abc,
            )
            .subquery()
        )
        query = query.filter(Previsao.item_id.in_(ids_classe))

    total = query.count()
    registros = (
        query.order_by(Previsao.item_id, Previsao.periodo)
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
        .all()
    )
    itens = [PrevisaoResponse.model_validate(p) for p in registros]
    return Pagina(itens=itens, total=total, pagina=pagina, tamanho=tamanho)


@router.get("/itens-omitidos", response_model=list[ItemOmitidoResponse])
def itens_omitidos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    series = carregar_series_por_item(db, current_user.empresa_id)
    _elegiveis, omitidos = separar_elegiveis(series)
    return [
        ItemOmitidoResponse(
            item_id=o.item_id, meses_disponiveis=o.meses_disponiveis, motivo=o.motivo
        )
        for o in omitidos
    ]


@router.get("/status-treino", response_model=StatusTreinoResponse)
def status_treino(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    ultimo = (
        db.query(ModeloTreinado)
        .filter(ModeloTreinado.empresa_id == current_user.empresa_id)
        .order_by(ModeloTreinado.treinado_em.desc())
        .first()
    )
    return StatusTreinoResponse(
        em_andamento=current_user.empresa_id in _TREINOS_EM_ANDAMENTO,
        ultimo_modelo=ultimo,
    )


def _executar_previsao_diaria(empresa_id: int) -> None:
    db = SessionLocal()
    try:
        diaria.gerar_previsoes_diarias(db, empresa_id)
    except Exception:  # pragma: no cover - proteção do worker de background
        logger.exception("Falha na previsão diária empresa=%s", empresa_id)
    finally:
        _DIARIOS_EM_ANDAMENTO.discard(empresa_id)
        db.close()


@router.post("/diaria/gerar", status_code=202)
def gerar_diaria(
    tarefas: BackgroundTasks,
    current_user: Usuario = Depends(require_admin),
):
    """Gera as previsões diárias (Croston/SBA para itens intermitentes,
    média móvel sazonal para os regulares) e os horizontes 7/15/30 dias."""
    empresa_id = current_user.empresa_id
    if empresa_id in _DIARIOS_EM_ANDAMENTO:
        raise HTTPException(status_code=409, detail="Já há uma geração diária em andamento.")
    _DIARIOS_EM_ANDAMENTO.add(empresa_id)
    tarefas.add_task(_executar_previsao_diaria, empresa_id)
    return {"detail": "Previsão diária iniciada."}


@router.get("/diaria/resumo", response_model=list[ResumoDiarioItem])
def resumo_diario(
    item_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Somatórios previstos por item nos horizontes próximo dia / 7 / 15 / 30 dias."""
    linhas = diaria.resumo_por_item(db, current_user.empresa_id, item_id)
    return [ResumoDiarioItem(**linha) for linha in linhas]


@router.get("/diaria/{item_id}", response_model=PrevisaoDiariaDetalhe)
def detalhe_diario(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Curva diária prevista de um item (os ``HORIZONTE_DIARIO`` dias) e os
    horizontes agregados."""
    pontos = (
        db.query(PrevisaoDiaria)
        .filter(
            PrevisaoDiaria.empresa_id == current_user.empresa_id,
            PrevisaoDiaria.item_id == item_id,
        )
        .order_by(PrevisaoDiaria.data)
        .all()
    )
    if not pontos:
        raise HTTPException(status_code=404, detail="Sem previsão diária para o item.")

    resumo = diaria.resumo_por_item(db, current_user.empresa_id, item_id)[0]
    return PrevisaoDiariaDetalhe(
        item_id=item_id,
        metodo=resumo["metodo"],
        base=resumo["base"],
        horizontes=HorizontesDiarios(
            proximo_dia=resumo["proximo_dia"],
            sete_dias=resumo["sete_dias"],
            quinze_dias=resumo["quinze_dias"],
            trinta_dias=resumo["trinta_dias"],
        ),
        dias=[
            PontoDiario(data=p.data, quantidade_prevista=p.quantidade_prevista)
            for p in pontos
        ],
    )


@router.get("/analise-intermitencia", response_model=AnaliseIntermitenciaResponse)
def analise_intermitencia(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Classificação SBC: diagnostica a intermitência da demanda de cada
    item para embasar a decisão de granularidade (diária vs mensal)."""
    resultados = analisar_empresa(db, current_user.empresa_id)
    return AnaliseIntermitenciaResponse(
        resumo=resumir(resultados),
        itens=[IntermitenciaItemResponse.model_validate(r) for r in resultados],
    )
