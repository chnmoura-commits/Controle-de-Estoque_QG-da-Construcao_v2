from fastapi import APIRouter, Depends

from controllers.dependencias import exigir_perfil
from models.schemas import LocalIn
from process import local_process

router = APIRouter(prefix="/locais", tags=["Locais"])

# Consultar: qualquer usuário autenticado. Cadastrar/editar/excluir: admin/gerente.
GESTAO = [Depends(exigir_perfil("admin", "gerente"))]


@router.get("")
def listar(incluir_inativos: bool = False):
    return local_process.listar(incluir_inativos)


@router.get("/{local_codigo}")
def obter(local_codigo: str):
    return local_process.obter(local_codigo)


@router.post("", status_code=201, dependencies=GESTAO)
def criar(corpo: LocalIn):
    return local_process.criar(corpo.model_dump())


@router.put("/{local_codigo}", dependencies=GESTAO)
def atualizar(local_codigo: str, corpo: LocalIn):
    return local_process.atualizar(local_codigo, corpo.model_dump())


@router.post("/{local_codigo}/desativar", dependencies=GESTAO)
def desativar(local_codigo: str):
    return local_process.definir_ativo(local_codigo, False)


@router.post("/{local_codigo}/reativar", dependencies=GESTAO)
def reativar(local_codigo: str):
    return local_process.definir_ativo(local_codigo, True)


@router.delete("/{local_codigo}", dependencies=GESTAO)
def excluir(local_codigo: str):
    return local_process.excluir(local_codigo)
