from typing import Optional

from fastapi import APIRouter, Depends

from controllers.dependencias import exigir_perfil
from models.schemas import AtivoIn, FornecedorIn, RepresentanteIn
from process import fornecedor_process, representante_process

router = APIRouter(prefix="/fornecedores", tags=["Fornecedores"])

# Consulta: qualquer perfil. Cadastro/edição: admin ou gerente.
GESTAO = [Depends(exigir_perfil("admin", "gerente"))]


@router.get("")
def listar(busca: Optional[str] = None):
    return fornecedor_process.listar(busca)


# --- Representantes (rotas antes de /{fornecedor_id} para não colidir) ------

@router.put("/representantes/{representante_id}", dependencies=GESTAO)
def atualizar_representante(representante_id: int, corpo: RepresentanteIn):
    return representante_process.atualizar(representante_id, corpo.model_dump())


@router.post("/representantes/{representante_id}/ativo", dependencies=GESTAO)
def definir_ativo_representante(representante_id: int, corpo: AtivoIn):
    return representante_process.definir_ativo(representante_id, corpo.ativo)


@router.get("/{fornecedor_id}/representantes")
def listar_representantes(fornecedor_id: int, incluir_inativos: bool = False):
    return representante_process.listar(fornecedor_id, incluir_inativos)


@router.post("/{fornecedor_id}/representantes", status_code=201, dependencies=GESTAO)
def criar_representante(fornecedor_id: int, corpo: RepresentanteIn):
    return representante_process.criar(fornecedor_id, corpo.model_dump())


# --- Fornecedores ----------------------------------------------------------

@router.get("/{fornecedor_id}")
def obter(fornecedor_id: int):
    return fornecedor_process.obter(fornecedor_id)


@router.post("", status_code=201, dependencies=GESTAO)
def criar(corpo: FornecedorIn):
    return fornecedor_process.criar(corpo.model_dump())


@router.put("/{fornecedor_id}", dependencies=GESTAO)
def atualizar(fornecedor_id: int, corpo: FornecedorIn):
    return fornecedor_process.atualizar(fornecedor_id, corpo.model_dump())
