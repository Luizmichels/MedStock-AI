"""Testes das dependências de autenticação/autorização."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import criar_token
from app.dependencies import (
    get_current_super_admin,
    get_current_user,
    require_admin,
)
from app.models.usuario import Usuario


def _cred(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_get_current_user_com_token_valido(db_session, usuario_admin):
    token = criar_token({"sub": str(usuario_admin.id), "perfil": "admin"})
    usuario = get_current_user(_cred(token), db_session)
    assert usuario.id == usuario_admin.id


def test_get_current_user_token_invalido_401(db_session):
    with pytest.raises(HTTPException) as exc:
        get_current_user(_cred("token.invalido.xyz"), db_session)
    assert exc.value.status_code == 401


def test_get_current_user_sem_sub_401(db_session):
    token = criar_token({"perfil": "admin"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(_cred(token), db_session)
    assert exc.value.status_code == 401


def test_get_current_user_usuario_inexistente_401(db_session):
    token = criar_token({"sub": "99999", "perfil": "admin"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(_cred(token), db_session)
    assert exc.value.status_code == 401


def test_require_admin_aceita_admin(usuario_admin):
    assert require_admin(usuario_admin) is usuario_admin


def test_require_admin_aceita_super_admin():
    # Correção D8: o super_admin também é perfil administrativo.
    super_admin = Usuario(nome="SA", email="sa@x.com", perfil="super_admin", ativo=True)
    assert require_admin(super_admin) is super_admin


def test_require_admin_rejeita_usuario_comum(usuario_comum):
    with pytest.raises(HTTPException) as exc:
        require_admin(usuario_comum)
    assert exc.value.status_code == 403


def test_get_current_super_admin_com_perfil_correto(token_super_admin):
    payload = get_current_super_admin(_cred(token_super_admin))
    assert payload["perfil"] == "super_admin"


def test_get_current_super_admin_rejeita_perfil_errado(usuario_admin):
    token = criar_token({"sub": str(usuario_admin.id), "perfil": "admin"})
    with pytest.raises(HTTPException) as exc:
        get_current_super_admin(_cred(token))
    assert exc.value.status_code == 403
