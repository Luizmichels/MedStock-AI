from sqlalchemy import Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class ConsumoTratado(Base):
    __tablename__ = "consumos_tratados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("itens.id"))
    # Primeiro dia do mês de referência
    periodo: Mapped[Date] = mapped_column(Date)
    quantidade_total: Mapped[float] = mapped_column(Float)
    local_estoque: Mapped[str | None] = mapped_column(String(255), nullable=True)
    atualizado_em: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    item = relationship("Item", back_populates="consumos_tratados")
