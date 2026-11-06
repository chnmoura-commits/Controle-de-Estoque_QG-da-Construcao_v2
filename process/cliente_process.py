"""Clientes da loja. Não fazem login no sistema: só são cadastrados na venda.

Sem exclusão física (evita quebrar o histórico de vendas): usar desativar.
CPF, telefone e e-mail são validados; CPF e e-mail são normalizados.
"""
import sqlite3

from database import conexao
from exceptions import NaoEncontradoError, RegraDeNegocioError, exigir
from repositories import cliente_repository as repo
from validacao import validar_cpf, validar_email, validar_telefone


def listar(busca=None, incluir_inativos=False):
    with conexao() as conn:
        clientes = repo.listar(conn, incluir_inativos)
    if busca:
        termo = busca.strip().lower()
        clientes = [c for c in clientes
                    if termo in c["cliente_nome"].lower()
                    or termo in (c["cliente_cpf"] or "")]
    return clientes


def obter(cliente_id):
    with conexao() as conn:
        cliente = repo.obter(conn, cliente_id)
    if cliente is None:
        raise NaoEncontradoError("Cliente não encontrado.")
    return cliente


def _validar(dados):
    nome = (dados.get("nome") or "").strip()
    exigir(nome, "O nome do cliente é obrigatório.")
    return {
        "nome": nome,
        "cpf": validar_cpf(dados.get("cpf"), obrigatorio=False),
        "telefone": validar_telefone(dados.get("telefone"), obrigatorio=False),
        "email": validar_email(dados.get("email"), obrigatorio=False),
        "endereco": (dados.get("endereco") or "").strip() or None,
    }


def _garantir_cpf_livre(conn, cpf, ignorar_id=None):
    if not cpf:
        return
    existente = repo.obter_por_cpf(conn, cpf)
    if existente is not None and existente["cliente_id"] != ignorar_id:
        raise RegraDeNegocioError("Já existe um cliente com esse CPF.")


def criar(dados):
    limpos = _validar(dados)
    with conexao() as conn:
        _garantir_cpf_livre(conn, limpos["cpf"])
        novo_id = repo.inserir(conn, limpos)
    return obter(novo_id)


def atualizar(cliente_id, dados):
    obter(cliente_id)
    limpos = _validar(dados)
    with conexao() as conn:
        _garantir_cpf_livre(conn, limpos["cpf"], ignorar_id=cliente_id)
        repo.atualizar(conn, cliente_id, limpos)
    return obter(cliente_id)


def definir_ativo(cliente_id, ativo):
    obter(cliente_id)
    with conexao() as conn:
        repo.definir_ativo(conn, cliente_id, ativo)
    return obter(cliente_id)
