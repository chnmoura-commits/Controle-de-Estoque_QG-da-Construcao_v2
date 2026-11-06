import os
import shutil
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class BaseTeste(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        copia = Path(self.pasta) / "teste.db"
        shutil.copy(RAIZ / "PJIdb_v2.db", copia)
        import database
        database.DB_PATH = copia
        # Banco de teste entra no estado atual do sistema (perfis, vendas, clientes...).
        from aplicar_migracao import migrar
        migrar(copia, fazer_backup=False)
        self._garantir_usuarios_de_teste()

    def _garantir_usuarios_de_teste(self):
        """Cria os usuários de teste na cópia, independente do banco real.

        O banco entregue tem apenas o admin provisório; os testes precisam de
        usuários com senha conhecida e definida (não provisória) e de cada perfil.
        """
        from database import conexao
        from repositories import usuario_repository as repo
        from security import gerar_hash
        with conexao() as conn:
            for usuario, senha, perfil in TestAutenticacao.USUARIOS:
                registro = repo.obter_por_usuario(conn, usuario)
                if registro is None:
                    repo.inserir(conn, usuario, gerar_hash(senha), perfil=perfil)
                else:
                    repo.atualizar_senha(conn, registro["usuario_id"], gerar_hash(senha))

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)






from exceptions import NaoEncontradoError, RegraDeNegocioError
from process import (alerta_process, compra_process, custo_process, local_process,
                     movimentacao_process, produto_process, venda_process)




from process import (alerta_process, auth_process, cliente_process,
                     colaborador_process, compra_process, fornecedor_process,
                     movimentacao_process, produto_process,
                     representante_process, venda_process)


class TestAutenticacao(BaseTeste):
    USUARIOS = (("admin", "admin123", "admin"), ("gerente", "gerente123", "gerente"),
                ("operador", "operador123", "vendedor"))

    def test_usuarios_de_teste_autenticam(self):
        for usuario, senha, perfil in self.USUARIOS:
            r = auth_process.autenticar({"usuario": usuario, "senha": senha})
            self.assertEqual(r["usuario"], usuario)
            self.assertIn("usuario_id", r)
            self.assertEqual(r["perfil"], perfil)

    def test_senha_errada_e_rejeitada(self):
        with self.assertRaises(RegraDeNegocioError):
            auth_process.autenticar({"usuario": "admin", "senha": "errada"})

    def test_usuario_inexistente_e_rejeitado(self):
        with self.assertRaises(RegraDeNegocioError):
            auth_process.autenticar({"usuario": "ninguem", "senha": "x"})

    def test_credenciais_vazias_sao_rejeitadas(self):
        with self.assertRaises(RegraDeNegocioError):
            auth_process.autenticar({"usuario": "", "senha": ""})

    def test_login_emite_token_valido(self):
        from security import decodificar_token
        r = auth_process.autenticar({"usuario": "admin", "senha": "admin123"})
        self.assertIn("access_token", r)
        corpo = decodificar_token(r["access_token"])
        self.assertEqual(corpo["sub"], r["usuario_id"])
        self.assertEqual(corpo["nome"], "admin")
        self.assertGreater(corpo["exp"], corpo["iat"])

    def test_login_senha_definida_nao_pede_troca(self):
        r = auth_process.autenticar({"usuario": "admin", "senha": "admin123"})
        self.assertFalse(r["trocar_senha"])


class TestSenhaProvisoria(BaseTeste):
    """Fluxo do primeiro acesso: senha provisória e troca obrigatória."""

    def _criar_provisorio(self, usuario="novo"):
        from database import conexao
        from repositories import usuario_repository as repo
        from security import gerar_hash, gerar_senha_provisoria
        senha = gerar_senha_provisoria()
        with conexao() as conn:
            repo.inserir(conn, usuario, gerar_hash(senha), senha_provisoria=1)
        return usuario, senha

    def test_login_com_senha_provisoria_sinaliza_troca(self):
        usuario, senha = self._criar_provisorio()
        r = auth_process.autenticar({"usuario": usuario, "senha": senha})
        self.assertTrue(r["trocar_senha"])

    def test_troca_senha_zera_a_flag(self):
        usuario, senha = self._criar_provisorio()
        r = auth_process.autenticar({"usuario": usuario, "senha": senha})
        auth_process.trocar_senha(r["usuario_id"], senha, "novaSenha123")
        r2 = auth_process.autenticar({"usuario": usuario, "senha": "novaSenha123"})
        self.assertFalse(r2["trocar_senha"])

    def test_troca_com_senha_atual_errada_falha(self):
        usuario, senha = self._criar_provisorio()
        r = auth_process.autenticar({"usuario": usuario, "senha": senha})
        with self.assertRaises(RegraDeNegocioError):
            auth_process.trocar_senha(r["usuario_id"], "errada", "novaSenha123")

    def test_troca_com_senha_curta_falha(self):
        usuario, senha = self._criar_provisorio()
        r = auth_process.autenticar({"usuario": usuario, "senha": senha})
        with self.assertRaises(RegraDeNegocioError):
            auth_process.trocar_senha(r["usuario_id"], senha, "curta")

    def test_senha_provisoria_gerada_e_forte(self):
        from security import gerar_senha_provisoria
        a, b = gerar_senha_provisoria(), gerar_senha_provisoria()
        self.assertGreaterEqual(len(a), 12)
        self.assertNotEqual(a, b)
        self.assertFalse(set(a) & set("0O1lI"))


