from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(255))
    cnpj: Mapped[str | None] = mapped_column(String(18), unique=True, nullable=True)
    email_responsavel: Mapped[str] = mapped_column(String(255))
    nome_responsavel: Mapped[str] = mapped_column(String(255))
    endereco: Mapped[str] = mapped_column(String(255))
    cidade: Mapped[str] = mapped_column(String(100))
    uf: Mapped[str] = mapped_column(String(10))
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    usuarios = relationship("Usuario", back_populates="empresa")
    importacoes = relationship("Importacao", back_populates="empresa")
    itens = relationship("Item", back_populates="empresa")
