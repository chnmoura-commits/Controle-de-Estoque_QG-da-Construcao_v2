from fastapi import APIRouter, Depends

from controllers.dependencias import usuario_autenticado
from models.schemas import LoginIn, TrocaSenhaIn
from process import auth_process

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login")
def login(corpo: LoginIn):
    return auth_process.autenticar(corpo.model_dump())


@router.post("/trocar-senha")
def trocar_senha(corpo: TrocaSenhaIn, usuario=Depends(usuario_autenticado)):
    """Troca a senha do usuário logado (obrigatório no primeiro acesso)."""
    return auth_process.trocar_senha(usuario["sub"], corpo.senha_atual, corpo.senha_nova)