class TestTokenSeguranca(unittest.TestCase):
    UTIL = {"usuario": "admin", "usuario_id": 1}

    def test_token_adulterado_e_rejeitado(self):
        from security import criar_token, decodificar_token
        token = criar_token(self.UTIL)
        cabecalho, corpo, assinatura = token.split(".")
        adulterado = f"{cabecalho}.{corpo}.{assinatura[:-4]}0000"
        self.assertIsNone(decodificar_token(adulterado))

    def test_token_malformado_e_rejeitado(self):
        from security import decodificar_token
        for ruim in ("", "abc", "a.b", "a.b.c.d", "xxx.yyy.zzz"):
            self.assertIsNone(decodificar_token(ruim), ruim)

    def test_token_expirado_e_rejeitado(self):
        import time
        from unittest import mock
        import security
        token = security.criar_token(self.UTIL)
        # Simula o relógio 10 anos à frente: o token deve estar vencido.
        futuro = int(time.time()) + 10 * 365 * 24 * 3600
        with mock.patch.object(security.time, "time", return_value=futuro):
            self.assertIsNone(security.decodificar_token(token))

    def test_payload_assinado_com_outro_segredo_falha(self):
        from unittest import mock
        import security
        token = security.criar_token(self.UTIL)
        with mock.patch.object(security, "JWT_SEGREDO", "outro-segredo-qualquer"):
            self.assertIsNone(security.decodificar_token(token))


class TestMovimentacao(BaseTeste):
    def _saldo(self, produto_id, campo="saldo_deposito"):
        return produto_process.obter(produto_id)[campo]

    def test_entrada_aumenta_saldo_e_gera_historico(self):
        antes = self._saldo(1)
        movimentacao_process.registrar(
            {"produto_id": 1, "local": "deposito", "tipo": "ENTRADA", "quantidade": 7})
        self.assertEqual(self._saldo(1), antes + 7)
        self.assertEqual(movimentacao_process.listar(produto_id=1, tipo="ENTRADA")[0]["quantidade"], 7)

    def test_saida_maior_que_saldo_e_bloqueada_e_nao_altera_nada(self):
        antes = self._saldo(1)
        with self.assertRaises(RegraDeNegocioError):
            movimentacao_process.registrar(
                {"produto_id": 1, "local": "deposito", "tipo": "SAIDA", "quantidade": antes + 1})
        self.assertEqual(self._saldo(1), antes)

    def test_quantidade_zero_ou_negativa_e_bloqueada(self):
        for q in (0, -3):
            with self.assertRaises(RegraDeNegocioError):
                movimentacao_process.registrar(
                    {"produto_id": 1, "local": "loja", "tipo": "SAIDA", "quantidade": q})

    def test_produto_inexistente(self):
        with self.assertRaises(NaoEncontradoError):
            movimentacao_process.registrar(
                {"produto_id": 9999, "local": "loja", "tipo": "ENTRADA", "quantidade": 1})

    def test_transferencia_mantem_total(self):
        total = self._saldo(1, "saldo_total")
        movimentacao_process.transferir(
            {"produto_id": 1, "origem": "deposito", "destino": "loja", "quantidade": 2})
        self.assertEqual(self._saldo(1, "saldo_total"), total)
        self.assertEqual(self._saldo(1, "saldo_deposito"), 3)
        self.assertEqual(self._saldo(1, "saldo_loja"), 10)

    def test_transferencia_sem_saldo_desfaz_tudo(self):
        with self.assertRaises(RegraDeNegocioError):
            movimentacao_process.transferir(
                {"produto_id": 1, "origem": "deposito", "destino": "loja", "quantidade": 999})
        self.assertEqual(self._saldo(1, "saldo_loja"), 8)

    def test_inventario_registra_divergencia(self):
        r = movimentacao_process.contar_inventario(
            {"produto_id": 1, "local": "loja", "quantidade_contada": 6})
        self.assertEqual(r["divergencia"], -2)
        self.assertEqual(self._saldo(1, "saldo_loja"), 6)
        r2 = movimentacao_process.contar_inventario(
            {"produto_id": 1, "local": "loja", "quantidade_contada": 6})
        self.assertEqual(r2["divergencia"], 0)

    def test_auditoria_fecha_apos_varias_operacoes(self):
        movimentacao_process.registrar({"produto_id": 1, "local": "loja", "tipo": "SAIDA", "quantidade": 3})
        movimentacao_process.registrar({"produto_id": 2, "local": "deposito", "tipo": "ENTRADA", "quantidade": 10})
        movimentacao_process.transferir({"produto_id": 2, "origem": "deposito", "destino": "loja", "quantidade": 4})
        movimentacao_process.contar_inventario({"produto_id": 1, "local": "deposito", "quantidade_contada": 1})
        self.assertEqual(movimentacao_process.auditar(), [])


