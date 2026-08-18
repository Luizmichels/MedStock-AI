from sqlalchemy import Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base

class FeriadoSincronizacao(Base):
    """Controla quais combinações uf+cidade+ano já foram buscadas na feriados.dev,
    evitando chamadas repetidas mesmo quando o ano não tem feriado municipal."""

    __tablename__ = "feriados_sincronizacoes"
    __table_args__ = (
        UniqueConstraint("uf", "cidade", "ano", name="uq_feriados_sync_uf_cidade_ano"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uf: Mapped[str] = mapped_column(String(10))
    cidade: Mapped[str] = mapped_column(String(100))
    ano: Mapped[int] = mapped_column(Integer)
    sincronizado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
