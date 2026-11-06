import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from aplicar_migracao import migrar

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _copia(nome):
    pasta = tempfile.mkdtemp()
    destino = Path(pasta) / "teste.db"
    shutil.copy(FIXTURES / nome, destino)
    return pasta, destino


def _auditoria(caminho):
    from repositories import movimentacao_repository
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    try:
        return movimentacao_repository.auditar_saldos(conn)
    finally:
        conn.close()


class TestMigracao(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, "pasta"):
            shutil.rmtree(self.pasta, ignore_errors=True)

    def test_versao_da_equipe(self):
        self.pasta, db = _copia("PJIdb_v2_versao_equipe.db")
        msgs, avisos = migrar(db, fazer_backup=False)
        conn = sqlite3.connect(db)
        cols = [c[1] for c in conn.execute("PRAGMA table_info(produtos)")]
        self.assertIn("produto_estoque_maximo", cols)
        tipos = {r[0] for r in conn.execute("SELECT DISTINCT tipo FROM movimentacoes")}
        self.assertNotIn("AJUSTE", tipos)
        self.assertIn("AJUSTE_NEGATIVO", tipos)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM movimentacoes WHERE registrado_por <> 'migracao'").fetchone()[0], 6)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0], 23)
        self.assertEqual(conn.execute("SELECT SUM(estoque_quantidade) FROM estoque").fetchone()[0],
                         sqlite3.connect(FIXTURES / "PJIdb_v2_versao_equipe.db")
                         .execute("SELECT SUM(estoque_quantidade) FROM estoque").fetchone()[0])
        conn.close()
        self.assertEqual(_auditoria(db), [])
        self.assertTrue(any("AJUSTE" in a for a in avisos))

    def test_primeira_versao_sem_movimentacoes(self):
        self.pasta, db = _copia("PJIdb_v2_primeira_versao.db")
        migrar(db, fazer_backup=False)
        conn = sqlite3.connect(db)
        self.assertIn("itens_compra_quantidade", [c[1] for c in conn.execute("PRAGMA table_info(itens_da_compra)")])
        self.assertIn("compras_id", [c[1] for c in conn.execute("PRAGMA table_info(compras)")])
        conn.close()
        self.assertEqual(_auditoria(db), [])

    def test_repetir_nao_muda_nada(self):
        self.pasta, db = _copia("PJIdb_v2_versao_equipe.db")
        migrar(db, fazer_backup=False)
        antes = sqlite3.connect(db).execute("SELECT COUNT(*) FROM movimentacoes").fetchone()[0]
        msgs, avisos = migrar(db, fazer_backup=False)
        depois = sqlite3.connect(db).execute("SELECT COUNT(*) FROM movimentacoes").fetchone()[0]
        self.assertEqual((msgs, avisos, antes), ([], [], depois))

    def test_banco_de_migracao_anterior_com_compra_id(self):
        self.pasta, db = _copia("PJIdb_v2_versao_equipe.db")
        migrar(db, fazer_backup=False)
        conn = sqlite3.connect(db)
        conn.execute("ALTER TABLE compras RENAME COLUMN compras_id TO compra_id")
        conn.commit()
        conn.close()
        migrar(db, fazer_backup=False)
        conn = sqlite3.connect(db)
        self.assertIn("compras_id", [c[1] for c in conn.execute("PRAGMA table_info(compras)")])
        conn.close()

    def test_backup_e_criado_so_quando_ha_mudanca(self):
        self.pasta, db = _copia("PJIdb_v2_versao_equipe.db")
        msgs, _ = migrar(db)
        self.assertTrue(msgs)  # o banco da fixture ainda não está atualizado
        self.assertEqual(len(list(Path(self.pasta).glob("*.bak"))), 1)
        msgs, _ = migrar(db)   # segunda execução: nada a fazer
        self.assertEqual(msgs, [])
        self.assertEqual(len(list(Path(self.pasta).glob("*.bak"))), 1)

    def test_perfis_criados_e_admin_mantido(self):
        self.pasta, db = _copia("PJIdb_v2_versao_equipe.db")
        # A fixture da equipe é anterior aos perfis (não tem a tabela usuarios).
        fixture = sqlite3.connect(FIXTURES / "PJIdb_v2_versao_equipe.db")
        self.assertNotIn("usuarios", [r[0] for r in fixture.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")])
        fixture.close()
        # Simula a instalação antiga que já tinha um admin com senha definida.
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE usuarios (usuario_id INTEGER PRIMARY KEY AUTOINCREMENT, "
                     "usuario_nome TEXT NOT NULL UNIQUE, usuario_senha_hash TEXT NOT NULL, "
                     "usuario_ativo INTEGER NOT NULL DEFAULT 1, "
                     "usuario_criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("INSERT INTO usuarios (usuario_nome, usuario_senha_hash) "
                     "VALUES ('admin', 'hash-de-teste')")
        conn.commit()
        conn.close()

        migrar(db, fazer_backup=False)
        conn = sqlite3.connect(db)
        cols = [c[1] for c in conn.execute("PRAGMA table_info(usuarios)")]
        for coluna in ("usuario_perfil", "usuario_nome_completo", "usuario_cpf",
                       "usuario_telefone", "usuario_email", "usuario_senha_provisoria"):
            self.assertIn(coluna, cols)
        # O usuário continua com o mesmo hash e passa a ser administrador.
        perfil, hash_senha = conn.execute(
            "SELECT usuario_perfil, usuario_senha_hash FROM usuarios WHERE usuario_nome = 'admin'").fetchone()
        self.assertEqual((perfil, hash_senha), ("admin", "hash-de-teste"))
        conn.close()

    def test_perfis_criados_quando_nao_havia_tabela(self):
        self.pasta, db = _copia("PJIdb_v2_primeira_versao.db")
        msgs, avisos = migrar(db, fazer_backup=False)
        conn = sqlite3.connect(db)
        linhas = conn.execute("SELECT usuario_nome, usuario_perfil, usuario_senha_provisoria "
                              "FROM usuarios").fetchall()
        for tabela in ("clientes", "fornecedor_representantes", "vendas", "itens_da_venda"):
            self.assertIsNotNone(conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabela,)).fetchone(), tabela)
        self.assertIn("venda_id", [c[1] for c in conn.execute("PRAGMA table_info(movimentacoes)")])
        conn.close()
        self.assertEqual(len(linhas), 1)
        usuario, perfil, provisoria = linhas[0]
        self.assertEqual((usuario, perfil, provisoria), ("admin", "admin", 1))
        self.assertTrue(any("SENHA INICIAL" in a for a in avisos))
        self.assertIn("tabela usuarios criada com o administrador 'admin'", msgs)


if __name__ == "__main__":
    unittest.main()
