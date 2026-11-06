"""Vendas: baixa de estoque, cálculo de totais e cancelamento com estorno.

Regras adotadas:
- a venda só é concluída se houver saldo no local escolhido (depósito ou loja);
- o preço unitário é o enviado pelo operador; se ausente, usa o preço de venda
  do produto (e é obrigatório que exista);
- a baixa no estoque acontece como movimentações do tipo SAIDA com `venda_id`;
- cancelar devolve o estoque via movimentação de estorno (tipo ENTRADA) e é
  bloqueado se a venda já estiver cancelada.
Tudo roda em uma única transação: qualquer erro desfaz baixa, itens e venda.
"""
from database import conexao
from exceptions import NaoEncontradoError, RegraDeNegocioError, exigir
from process import local_process, movimentacao_process
from repositories import (cliente_repository, produto_repository,
                          venda_repository as repo)

STATUS = ("CONCLUIDA", "CANCELADA")
_TOLERANCIA = 1e-9


def _validar_item(conn, item, local, nome_local):
    produto_id = item.get("produto_id")
    produto = produto_repository.obter(conn, produto_id)
    if produto is None:
        raise NaoEncontradoError(f"Produto {produto_id} não encontrado.")
    exigir(produto["produto_ativo"] == 1, f"Produto '{produto['produto_nome']}' está desativado.")

    quantidade = item.get("quantidade")
    exigir(quantidade is not None and quantidade > 0,
           f"Quantidade inválida para o produto '{produto['produto_nome']}'.")

    preco = item.get("preco_unitario")
    if preco is None:
        preco = produto["produto_preco_venda"]
        exigir(preco is not None,
               f"Produto '{produto['produto_nome']}' sem preço de venda; informe o preço unitário.")
    exigir(preco >= 0, "O preço unitário não pode ser negativo.")

    desconto = item.get("desconto_item") or 0
    exigir(desconto >= 0, "O desconto do item não pode ser negativo.")
    exigir(desconto <= quantidade * preco + _TOLERANCIA,
           f"O desconto do item '{produto['produto_nome']}' é maior que o valor do item.")

    saldo = conn.execute(
        "SELECT COALESCE(estoque_quantidade, 0) FROM estoque WHERE produto_id = ? AND estoque_local = ?",
        (produto_id, local),
    ).fetchone()
    saldo = saldo[0] if saldo else 0
    exigir(saldo + _TOLERANCIA >= quantidade,
           f"Saldo insuficiente em '{nome_local}' para '{produto['produto_nome']}': "
           f"disponível {saldo:g}, solicitado {quantidade:g}.")

    return {
        "produto_id": produto_id,
        "quantidade": quantidade,
        "preco_unitario": preco,
        "desconto_item": desconto,
        "subtotal": round(quantidade * preco - desconto, 2),
    }


def registrar(dados):
    itens = dados.get("itens") or []
    exigir(len(itens) > 0, "A venda precisa ter ao menos um item.")
    # Sem local informado, vende do depósito; senão, do local escolhido.
    local = dados.get("local") or local_process.deposito()
    desconto = dados.get("desconto") or 0
    exigir(desconto >= 0, "O desconto da venda não pode ser negativo.")

    with conexao() as conn:
        local_info = local_process.exigir_ativo(conn, local, campo="local da venda")
        cliente_id = dados.get("cliente_id")
        if cliente_id is not None:
            cliente = cliente_repository.obter(conn, cliente_id)
            if cliente is None:
                raise NaoEncontradoError("Cliente não encontrado.")
            exigir(cliente["cliente_ativo"] == 1, "Cliente inativo não pode receber novas vendas.")

        limpos = [_validar_item(conn, item, local, local_info["local_nome"]) for item in itens]
        bruto = round(sum(i["subtotal"] for i in limpos), 2)
        exigir(desconto <= bruto + _TOLERANCIA, "O desconto da venda é maior que o valor dos itens.")
        total = round(bruto - desconto, 2)

        venda_id = repo.inserir(conn, {
            "numero": repo.proximo_numero(conn),
            "cliente_id": cliente_id,
            "total": total,
            "desconto": desconto,
            "local": local,
            "observacao": dados.get("observacao"),
            "registrado_por": dados.get("registrado_por"),
        })
        for item in limpos:
            repo.inserir_item(conn, venda_id, item)
            movimentacao_process.aplicar(conn, {
                "produto_id": item["produto_id"],
                "local": local,
                "tipo": "SAIDA",
                "quantidade": item["quantidade"],
                "venda_id": venda_id,
                "observacao": f"Venda {repo.obter(conn, venda_id)['venda_numero']}",
                "registrado_por": dados.get("registrado_por"),
            })
    return obter(venda_id)


def listar(cliente_id=None, status=None, data_inicio=None, data_fim=None, limite=200):
    exigir(status is None or status in STATUS, f"Status inválido. Use: {', '.join(STATUS)}.")
    exigir(1 <= limite <= 1000, "O limite deve estar entre 1 e 1000.")
    with conexao() as conn:
        return repo.listar(conn, cliente_id, status, data_inicio, data_fim, limite)


def obter(venda_id):
    with conexao() as conn:
        venda = repo.obter(conn, venda_id)
        if venda is None:
            raise NaoEncontradoError("Venda não encontrada.")
        venda["itens"] = repo.listar_itens(conn, venda_id)
    return venda


def cancelar(venda_id, cancelado_por=None):
    """Cancela a venda e devolve as quantidades ao estoque do mesmo local."""
    with conexao() as conn:
        venda = repo.obter(conn, venda_id)
        if venda is None:
            raise NaoEncontradoError("Venda não encontrada.")
        exigir(venda["venda_status"] != "CANCELADA", "Esta venda já está cancelada.")

        for item in repo.listar_itens(conn, venda_id):
            movimentacao_process.aplicar(conn, {
                "produto_id": item["produto_id"],
                "local": venda["venda_local"],
                "tipo": "ENTRADA",
                "quantidade": item["quantidade"],
                "venda_id": venda_id,
                "observacao": f"Estorno da venda {venda['venda_numero']}",
                "registrado_por": cancelado_por,
            })
        repo.cancelar(conn, venda_id, cancelado_por)
    return obter(venda_id)


def resumo(data_inicio=None, data_fim=None):
    with conexao() as conn:
        return {"por_dia": repo.resumo_por_dia(conn, data_inicio, data_fim),
                "por_produto": repo.resumo_por_produto(conn, data_inicio, data_fim)}
