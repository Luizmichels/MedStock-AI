from sqlalchemy import Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class Consumo(Base):
    __tablename__ = "consumos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    importacao_id: Mapped[int] = mapped_column(ForeignKey("importacoes.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("itens.id"))
    data: Mapped[Date] = mapped_column(Date)
    quantidade: Mapped[float] = mapped_column(Float)
    local_estoque: Mapped[str | None] = mapped_column(String(255), nullable=True)
    criado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    importacao = relationship("Importacao", back_populates="consumos")
    item = relationship("Item", back_populates="consumos")
