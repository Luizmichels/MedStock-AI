from sqlalchemy import Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class ClassificacaoABC(Base):
    __tablename__ = "classificacao_abc"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("itens.id"))
    classe: Mapped[str] = mapped_column(String(1))  # 'A' | 'B' | 'C'
    valor_acumulado_percentual: Mapped[float] = mapped_column(Float)
    calculado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    item = relationship("Item", back_populates="classificacoes_abc")
