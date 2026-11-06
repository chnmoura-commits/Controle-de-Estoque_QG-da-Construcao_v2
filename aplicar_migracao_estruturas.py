"""Estruturas criadas pela migração: tabelas novas, colunas e a primeira carga.

Separado de `aplicar_migracao.py` para manter as funções de migração curtas e
legíveis. Tudo é idempotente: cada função só cria/adiciona o que ainda falta.
"""
from security import gerar_hash, gerar_senha_provisoria

# --- Tabelas novas ----------------------------------------------------------

SQL_USUARIOS = """
CREATE TABLE IF NOT EXISTS usuarios (
    usuario_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_nome               TEXT NOT NULL UNIQUE,
    usuario_senha_hash         TEXT NOT NULL,
    usuario_ativo              INTEGER NOT NULL DEFAULT 1,
    usuario_senha_provisoria   INTEGER NOT NULL DEFAULT 0,
    usuario_criado_em          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_perfil             TEXT NOT NULL DEFAULT 'vendedor'
                               CHECK (usuario_perfil IN ('admin','gerente','vendedor')),
    usuario_nome_completo      TEXT,
    usuario_cpf                TEXT,
    usuario_telefone           TEXT,
    usuario_email              TEXT
)"""

SQL_MOVIMENTACOES = """
CREATE TABLE {nome} (
    movimentacao_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id       INTEGER NOT NULL REFERENCES produtos(produto_id),
    -- Código do local (tabela `locais`). Sem CHECK: a validação é feita no
    -- `process`, para que novos locais possam ser cadastrados sem migração.
    estoque_local    TEXT NOT NULL,
    tipo             TEXT NOT NULL CHECK (tipo IN (
                        'SALDO_INICIAL','ENTRADA','SAIDA','PERDA',
                        'AJUSTE_POSITIVO','AJUSTE_NEGATIVO',
                        'TRANSFERENCIA_ENTRADA','TRANSFERENCIA_SAIDA')),
    quantidade       REAL NOT NULL CHECK (quantidade > 0),
    compra_id        INTEGER REFERENCES compras(compras_id),
    venda_id         INTEGER,
    observacao       TEXT,
    registrado_por   TEXT,
    criado_em        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""

SQL_ESTOQUE = """
CREATE TABLE {nome} (
    produto_id          INTEGER NOT NULL REFERENCES produtos(produto_id),
    estoque_local       TEXT NOT NULL,
    estoque_quantidade  REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (produto_id, estoque_local)
)"""

SQL_CLIENTES = """
CREATE TABLE IF NOT EXISTS clientes (
    cliente_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_nome       TEXT NOT NULL,
    cliente_cpf        TEXT,
    cliente_telefone   TEXT,
    cliente_email      TEXT,
    cliente_endereco   TEXT,
    cliente_ativo      INTEGER NOT NULL DEFAULT 1,
    cliente_criado_em  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""

SQL_FORNECEDOR_REPRESENTANTES = """
CREATE TABLE IF NOT EXISTS fornecedor_representantes (
    representante_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    fornecedor_id           INTEGER NOT NULL REFERENCES fornecedores(fornecedor_id),
    representante_nome      TEXT NOT NULL,
    representante_contato   TEXT,
    representante_email     TEXT,
    representante_ativo     INTEGER NOT NULL DEFAULT 1,
    representante_criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""

SQL_VENDAS = """
CREATE TABLE IF NOT EXISTS vendas (
    venda_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_numero      TEXT NOT NULL UNIQUE,
    cliente_id        INTEGER REFERENCES clientes(cliente_id),
    venda_status      TEXT NOT NULL DEFAULT 'CONCLUIDA'
                      CHECK (venda_status IN ('CONCLUIDA','CANCELADA')),
    venda_total       REAL NOT NULL DEFAULT 0,
    venda_desconto    REAL NOT NULL DEFAULT 0,
    -- Código do local (tabela `locais`); validado no `process`.
    venda_local       TEXT NOT NULL,
    venda_observacao  TEXT,
    registrado_por    TEXT,
    criado_em         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cancelado_em      TEXT,
    cancelado_por     TEXT
)"""

SQL_ITENS_DA_VENDA = """
CREATE TABLE IF NOT EXISTS itens_da_venda (
    item_venda_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id         INTEGER NOT NULL REFERENCES vendas(venda_id),
    produto_id       INTEGER NOT NULL REFERENCES produtos(produto_id),
    quantidade       REAL NOT NULL CHECK (quantidade > 0),
    preco_unitario   REAL NOT NULL CHECK (preco_unitario >= 0),
    desconto_item    REAL NOT NULL DEFAULT 0 CHECK (desconto_item >= 0),
    subtotal         REAL NOT NULL
)"""

# Locais (depósito e lojas): onde o estoque fica e para onde ele vai.
# O estoque, as movimentações e as vendas guardam o local pelo CÓDIGO (texto)
# em `estoque_local` / `venda_local`; por isso o código é a chave primária.
# Existe no máximo um local do tipo 'deposito' (índice único parcial).
SQL_LOCAIS = """
CREATE TABLE IF NOT EXISTS locais (
    local_codigo      TEXT PRIMARY KEY,
    local_nome        TEXT NOT NULL,
    local_tipo        TEXT NOT NULL DEFAULT 'loja'
                      CHECK (local_tipo IN ('deposito','loja')),
    local_cnpj        TEXT,
    local_endereco    TEXT,
    local_telefone    TEXT,
    local_email       TEXT,
    local_ativo       INTEGER NOT NULL DEFAULT 1,
    local_criado_em   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""

# Dados dos locais históricos (antes eram valores fixos 'deposito' / 'loja').
# INSERT OR IGNORE: se o usuário já cadastrou/editou o local, nada é sobrescrito.
_SEED_LOCAIS = (
    ("deposito", "Depósito", "deposito"),
    ("loja", "Loja", "loja"),
)


def _existe(conn, tabela):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
    ).fetchone() is not None


def _colunas(conn, tabela):
    return [c[1] for c in conn.execute(f"PRAGMA table_info({tabela})")]


def _sql_da_tabela(conn, tabela):
    r = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabela,)).fetchone()
    return r[0] if r else None


