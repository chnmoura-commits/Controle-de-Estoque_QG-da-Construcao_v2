from typing import Optional

from fastapi import APIRouter, Depends

from controllers.dependencias import exigir_perfil
from models.schemas import AtivoIn, ClienteIn
from process import cliente_process

router = APIRouter(prefix="/clientes", tags=["Clientes"])

# Consulta: qualquer perfil. Cadastro/edição/desativação: admin ou gerente.
GESTAO = [Depends(exigir_perfil("admin", "gerente"))]


@router.get("")
def listar(busca: Optional[str] = None, incluir_inativos: bool = False):
    return cliente_process.listar(busca, incluir_inativos)


@router.get("/{cliente_id}")
def obter(cliente_id: int):
    return cliente_process.obter(cliente_id)


@router.post("", status_code=201, dependencies=GESTAO)
def criar(corpo: ClienteIn):
    return cliente_process.criar(corpo.model_dump())


@router.put("/{cliente_id}", dependencies=GESTAO)
def atualizar(cliente_id: int, corpo: ClienteIn):
    return cliente_process.atualizar(cliente_id, corpo.model_dump())


@router.post("/{cliente_id}/ativo", dependencies=GESTAO)
def definir_ativo(cliente_id: int, corpo: AtivoIn):
    return cliente_process.definir_ativo(cliente_id, corpo.ativo)
