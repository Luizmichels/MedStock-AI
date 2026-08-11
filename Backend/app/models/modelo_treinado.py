from sqlalchemy import Integer, String, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

class ModeloTreinado(Base):
    __tablename__ = "modelos_treinados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"))
    # 'sma' | 'sarima' | 'holt_winters' | 'random_forest' | 'xgboost'
    algoritmo: Mapped[str] = mapped_column(String(50))
    parametros: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rmse: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Indica o modelo ativo para previsões desta empresa
    ativo: Mapped[bool] = mapped_column(Boolean, default=False)
    treinado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    previsoes = relationship("Previsao", back_populates="modelo")
