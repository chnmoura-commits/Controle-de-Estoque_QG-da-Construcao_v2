from database import linha_para_dict, linhas_para_lista

_COLUNAS = (
    "v.venda_id, v.venda_numero, v.cliente_id, c.cliente_nome, v.venda_status, "
    "v.venda_total, v.venda_desconto, v.venda_local, v.venda_observacao, "
    "v.registrado_por, v.criado_em, v.cancelado_em, v.cancelado_por"
)


def proximo_numero(conn):
    """Gera o número sequencial da venda (ex.: VND-000123).

    Usa o maior número já emitido (e não a contagem): assim, mesmo que alguma
    venda seja removida direto do banco, o número não se repete.
    """
    maior = conn.execute(
        "SELECT COALESCE(MAX(CAST(SUBSTR(venda_numero, 5) AS INTEGER)), 0) FROM vendas"
    ).fetchone()[0]
    return f"VND-{maior + 1:06d}"


def inserir(conn, dados):
    cur = conn.execute(
        """INSERT INTO vendas
           (venda_numero, cliente_id, venda_total, venda_desconto, venda_local,
            venda_observacao, registrado_por)
           VALUES (:numero, :cliente_id, :total, :desconto, :local, :observacao, :registrado_por)""",
        dados,
    )
    return cur.lastrowid


def inserir_item(conn, venda_id, dados):
    conn.execute(
        """INSERT INTO itens_da_venda
           (venda_id, produto_id, quantidade, preco_unitario, desconto_item, subtotal)
           VALUES (:venda_id, :produto_id, :quantidade, :preco_unitario,
                   :desconto_item, :subtotal)""",
        {**dados, "venda_id": venda_id},
    )


def listar(conn, cliente_id=None, status=None, data_inicio=None, data_fim=None, limite=200):
    sql = f"""
        SELECT {_COLUNAS}
        FROM vendas v
        LEFT JOIN clientes c ON c.cliente_id = v.cliente_id
        WHERE 1 = 1"""
    params = []
    if cliente_id:
        sql += " AND v.cliente_id = ?"
        params.append(cliente_id)
    if status:
        sql += " AND v.venda_status = ?"
        params.append(status)
    if data_inicio:
        sql += " AND date(v.criado_em) >= date(?)"
        params.append(data_inicio)
    if data_fim:
        sql += " AND date(v.criado_em) <= date(?)"
        params.append(data_fim)
    sql += " ORDER BY v.criado_em DESC, v.venda_id DESC LIMIT ?"
    params.append(limite)
    return linhas_para_lista(conn.execute(sql, params).fetchall())


def obter(conn, venda_id):
    linha = conn.execute(
        f"""SELECT {_COLUNAS}
            FROM vendas v LEFT JOIN clientes c ON c.cliente_id = v.cliente_id
            WHERE v.venda_id = ?""",
        (venda_id,),
    ).fetchone()
    return linha_para_dict(linha)


def listar_itens(conn, venda_id):
    sql = """
        SELECT i.item_venda_id, i.produto_id, p.produto_sku, p.produto_nome,
               i.quantidade, i.preco_unitario, i.desconto_item, i.subtotal
        FROM itens_da_venda i JOIN produtos p ON p.produto_id = i.produto_id
        WHERE i.venda_id = ?
        ORDER BY i.item_venda_id"""
    return linhas_para_lista(conn.execute(sql, (venda_id,)).fetchall())


def cancelar(conn, venda_id, cancelado_por):
    conn.execute(
        "UPDATE vendas SET venda_status = 'CANCELADA', cancelado_em = CURRENT_TIMESTAMP, "
        "cancelado_por = ? WHERE venda_id = ?",
        (cancelado_por, venda_id),
    )


def resumo_por_dia(conn, data_inicio=None, data_fim=None):
    sql = """
        SELECT date(v.criado_em) AS dia,
               COUNT(*) AS total_vendas,
               COALESCE(SUM(v.venda_total), 0) AS faturamento
        FROM vendas v
        WHERE v.venda_status = 'CONCLUIDA'"""
    params = []
    if data_inicio:
        sql += " AND date(v.criado_em) >= date(?)"
        params.append(data_inicio)
    if data_fim:
        sql += " AND date(v.criado_em) <= date(?)"
        params.append(data_fim)
    sql += " GROUP BY dia ORDER BY dia"
    return linhas_para_lista(conn.execute(sql, params).fetchall())


def resumo_por_produto(conn, data_inicio=None, data_fim=None):
    sql = """
        SELECT i.produto_id, p.produto_sku, p.produto_nome,
               SUM(i.quantidade) AS quantidade_vendida,
               SUM(i.subtotal) AS valor_vendido
        FROM itens_da_venda i
        JOIN vendas v  ON v.venda_id = i.venda_id
        JOIN produtos p ON p.produto_id = i.produto_id
        WHERE v.venda_status = 'CONCLUIDA'"""
    params = []
    if data_inicio:
        sql += " AND date(v.criado_em) >= date(?)"
        params.append(data_inicio)
    if data_fim:
        sql += " AND date(v.criado_em) <= date(?)"
        params.append(data_fim)
    sql += " GROUP BY i.produto_id ORDER BY quantidade_vendida DESC"
    return linhas_para_lista(conn.execute(sql, params).fetchall())

