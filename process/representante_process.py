"""Representantes comerciais de um fornecedor (vários por fornecedor).

Não fazem login no sistema. O telefone é opcional, mas validado quando informado;
o e-mail também é validado quando informado.
"""
from database import conexao
from exceptions import NaoEncontradoError, exigir
from repositories import fornecedor_repository
from repositories import representante_repository as repo
from validacao import validar_email, validar_telefone


def _garantir_fornecedor(conn, fornecedor_id):
    if fornecedor_repository.obter(conn, fornecedor_id) is None:
        raise NaoEncontradoError("Fornecedor não encontrado.")


def _validar(dados):
    nome = (dados.get("nome") or "").strip()
    exigir(nome, "O nome do representante é obrigatório.")
    return {
        "nome": nome,
        "contato": validar_telefone(dados.get("contato"), campo="contato", obrigatorio=False),
        "email": validar_email(dados.get("email"), obrigatorio=False),
    }


def listar(fornecedor_id, incluir_inativos=False):
    with conexao() as conn:
        _garantir_fornecedor(conn, fornecedor_id)
        return repo.listar(conn, fornecedor_id, incluir_inativos)


def obter(representante_id):
    with conexao() as conn:
        representante = repo.obter(conn, representante_id)
    if representante is None:
        raise NaoEncontradoError("Representante não encontrado.")
    return representante


def criar(fornecedor_id, dados):
    limpos = _validar(dados)
    with conexao() as conn:
        _garantir_fornecedor(conn, fornecedor_id)
        novo_id = repo.inserir(conn, fornecedor_id, limpos)
    return obter(novo_id)


def atualizar(representante_id, dados):
    obter(representante_id)
    limpos = _validar(dados)
    with conexao() as conn:
        repo.atualizar(conn, representante_id, limpos)
    return obter(representante_id)


def definir_ativo(representante_id, ativo):
    obter(representante_id)
    with conexao() as conn:
        repo.definir_ativo(conn, representante_id, ativo)
    return obter(representante_id)
