from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ChaveIntegracao(Base):
    """Chave de API usada pelo sistema do hospital (ERP/estoque) para enviar
    consumos sem login. Só o hash SHA-256 é guardado; a chave em texto aparece
    uma única vez, quando é gerada. Cada hospital tem no máximo uma chave ativa."""

    __tablename__ = "chaves_integracao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), index=True)
    # Usuário (admin) que gerou a chave; as importações via API ficam no nome dele.
    criado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    prefixo: Mapped[str] = mapped_column(String(16))  # início da chave, para identificá-la na tela
    hash_chave: Mapped[str] = mapped_column(String(64), unique=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    ultimo_uso_em: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    revogada_em: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