class TestProduto(BaseTeste):
    DADOS = {"sku": "SKU-TESTE", "nome": "CIMENTO CP II 50KG", "unidade": "saco",
             "estoque_minimo": 20, "estoque_maximo": 100}

    def test_criar_produto_nasce_zerado(self):
        p = produto_process.criar(self.DADOS)
        self.assertEqual(p["saldo_total"], 0)
        self.assertEqual(p["status"], "ZERADO")

    def test_sku_duplicado(self):
        produto_process.criar(self.DADOS)
        with self.assertRaises(RegraDeNegocioError):
            produto_process.criar(self.DADOS)

    def test_maximo_menor_que_minimo(self):
        with self.assertRaises(RegraDeNegocioError):
            produto_process.criar({**self.DADOS, "estoque_minimo": 50, "estoque_maximo": 10})

    def test_status_baixo_normal_excesso(self):
        p = produto_process.criar(self.DADOS)
        pid = p["produto_id"]
        mov = lambda q: movimentacao_process.registrar(
            {"produto_id": pid, "local": "deposito", "tipo": "ENTRADA", "quantidade": q})
        mov(15)
        self.assertEqual(produto_process.obter(pid)["status"], "BAIXO")
        mov(30)
        self.assertEqual(produto_process.obter(pid)["status"], "NORMAL")
        mov(100)
        self.assertEqual(produto_process.obter(pid)["status"], "EXCESSO")

    def test_desativar_nao_apaga_e_bloqueia_movimentacao(self):
        produto_process.desativar(1)
        self.assertNotIn(1, [p["produto_id"] for p in produto_process.listar()])
        self.assertIn(1, [p["produto_id"] for p in produto_process.listar(incluir_desativados=True)])
        with self.assertRaises(RegraDeNegocioError):
            movimentacao_process.registrar(
                {"produto_id": 1, "local": "loja", "tipo": "ENTRADA", "quantidade": 1})

    def test_busca_por_nome_ou_sku(self):
        self.assertTrue(len(produto_process.listar(busca="BICA")) > 0)
        self.assertEqual(len(produto_process.listar(busca="SKU-0001")), 1)


class TestColaboradores(BaseTeste):
    """Cadastro de colaboradores/perfis (tela do administrador)."""

    DADOS = {"usuario": "maria", "nome_completo": "Maria da Silva",
             "cpf": "529.982.247-25", "telefone": "(11) 91234-5678",
             "email": "Maria@Empresa.com", "perfil": "vendedor"}

    def _admin(self):
        return auth_process.autenticar({"usuario": "admin", "senha": "admin123"})["usuario_id"]

    def test_criar_gera_senha_provisoria_que_autentica(self):
        colaborador, senha = colaborador_process.criar(self.DADOS)
        self.assertEqual(colaborador["usuario_perfil"], "vendedor")
        self.assertEqual(colaborador["usuario_cpf"], "52998224725")
        self.assertEqual(colaborador["usuario_email"], "maria@empresa.com")
        self.assertEqual(colaborador["usuario_telefone"], "11912345678")
        self.assertTrue(colaborador["usuario_senha_provisoria"])
        self.assertNotIn("usuario_senha_hash", colaborador)
        r = auth_process.autenticar({"usuario": "maria", "senha": senha})
        self.assertTrue(r["trocar_senha"])
        self.assertEqual(r["perfil"], "vendedor")

    def test_cpf_invalido_ou_duplicado(self):
        with self.assertRaises(RegraDeNegocioError):
            colaborador_process.criar({**self.DADOS, "cpf": "111.111.111-11"})
        colaborador_process.criar(self.DADOS)
        with self.assertRaises(RegraDeNegocioError):
            colaborador_process.criar({**self.DADOS, "usuario": "outro"})

    def test_campos_obrigatorios_e_formatos(self):
        for campo, ruim in (("nome_completo", ""), ("perfil", "chefe"),
                            ("email", "sem-arroba"), ("telefone", "1234"),
                            ("cpf", "")):
            with self.assertRaises(RegraDeNegocioError, msg=campo):
                colaborador_process.criar({**self.DADOS, campo: ruim})

    def test_usuario_duplicado(self):
        colaborador_process.criar(self.DADOS)
        with self.assertRaises(RegraDeNegocioError):
            colaborador_process.criar({**self.DADOS, "cpf": "11144477735"})

    def test_atualizar_dados(self):
        colaborador, _ = colaborador_process.criar(self.DADOS)
        atualizado = colaborador_process.atualizar(colaborador["usuario_id"], {
            **self.DADOS, "nome_completo": "Maria Souza", "perfil": "gerente"})
        self.assertEqual(atualizado["usuario_nome_completo"], "Maria Souza")
        self.assertEqual(atualizado["usuario_perfil"], "gerente")

    def test_desativar_bloqueia_login(self):
        colaborador, senha = colaborador_process.criar(self.DADOS)
        colaborador_process.definir_ativo(colaborador["usuario_id"], False)
        with self.assertRaises(RegraDeNegocioError):
            auth_process.autenticar({"usuario": "maria", "senha": senha})

    def test_nao_pode_desativar_a_si_mesmo(self):
        with self.assertRaises(RegraDeNegocioError):
            colaborador_process.definir_ativo(self._admin(), False, administrador_id=self._admin())

    def test_resetar_senha_volta_a_pedir_troca(self):
        colaborador, _ = colaborador_process.criar(self.DADOS)
        nova = colaborador_process.resetar_senha(colaborador["usuario_id"])
        r = auth_process.autenticar({"usuario": "maria", "senha": nova})
        self.assertTrue(r["trocar_senha"])

    def test_colaborador_inexistente(self):
        with self.assertRaises(NaoEncontradoError):
            colaborador_process.obter(9999)


