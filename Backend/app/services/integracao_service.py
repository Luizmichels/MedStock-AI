"""Chaves de integração: geração, revogação e autenticação por ``X-API-Key``.

A chave tem alta entropia (32 bytes aleatórios), então um SHA-256 basta para
guardá-la — não é uma senha escolhida por pessoa, que exigiria bcrypt.
"""

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.chave_integracao import ChaveIntegracao

PREFIXO_CHAVE = "msk_"
TAMANHO_PREFIXO_EXIBIDO = 12


def _hash(chave: str) -> str:
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


def _agora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def chave_ativa(db: Session, empresa_id: int) -> ChaveIntegracao | None:
    return (
        db.query(ChaveIntegracao)
        .filter(ChaveIntegracao.empresa_id == empresa_id, ChaveIntegracao.ativa.is_(True))
        .first()
    )


def revogar_chave(db: Session, empresa_id: int) -> bool:
    """Revoga a chave ativa do hospital. Devolve False se não havia nenhuma."""
    chave = chave_ativa(db, empresa_id)
    if chave is None:
        return False
    chave.ativa = False
    chave.revogada_em = _agora()
    db.commit()
    return True


def gerar_chave(db: Session, empresa_id: int, usuario_id: int) -> tuple[str, ChaveIntegracao]:
    """Gera uma nova chave (a anterior, se houver, deixa de funcionar na hora)."""
    revogar_chave(db, empresa_id)
    texto = PREFIXO_CHAVE + secrets.token_urlsafe(32)
    registro = ChaveIntegracao(
        empresa_id=empresa_id,
        criado_por=usuario_id,
        prefixo=texto[:TAMANHO_PREFIXO_EXIBIDO],
        hash_chave=_hash(texto),
        ativa=True,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return texto, registro


def autenticar(db: Session, chave: str | None) -> ChaveIntegracao:
    """Valida a chave enviada no cabeçalho e registra o uso."""
    if not chave:
        raise HTTPException(status_code=401, detail="Informe a chave de integração no cabeçalho X-API-Key.")
    registro = (
        db.query(ChaveIntegracao)
        .filter(ChaveIntegracao.hash_chave == _hash(chave.strip()), ChaveIntegracao.ativa.is_(True))
        .first()
    )
    if registro is None:
        raise HTTPException(status_code=401, detail="Chave de integração inválida ou revogada.")
    registro.ultimo_uso_em = _agora()
    db.commit()
    return registro
