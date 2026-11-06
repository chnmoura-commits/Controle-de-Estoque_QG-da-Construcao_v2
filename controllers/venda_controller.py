from typing import Optional

from fastapi import APIRouter, Depends

from controllers.dependencias import exigir_perfil, usuario_autenticado
from models.schemas import VendaIn
from process import venda_process

router = APIRouter(prefix="/vendas", tags=["Vendas"])

# Vender: qualquer perfil autenticado (admin, gerente ou vendedor).
# Cancelar exige admin ou gerente.
GESTAO = [Depends(exigir_perfil("admin", "gerente"))]


@router.get("")
def listar(cliente_id: Optional[int] = None, status: Optional[str] = None,
           data_inicio: Optional[str] = None, data_fim: Optional[str] = None,
           limite: int = 200):
    return venda_process.listar(cliente_id, status, data_inicio, data_fim, limite)


@router.get("/resumo")
def resumo(data_inicio: Optional[str] = None, data_fim: Optional[str] = None):
    return venda_process.resumo(data_inicio, data_fim)


@router.get("/{venda_id}")
def obter(venda_id: int):
    return venda_process.obter(venda_id)


@router.post("", status_code=201)
def registrar(corpo: VendaIn, usuario: dict = Depends(usuario_autenticado)):
    dados = corpo.model_dump()
    dados["registrado_por"] = usuario.get("nome") or dados.get("registrado_por")
    return venda_process.registrar(dados)


@router.post("/{venda_id}/cancelar", dependencies=GESTAO)
def cancelar(venda_id: int, usuario: dict = Depends(exigir_perfil("admin", "gerente"))):
    return venda_process.cancelar(venda_id, cancelado_por=usuario.get("nome"))