class TestClientes(BaseTeste):
    """CRUD de clientes (sem login; CPF/telefone/e-mail validados)."""

    DADOS = {"nome": "João Cliente", "cpf": "529.982.247-25",
             "telefone": "(11) 91234-5678", "email": "Joao@Loja.com",
             "endereco": "Rua A, 10"}

    def test_criar_normaliza_campos(self):
        cliente = cliente_process.criar(self.DADOS)
        self.assertEqual(cliente["cliente_cpf"], "52998224725")
        self.assertEqual(cliente["cliente_email"], "joao@loja.com")
        self.assertEqual(cliente["cliente_telefone"], "11912345678")
        self.assertEqual(cliente["cliente_ativo"], 1)

    def test_campos_opcionais(self):
        cliente = cliente_process.criar({"nome": "Sem Documento"})
        self.assertIsNone(cliente["cliente_cpf"])
        self.assertIsNone(cliente["cliente_telefone"])
        self.assertIsNone(cliente["cliente_email"])

    def test_cpf_duplicado(self):
        cliente_process.criar(self.DADOS)
        with self.assertRaises(RegraDeNegocioError):
            cliente_process.criar({**self.DADOS, "nome": "Outro"})

    def test_campos_invalidos(self):
        for campo, ruim in (("nome", ""), ("cpf", "111.111.111-11"),
                            ("telefone", "1234"), ("email", "sem-arroba")):
            with self.assertRaises(RegraDeNegocioError, msg=campo):
                cliente_process.criar({**self.DADOS, campo: ruim})

    def test_desativar_some_da_lista_padrao(self):
        cliente = cliente_process.criar(self.DADOS)
        cliente_process.definir_ativo(cliente["cliente_id"], False)
        self.assertFalse(any(c["cliente_id"] == cliente["cliente_id"]
                             for c in cliente_process.listar()))
        self.assertTrue(any(c["cliente_id"] == cliente["cliente_id"]
                            for c in cliente_process.listar(incluir_inativos=True)))

    def test_atualizar(self):
        cliente = cliente_process.criar(self.DADOS)
        atualizado = cliente_process.atualizar(cliente["cliente_id"],
                                               {**self.DADOS, "nome": "João Atualizado"})
        self.assertEqual(atualizado["cliente_nome"], "João Atualizado")


