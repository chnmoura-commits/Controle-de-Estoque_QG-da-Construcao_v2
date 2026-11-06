"""Funções de hash e verificação de senha (PBKDF2 com salt aleatório)."""
import base64
import hashlib
import hmac
import json
import secrets
import time

from config import JWT_EXPIRACAO_MINUTOS, JWT_SEGREDO, SENHA_ITERACOES

_ALGORITMO = "sha256"

# Perfis de acesso fixos do sistema. O mais restrito é o padrão.
PERFIL_PADRAO = "vendedor"
PERFIS = ("admin", "gerente", "vendedor")


def gerar_hash(senha: str) -> str:
    """Gera um hash no formato 'pbkdf2_sha256$<iteracoes>$<salt>$<hash>'."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(_ALGORITMO, senha.encode("utf-8"),
                                 salt.encode("utf-8"), SENHA_ITERACOES)
    return f"pbkdf2_{_ALGORITMO}${SENHA_ITERACOES}${salt}${digest.hex()}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Confere a senha contra o hash armazenado usando comparação segura."""
    try:
        algoritmo, iteracoes, salt, _ = hash_armazenado.split("$", 3)
    except (ValueError, AttributeError):
        return False
    if not algoritmo.startswith("pbkdf2_"):
        return False
    digest = hashlib.pbkdf2_hmac(algoritmo.replace("pbkdf2_", "", 1),
                                 senha.encode("utf-8"),
                                 salt.encode("utf-8"), int(iteracoes))
    return hmac.compare_digest(digest.hex(), hash_armazenado.split("$", 3)[3])


def gerar_senha_provisoria(tamanho: int = 12) -> str:
    """Cria uma senha aleatória e legível para o primeiro acesso.

    Usa `secrets` (criptograficamente seguro). Evita caracteres ambíguos
    (0/O, 1/l/I) para facilitar a digitação a partir do console na instalação.
    """
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


# --- Tokens de sessão (JWT HS256) -------------------------------------------
# Implementação mínima com stdlib, sem dependência externa. O token carrega o
# id e o nome do usuário e um vencimento; a integridade é garantida por HMAC.

def _b64url(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode("ascii")


def _b64url_decode(texto: str) -> bytes:
    padding = "=" * (-len(texto) % 4)
    return base64.urlsafe_b64decode(texto + padding)


def _assinar(conteudo: str) -> str:
    return hmac.new(JWT_SEGREDO.encode("utf-8"),
                    conteudo.encode("ascii"), hashlib.sha256).hexdigest()


def criar_token(usuario: dict) -> str:
    """Gera um JWT assinado para o usuário autenticado.

    O corpo carrega `sub` (id), `nome`, `perfil` (admin/gerente/vendedor),
    `iat` (emitido em) e `exp` (expira em).
    """
    agora = int(time.time())
    cabecalho = {"alg": "HS256", "typ": "JWT"}
    corpo = {
        "sub": usuario["usuario_id"],
        "nome": usuario["usuario"],
        "perfil": usuario.get("perfil", PERFIL_PADRAO),
        "iat": agora,
        "exp": agora + JWT_EXPIRACAO_MINUTOS * 60,
    }
    partes = (
        _b64url(json.dumps(cabecalho, separators=(",", ":")).encode("utf-8"))
        + "."
        + _b64url(json.dumps(corpo, separators=(",", ":")).encode("utf-8"))
    )
    return f"{partes}.{_assinar(partes)}"


def decodificar_token(token: str):
    """Valida assinatura e validade; devolve o corpo ou None se inválido."""
    try:
        cabecalho_b64, corpo_b64, assinatura = token.split(".")
    except (ValueError, AttributeError):
        return None

    if not hmac.compare_digest(_assinar(f"{cabecalho_b64}.{corpo_b64}"), assinatura):
        return None

    try:
        corpo = json.loads(_b64url_decode(corpo_b64))
    except (ValueError, json.JSONDecodeError):
        return None

    if not isinstance(corpo, dict) or corpo.get("exp", 0) < int(time.time()):
        return None
    return corpo


