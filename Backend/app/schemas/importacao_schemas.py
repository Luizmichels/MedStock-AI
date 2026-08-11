from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ImportacaoResponse(BaseModel):
    id: int
    nome_arquivo: str
    tipo: str
    status: str
    total_registros: int
    registros_validos: int
    registros_invalidos: int
    erros: Optional[List[str]]
    criado_em: datetime
    concluido_em: Optional[datetime]

    model_config = {"from_attributes": True}