class TestFornecedorRepresentantes(BaseTeste):
    """Fornecedor com CNPJ validado e vários representantes."""

    FORNECEDOR = {"nome": "Fornecedor Novo", "cnpj": "11.222.333/0001-81",
                  "telefone": "(11) 3000-1000", "email": "Vendas@Forn.com"}

    def test_criar_normaliza_cnpj_email(self):
        fornecedor = fornecedor_process.criar(self.FORNECEDOR)
        self.assertEqual(fornecedor["fornecedor_cnpj"], "11222333000181")
        self.assertEqual(fornecedor["fornecedor_email"], "vendas@forn.com")
        self.assertEqual(fornecedor["representantes"], [])

    def test_cnpj_invalido(self):
        with self.assertRaises(RegraDeNegocioError):
            fornecedor_process.criar({**self.FORNECEDOR, "cnpj": "11.111.111/1111-11"})

    def test_cnpj_duplicado(self):
        fornecedor_process.criar(self.FORNECEDOR)
        with self.assertRaises(RegraDeNegocioError):
            fornecedor_process.criar({**self.FORNECEDOR, "nome": "Outro"})

    def test_representantes_por_fornecedor(self):
        fornecedor = fornecedor_process.criar(self.FORNECEDOR)
        fid = fornecedor["fornecedor_id"]
        rep = representante_process.criar(fid, {"nome": "Carlos", "contato": "(11) 91234-5678",
                                                "email": "Carlos@Forn.com"})
        self.assertEqual(rep["representante_contato"], "11912345678")
        self.assertEqual(len(fornecedor_process.obter(fid)["representantes"]), 1)

        representante_process.definir_ativo(rep["representante_id"], False)
        self.assertEqual(len(fornecedor_process.obter(fid)["representantes"]), 0)
        self.assertEqual(len(representante_process.listar(fid, incluir_inativos=True)), 1)

    def test_representante_sem_contato_e_valido(self):
        fornecedor = fornecedor_process.criar(self.FORNECEDOR)
        rep = representante_process.criar(fornecedor["fornecedor_id"], {"nome": "Ana"})
        self.assertIsNone(rep["representante_contato"])

    def test_representante_contato_invalido(self):
        fornecedor = fornecedor_process.criar(self.FORNECEDOR)
        with self.assertRaises(RegraDeNegocioError):
            representante_process.criar(fornecedor["fornecedor_id"],
                                        {"nome": "Ana", "contato": "1234"})

    def test_representante_de_fornecedor_inexistente(self):
        with self.assertRaises(NaoEncontradoError):
            representante_process.criar(9999, {"nome": "Ana"})


class TestCustoMedio(BaseTeste):
    """Custo médio ponderado: recalculado a cada entrada com custo."""

    def _produto_zerado(self):
        return produto_process.criar({"sku": "SKU-CUSTO", "nome": "Areia média",
                                      "unidade": "m3"})["produto_id"]

    def test_funcao_pura_de_custo_medio(self):
        from process.custo_process import custo_medio_atual
        # 10 un a 10,00 + 10 un a 20,00 => média 15,00
        self.assertEqual(custo_medio_atual(10, 10, 10, 20), 15)
        # Partindo do zero: custo da entrada
        self.assertEqual(custo_medio_atual(0, 0, 5, 7.5), 7.5)
        # Ponderada: 90 un a 1,00 + 10 un a 6,00 => 1,50
        self.assertEqual(custo_medio_atual(90, 1, 10, 6), 1.5)

    def test_entrada_com_custo_recalcula_produto(self):
        pid = self._produto_zerado()
        movimentacao_process.registrar({"produto_id": pid, "local": "deposito",
                                        "tipo": "ENTRADA", "quantidade": 10, "custo_unit": 8.0})
        self.assertEqual(produto_process.obter(pid)["custo_medio"], 8.0)
        r = movimentacao_process.registrar({"produto_id": pid, "local": "deposito",
                                            "tipo": "ENTRADA", "quantidade": 10, "custo_unit": 12.0})
        self.assertEqual(r["custo_medio"], 10.0)
        produto = produto_process.obter(pid)
        self.assertEqual(produto["custo_medio"], 10.0)
        self.assertEqual(produto["valor_estoque"], 200.0)

    def test_entrada_sem_custo_nao_altera_custo_medio(self):
        pid = self._produto_zerado()
        movimentacao_process.registrar({"produto_id": pid, "local": "deposito",
                                        "tipo": "ENTRADA", "quantidade": 10, "custo_unit": 5.0})
        movimentacao_process.registrar({"produto_id": pid, "local": "deposito",
                                        "tipo": "ENTRADA", "quantidade": 90})
        self.assertEqual(produto_process.obter(pid)["custo_medio"], 5.0)

    def test_custo_em_saida_e_rejeitado(self):
        pid = self._produto_zerado()
        movimentacao_process.registrar({"produto_id": pid, "local": "loja",
                                        "tipo": "ENTRADA", "quantidade": 5, "custo_unit": 1.0})
        with self.assertRaises(RegraDeNegocioError):
            movimentacao_process.registrar({"produto_id": pid, "local": "loja",
                                            "tipo": "SAIDA", "quantidade": 1, "custo_unit": 2.0})

    def test_compra_recalcula_custo_medio(self):
        pid = self._produto_zerado()
        compra_process.registrar({"fornecedor_id": 1, "data": "2026-10-01",
                                  "itens": [{"produto_id": pid, "quantidade": 10, "custo_unit": 30.0}]})
        compra_process.registrar({"fornecedor_id": 1, "data": "2026-10-02",
                                  "itens": [{"produto_id": pid, "quantidade": 30, "custo_unit": 50.0}]})
        self.assertEqual(produto_process.obter(pid)["custo_medio"], 45.0)

    def test_cadastro_com_quantidade_e_valor_gera_saldo_inicial(self):
        produto = produto_process.criar({"sku": "SKU-ABERTURA", "nome": "Brita 1",
                                         "unidade": "m3", "preco_custo": 70.0,
                                         "quantidade_inicial": 20})
        self.assertEqual(produto["saldo_deposito"], 20)
        self.assertEqual(produto["custo_medio"], 70.0)
        self.assertEqual(produto["valor_estoque"], 1400.0)
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_cadastro_com_quantidade_sem_custo_falha(self):
        with self.assertRaises(RegraDeNegocioError):
            produto_process.criar({"sku": "SKU-X", "nome": "X", "quantidade_inicial": 5})



