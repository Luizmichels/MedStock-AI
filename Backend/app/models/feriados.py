from sqlalchemy import Integer, String, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base

class Feriado(Base):
    __tablename__ = "feriados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[Date] = mapped_column(Date)
    uf: Mapped[str] = mapped_column(String(10))
    ds_feriado: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(50))
    criado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())