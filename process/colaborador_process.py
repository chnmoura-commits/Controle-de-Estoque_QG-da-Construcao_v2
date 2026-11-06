"""Gerenciamento de colaboradores (usuários do sistema) — uso pelo administrador.

Diferente de `usuarios_admin.py` (linha de comando), estas funções são chamadas
pela API e aparecem na tela de Colaboradores do sistema.

Regras:
- o login (`usuario`) é único e, ao ser criado, sempre nasce com senha
  provisória que precisa ser trocada no primeiro acesso;
- o CPF é único entre colaboradores;
- e-mail, telefone e CPF são validados (e o CPF/e-mail são normalizados);
- só o administrador deve chamar estes métodos (a permissão é checada no
  controller, via `exigir_perfil("admin")`).
"""
import sqlite3

from database import conexao
from exceptions import NaoEncontradoError, RegraDeNegocioError, exigir
from repositories import usuario_repository as repo
from security import PERFIS, gerar_hash, gerar_senha_provisoria
from validacao import validar_cpf, validar_email, validar_telefone


def listar(busca=None):
    with conexao() as conn:
        colaboradores = repo.listar(conn)
    if busca:
        termo = busca.strip().lower()
        colaboradores = [c for c in colaboradores
                         if termo in c["usuario_nome"].lower()
                         or termo in (c["usuario_nome_completo"] or "").lower()
                         or termo in (c["usuario_cpf"] or "")]
    return colaboradores


def obter(usuario_id):
    with conexao() as conn:
        colaborador = repo.obter_completo(conn, usuario_id)
    if colaborador is None:
        raise NaoEncontradoError("Colaborador não encontrado.")
    return colaborador


def _validar_campos(dados):
    """Valida e normaliza os dados cadastrais comuns a criar e editar."""
    nome_completo = (dados.get("nome_completo") or "").strip()
    exigir(nome_completo, "O nome completo é obrigatório.")

    perfil = (dados.get("perfil") or "").strip().lower()
    exigir(perfil in PERFIS, f"Perfil inválido. Use um destes: {', '.join(PERFIS)}.")

    return {
        "nome_completo": nome_completo,
        "perfil": perfil,
        "cpf": validar_cpf(dados.get("cpf")),
        "telefone": validar_telefone(dados.get("telefone")),
        "email": validar_email(dados.get("email")),
    }


def _garantir_cpf_livre(conn, cpf, ignorar_id=None):
    existente = repo.obter_por_cpf(conn, cpf)
    if existente is not None and existente["usuario_id"] != ignorar_id:
        raise RegraDeNegocioError("Já existe um colaborador com esse CPF.")


def criar(dados):
    """Cria o colaborador e devolve (colaborador, senha_provisoria).

    A senha provisória é mostrada apenas uma vez, na resposta da criação.
    """
    campos = _validar_campos(dados)
    usuario = (dados.get("usuario") or "").strip()
    exigir(usuario, "O nome de usuário (login) é obrigatório.")
    exigir(" " not in usuario, "O nome de usuário não pode conter espaços.")

    senha_provisoria = gerar_senha_provisoria()
    try:
        with conexao() as conn:
            if repo.obter_por_usuario(conn, usuario) is not None:
                raise RegraDeNegocioError("Já existe um colaborador com esse nome de usuário.")
            _garantir_cpf_livre(conn, campos["cpf"])
            novo_id = repo.inserir(conn, usuario, gerar_hash(senha_provisoria),
                                   senha_provisoria=1, dados=campos)
    except sqlite3.IntegrityError:
        raise RegraDeNegocioError("Já existe um colaborador com esse usuário ou CPF.")

    return obter(novo_id), senha_provisoria


def atualizar(usuario_id, dados):
    """Atualiza dados cadastrais e perfil. Não altera senha nem o login."""
    original = obter(usuario_id)
    campos = _validar_campos(dados)
    try:
        with conexao() as conn:
            _garantir_cpf_livre(conn, campos["cpf"], ignorar_id=usuario_id)
            repo.atualizar_dados(conn, usuario_id, {**campos, "usuario": original["usuario_nome"]})
    except sqlite3.IntegrityError:
        raise RegraDeNegocioError("Já existe um colaborador com esse CPF.")
    return obter(usuario_id)


def definir_ativo(usuario_id, ativo, administrador_id=None):
    """Ativa ou desativa um colaborador.

    Impede o administrador de se desativar (evita perder o próprio acesso).
    """
    obter(usuario_id)
    if administrador_id is not None and usuario_id == administrador_id and not ativo:
        raise RegraDeNegocioError("Você não pode desativar o seu próprio acesso.")
    with conexao() as conn:
        repo.definir_ativo(conn, usuario_id, ativo)
    return obter(usuario_id)


def resetar_senha(usuario_id):
    """Gera uma nova senha provisória (troca obrigatória no próximo acesso)."""
    obter(usuario_id)
    senha_provisoria = gerar_senha_provisoria()
    with conexao() as conn:
        repo.definir_senha_provisoria(conn, usuario_id, gerar_hash(senha_provisoria))
    return senha_provisoria


def remover(usuario_id, administrador_id=None):
    """Exclui um colaborador (preferir desativar quando houver histórico)."""
    obter(usuario_id)
    if administrador_id is not None and usuario_id == administrador_id:
        raise RegraDeNegocioError("Você não pode remover o seu próprio acesso.")
    with conexao() as conn:
        admin_restantes = conn.execute(
            "SELECT COUNT(*) FROM usuarios WHERE usuario_perfil = 'admin' AND usuario_ativo = 1 "
            "AND usuario_id <> ?", (usuario_id,)).fetchone()[0]
        exigir(admin_restantes > 0,
               "Não é possível remover o último administrador ativo do sistema.")
        repo.remover(conn, usuario_id)
    return {"mensagem": "Colaborador removido."}
