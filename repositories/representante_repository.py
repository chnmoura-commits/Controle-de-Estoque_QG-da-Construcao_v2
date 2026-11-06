from database import linha_para_dict, linhas_para_lista

_COLUNAS = ("representante_id, fornecedor_id, representante_nome, representante_contato, "
            "representante_email, representante_ativo, representante_criado_em")


def listar(conn, fornecedor_id, incluir_inativos=False):
    filtro = "" if incluir_inativos else "AND representante_ativo = 1"
    linhas = conn.execute(
        f"SELECT {_COLUNAS} FROM fornecedor_representantes "
        f"WHERE fornecedor_id = ? {filtro} ORDER BY representante_nome",
        (fornecedor_id,),
    ).fetchall()
    return linhas_para_lista(linhas)


def obter(conn, representante_id):
    linha = conn.execute(
        f"SELECT {_COLUNAS} FROM fornecedor_representantes WHERE representante_id = ?",
        (representante_id,),
    ).fetchone()
    return linha_para_dict(linha)


def inserir(conn, fornecedor_id, dados):
    cur = conn.execute(
        "INSERT INTO fornecedor_representantes (fornecedor_id, representante_nome, "
        "representante_contato, representante_email) "
        "VALUES (:fornecedor_id, :nome, :contato, :email)",
        {**dados, "fornecedor_id": fornecedor_id},
    )
    return cur.lastrowid


def atualizar(conn, representante_id, dados):
    conn.execute(
        "UPDATE fornecedor_representantes SET representante_nome = :nome, "
        "representante_contato = :contato, representante_email = :email "
        "WHERE representante_id = :id",
        {**dados, "id": representante_id},
    )


def definir_ativo(conn, representante_id, ativo):
    conn.execute("UPDATE fornecedor_representantes SET representante_ativo = ? "
                 "WHERE representante_id = ?", (1 if ativo else 0, representante_id))
