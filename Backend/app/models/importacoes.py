from sqlalchemy import Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class Importacao(Base):
    __tablename__ = "importacoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    nome_arquivo: Mapped[str] = mapped_column(String(500))
    tipo: Mapped[str] = mapped_column(String(10))  # 'csv' | 'excel' | 'api'
    status: Mapped[str] = mapped_column(String(20))  # 'processando' | 'concluido' | 'erro'
    total_registros: Mapped[int] = mapped_column(Integer, default=0)
    registros_validos: Mapped[int] = mapped_column(Integer, default=0)
    registros_invalidos: Mapped[int] = mapped_column(Integer, default=0)
    erros: Mapped[list | None] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    concluido_em: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)

    empresa = relationship("Empresa", back_populates="importacoes")
    usuario = relationship("Usuario")
    consumos = relationship("Consumo", back_populates="importacao")