# --- Usuários / colaboradores ----------------------------------------------

def garantir_usuarios(conn, msgs, avisos):
    """Cria a tabela `usuarios` (com o admin inicial) ou completa as colunas novas.

    Retorna True quando a tabela acabou de ser criada nesta execução.
    """
    criada_agora = not _existe(conn, "usuarios")
    if criada_agora:
        conn.execute(SQL_USUARIOS)
        msgs.append("tabela usuarios criada com o administrador 'admin'")
    elif "usuario_senha_provisoria" not in _colunas(conn, "usuarios"):
        conn.execute("ALTER TABLE usuarios ADD COLUMN "
                     "usuario_senha_provisoria INTEGER NOT NULL DEFAULT 0")
        msgs.append("coluna usuarios.usuario_senha_provisoria criada")

    # Perfis de acesso: coluna com CHECK. Como o SQLite não altera um CHECK,
    # um banco antigo (sem a coluna) é reconstruído copiando os dados.
    if "usuario_perfil" not in _colunas(conn, "usuarios"):
        _reconstruir_usuarios_com_perfil(conn)
        msgs.append("tabela usuarios reconstruída com usuario_perfil (todos viram 'admin')")

    for coluna in ("usuario_nome_completo", "usuario_cpf", "usuario_telefone", "usuario_email"):
        if coluna not in _colunas(conn, "usuarios"):
            conn.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} TEXT")
            msgs.append(f"coluna usuarios.{coluna} criada")

    # O admin existente (ou o único usuário de uma instalação antiga) vira admin.
    if conn.execute("SELECT COUNT(*) FROM usuarios WHERE usuario_perfil = 'admin'").fetchone()[0] == 0:
        conn.execute("UPDATE usuarios SET usuario_perfil = 'admin'")
        msgs.append("usuários existentes definidos com o perfil 'admin'")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_usuarios_cpf "
                 "ON usuarios (usuario_cpf) WHERE usuario_cpf IS NOT NULL")

    if criada_agora:
        senha_inicial = gerar_senha_provisoria()
        conn.execute(
            "INSERT INTO usuarios (usuario_nome, usuario_senha_hash, usuario_senha_provisoria, "
            "usuario_perfil, usuario_nome_completo) VALUES (?, ?, 1, 'admin', 'Administrador')",
            ("admin", gerar_hash(senha_inicial)),
        )
        avisos.append(
            f"SENHA INICIAL do usuário 'admin': {senha_inicial}  "
            "(anote agora; você será obrigado a trocá-la no primeiro acesso)")
    return criada_agora


