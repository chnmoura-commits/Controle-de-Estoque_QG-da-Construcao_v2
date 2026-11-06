"""Locais (depósito e lojas): onde o estoque fica e para onde ele vai.

Regras:
- o estoque é por local (coluna `estoque_local`, que guarda o código do local);
  os demais processos consultam esta camada para validar o local escolhido;
- existe sempre UM local do tipo 'deposito' (destino das compras e origem das
  transferências). Ele pode ser renomeado, mas não rebaixado para 'loja';
- o código (ex.: `loja-centro`) é a chave usada no histórico; renomeá-lo
  atualiza estoque, movimentações e vendas na mesma transação;
- um local com saldo/histórico não é excluído: desativa-se (não recebe mais
  estoque nem aparece nas listas).
"""
import re
import sqlite3
import unicodedata

from database import conexao
from exceptions import NaoEncontradoError, RegraDeNegocioError, exigir
from repositories import local_repository as repo
from validacao import validar_cnpj, validar_email, validar_telefone

TIPOS = ("deposito", "loja")


def _slug(texto):
    """Gera o código a partir do nome: 'Loja Centro' -> 'loja-centro'."""
    sem_acento = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = sem_acento.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento).strip("-")


def _validar(dados, codigo_atual=None):
    nome = (dados.get("nome") or "").strip()
    exigir(nome, "O nome do local é obrigatório.")

    tipo = (dados.get("tipo") or "loja").strip().lower()
    exigir(tipo in TIPOS, f"Tipo inválido. Use: {', '.join(TIPOS)}.")

    codigo = _slug(dados.get("codigo") or codigo_atual or nome)
    exigir(len(codigo) >= 2, "Não foi possível gerar um código para o local; informe o código.")

    return {
        "codigo": codigo,
        "nome": nome,
        "tipo": tipo,
        "cnpj": validar_cnpj(dados.get("cnpj"), campo="CNPJ do local", obrigatorio=False),
        "telefone": validar_telefone(dados.get("telefone"), campo="Telefone do local",
                                     obrigatorio=False),
        "email": validar_email(dados.get("email"), campo="e-mail do local", obrigatorio=False),
        "endereco": (dados.get("endereco") or "").strip() or None,
    }


def _exigir_um_unico_deposito(conn, tipo, codigo_do_deposito=None, codigo=None):
    """Garante que continuará havendo exatamente um depósito."""
    if tipo != "deposito":
        return
    outro = repo.obter_deposito(conn)
    exigir(outro is None or outro == codigo,
           f"Já existe um depósito cadastrado ('{outro}'). Só pode haver um local do tipo depósito.")


def listar(incluir_inativos=False):
    with conexao() as conn:
        return repo.listar(conn, incluir_inativos)


def obter(local_codigo):
    with conexao() as conn:
        local = repo.obter(conn, local_codigo)
        if local is None:
            raise NaoEncontradoError("Local não encontrado.")
    return local


def deposito():
    """Código do depósito (destino padrão de compras)."""
    with conexao() as conn:
        codigo = repo.obter_deposito(conn)
    exigir(codigo, "Nenhum depósito cadastrado. Cadastre um local do tipo 'deposito'.")
    return codigo


def exigir_ativo(conn, local_codigo, campo="local"):
    """Validação reutilizada pelas movimentações, compras e vendas."""
    exigir(local_codigo not in (None, ""), f"O {campo} é obrigatório.")
    local = repo.obter(conn, local_codigo)
    if local is None:
        raise NaoEncontradoError(f"O {campo} '{local_codigo}' não existe.")
    exigir(local["local_ativo"] == 1, f"O {campo} '{local['local_nome']}' está desativado.")
    return local


def criar(dados):
    limpos = _validar(dados)
    with conexao() as conn:
        exigir(not repo.codigo_ocupado(conn, limpos["codigo"]),
               f"Já existe um local com o código '{limpos['codigo']}'. Informe outro código.")
        _exigir_um_unico_deposito(conn, limpos["tipo"], codigo=limpos["codigo"])
        repo.inserir(conn, limpos)
    return obter(limpos["codigo"])


def atualizar(local_codigo, dados):
    atual = obter(local_codigo)
    limpos = _validar(dados, codigo_atual=local_codigo)
    with conexao() as conn:
        _exigir_um_unico_deposito(conn, limpos["tipo"], codigo=local_codigo)
        if atual["local_tipo"] == "deposito" and limpos["tipo"] != "deposito":
            raise RegraDeNegocioError(
                "O depósito não pode ser transformado em loja. Cadastre uma loja separada.")
        if atual["local_ativo"] == 1 and dados.get("ativo") is False:
            _exigir_pode_desativar(conn, local_codigo, atual)
        novo_codigo = limpos["codigo"]
        if novo_codigo != local_codigo:
            exigir(not repo.codigo_ocupado(conn, novo_codigo, ignorar_codigo=local_codigo),
                   f"Já existe um local com o código '{novo_codigo}'. Informe outro código.")
            try:
                repo.trocar_codigo(conn, local_codigo, novo_codigo)
            except sqlite3.IntegrityError:
                raise RegraDeNegocioError(
                    f"Não foi possível trocar o código para '{novo_codigo}': "
                    "já existem registros de estoque com esse código.")
        repo.atualizar(conn, novo_codigo, limpos)
    return obter(limpos["codigo"])


def _exigir_pode_desativar(conn, local_codigo, local):
    refs = repo.contar_referencias(conn, local_codigo)
    exigir(abs(refs["saldo"]) < 1e-9,
           f"Não é possível desativar '{local['local_nome']}': ainda há "
           f"{refs['saldo']:g} unidade(s) em estoque. Transfira o saldo para outro local.")
    if local["local_tipo"] == "deposito":
        raise RegraDeNegocioError("O depósito não pode ser desativado.")


def definir_ativo(local_codigo, ativo):
    local = obter(local_codigo)
    with conexao() as conn:
        if not ativo:
            if local["local_tipo"] == "deposito":
                raise RegraDeNegocioError("O depósito não pode ser desativado.")
            _exigir_pode_desativar(conn, local_codigo, local)
        repo.definir_ativo(conn, local_codigo, ativo)
    return obter(local_codigo)


def excluir(local_codigo):
    """Só remove locais sem nenhum saldo/histórico; senão orienta desativar."""
    local = obter(local_codigo)
    with conexao() as conn:
        if local["local_tipo"] == "deposito":
            raise RegraDeNegocioError("O depósito não pode ser excluído.")
        refs = repo.contar_referencias(conn, local_codigo)
        exigir(refs["saldo"] == 0 and refs["movimentacoes"] == 0 and refs["vendas"] == 0,
               f"Não é possível excluir '{local['local_nome']}': ele já tem "
               f"{refs['movimentacoes']} movimentação(ões) e {refs['vendas']} venda(s). "
               "Desative-o em vez de excluir, para preservar o histórico.")
        repo.excluir(conn, local_codigo)
    return {"local_codigo": local_codigo, "excluido": True}
