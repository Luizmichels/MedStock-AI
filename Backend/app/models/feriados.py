from sqlalchemy import Integer, String, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base

class Feriado(Base):
    __tablename__ = "feriados"
    __table_args__ = (
        UniqueConstraint(
            "data", "uf", "cidade", "tipo", "ds_feriado",
            name="uq_feriados_data_uf_cidade_tipo_ds",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[Date] = mapped_column(Date)
    # Nulo = feriado nacional (vale para todas as UFs)
    uf: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Nulo = feriado nacional ou estadual (vale para toda a UF)
    cidade: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ds_feriado: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(50))  # nacional | estadual | municipal
    criado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
