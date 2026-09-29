from sqlalchemy import Integer, Float, Date, String, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PrevisaoDiaria(Base):
    """Ponto de previsão em granularidade diária. Cada linha é a demanda
    prevista de um item para um dia futuro; os horizontes 7/15/30 dias são somas
    destes pontos."""

    __tablename__ = "previsoes_diarias"
    __table_args__ = (
        Index("ix_prev_diaria_empresa_item_data", "empresa_id", "item_id", "data"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("itens.id"))
    data: Mapped[Date] = mapped_column(Date)
    quantidade_prevista: Mapped[float] = mapped_column(Float)
    # Método usado: "croston_sba" (intermitente) ou "media_movel_sazonal".
    metodo: Mapped[str] = mapped_column(String(30))
    gerado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
