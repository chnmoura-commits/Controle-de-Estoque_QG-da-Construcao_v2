"""Administração de usuários da API — uso pela linha de comando.

Permite criar, listar, alterar senha, ativar/desativar e remover usuários sem
mexer no banco à mão. As senhas nunca aparecem na tela nem no histórico do shell
(são lidas com getpass) e são gravadas sempre como hash PBKDF2.

Exemplos:
    python usuarios_admin.py listar
    python usuarios_admin.py criar
    python usuarios_admin.py criar --provisoria novo_admin
    python usuarios_admin.py resetar-senha admin
    python usuarios_admin.py senha admin
    python usuarios_admin.py desativar operador
    python usuarios_admin.py ativar operador
    python usuarios_admin.py remover operador

Respeita a variável de ambiente ESTOQUE_DB (mesma do restante do sistema).
"""
import argparse
import getpass
import sys

from database import conexao
from repositories import usuario_repository as repo
from security import gerar_hash, gerar_senha_provisoria

# Usuários de teste de versões antigas, que podem existir em bancos já migrados.
USUARIOS_DE_TESTE = ("admin", "gerente", "operador")

SENHA_MINIMA = 8


def _pedir_senha(mensagem="Senha: "):
    """Lê a senha duas vezes, sem eco, e valida o tamanho mínimo."""
    senha = getpass.getpass(mensagem)
    if len(senha) < SENHA_MINIMA:
        sys.exit(f"Erro: a senha deve ter ao menos {SENHA_MINIMA} caracteres.")
    if senha != getpass.getpass("Confirme a senha: "):
        sys.exit("Erro: as senhas não conferem.")
    return senha


def _existe(conn, usuario):
    return repo.obter_por_usuario(conn, usuario) is not None


# --- Comandos ---------------------------------------------------------------

def listar():
    with conexao() as conn:
        usuarios = repo.listar(conn)
    if not usuarios:
        print("Nenhum usuário cadastrado.")
        return
    print(f"{'ID':>4}  {'USUÁRIO':<20} {'ATIVO':<6} {'SENHA':<12} CRIADO EM")
    for u in usuarios:
        ativo = "sim" if u["usuario_ativo"] else "não"
        senha_estado = "provisória" if u.get("usuario_senha_provisoria") else "definida"
        print(f"{u['usuario_id']:>4}  {u['usuario_nome']:<20} {ativo:<6} {senha_estado:<12} {u['usuario_criado_em']}")


def criar(usuario=None, provisoria=False):
    usuario = (usuario or input("Novo usuário: ")).strip()
    if not usuario:
        sys.exit("Erro: o nome do usuário não pode ser vazio.")
    with conexao() as conn:
        if _existe(conn, usuario):
            sys.exit(f"Erro: já existe um usuário chamado '{usuario}'.")
        if provisoria:
            # Senha aleatória mostrada uma única vez; troca forçada no 1º acesso.
            gerada = gerar_senha_provisoria()
            repo.inserir(conn, usuario, gerar_hash(gerada), senha_provisoria=1)
            print(f"Usuário '{usuario}' criado com senha provisória: {gerada}")
            print("(anote; será exigida a troca no primeiro acesso)")
        else:
            senha = _pedir_senha()
            repo.inserir(conn, usuario, gerar_hash(senha))
            print(f"Usuário '{usuario}' criado.")


def senha(usuario):
    with conexao() as conn:
        registro = repo.obter_por_usuario(conn, usuario)
        if registro is None:
            sys.exit(f"Erro: usuário '{usuario}' não encontrado.")
        nova = _pedir_senha("Nova senha: ")
        repo.atualizar_senha(conn, registro["usuario_id"], gerar_hash(nova))
    print(f"Senha de '{usuario}' atualizada.")


def resetar_senha(usuario):
    """Define uma senha provisória aleatória (para quando o admin esquecer)."""
    with conexao() as conn:
        registro = repo.obter_por_usuario(conn, usuario)
        if registro is None:
            sys.exit(f"Erro: usuário '{usuario}' não encontrado.")
        gerada = gerar_senha_provisoria()
        conn.execute(
            "UPDATE usuarios SET usuario_senha_hash = ?, usuario_senha_provisoria = 1 "
            "WHERE usuario_id = ?",
            (gerar_hash(gerada), registro["usuario_id"]),
        )
    print(f"Nova senha provisória de '{usuario}': {gerada}")
    print("(o usuário será obrigado a trocá-la no próximo acesso)")


