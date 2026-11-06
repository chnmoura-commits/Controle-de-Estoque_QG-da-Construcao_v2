"""Custo médio ponderado.

Decisão do projeto: `produto_preco_custo` guarda o **custo médio corrente**.
O custo é recalculado a cada entrada com custo (compra, entrada manual ou saldo
inicial) pela fórmula do custo médio ponderado:

    novo_custo = (qtd_atual * custo_atual + qtd_entrada * custo_entrada)
                 / (qtd_atual + qtd_entrada)

O estoque legado (sem custo conhecido) tem custo 0 até a primeira entrada com
valor. Regras de negócio de movimentação ficam em `movimentacao_process`.
"""
from repositories import produto_repository

_TOLERANCIA = 1e-9


def custo_medio_atual(qtd_atual, custo_atual, qtd_entrada, custo_entrada):
    """Calcula o novo custo médio ponderado (função pura, fácil de testar)."""
    qtd_atual = qtd_atual or 0
    custo_atual = custo_atual or 0
    total = qtd_atual + qtd_entrada
    if total <= _TOLERANCIA:
        return custo_entrada or 0
    valor = qtd_atual * custo_atual + qtd_entrada * custo_entrada
    return round(valor / total, 4)


def recalcular_na_entrada(conn, produto_id, quantidade, custo_entrada):
    """Atualiza `produto_preco_custo` após uma entrada com custo. Devolve o novo custo.

    Considera o saldo total do produto (depósito + loja) antes da entrada.
    """
    if custo_entrada is None:
        return None
    produto = produto_repository.obter(conn, produto_id)
    qtd_atual = conn.execute(
        "SELECT COALESCE(SUM(estoque_quantidade), 0) FROM estoque WHERE produto_id = ?",
        (produto_id,),
    ).fetchone()[0]
    novo_custo = custo_medio_atual(qtd_atual, produto["produto_preco_custo"],
                                   quantidade, custo_entrada)
    conn.execute("UPDATE produtos SET produto_preco_custo = ? WHERE produto_id = ?",
                 (novo_custo, produto_id))
    return novo_custo
