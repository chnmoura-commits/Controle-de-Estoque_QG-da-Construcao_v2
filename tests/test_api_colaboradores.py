"""Testes das rotas de colaboradores: autenticação e permissões por perfil.

Usa o TestClient do FastAPI para exercitar as dependências de segurança
(401 sem token, 403 para quem não é administrador, 200/201 para o admin).
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent


class TestColaboradoresAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pasta = tempfile.mkdtemp()
        copia = Path(cls.pasta) / "teste.db"
        shutil.copy(RAIZ / "PJIdb_v2.db", copia)
        import database
        database.DB_PATH = copia
        from aplicar_migracao import migrar
        migrar(copia, fazer_backup=False)

        from process import colaborador_process
        # Um administrador e um vendedor fixos, com senha conhecida.
        colaborador_process.criar({
            "usuario": "admin_t", "nome_completo": "Admin Teste", "cpf": "529.982.247-25",
            "telefone": "(11) 99999-0000", "email": "admin@teste.com", "perfil": "admin"})
        colaborador_process.criar({
            "usuario": "vendedor_t", "nome_completo": "Vendedor Teste", "cpf": "111.444.777-35",
            "telefone": "(11) 99999-1111", "email": "vendedor@teste.com", "perfil": "vendedor"})
        from database import conexao
        from repositories import usuario_repository as repo
        from security import gerar_hash
        with conexao() as conn:
            for usuario in ("admin_t", "vendedor_t"):
                registro = repo.obter_por_usuario(conn, usuario)
                repo.atualizar_senha(conn, registro["usuario_id"], gerar_hash(f"{usuario}123"))

        from main import app
        cls.cliente = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.pasta, ignore_errors=True)

    def _token(self, usuario):
        r = self.cliente.post("/auth/login", json={"usuario": usuario, "senha": f"{usuario}123"})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["access_token"]

    def _cabecalho(self, usuario):
        return {"Authorization": f"Bearer {self._token(usuario)}"}

    def test_sem_token_devolve_401(self):
        self.assertEqual(self.cliente.get("/colaboradores").status_code, 401)

    def test_token_invalido_devolve_401(self):
        r = self.cliente.get("/colaboradores", headers={"Authorization": "Bearer abc.def.ghi"})
        self.assertEqual(r.status_code, 401)

    def test_vendedor_nao_pode_gerenciar_colaboradores(self):
        cabecalho = self._cabecalho("vendedor_t")
        self.assertEqual(self.cliente.get("/colaboradores", headers=cabecalho).status_code, 403)
        self.assertEqual(self.cliente.post("/colaboradores", headers=cabecalho, json={
            "usuario": "x", "nome_completo": "X", "cpf": "390.533.447-05",
            "telefone": "(11) 98888-7777", "email": "x@x.com", "perfil": "admin"}).status_code, 403)

    def test_vendedor_nao_pode_criar_produto_admin_only(self):
        r = self.cliente.delete("/colaboradores/1", headers=self._cabecalho("vendedor_t"))
        self.assertEqual(r.status_code, 403)

    def test_admin_lista_e_cria_colaborador(self):
        cabecalho = self._cabecalho("admin_t")
        r = self.cliente.get("/colaboradores", headers=cabecalho)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(c["usuario_nome"] == "vendedor_t" for c in r.json()))

        r = self.cliente.post("/colaboradores", headers=cabecalho, json={
            "usuario": "novo", "nome_completo": "Novo Colaborador",
            "cpf": "390.533.447-05", "telefone": "(11) 97777-6666",
            "email": "novo@teste.com", "perfil": "gerente"})
        self.assertEqual(r.status_code, 201, r.text)
        corpo = r.json()
        self.assertTrue(corpo["senha_provisoria"])
        self.assertEqual(corpo["colaborador"]["usuario_perfil"], "gerente")
        self.assertNotIn("usuario_senha_hash", corpo["colaborador"])

        # A senha provisória funciona e exige a troca.
        r = self.cliente.post("/auth/login", json={
            "usuario": "novo", "senha": corpo["senha_provisoria"]})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["trocar_senha"])

    def test_erros_de_validacao_viram_422_com_mensagem(self):
        cabecalho = self._cabecalho("admin_t")
        r = self.cliente.post("/colaboradores", headers=cabecalho, json={
            "usuario": "invalido", "nome_completo": "Fulano",
            "cpf": "111.111.111-11", "telefone": "(11) 98888-7777",
            "email": "fulano@teste.com", "perfil": "vendedor"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("CPF", r.json()["erro"])

    def test_login_retorna_perfil(self):
        r = self.cliente.post("/auth/login", json={"usuario": "admin_t", "senha": "admin_t123"})
        self.assertEqual(r.json()["perfil"], "admin")


if __name__ == "__main__":
    unittest.main()