class TestVendas(BaseTeste):
    """Venda baixa estoque, calcula totais e cancelar estorna tudo."""

    def _saldo(self, produto_id, campo="saldo_loja"):
        return produto_process.obter(produto_id)[campo]

    def _venda_simples(self, produto_id=1, quantidade=2, local="loja"):
        return venda_process.registrar({
            "local": local,
            "itens": [{"produto_id": produto_id, "quantidade": quantidade, "preco_unitario": 10.0}]})

    def test_venda_baixa_estoque_e_calcula_total(self):
        antes = self._saldo(1)
        venda = self._venda_simples()
        self.assertEqual(venda["venda_status"], "CONCLUIDA")
        self.assertEqual(venda["venda_total"], 20.0)
        self.assertEqual(self._saldo(1), antes - 2)
        self.assertEqual(len(venda["itens"]), 1)
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_numero_sequencial(self):
        a = self._venda_simples()
        b = self._venda_simples()
        self.assertTrue(a["venda_numero"].startswith("VND-"))
        self.assertNotEqual(a["venda_numero"], b["venda_numero"])

    def test_desconto_do_item_e_da_venda(self):
        venda = venda_process.registrar({"local": "loja", "desconto": 5.0, "itens": [
            {"produto_id": 1, "quantidade": 2, "preco_unitario": 10.0, "desconto_item": 3.0}]})
        # item: 2*10 - 3 = 17; venda: 17 - 5 = 12
        self.assertEqual(venda["itens"][0]["subtotal"], 17.0)
        self.assertEqual(venda["venda_total"], 12.0)

    def test_preco_padrao_vem_do_produto(self):
        produto = produto_process.obter(1)
        venda = venda_process.registrar({"local": "loja",
                                         "itens": [{"produto_id": 1, "quantidade": 1}]})
        self.assertEqual(venda["itens"][0]["preco_unitario"], produto["produto_preco_venda"])

    def test_saldo_insuficiente_bloqueia_e_nao_grava(self):
        antes = len(venda_process.listar())
        with self.assertRaises(RegraDeNegocioError):
            self._venda_simples(quantidade=9999)
        self.assertEqual(len(venda_process.listar()), antes)
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_item_invalido_desfaz_a_venda_inteira(self):
        saldo = self._saldo(1)
        antes = len(venda_process.listar())
        with self.assertRaises(NaoEncontradoError):
            venda_process.registrar({"local": "loja", "itens": [
                {"produto_id": 1, "quantidade": 1, "preco_unitario": 10.0},
                {"produto_id": 9999, "quantidade": 1, "preco_unitario": 10.0}]})
        self.assertEqual(len(venda_process.listar()), antes)
        self.assertEqual(self._saldo(1), saldo)
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_desconto_maior_que_o_total(self):
        with self.assertRaises(RegraDeNegocioError):
            venda_process.registrar({"local": "loja", "desconto": 100.0, "itens": [
                {"produto_id": 1, "quantidade": 1, "preco_unitario": 10.0}]})

    def test_venda_sem_itens(self):
        with self.assertRaises(RegraDeNegocioError):
            venda_process.registrar({"local": "loja", "itens": []})

    def test_cliente_inativo_nao_pode_comprar(self):
        cliente = cliente_process.criar({"nome": "Cliente Inativo"})
        cliente_process.definir_ativo(cliente["cliente_id"], False)
        with self.assertRaises(RegraDeNegocioError):
            venda_process.registrar({"local": "loja", "cliente_id": cliente["cliente_id"],
                                     "itens": [{"produto_id": 1, "quantidade": 1,
                                                "preco_unitario": 10.0}]})

    def test_cancelar_estorna_estoque_e_bloqueia_recancelamento(self):
        saldo = self._saldo(1)
        venda = self._venda_simples(quantidade=3)
        self.assertEqual(self._saldo(1), saldo - 3)
        cancelada = venda_process.cancelar(venda["venda_id"], cancelado_por="admin")
        self.assertEqual(cancelada["venda_status"], "CANCELADA")
        self.assertEqual(self._saldo(1), saldo)
        self.assertEqual(movimentacao_process.auditar(), [])
        with self.assertRaises(RegraDeNegocioError):
            venda_process.cancelar(venda["venda_id"], cancelado_por="admin")

    def test_resumo_ignora_canceladas(self):
        v1 = self._venda_simples()
        venda_process.cancelar(v1["venda_id"], cancelado_por="admin")
        self._venda_simples()
        resumo = venda_process.resumo()
        # A venda cancelada não entra no faturamento.
        self.assertEqual(len(resumo["por_dia"]), 1)
        self.assertEqual(resumo["por_dia"][0]["total_vendas"], 1)
