from fastapi import Depends, Header, HTTPException

from security import decodificar_token


def usuario_autenticado(authorization: str | None = Header(default=None)) -> dict:
    """Exige um cabeçalho `Authorization: Bearer <token>` válido.

    Retorna o corpo do token (`sub`, `nome`, `perfil`, `iat`, `exp`) ou 401.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    corpo = decodificar_token(token)
    if corpo is None:
        raise HTTPException(
            status_code=401,
            detail="Sessão inválida ou expirada.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return corpo


def exigir_perfil(*perfis):
    """Cria uma dependência que só deixa passar os perfis informados (senão 403).

    Uso: `Depends(exigir_perfil("admin", "gerente"))`. A permissão é checada no
    backend (o frontend só esconde botões, não é segurança).
    """
    def dependencia(usuario: dict = Depends(usuario_autenticado)) -> dict:
        if usuario.get("perfil") not in perfis:
            raise HTTPException(
                status_code=403,
                detail="Seu perfil não tem permissão para esta operação.",
            )
        return usuario

    return dependencia
