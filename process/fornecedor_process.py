import sqlite3

from database import conexao
from exceptions import NaoEncontradoError, RegraDeNegocioError, exigir
from repositories import fornecedor_repository as repo
from repositories import representante_repository as rep_repo
from validacao import validar_cnpj, validar_email, validar_telefone


def _validar(dados):
    nome = (dados.get("nome") or "").strip()
    exigir(nome, "O nome do fornecedor é obrigatório.")
    return {
        "nome": nome,
        "cnpj": validar_cnpj(dados.get("cnpj"), obrigatorio=False),
        "telefone": validar_telefone(dados.get("telefone"), obrigatorio=False),
        "email": validar_email(dados.get("email"), obrigatorio=False),
    }


def _garantir_cnpj_livre(conn, cnpj, ignorar_id=None):
    if not cnpj:
        return
    linha = conn.execute(
        "SELECT fornecedor_id FROM fornecedores WHERE fornecedor_cnpj = ?", (cnpj,)
    ).fetchone()
    if linha is not None and linha[0] != ignorar_id:
        raise RegraDeNegocioError("Já existe um fornecedor com esse CNPJ.")


def listar(busca=None):
    with conexao() as conn:
        return repo.listar(conn, busca)


def obter(fornecedor_id):
    """Devolve o fornecedor, já com a lista de representantes ativos."""
    with conexao() as conn:
        fornecedor = repo.obter(conn, fornecedor_id)
        if fornecedor is None:
            raise NaoEncontradoError("Fornecedor não encontrado.")
        fornecedor["representantes"] = rep_repo.listar(conn, fornecedor_id)
    return fornecedor


def criar(dados):
    limpos = _validar(dados)
    with conexao() as conn:
        _garantir_cnpj_livre(conn, limpos["cnpj"])
        try:
            novo_id = repo.inserir(conn, limpos)
        except sqlite3.IntegrityError:
            raise RegraDeNegocioError("Já existe um fornecedor com esse CNPJ.")
    return obter(novo_id)


def atualizar(fornecedor_id, dados):
    obter(fornecedor_id)
    limpos = _validar(dados)
    with conexao() as conn:
        _garantir_cnpj_livre(conn, limpos["cnpj"], ignorar_id=fornecedor_id)
        try:
            repo.atualizar(conn, fornecedor_id, limpos)
        except sqlite3.IntegrityError:
            raise RegraDeNegocioError("Já existe um fornecedor com esse CNPJ.")
    return obter(fornecedor_id)