class TestLocais(BaseTeste):
    """Locais (depósito/lojas): cadastro, integração com estoque e proteções."""

    LOJA = {"nome": "Loja Centro", "tipo": "loja", "cnpj": "11.222.333/0001-81",
            "telefone": "(11) 3000-1000", "email": "Centro@QG.com",
            "endereco": "Rua A, 10"}

    def test_seed_e_deposito_unico(self):
        locais = {l["local_codigo"]: l for l in local_process.listar()}
        self.assertEqual(locais["deposito"]["local_tipo"], "deposito")
        self.assertEqual(locais["loja"]["local_tipo"], "loja")
        self.assertEqual(local_process.deposito(), "deposito")

    def test_criar_normaliza_campos_e_gera_codigo(self):
        loja = local_process.criar(self.LOJA)
        self.assertEqual(loja["local_codigo"], "loja-centro")
        self.assertEqual(loja["local_cnpj"], "11222333000181")
        self.assertEqual(loja["local_telefone"], "1130001000")
        self.assertEqual(loja["local_email"], "centro@qg.com")
        self.assertEqual(loja["local_ativo"], 1)
        self.assertEqual(loja["saldo_total"], 0)

    def test_campos_invalidos(self):
        for campo, ruim in (("nome", ""), ("tipo", "fabrica"),
                            ("cnpj", "11.111.111/1111-11"), ("telefone", "1234"),
                            ("email", "sem-arroba")):
            with self.assertRaises(RegraDeNegocioError, msg=campo):
                local_process.criar({**self.LOJA, campo: ruim})

    def test_somente_um_deposito(self):
        with self.assertRaises(RegraDeNegocioError):
            local_process.criar({"nome": "Depósito 2", "tipo": "deposito"})

    def test_deposito_nao_vira_loja(self):
        with self.assertRaises(RegraDeNegocioError):
            local_process.atualizar("deposito", {"nome": "Loja X", "tipo": "loja"})

    def test_codigo_duplicado(self):
        local_process.criar(self.LOJA)
        with self.assertRaises(RegraDeNegocioError):
            local_process.criar({**self.LOJA, "nome": "Loja Centro"})

    def test_fluxo_completo_com_local_novo(self):
        local_process.criar(self.LOJA)
        pid = produto_process.criar({"nome": "Cimento CP II", "preco_venda": 10.0,
                                     "preco_custo": 5.0, "quantidade_inicial": 10})["produto_id"]
        movimentacao_process.transferir(
            {"produto_id": pid, "origem": "deposito", "destino": "loja-centro", "quantidade": 4})
        produto = produto_process.obter(pid)
        self.assertEqual(produto["saldos"]["deposito"], 6)
        self.assertEqual(produto["saldos"]["loja-centro"], 4)

        venda = venda_process.registrar({"local": "loja-centro", "itens": [
            {"produto_id": pid, "quantidade": 3}]})
        self.assertEqual(venda["venda_local"], "loja-centro")
        self.assertEqual(produto_process.obter(pid)["saldos"]["loja-centro"], 1)

        venda_process.cancelar(venda["venda_id"], cancelado_por="admin")
        self.assertEqual(produto_process.obter(pid)["saldos"]["loja-centro"], 4)
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_venda_em_local_sem_saldo_e_bloqueada(self):
        local_process.criar(self.LOJA)
        pid = produto_process.criar({"nome": "Areia", "preco_venda": 10.0,
                                     "preco_custo": 5.0, "quantidade_inicial": 10})["produto_id"]
        with self.assertRaises(RegraDeNegocioError):
            venda_process.registrar({"local": "loja-centro",
                                     "itens": [{"produto_id": pid, "quantidade": 1}]})

    def test_local_inexistente_ou_inativo_e_rejeitado(self):
        with self.assertRaises(NaoEncontradoError):
            movimentacao_process.registrar(
                {"produto_id": 1, "local": "loja-fantasma", "tipo": "ENTRADA", "quantidade": 1})
        local_process.criar(self.LOJA)
        local_process.definir_ativo("loja-centro", False)
        with self.assertRaises(RegraDeNegocioError):
            movimentacao_process.registrar(
                {"produto_id": 1, "local": "loja-centro", "tipo": "ENTRADA", "quantidade": 1})

    def test_compras_entram_no_deposito_por_padrao(self):
        antes = produto_process.obter(1)["saldos"].get("deposito", 0)
        compra_process.registrar({"fornecedor_id": 1, "data": "2026-10-01",
                                  "itens": [{"produto_id": 1, "quantidade": 3, "custo_unit": 1.0}]})
        self.assertEqual(produto_process.obter(1)["saldos"]["deposito"], antes + 3)

    def test_renomear_nome_mantem_codigo(self):
        local_process.criar(self.LOJA)
        renomeado = local_process.atualizar("loja-centro", {**self.LOJA, "nome": "Loja Sul"})
        self.assertEqual(renomeado["local_nome"], "Loja Sul")
        self.assertEqual(renomeado["local_codigo"], "loja-centro")  # código é estável

    def test_renomear_codigo_atualiza_referencias(self):
        local_process.criar(self.LOJA)
        pid = produto_process.criar({"nome": "Brita", "preco_venda": 1.0,
                                     "preco_custo": 1.0, "quantidade_inicial": 5})["produto_id"]
        movimentacao_process.transferir(
            {"produto_id": pid, "origem": "deposito", "destino": "loja-centro", "quantidade": 2})
        renomeado = local_process.atualizar(
            "loja-centro", {**self.LOJA, "nome": "Loja Sul", "codigo": "loja-sul"})
        self.assertEqual(renomeado["local_codigo"], "loja-sul")
        self.assertEqual(produto_process.obter(pid)["saldos"]["loja-sul"], 2)
        self.assertNotIn("loja-centro", produto_process.obter(pid)["saldos"])
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_nao_exclui_nem_desativa_local_com_historico(self):
        local_process.criar(self.LOJA)
        pid = produto_process.criar({"nome": "Telha", "preco_venda": 1.0,
                                     "preco_custo": 1.0, "quantidade_inicial": 5})["produto_id"]
        movimentacao_process.transferir(
            {"produto_id": pid, "origem": "deposito", "destino": "loja-centro", "quantidade": 2})
        with self.assertRaises(RegraDeNegocioError):
            local_process.excluir("loja-centro")
        with self.assertRaises(RegraDeNegocioError):
            local_process.definir_ativo("loja-centro", False)
        # Sem saldo, desativa (o histórico fica preservado).
        movimentacao_process.transferir(
            {"produto_id": pid, "origem": "loja-centro", "destino": "deposito", "quantidade": 2})
        local_process.definir_ativo("loja-centro", False)
        self.assertNotIn("loja-centro", [l["local_codigo"] for l in local_process.listar()])
        self.assertIn("loja-centro", [l["local_codigo"] for l in local_process.listar(True)])

    def test_exclui_local_sem_uso(self):
        local_process.criar(self.LOJA)
        local_process.excluir("loja-centro")
        with self.assertRaises(NaoEncontradoError):
            local_process.obter("loja-centro")

    def test_produto_novo_ganha_linha_em_todos_os_locais(self):
        local_process.criar(self.LOJA)
        pid = produto_process.criar({"nome": "Prego", "preco_custo": 1.0, "quantidade_inicial": 2})["produto_id"]
        saldos = produto_process.obter(pid)["saldos"]
        self.assertEqual(saldos, {"deposito": 2})


