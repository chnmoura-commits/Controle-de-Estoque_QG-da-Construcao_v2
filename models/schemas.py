from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# O local é identificado pelo CÓDIGO cadastrado em `locais` (ex.: 'deposito',
# 'loja-centro'). A validação de existência/atividade fica no `process`.
Local = str
TipoLocal = Literal["deposito", "loja"]
Perfil = Literal["admin", "gerente", "vendedor"]


class LocalIn(BaseModel):
    """Local (depósito ou loja). CNPJ/endereço/telefone/e-mail são opcionais,
    mas, quando informados, são validados no `process`."""
    nome: str
    tipo: TipoLocal = "loja"
    codigo: Optional[str] = None
    cnpj: Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    ativo: Optional[bool] = None


class CategoriaIn(BaseModel):
    nome: str
    descricao: Optional[str] = None


class FornecedorIn(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None


class RepresentanteIn(BaseModel):
    """Representante comercial de um fornecedor (contato/e-mail são opcionais,
    mas validados no `process` quando informados)."""
    nome: str
    contato: Optional[str] = None
    email: Optional[str] = None


class ClienteIn(BaseModel):
    """Cliente da loja (não loga no sistema). CPF/telefone/e-mail são opcionais,
    mas, quando informados, são validados no `process`."""
    nome: str
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None


class ProdutoIn(BaseModel):
    sku: Optional[str] = None
    nome: str
    descricao: Optional[str] = None
    categoria_id: Optional[int] = None
    fornecedor_id: Optional[int] = None
    unidade: str = "un"
    preco_custo: Optional[float] = Field(default=None, ge=0)
    preco_venda: Optional[float] = Field(default=None, ge=0)
    estoque_minimo: float = Field(default=0, ge=0)
    estoque_maximo: Optional[float] = Field(default=None, ge=0)


class ProdutoCriarIn(ProdutoIn):
    """Cadastro com saldo de abertura opcional: informar quantidade + valor unitário
    gera uma movimentação de saldo inicial e define o custo médio inicial."""
    quantidade_inicial: Optional[float] = Field(default=None, ge=0)


class MovimentacaoIn(BaseModel):
    produto_id: int
    local: Local
    tipo: Literal["ENTRADA", "SAIDA", "PERDA"]
    quantidade: float = Field(gt=0)
    # Custo unitário só faz sentido em ENTRADA (recalcula o custo médio).
    custo_unit: Optional[float] = Field(default=None, ge=0)
    observacao: Optional[str] = None
    registrado_por: Optional[str] = None


class TransferenciaIn(BaseModel):
    produto_id: int
    origem: Local
    destino: Local
    quantidade: float = Field(gt=0)
    observacao: Optional[str] = None
    registrado_por: Optional[str] = None


class InventarioIn(BaseModel):
    produto_id: int
    local: str  # Alterado para `Local` (str) conforme sugestão
    quantidade_contada: float = Field(ge=0)
    observacao: Optional[str] = None
    registrado_por: Optional[str] = None


class ItemCompraIn(BaseModel):
    produto_id: int
    quantidade: float = Field(gt=0)
    custo_unit: float = Field(ge=0)


class CompraIn(BaseModel):
    fornecedor_id: int
    data: date
    nota_fiscal: Optional[str] = None
    local_destino: Local = "deposito"  # Mantido conforme contexto de `Local` agora sendo str
    registrado_por: Optional[str] = None
    itens: List[ItemCompraIn]


class LoginIn(BaseModel):
    usuario: str
    senha: str


class TrocaSenhaIn(BaseModel):
    senha_atual: str
    senha_nova: str = Field(min_length=8)


class ColaboradorIn(BaseModel):
    """Dados de cadastro de um colaborador (usuário do sistema)."""
    nome_completo: str
    cpf: str
    telefone: str
    email: str
    perfil: Perfil


class ColaboradorCriarIn(ColaboradorIn):
    usuario: str


class AtivoIn(BaseModel):
    ativo: bool


class ItemVendaIn(BaseModel):
    produto_id: int
    quantidade: float = Field(gt=0)
    preco_unitario: Optional[float] = Field(default=None, ge=0)
    desconto_item: float = Field(default=0, ge=0)


class VendaIn(BaseModel):
    cliente_id: Optional[int] = None
    local: Local = "loja"  # Mantido conforme contexto de `Local` agora sendo str
    desconto: float = Field(default=0, ge=0)
    observacao: Optional[str] = None
    registrado_por: Optional[str] = None
    itens: List[ItemVendaIn]


