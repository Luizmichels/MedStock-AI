from sqlalchemy import Integer, String, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base


class LogExecucao(Base):
    """Registro de rastreabilidade de execuções (RNF09): importações, treinos,
    cargas de ERP e falhas de integração."""

    __tablename__ = "logs_execucao"
    __table_args__ = (
        Index("ix_logs_empresa_modulo", "empresa_id", "modulo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Nulo = evento de nível sistema (sem empresa associada)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"), nullable=True)
    modulo: Mapped[str] = mapped_column(String(50))  # 'importacao' | 'treino' | 'erp' | ...
    nivel: Mapped[str] = mapped_column(String(20))  # 'info' | 'warning' | 'erro'
    mensagem: Mapped[str] = mapped_column(String(1000))
    contexto: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    criado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
