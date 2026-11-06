"""Testes das validações de CPF, CNPJ, telefone e e-mail (sem banco)."""
import unittest

from exceptions import RegraDeNegocioError
from validacao import (cnpj_valido, cpf_valido, email_valido, limpar_telefone,
                       telefone_valido, validar_cnpj, validar_cpf,
                       validar_email, validar_telefone)


class TestCPF(unittest.TestCase):
    VALIDOS = ("52998224725", "529.982.247-25", "11144477735", "12345678909")
    INVALIDOS = (
        "52998224724",        # dígito verificador errado
        "11111111111",        # sequência repetida
        "00000000000",
        "1234567890",         # 10 dígitos
        "123456789012",       # 12 dígitos
        "5299822472a",        # letra
    )

    def test_cpfs_validos(self):
        for cpf in self.VALIDOS:
            self.assertTrue(cpf_valido(cpf), cpf)

    def test_cpfs_invalidos(self):
        for cpf in self.INVALIDOS:
            self.assertFalse(cpf_valido(cpf), cpf)

    def test_validar_cpf_devolve_so_digitos(self):
        self.assertEqual(validar_cpf("529.982.247-25"), "52998224725")

    def test_validar_cpf_vazio_ou_invalido_pede_erro(self):
        with self.assertRaises(RegraDeNegocioError):
            validar_cpf("")
        with self.assertRaises(RegraDeNegocioError):
            validar_cpf(None)
        with self.assertRaises(RegraDeNegocioError):
            validar_cpf("11111111111")

    def test_mensagem_do_erro_cita_o_campo(self):
        with self.assertRaises(RegraDeNegocioError) as ctx:
            validar_cpf("123", campo="CPF do colaborador")
        self.assertIn("CPF do colaborador", str(ctx.exception))


class TestCNPJ(unittest.TestCase):
    VALIDOS = ("11222333000181", "11.222.333/0001-81", "11444777000161")
    INVALIDOS = ("11222333000180", "00000000000000", "11111111111111",
                 "1122233300018", "112223330001811")

    def test_cnpjs_validos(self):
        for cnpj in self.VALIDOS:
            self.assertTrue(cnpj_valido(cnpj), cnpj)

    def test_cnpjs_invalidos(self):
        for cnpj in self.INVALIDOS:
            self.assertFalse(cnpj_valido(cnpj), cnpj)

    def test_validar_cnpj_normaliza(self):
        self.assertEqual(validar_cnpj("11.222.333/0001-81"), "11222333000181")

    def test_validar_cnpj_invalido(self):
        with self.assertRaises(RegraDeNegocioError):
            validar_cnpj("11.222.333/0001-82")


class TestTelefone(unittest.TestCase):
    def test_fixo_e_celular_validos(self):
        self.assertTrue(telefone_valido("(11) 4001-1122"))
        self.assertTrue(telefone_valido("11912345678"))
        self.assertTrue(telefone_valido("+55 11 91234-5678"))

    def test_invalidos(self):
        # 9 dígitos, DDD inválido (00), curto, longo, DDD repetido e número começando por 1.
        for telefone in ("", None, "1234", "119123456", "00912345678",
                         "1191234567891", "119123456789", "99999999999", "11112345678"):
            self.assertFalse(telefone_valido(telefone), telefone)

    def test_celular_precisa_do_9(self):
        self.assertFalse(telefone_valido("11812345678"))
        self.assertTrue(telefone_valido("11912345678"))

    def test_normalizacao_remove_mascara_e_prefixo_55(self):
        self.assertEqual(limpar_telefone("(11) 91234-5678"), "11912345678")
        self.assertEqual(limpar_telefone("+55 (11) 4001-1122"), "1140011122")

    def test_validar_telefone_invalido(self):
        with self.assertRaises(RegraDeNegocioError):
            validar_telefone("00 0000-0000")


class TestEmail(unittest.TestCase):
    def test_validos(self):
        for email in ("a@b.com", "joao.silva@empresa.com.br", "x+y@sub.dominio.io"):
            self.assertTrue(email_valido(email), email)

    def test_invalidos(self):
        for email in ("", None, "sem-arroba", "a@b", "a@.com", "a b@c.com", "@b.com"):
            self.assertFalse(email_valido(email), email)

    def test_validar_email_normaliza(self):
        self.assertEqual(validar_email("  Joao@Empresa.COM "), "joao@empresa.com")

    def test_validar_email_invalido(self):
        with self.assertRaises(RegraDeNegocioError):
            validar_email("sem-arroba")


if __name__ == "__main__":
    unittest.main()
