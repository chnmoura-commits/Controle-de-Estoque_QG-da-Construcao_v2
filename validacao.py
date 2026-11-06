"""Validações de dados cadastrais brasileiros (CPF, CNPJ, telefone e e-mail).

Módulo sem dependência do framework web nem do banco, para poder ser usado em
qualquer camada e testado isoladamente. As funções `limpar_*` só normalizam e as
`validar_*` normalizam e conferem o formato; em caso de problema lançam
`RegraDeNegocioError` (HTTP 422) com mensagem em português.

Decisão do projeto: a validação roda no `process` (não no Pydantic), para que as
mensagens de erro fiquem consistentes com o restante do sistema.
"""
import re

from exceptions import exigir

# DDDs válidos no Brasil (ANATEL) — atualização de 2024.
_DDDS_VALIDOS = {
    11, 12, 13, 14, 15, 16, 17, 18, 19,        # SP
    21, 22, 24, 27, 28,                        # RJ/ES
    31, 32, 33, 34, 35, 37, 38,                # MG
    41, 42, 43, 44, 45, 46, 47, 48, 49,        # PR/SC/RS
    51, 53, 54, 55,                            # RS
    61, 62, 63, 64, 65, 66, 67, 68, 69,        # DF/GO/TO/MT/MS/AC/RO
    71, 73, 74, 75, 77, 79,                    # BA/SE
    81, 82, 83, 84, 85, 86, 87, 88, 89,        # PE/AL/PB/RN/CE/PI
    91, 92, 93, 94, 95, 96, 97, 98, 99,        # PA/AM/RR/AP/MA
}

_REGEX_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


def apenas_digitos(valor) -> str:
    """Remove máscara: mantém somente os dígitos do valor informado."""
    return re.sub(r"\D", "", str(valor or ""))


# --- CPF --------------------------------------------------------------------

def limpar_cpf(valor) -> str:
    return apenas_digitos(valor)


def _digitos_verificadores_cpf(primeiros: str) -> str:
    """Calcula os dois dígitos verificadores a partir dos 9 primeiros dígitos."""
    soma = sum(int(d) * peso for d, peso in zip(primeiros, range(10, 1, -1)))
    resto = (soma * 10) % 11
    primeiro = 0 if resto == 10 else resto
    soma = sum(int(d) * peso for d, peso in zip(primeiros + str(primeiro), range(11, 1, -1)))
    resto = (soma * 10) % 11
    segundo = 0 if resto == 10 else resto
    return f"{primeiro}{segundo}"


def cpf_valido(valor) -> bool:
    """Confere formato e dígitos verificadores do CPF (algoritmo oficial)."""
    cpf = limpar_cpf(valor)
    if len(cpf) != 11 or len(set(cpf)) == 1:   # 000..., 111... são inválidos
        return False
    return cpf[-2:] == _digitos_verificadores_cpf(cpf[:9])


def validar_cpf(valor, campo="CPF", obrigatorio=True) -> str:
    """Devolve o CPF só com dígitos; lança erro se inválido.

    Com `obrigatorio=False`, valor vazio é aceito e devolvido como None
    (caso dos campos opcionais de cliente e representante).
    """
    if not obrigatorio and valor in (None, ""):
        return None
    exigir(valor not in (None, ""), f"O {campo} é obrigatório.")
    cpf = limpar_cpf(valor)
    exigir(len(cpf) == 11, f"O {campo} deve ter 11 dígitos.")
    exigir(cpf_valido(cpf), f"O {campo} informado é inválido.")
    return cpf


# --- CNPJ -------------------------------------------------------------------

def limpar_cnpj(valor) -> str:
    return apenas_digitos(valor)


def _digito_verificador_cnpj(parcial: str) -> str:
    """Calcula um dígito verificador do CNPJ (pesos 2..9 recomeçando)."""
    soma = 0
    peso = 2
    for digito in reversed(parcial):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def cnpj_valido(valor) -> bool:
    """Confere formato e dígitos verificadores do CNPJ (algoritmo oficial)."""
    cnpj = limpar_cnpj(valor)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False
    primeiro = _digito_verificador_cnpj(cnpj[:12])
    segundo = _digito_verificador_cnpj(cnpj[:12] + primeiro)
    return cnpj[-2:] == f"{primeiro}{segundo}"


def validar_cnpj(valor, campo="CNPJ", obrigatorio=True) -> str:
    """Devolve o CNPJ só com dígitos; lança erro se inválido.

    Com `obrigatorio=False`, valor vazio é aceito e devolvido como None.
    """
    if not obrigatorio and valor in (None, ""):
        return None
    exigir(valor not in (None, ""), f"O {campo} é obrigatório.")
    cnpj = limpar_cnpj(valor)
    exigir(len(cnpj) == 14, f"O {campo} deve ter 14 dígitos.")
    exigir(cnpj_valido(cnpj), f"O {campo} informado é inválido.")
    return cnpj


# --- Telefone ---------------------------------------------------------------

def limpar_telefone(valor) -> str:
    """Remove máscara e o prefixo internacional 55, quando houver."""
    digitos = apenas_digitos(valor)
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    return digitos


def telefone_valido(valor) -> bool:
    """Celular (11 dígitos, com 9 após o DDD) ou fixo (10 dígitos), DDD válido."""
    telefone = limpar_telefone(valor)
    if len(telefone) not in (10, 11):
        return False
    if int(telefone[:2]) not in _DDDS_VALIDOS:
        return False
    if telefone[2] in ("0", "1"):              # não existe número começando por 0/1
        return False
    if len(telefone) == 11 and telefone[2] != "9":
        return False
    if len(set(telefone)) == 1:                # 00000000000, 11111111111...
        return False
    return True


def validar_telefone(valor, campo="Telefone", obrigatorio=True) -> str:
    """Devolve o telefone só com dígitos (DDD + número); lança erro se inválido.

    Com `obrigatorio=False`, valor vazio é aceito e devolvido como None.
    """
    if not obrigatorio and valor in (None, ""):
        return None
    exigir(valor not in (None, ""), f"O {campo} é obrigatório.")
    exigir(telefone_valido(valor),
           f"O {campo} deve ser um telefone brasileiro válido, com DDD "
           "(10 dígitos para fixo ou 11 para celular).")
    return limpar_telefone(valor)


# --- E-mail -----------------------------------------------------------------

def email_valido(valor) -> bool:
    return bool(_REGEX_EMAIL.match(str(valor or "").strip()))


def validar_email(valor, campo="e-mail", obrigatorio=True) -> str:
    """Devolve o e-mail em minúsculas, sem espaços; lança erro se inválido.

    Com `obrigatorio=False`, valor vazio é aceito e devolvido como None.
    """
    if not obrigatorio and valor in (None, ""):
        return None
    exigir(valor not in (None, ""), f"O {campo} é obrigatório.")
    email = str(valor).strip().lower()
    exigir(len(email) <= 254 and email_valido(email), f"O {campo} informado é inválido.")
    return email
