from sqlalchemy import Integer, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class Previsao(Base):
    __tablename__ = "previsoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    modelo_id: Mapped[int] = mapped_column(ForeignKey("modelos_treinados.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("itens.id"))
    periodo: Mapped[Date] = mapped_column(Date)
    quantidade_prevista: Mapped[float] = mapped_column(Float)
    intervalo_inferior: Mapped[float | None] = mapped_column(Float, nullable=True)
    intervalo_superior: Mapped[float | None] = mapped_column(Float, nullable=True)
    gerado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    modelo = relationship("ModeloTreinado", back_populates="previsoes")
    item = relationship("Item", back_populates="previsoes")
