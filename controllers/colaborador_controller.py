from typing import Optional

from fastapi import APIRouter, Depends

from controllers.dependencias import exigir_perfil, usuario_autenticado
from models.schemas import AtivoIn, ColaboradorCriarIn, ColaboradorIn
from process import colaborador_process

# Cadastro de colaboradores: exclusivo do administrador (checado no backend).
router = APIRouter(prefix="/colaboradores", tags=["Colaboradores"],
                   dependencies=[Depends(exigir_perfil("admin"))])


@router.get("")
def listar(busca: Optional[str] = None):
    return colaborador_process.listar(busca)


@router.get("/{colaborador_id}")
def obter(colaborador_id: int):
    return colaborador_process.obter(colaborador_id)


@router.post("", status_code=201)
def criar(corpo: ColaboradorCriarIn):
    """Cria o colaborador e devolve a senha provisória (mostrada só aqui)."""
    colaborador, senha_provisoria = colaborador_process.criar(corpo.model_dump())
    return {
        "colaborador": colaborador,
        "senha_provisoria": senha_provisoria,
        "mensagem": ("Colaborador criado. Repasse a senha provisória: "
                     "ela deve ser trocada no primeiro acesso."),
    }


@router.put("/{colaborador_id}")
def atualizar(colaborador_id: int, corpo: ColaboradorIn):
    return colaborador_process.atualizar(colaborador_id, corpo.model_dump())


@router.post("/{colaborador_id}/ativo")
def definir_ativo(colaborador_id: int, corpo: AtivoIn,
                  usuario=Depends(usuario_autenticado)):
    return colaborador_process.definir_ativo(colaborador_id, corpo.ativo,
                                             administrador_id=usuario["sub"])


@router.post("/{colaborador_id}/resetar-senha")
def resetar_senha(colaborador_id: int):
    senha = colaborador_process.resetar_senha(colaborador_id)
    return {"senha_provisoria": senha,
            "mensagem": "Nova senha provisória gerada. Ela deve ser trocada no próximo acesso."}


@router.delete("/{colaborador_id}")
def remover(colaborador_id: int, usuario=Depends(usuario_autenticado)):
    return colaborador_process.remover(colaborador_id, administrador_id=usuario["sub"])
