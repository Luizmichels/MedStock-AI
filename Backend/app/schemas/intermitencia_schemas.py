"""Schemas da análise de intermitência (SBC)"""

from pydantic import BaseModel


class IntermitenciaItemResponse(BaseModel):
    item_id: int
    dias_totais: int
    dias_com_demanda: int
    densidade: float
    adi: float | None = None
    cv2: float | None = None
    classe: str
    adequado_diario: bool

    model_config = {"from_attributes": True}


class ResumoIntermitencia(BaseModel):
    total_itens: int
    por_classe: dict[str, int]
    itens_adequados_ao_diario: int
    percentual_adequado_ao_diario: float


class AnaliseIntermitenciaResponse(BaseModel):
    resumo: ResumoIntermitencia
    itens: list[IntermitenciaItemResponse]
