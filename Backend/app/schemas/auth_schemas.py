from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class DefinirSenhaRequest(BaseModel):
    token: str
    senha: str

class MensagemResponse(BaseModel):
    mensagem: str