def _reconstruir_usuarios_com_perfil(conn):
    """Recria a tabela usuarios preservando todos os dados existentes."""
    conn.execute("ALTER TABLE usuarios RENAME TO usuarios_antigos")
    conn.execute(SQL_USUARIOS)
    antigas = _colunas(conn, "usuarios_antigos")
    conn.execute(f"""
        INSERT INTO usuarios (usuario_id, usuario_nome, usuario_senha_hash, usuario_ativo,
                              usuario_senha_provisoria, usuario_criado_em, usuario_perfil)
        SELECT usuario_id, usuario_nome, usuario_senha_hash, usuario_ativo,
               usuario_senha_provisoria, usuario_criado_em, 'admin'
        FROM usuarios_antigos""")
    if "usuario_nome_completo" in antigas:
        conn.execute("UPDATE usuarios SET usuario_nome_completo = "
                     "(SELECT usuario_nome_completo FROM usuarios_antigos a "
                     " WHERE a.usuario_id = usuarios.usuario_id)")
    conn.execute("DROP TABLE usuarios_antigos")


# --- Movimentações (novo tipo de referência: venda_id) ----------------------

def garantir_movimentacoes(conn, msgs, avisos):
    """Cria/reconstrói `movimentacoes`. Retorna True se acabou de ser criada.

    A reconstrução também converte o tipo antigo 'AJUSTE' (sem direção) em
    'AJUSTE_NEGATIVO'. A reconciliação do histórico com o saldo fica a cargo de
    quem chama, usando o valor devolvido.
    """
    sql_atual = _sql_da_tabela(conn, "movimentacoes")
    if sql_atual is None:
        conn.execute(SQL_MOVIMENTACOES.format(nome="movimentacoes"))
        msgs.append("tabela movimentacoes criada")
        criada = True
    elif "AJUSTE_POSITIVO" not in sql_atual or "venda_id" not in sql_atual:
        tem_ajuste = "AJUSTE_POSITIVO" in sql_atual
        conn.execute(SQL_MOVIMENTACOES.format(nome="movimentacoes_nova"))
        # Copia os dados. Bancos muito antigos têm o tipo 'AJUSTE', sem direção:
        # são convertidos em AJUSTE_NEGATIVO com um aviso na observação.
        if tem_ajuste:
            conn.execute("""
                INSERT INTO movimentacoes_nova
                    (movimentacao_id, produto_id, estoque_local, tipo, quantidade, compra_id,
                     venda_id, observacao, registrado_por, criado_em)
                SELECT movimentacao_id, produto_id, estoque_local, tipo, quantidade, compra_id,
                       NULL, observacao, registrado_por, criado_em
                FROM movimentacoes""")
        else:
            n_ajustes = conn.execute(
                "SELECT COUNT(*) FROM movimentacoes WHERE tipo = 'AJUSTE'").fetchone()[0]
            conn.execute("""
                INSERT INTO movimentacoes_nova
                    (movimentacao_id, produto_id, estoque_local, tipo, quantidade, compra_id,
                     venda_id, observacao, registrado_por, criado_em)
                SELECT movimentacao_id, produto_id, estoque_local,
                       CASE WHEN tipo = 'AJUSTE' THEN 'AJUSTE_NEGATIVO' ELSE tipo END,
                       quantidade, compra_id, NULL,
                       CASE WHEN tipo = 'AJUSTE'
                            THEN COALESCE(observacao, '') || ' [migração: direção do ajuste assumida como negativa]'
                            ELSE observacao END,
                       registrado_por, criado_em
                FROM movimentacoes""")
            if n_ajustes:
                avisos.append(f"{n_ajustes} movimentação(ões) 'AJUSTE' antiga(s) foram marcadas como "
                              "AJUSTE_NEGATIVO (o tipo antigo não informava a direção). Confira se é o caso.")
        conn.execute("DROP TABLE movimentacoes")
        conn.execute("ALTER TABLE movimentacoes_nova RENAME TO movimentacoes")
        msgs.append("tabela movimentacoes reconstruída (tipos de ajuste e referência a vendas)")
        criada = not tem_ajuste
    else:
        criada = False
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mov_produto ON movimentacoes(produto_id, criado_em)")
    return criada