def _definir_ativo(usuario, ativo):
    with conexao() as conn:
        registro = repo.obter_por_usuario(conn, usuario)
        if registro is None:
            sys.exit(f"Erro: usuário '{usuario}' não encontrado.")
        repo.definir_ativo(conn, registro["usuario_id"], ativo)
    print(f"Usuário '{usuario}' {'ativado' if ativo else 'desativado'}.")


def ativar(usuario):
    _definir_ativo(usuario, True)


def desativar(usuario):
    _definir_ativo(usuario, False)


def remover(usuario, forcar=False):
    with conexao() as conn:
        registro = repo.obter_por_usuario(conn, usuario)
        if registro is None:
            sys.exit(f"Erro: usuário '{usuario}' não encontrado.")
        if not forcar and not _confirmar(f"Remover definitivamente o usuário '{usuario}'?"):
            sys.exit("Operação cancelada.")
        repo.remover(conn, registro["usuario_id"])
    print(f"Usuário '{usuario}' removido.")


def remover_teste(forcar=False):
    """Remove os usuários de teste criados pela migração (se existirem)."""
    removidos = []
    with conexao() as conn:
        existentes = [u for u in USUARIOS_DE_TESTE if _existe(conn, u)]
        if not existentes:
            print("Nenhum usuário de teste encontrado. Nada a fazer.")
            return
        print("Usuários de teste encontrados:", ", ".join(existentes))
        if not forcar and not _confirmar("Remover todos eles?"):
            sys.exit("Operação cancelada.")
        for usuario in existentes:
            registro = repo.obter_por_usuario(conn, usuario)
            repo.remover(conn, registro["usuario_id"])
            removidos.append(usuario)
    print("Removidos:", ", ".join(removidos))


def _confirmar(pergunta):
    return input(f"{pergunta} [s/N] ").strip().lower() in ("s", "sim", "y", "yes")


def principal(argv=None):
    parser = argparse.ArgumentParser(
        description="Administração de usuários da API de Controle de Estoque.")
    parser.add_argument("--banco", help="caminho do banco (sobrescreve ESTOQUE_DB)")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("listar", help="lista os usuários")

    p_criar = sub.add_parser("criar", help="cria um novo usuário")
    p_criar.add_argument("usuario", nargs="?", help="nome do usuário (pede se omitido)")
    p_criar.add_argument("--provisoria", action="store_true",
                         help="gera uma senha provisória aleatória e exige troca no 1º acesso")

    p_senha = sub.add_parser("senha", help="altera a senha de um usuário")
    p_senha.add_argument("usuario")

    p_reset = sub.add_parser("resetar-senha",
                             help="gera uma senha provisória aleatória (troca obrigatória no login)")
    p_reset.add_argument("usuario")

    p_ativar = sub.add_parser("ativar", help="reativa um usuário")
    p_ativar.add_argument("usuario")

    p_desativar = sub.add_parser("desativar", help="desativa um usuário (sem apagar)")
    p_desativar.add_argument("usuario")

    p_remover = sub.add_parser("remover", help="remove um usuário")
    p_remover.add_argument("usuario")
    p_remover.add_argument("-f", "--forcar", action="store_true", help="não pede confirmação")

    p_rem_teste = sub.add_parser("remover-teste", help="remove os usuários de teste da migração")
    p_rem_teste.add_argument("-f", "--forcar", action="store_true", help="não pede confirmação")

    args = parser.parse_args(argv)

    if args.banco:
        import database
        database.DB_PATH = args.banco

    import database
    print(f"Banco: {database.DB_PATH}\n")

    if args.comando == "listar":
        listar()
    elif args.comando == "criar":
        criar(args.usuario, args.provisoria)
    elif args.comando == "senha":
        senha(args.usuario)
    elif args.comando == "resetar-senha":
        resetar_senha(args.usuario)
    elif args.comando == "ativar":
        ativar(args.usuario)
    elif args.comando == "desativar":
        desativar(args.usuario)
    elif args.comando == "remover":
        remover(args.usuario, args.forcar)
    elif args.comando == "remover-teste":
        remover_teste(args.forcar)


if __name__ == "__main__":
    principal()