class TestCompraEAlertas(BaseTeste):
    def test_compra_gera_entradas_no_estoque(self):
        antes = produto_process.obter(1)["saldo_deposito"]
        c = compra_process.registrar({
            "fornecedor_id": 1, "data": "2026-10-01", "nota_fiscal": "999",
            "itens": [{"produto_id": 1, "quantidade": 10, "custo_unit": 50.0}]})
        self.assertEqual(c["valor_total"], 500.0)
        self.assertEqual(produto_process.obter(1)["saldo_deposito"], antes + 10)
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_compra_com_item_invalido_nao_grava_nada(self):
        antes = len(compra_process.listar())
        with self.assertRaises(NaoEncontradoError):
            compra_process.registrar({
                "fornecedor_id": 1, "data": "2026-10-01",
                "itens": [{"produto_id": 1, "quantidade": 5, "custo_unit": 1.0},
                          {"produto_id": 9999, "quantidade": 5, "custo_unit": 1.0}]})
        self.assertEqual(len(compra_process.listar()), antes)
        self.assertEqual(movimentacao_process.auditar(), [])

    def test_compra_sem_itens(self):
        with self.assertRaises(RegraDeNegocioError):
            compra_process.registrar({"fornecedor_id": 1, "data": "2026-10-01", "itens": []})

    def test_alertas_e_lista_de_compras(self):
        movimentacao_process.contar_inventario({"produto_id": 1, "local": "deposito", "quantidade_contada": 0})
        movimentacao_process.contar_inventario({"produto_id": 1, "local": "loja", "quantidade_contada": 0})
        alertas = alerta_process.listar_alertas()
        self.assertIn(1, [p["produto_id"] for p in alertas["zerados"]])
        compras = alerta_process.lista_de_compras()
        item = next(c for c in compras if c["produto_id"] == 1)
        self.assertEqual(item["quantidade_sugerida"], 20)


if __name__ == "__main__":
    unittest.main()
