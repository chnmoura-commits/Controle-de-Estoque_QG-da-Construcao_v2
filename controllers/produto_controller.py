from typing import Optional

from fastapi import APIRouter, Depends

from controllers.dependencias import exigir_perfil
from models.schemas import ProdutoCriarIn, ProdutoIn
from process import produto_process

router = APIRouter(prefix="/produtos", tags=["Produtos"])

# Consulta: qualquer perfil. Cadastro/edição/desativação: admin ou gerente.
GESTAO = [Depends(exigir_perfil("admin", "gerente"))]


@router.get("")
def listar(
    busca: Optional[str] = None,
    categoria_id: Optional[int] = None,
    status: Optional[str] = None,
    incluir_desativados: bool = False,
):
    return produto_process.listar(busca, categoria_id, status, incluir_desativados)


@router.get("/{produto_id}")
def obter(produto_id: int):
    return produto_process.obter(produto_id)


@router.post("", status_code=201, dependencies=GESTAO)
def criar(corpo: ProdutoCriarIn):
    return produto_process.criar(corpo.model_dump())


@router.put("/{produto_id}", dependencies=GESTAO)
def atualizar(produto_id: int, corpo: ProdutoIn):
    return produto_process.atualizar(produto_id, corpo.model_dump())


@router.post("/{produto_id}/desativar", dependencies=GESTAO)
def desativar(produto_id: int):
    return produto_process.desativar(produto_id)


@router.post("/{produto_id}/reativar", dependencies=GESTAO)
def reativar(produto_id: int):
    return produto_process.reativar(produto_id)
