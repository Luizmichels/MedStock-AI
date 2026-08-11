from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class Item(Base):
    __tablename__ = "itens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    codigo_item: Mapped[str] = mapped_column(String(100))
    descricao_item: Mapped[str] = mapped_column(String(500))
    unidade_medida: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    empresa = relationship("Empresa", back_populates="itens")
    consumos = relationship("Consumo", back_populates="item")
    consumos_tratados = relationship("ConsumoTratado", back_populates="item")
    classificacoes_abc = relationship("ClassificacaoABC", back_populates="item")
    previsoes = relationship("Previsao", back_populates="item")
