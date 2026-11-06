from database import linha_para_dict, linhas_para_lista

_COLUNAS = ("cliente_id, cliente_nome, cliente_cpf, cliente_telefone, cliente_email, "
            "cliente_endereco, cliente_ativo, cliente_criado_em")


def listar(conn, incluir_inativos=False):
    filtro = "" if incluir_inativos else "WHERE cliente_ativo = 1"
    linhas = conn.execute(
        f"SELECT {_COLUNAS} FROM clientes {filtro} ORDER BY cliente_nome"
    ).fetchall()
    return linhas_para_lista(linhas)


def obter(conn, cliente_id):
    linha = conn.execute(
        f"SELECT {_COLUNAS} FROM clientes WHERE cliente_id = ?", (cliente_id,)
    ).fetchone()
    return linha_para_dict(linha)


def obter_por_cpf(conn, cpf):
    linha = conn.execute(
        f"SELECT {_COLUNAS} FROM clientes WHERE cliente_cpf = ?", (cpf,)
    ).fetchone()
    return linha_para_dict(linha)


def inserir(conn, dados):
    cur = conn.execute(
        "INSERT INTO clientes (cliente_nome, cliente_cpf, cliente_telefone, "
        "cliente_email, cliente_endereco) VALUES (:nome, :cpf, :telefone, :email, :endereco)",
        dados,
    )
    return cur.lastrowid


def atualizar(conn, cliente_id, dados):
    conn.execute(
        "UPDATE clientes SET cliente_nome = :nome, cliente_cpf = :cpf, "
        "cliente_telefone = :telefone, cliente_email = :email, cliente_endereco = :endereco "
        "WHERE cliente_id = :id",
        {**dados, "id": cliente_id},
    )


def definir_ativo(conn, cliente_id, ativo):
    conn.execute("UPDATE clientes SET cliente_ativo = ? WHERE cliente_id = ?",
                 (1 if ativo else 0, cliente_id))


def contar_vendas(conn, cliente_id):
    return conn.execute("SELECT COUNT(*) FROM vendas WHERE cliente_id = ?",
                        (cliente_id,)).fetchone()[0]