# --- Clientes, representantes, vendas --------------------------------------

def garantir_tabelas_novas(conn, msgs):
    for tabela, sql in (
        ("clientes", SQL_CLIENTES),
        ("fornecedor_representantes", SQL_FORNECEDOR_REPRESENTANTES),
        ("vendas", SQL_VENDAS),
        ("itens_da_venda", SQL_ITENS_DA_VENDA),
    ):
        if not _existe(conn, tabela):
            conn.execute(sql)
            msgs.append(f"tabela {tabela} criada")


# --- Locais (depósito / lojas) ---------------------------------------------

def garantir_locais(conn, msgs):
    """Cria `locais` e garante os locais históricos e um (único) depósito."""
    if not _existe(conn, "locais"):
        conn.execute(SQL_LOCAIS)
        msgs.append("tabela locais criada")
    conn.executemany(
        "INSERT OR IGNORE INTO locais (local_codigo, local_nome, local_tipo) VALUES (?, ?, ?)",
        _SEED_LOCAIS,
    )
    # O sistema sempre precisou de um depósito (destino de compras, origem das
    # transferências). Se o local 'deposito' virou loja, recria o depósito.
    if conn.execute("SELECT 1 FROM locais WHERE local_tipo = 'deposito'").fetchone() is None:
        conn.execute(
            "INSERT OR IGNORE INTO locais (local_codigo, local_nome, local_tipo) "
            "VALUES ('deposito', 'Depósito', 'deposito')"
        )
        msgs.append("depósito padrão recriado (o sistema precisa de um local 'deposito')")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_locais_um_deposito "
        "ON locais (local_tipo) WHERE local_tipo = 'deposito'"
    )


def _tem_check_de_local(sql):
    """Indica se a tabela ainda aceita apenas os locais fixos 'deposito'/'loja'."""
    return sql is not None and "IN ('deposito'" in sql.replace('"', "'")


def liberar_locais_nas_tabelas(conn, msgs):
    """Remove o CHECK fixo de local em `estoque`, `movimentacoes` e `vendas`.

    Antes de existir o cadastro de locais, essas tabelas só aceitavam os textos
    'deposito' e 'loja'. Como o SQLite não altera um CHECK, a tabela é recriada
    copiando os dados. Idempotente: só age quando o CHECK antigo ainda existe.
    """
    # (tabela, SQL novo, índice a recriar depois da reconstrução)
    alvos = (
        ("estoque", SQL_ESTOQUE,
         "CREATE INDEX IF NOT EXISTS idx_estoque_local ON estoque(estoque_local)"),
        ("movimentacoes", SQL_MOVIMENTACOES,
         "CREATE INDEX IF NOT EXISTS idx_mov_produto ON movimentacoes(produto_id, criado_em)"),
        ("vendas", SQL_VENDAS,
         "CREATE INDEX IF NOT EXISTS idx_vendas_local ON vendas(venda_local)"),
    )
    for tabela, sql_novo, sql_indice in alvos:
        sql_atual = _sql_da_tabela(conn, tabela)
        if not _tem_check_de_local(sql_atual):
            continue
        colunas = ", ".join(_colunas(conn, tabela))
        conn.execute(sql_novo.format(nome=f"{tabela}_nova"))
        conn.execute(f"INSERT INTO {tabela}_nova ({colunas}) SELECT {colunas} FROM {tabela}")
        conn.execute(f"DROP TABLE {tabela}")
        conn.execute(f"ALTER TABLE {tabela}_nova RENAME TO {tabela}")
        conn.execute(sql_indice)
        msgs.append(f"tabela {tabela} liberada para os locais cadastrados (CHECK removido)")
