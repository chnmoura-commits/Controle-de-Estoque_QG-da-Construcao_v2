from database import conexao
from exceptions import RegraDeNegocioError, exigir
from repositories import usuario_repository as repo
from security import criar_token, gerar_hash, verificar_senha


def autenticar(dados):
    usuario = (dados.get("usuario") or "").strip()
    senha = dados.get("senha") or ""
    exigir(usuario and senha, "Informe usuário e senha.")

    with conexao() as conn:
        registro = repo.obter_por_usuario(conn, usuario)

    # Mensagem genérica para não revelar se o usuário existe.
    if registro is None or not verificar_senha(senha, registro["usuario_senha_hash"]):
        raise RegraDeNegocioError("Usuário ou senha inválidos.")
    exigir(registro["usuario_ativo"] == 1, "Usuário inativo.")

    usuario_logado = {
        "usuario": registro["usuario_nome"],
        "usuario_id": registro["usuario_id"],
        "perfil": registro["usuario_perfil"],
    }
    return {
        **usuario_logado,
        "access_token": criar_token(usuario_logado),
        "token_type": "bearer",
        # Sinaliza ao frontend que a senha é provisória e precisa ser trocada.
        "trocar_senha": bool(registro["usuario_senha_provisoria"]),
        "mensagem": "Login realizado com sucesso.",
    }


TAMANHO_MINIMO_SENHA = 8


def trocar_senha(usuario_id, senha_atual, senha_nova):
    """Troca a senha do usuário autenticado (usado no primeiro acesso)."""
    senha_atual = senha_atual or ""
    senha_nova = senha_nova or ""
    exigir(len(senha_nova) >= TAMANHO_MINIMO_SENHA,
           f"A nova senha deve ter ao menos {TAMANHO_MINIMO_SENHA} caracteres.")
    exigir(senha_nova != senha_atual,
           "A nova senha deve ser diferente da atual.")

    with conexao() as conn:
        registro = repo.obter_por_id(conn, usuario_id)
        exigir(registro is not None, "Usuário não encontrado.")
        if not verificar_senha(senha_atual, registro["usuario_senha_hash"]):
            raise RegraDeNegocioError("Senha atual incorreta.")
        repo.atualizar_senha(conn, usuario_id, gerar_hash(senha_nova))
    return {"mensagem": "Senha alterada com sucesso."}

