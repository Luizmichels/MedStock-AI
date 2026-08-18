from datetime import date
from pydantic import BaseModel


class FeriadoResponse(BaseModel):
    id: int
    data: date
    uf: str | None
    cidade: str | None
    ds_feriado: str
    tipo: str

    model_config = {"from_attributes": True}
