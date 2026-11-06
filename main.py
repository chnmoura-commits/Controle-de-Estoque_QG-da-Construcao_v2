from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from controllers import (alerta_controller, auth_controller, categoria_controller,
                         cliente_controller, colaborador_controller,
                         compra_controller, fornecedor_controller, local_controller,
                         movimentacao_controller, produto_controller,
                         relatorio_controller, venda_controller)
from controllers.dependencias import usuario_autenticado
from exceptions import NaoEncontradoError, RegraDeNegocioError

app = FastAPI(title="Controle de Estoque - QG da Construção", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NaoEncontradoError)
def tratar_nao_encontrado(request: Request, erro: NaoEncontradoError):
    return JSONResponse(status_code=404, content={"erro": str(erro)})


@app.exception_handler(RegraDeNegocioError)
def tratar_regra_de_negocio(request: Request, erro: RegraDeNegocioError):
    return JSONResponse(status_code=422, content={"erro": str(erro)})

# Autenticação é pública (é onde o token nasce); os demais routers exigem token.
app.include_router(auth_controller.router)

for modulo in (categoria_controller, fornecedor_controller, produto_controller,
               movimentacao_controller, compra_controller, alerta_controller,
                              relatorio_controller, colaborador_controller, cliente_controller,
               venda_controller, local_controller):
    app.include_router(modulo.router, dependencies=[Depends(usuario_autenticado)])


@app.get("/", tags=["Saúde"])
def raiz():
    return {"status": "ok", "docs": "/docs"}


