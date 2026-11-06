import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from aplicar_migracao_estruturas import (garantir_locais,
                                         garantir_movimentacoes,
                                         garantir_tabelas_novas,
                                         garantir_usuarios,
                                         liberar_locais_nas_tabelas)
from database import DB_PATH

TIPOS_QUE_SOMAM = ("SALDO_INICIAL", "ENTRADA", "AJUSTE_POSITIVO", "TRANSFERENCIA_ENTRADA")


def _colunas(conn, tabela):
    return [c[1] for c in conn.execute(f"PRAGMA table_info({tabela})")]


def _conciliar_historico(conn, avisos):
    soma = ",".join(f"'{t}'" for t in TIPOS_QUE_SOMAM)
    linhas = conn.execute(f"""
        SELECT e.produto_id, e.estoque_local, e.estoque_quantidade AS saldo,
               COALESCE((SELECT SUM(CASE WHEN m.tipo IN ({soma}) THEN m.quantidade ELSE -m.quantidade END)
                         FROM movimentacoes m
                         WHERE m.produto_id = e.produto_id AND m.estoque_local = e.estoque_local), 0) AS historico
        FROM estoque e""").fetchall()

    ts = conn.execute("SELECT datetime(MIN(criado_em), '-1 second') FROM movimentacoes").fetchone()[0]
    criados = corrigidos = 0
    for produto_id, local, saldo, historico in linhas:
        dif = saldo - historico
        if abs(dif) < 1e-9:
            continue
        if dif > 0:
            conn.execute(
                """INSERT INTO movimentacoes (produto_id, estoque_local, tipo, quantidade,
                                              observacao, registrado_por, criado_em)
                   VALUES (?, ?, 'SALDO_INICIAL', ?, 'Saldo existente na migração', 'migracao',
                           COALESCE(?, CURRENT_TIMESTAMP))""",
                (produto_id, local, dif, ts))
            criados += 1
        else:
            conn.execute(
                """INSERT INTO movimentacoes (produto_id, estoque_local, tipo, quantidade,
                                              observacao, registrado_por)
                   VALUES (?, ?, 'AJUSTE_NEGATIVO', ?,
                           'Migração: o histórico anterior somava mais que o saldo do estoque', 'migracao')""",
                (produto_id, local, -dif))
            corrigidos += 1
            avisos.append(f"produto {produto_id} ({local}): histórico anterior somava {historico:g}, "
                          f"saldo real é {saldo:g}; ajuste de {-dif:g} registrado")
    return criados, corrigidos


def migrar(caminho, fazer_backup=True):
    """Aplica todas as alterações de esquema necessárias, num único commit.

    É idempotente: rodar de novo num banco já atualizado não muda nada (e não
    gera backup). Em caso de falha, desfaz tudo (ROLLBACK). Retorna
    (mensagens, avisos).
    """
    caminho = Path(caminho)
    msgs, avisos = [], []
    backup = None
    if fazer_backup:
        backup = Path(f"{caminho}.{datetime.now():%Y%m%d-%H%M%S-%f}.bak")
        shutil.copy(caminho, backup)

    conn = sqlite3.connect(caminho)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")

        if "itens_compptra_quantidade" in _colunas(conn, "itens_da_compra"):
            conn.execute("ALTER TABLE itens_da_compra "
                         "RENAME COLUMN itens_compptra_quantidade TO itens_compra_quantidade")
            msgs.append("coluna itens_compra_quantidade corrigida")
        if "compra_id" in _colunas(conn, "compras"):
            conn.execute("ALTER TABLE compras RENAME COLUMN compra_id TO compras_id")
            msgs.append("compras.compras_id restaurado (nome usado pela equipe)")

        if "fornecedor_id" not in _colunas(conn, "produtos"):
            conn.execute("ALTER TABLE produtos ADD COLUMN fornecedor_id "
                         "INTEGER REFERENCES fornecedores(fornecedor_id)")
            msgs.append("produtos.fornecedor_id criada")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_produtos_fornecedor ON produtos (fornecedor_id)")
        if "produto_estoque_maximo" not in _colunas(conn, "produtos"):
            conn.execute("ALTER TABLE produtos ADD COLUMN produto_estoque_maximo REAL")
            msgs.append("produtos.produto_estoque_maximo criada (vazia: preencher por produto)")

        if "categoria_descricao" not in _colunas(conn, "categorias"):
            conn.execute("ALTER TABLE categorias ADD COLUMN categoria_descricao TEXT")
            msgs.append("categorias.categoria_descricao criada")
        if "fornecedor_email" not in _colunas(conn, "fornecedores"):
            conn.execute("ALTER TABLE fornecedores ADD COLUMN fornecedor_email TEXT")
            msgs.append("fornecedores.fornecedor_email criada")

        # Reconstrução (quando preciso) e criação da tabela movimentacoes; um
        # tipo 'AJUSTE' antigo (sem direção) é convertido. Retorna True quando
        # o histórico precisa ser reconciliado com o saldo do estoque.
        precisa_conciliar = garantir_movimentacoes(conn, msgs, avisos)

        if precisa_conciliar:
            criados, corrigidos = _conciliar_historico(conn, avisos)
            msgs.append(f"histórico reconciliado com o estoque ({criados} saldo(s) inicial(is), "
                        f"{corrigidos} correção(ões))")

        garantir_usuarios(conn, msgs, avisos)
        garantir_tabelas_novas(conn, msgs)
        garantir_locais(conn, msgs)
        # O CHECK fixo 'deposito'/'loja' sai depois que as tabelas já existem e
        # antes de qualquer escrita que use um local novo.
        liberar_locais_nas_tabelas(conn, msgs)

        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    if backup is not None and not msgs:
        backup.unlink()
    return msgs, avisos


def main():
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else DB_PATH
    msgs, avisos = migrar(caminho)
    print(f"Banco: {caminho}")
    if not msgs:
        print("Nada a fazer: o banco já está atualizado.")
    for m in msgs:
        print(f"- {m}")
    senha_avisos = [a for a in avisos if a.startswith("SENHA INICIAL")]
    outros = [a for a in avisos if not a.startswith("SENHA INICIAL")]
    for a in outros:
        print(f"ATENÇÃO: {a}")
    if senha_avisos:
        linha = "=" * 60
        print(linha)
        for a in senha_avisos:
            print(a)
        print(linha)
    if msgs:
        print("(uma cópia de segurança do banco anterior foi salva ao lado do arquivo, com extensão .bak)")
    print("Migração concluída.")


if __name__ == "__main__":
    main()
