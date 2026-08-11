from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base

class SolicitacaoAcesso(Base):
    __tablename__ = "solicitacoes_acesso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome_responsavel: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    nome_hospital: Mapped[str] = mapped_column(String(255))
    endereco: Mapped[str] = mapped_column(String(255))
    # 'pendente' | 'aprovado' | 'rejeitado'
    uf: Mapped[str] = mapped_column(String(2))
    cidade: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pendente")
    criado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
