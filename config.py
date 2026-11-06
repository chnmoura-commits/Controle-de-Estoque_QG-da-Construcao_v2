"""Configuração central do sistema, lida de variáveis de ambiente.

Nenhum valor sensível ou específico de máquina deve ficar no código: tudo o
que pode mudar entre ambientes (CORS, parâmetros de sessão) é definido aqui e
pode ser sobrescrito por variáveis de ambiente.
"""
import os
import secrets
# Origens permitidas no CORS. Padrão: o servidor estático do frontend local.
# Ex.: ESTOQUE_CORS_ORIGINS="https://estoque.exemplo.com,https://admin.exemplo.com"
CORS_ORIGINS = [
    origem.strip()
    for origem in os.getenv(
        "ESTOQUE_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origem.strip()
]

# Quantidade de iterações do PBKDF2 para o hash de senha.
SENHA_ITERACOES = int(os.getenv("ESTOQUE_SENHA_ITERACOES", "120000"))


# Segredo usado para assinar os tokens de sessão (JWT HS256).
# Em produção DEVE ser definido por variável de ambiente com um valor longo e
# aleatório (ex.: `python -c "import secrets; print(secrets.token_urlsafe(48))"`).
# O padrão existe apenas para desenvolvimento local e é trocado a cada processo
# quando não informado, evitando que um segredo fixo vaze para produção.
JWT_SEGREDO = os.getenv("ESTOQUE_JWT_SEGREDO") or secrets.token_urlsafe(48)

# Tempo de validade do token de sessão, em minutos (padrão: 8 horas).
JWT_EXPIRACAO_MINUTOS = int(os.getenv("ESTOQUE_JWT_EXPIRACAO_MINUTOS", "480"))


