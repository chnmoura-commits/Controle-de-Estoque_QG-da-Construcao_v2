from database import linha_para_dict, linhas_para_lista


def listar(conn):
    linhas = conn.execute(
                "SELECT categoria_id, categoria_nome, categoria_descricao "
        "FROM categorias ORDER BY categoria_nome"
    ).fetchall()
    return linhas_para_lista(linhas)


def obter(conn, categoria_id):
    linha = conn.execute(
        "SELECT categoria_id, categoria_nome, categoria_descricao "
        "FROM categorias WHERE categoria_id = ?",
        (categoria_id,),
    ).fetchone()
    return linha_para_dict(linha)


def inserir(conn, dados):
    cur = conn.execute(
        "INSERT INTO categorias (categoria_nome, categoria_descricao) VALUES (:nome, :descricao)",
        dados,
    )
    return cur.lastrowid


def atualizar(conn, categoria_id, dados):
    conn.execute(
        "UPDATE categorias SET categoria_nome = :nome, categoria_descricao = :descricao "
        "WHERE categoria_id = :id",
        {**dados, "id": categoria_id},
    )

