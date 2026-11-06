from database import linha_para_dict, linhas_para_lista

# Colunas expostas nas consultas de usuários/colaboradores (nunca o hash da senha).
_COLUNAS_LISTAGEM = (
    "usuario_id, usuario_nome, usuario_perfil, usuario_nome_completo, usuario_cpf, "
    "usuario_telefone, usuario_email, usuario_ativo, usuario_senha_provisoria, "
    "usuario_criado_em"
)


def obter_por_usuario(conn, usuario):
    """Busca pelo nome de usuário (login). Inclui o hash para a autenticação."""
    linha = conn.execute(
        "SELECT usuario_id, usuario_nome, usuario_senha_hash, usuario_ativo, "
        "usuario_senha_provisoria, usuario_perfil FROM usuarios WHERE usuario_nome = ?",
        (usuario,),
    ).fetchone()
    return linha_para_dict(linha)


def obter_por_id(conn, usuario_id):
    """Busca pelo id. Inclui o hash para a troca de senha."""
    linha = conn.execute(
        "SELECT usuario_id, usuario_nome, usuario_senha_hash, usuario_ativo, "
        "usuario_senha_provisoria, usuario_perfil FROM usuarios WHERE usuario_id = ?",
        (usuario_id,),
    ).fetchone()
    return linha_para_dict(linha)


def obter_completo(conn, usuario_id):
    """Colaborador completo (sem o hash) para a tela de cadastro."""
    linha = conn.execute(
        f"SELECT {_COLUNAS_LISTAGEM} FROM usuarios WHERE usuario_id = ?", (usuario_id,)
    ).fetchone()
    return linha_para_dict(linha)


def obter_por_cpf(conn, cpf):
    linha = conn.execute(
        f"SELECT {_COLUNAS_LISTAGEM} FROM usuarios WHERE usuario_cpf = ?", (cpf,)
    ).fetchone()
    return linha_para_dict(linha)


def inserir(conn, usuario, senha_hash, senha_provisoria=0, perfil=None, dados=None):
    """Insere um usuário. `dados` traz os campos de perfil, quando houver."""
    dados = dados or {}
    cur = conn.execute(
        "INSERT INTO usuarios (usuario_nome, usuario_senha_hash, usuario_senha_provisoria, "
        "usuario_perfil, usuario_nome_completo, usuario_cpf, usuario_telefone, usuario_email) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            usuario, senha_hash, 1 if senha_provisoria else 0,
            perfil or dados.get("perfil") or "vendedor",
            dados.get("nome_completo"), dados.get("cpf"),
            dados.get("telefone"), dados.get("email"),
        ),
    )
    return cur.lastrowid


def atualizar_dados(conn, usuario_id, dados):
    """Atualiza os dados cadastrais e o perfil (não mexe na senha)."""
    conn.execute(
        "UPDATE usuarios SET usuario_nome = :usuario, usuario_perfil = :perfil, "
        "usuario_nome_completo = :nome_completo, usuario_cpf = :cpf, "
        "usuario_telefone = :telefone, usuario_email = :email "
        "WHERE usuario_id = :id",
        {**dados, "id": usuario_id},
    )


def listar(conn):
    linhas = conn.execute(
        f"SELECT {_COLUNAS_LISTAGEM} FROM usuarios ORDER BY usuario_nome"
    ).fetchall()
    return linhas_para_lista(linhas)


def atualizar_senha(conn, usuario_id, senha_hash):
    """Troca a senha e marca que já não é mais provisória."""
    conn.execute(
        "UPDATE usuarios SET usuario_senha_hash = ?, usuario_senha_provisoria = 0 "
        "WHERE usuario_id = ?",
        (senha_hash, usuario_id),
    )


def definir_senha_provisoria(conn, usuario_id, senha_hash):
    """Define uma senha provisória (troca obrigatória no próximo acesso)."""
    conn.execute(
        "UPDATE usuarios SET usuario_senha_hash = ?, usuario_senha_provisoria = 1 "
        "WHERE usuario_id = ?",
        (senha_hash, usuario_id),
    )


def definir_ativo(conn, usuario_id, ativo):
    conn.execute(
        "UPDATE usuarios SET usuario_ativo = ? WHERE usuario_id = ?",
        (1 if ativo else 0, usuario_id),
    )


def remover(conn, usuario_id):
    conn.execute("DELETE FROM usuarios WHERE usuario_id = ?", (usuario_id,))
