from database import linha_para_dict, linhas_para_lista

_COLUNAS = ("l.local_codigo, l.local_nome, l.local_tipo, l.local_cnpj, l.local_endereco, "
            "l.local_telefone, l.local_email, l.local_ativo, l.local_criado_em, "
            "COALESCE((SELECT SUM(e.estoque_quantidade) FROM estoque e "
            "          WHERE e.estoque_local = l.local_codigo), 0) AS saldo_total")

# Flag "pode_excluir": só quando não há saldo nem histórico ligado ao local.
_COLUNA_PODE_EXCLUIR = """
CASE WHEN COALESCE((SELECT SUM(e.estoque_quantidade) FROM estoque e
                    WHERE e.estoque_local = l.local_codigo), 0) <> 0
       OR EXISTS (SELECT 1 FROM movimentacoes m WHERE m.estoque_local = l.local_codigo)
       OR EXISTS (SELECT 1 FROM vendas v WHERE v.venda_local = l.local_codigo)
     THEN 0 ELSE 1 END AS pode_excluir
"""


def listar(conn, incluir_inativos=False):
    filtro = "" if incluir_inativos else "WHERE l.local_ativo = 1"
    sql = (f"SELECT {_COLUNAS}, {_COLUNA_PODE_EXCLUIR} FROM locais l {filtro} "
           "ORDER BY CASE WHEN l.local_tipo = 'deposito' THEN 0 ELSE 1 END, l.local_nome")
    return linhas_para_lista(conn.execute(sql).fetchall())


def obter(conn, local_codigo):
    sql = (f"SELECT {_COLUNAS}, {_COLUNA_PODE_EXCLUIR} FROM locais l "
           "WHERE l.local_codigo = ?")
    return linha_para_dict(conn.execute(sql, (local_codigo,)).fetchone())


def obter_por_tipo(conn, local_tipo):
    linha = conn.execute("SELECT local_codigo FROM locais WHERE local_tipo = ? LIMIT 1",
                         (local_tipo,)).fetchone()
    return linha[0] if linha else None


def obter_deposito(conn):
    return obter_por_tipo(conn, "deposito")


def listar_ativos(conn):
    return listar(conn, incluir_inativos=False)


def existe_ativo(conn, local_codigo):
    """Usado pelas demais entidades: o local existe e aceita receber estoque?"""
    linea = conn.execute("SELECT 1 FROM locais WHERE local_codigo = ? AND local_ativo = 1",
                         (local_codigo,)).fetchone()
    return linea is not None


def codigo_ocupado(conn, local_codigo, ignorar_codigo=None):
    linha = conn.execute("SELECT local_codigo FROM locais WHERE local_codigo = ?",
                         (local_codigo,)).fetchone()
    return linha is not None and linha[0] != ignorar_codigo


def inserir(conn, dados):
    conn.execute(
        """INSERT INTO locais
           (local_codigo, local_nome, local_tipo, local_cnpj, local_endereco,
            local_telefone, local_email)
           VALUES (:codigo, :nome, :tipo, :cnpj, :endereco, :telefone, :email)""",
        dados,
    )


def atualizar(conn, local_codigo, dados):
    conn.execute(
        """UPDATE locais SET
               local_nome = :nome, local_tipo = :tipo, local_cnpj = :cnpj,
               local_endereco = :endereco, local_telefone = :telefone, local_email = :email
           WHERE local_codigo = :codigo_original""",
        {**dados, "codigo_original": local_codigo},
    )


def trocar_codigo(conn, codigo_antigo, codigo_novo):
    """Renomeia o código e atualiza todas as referências (estoque/histórico/vendas)."""
    conn.execute("UPDATE locais SET local_codigo = ? WHERE local_codigo = ?",
                 (codigo_novo, codigo_antigo))
    for tabela, coluna in (("estoque", "estoque_local"),
                           ("movimentacoes", "estoque_local"),
                           ("vendas", "venda_local")):
        conn.execute(f"UPDATE {tabela} SET {coluna} = ? WHERE {coluna} = ?",
                     (codigo_novo, codigo_antigo))


def definir_ativo(conn, local_codigo, ativo):
    conn.execute("UPDATE locais SET local_ativo = ? WHERE local_codigo = ?",
                 (1 if ativo else 0, local_codigo))


def excluir(conn, local_codigo):
    conn.execute("DELETE FROM locais WHERE local_codigo = ?", (local_codigo,))


def contar_referencias(conn, local_codigo):
    mov = conn.execute("SELECT COUNT(*) FROM movimentacoes WHERE estoque_local = ?",
                       (local_codigo,)).fetchone()[0]
    vendas = conn.execute("SELECT COUNT(*) FROM vendas WHERE venda_local = ?",
                          (local_codigo,)).fetchone()[0]
    saldo = conn.execute("SELECT COALESCE(SUM(estoque_quantidade), 0) FROM estoque "
                         "WHERE estoque_local = ?", (local_codigo,)).fetchone()[0]
    return {"movimentacoes": mov, "vendas": vendas, "saldo": saldo}
