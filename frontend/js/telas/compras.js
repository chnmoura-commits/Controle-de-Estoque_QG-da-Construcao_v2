/* Tela de compras: listagem, detalhe e registro (com itens). */

function compraId(c) { return valor(c, 'compras_id', 'compra_id', 'id'); }
function itemQtd(i) { return valor(i, 'itens_compra_quantidade', 'quantidade') ?? 0; }
function itemCusto(i) { return valor(i, 'itens_compra_custo_unit', 'custo_unit', 'custo_unitario') ?? 0; }
function totalDaCompra(c) {
    const t = valor(c, 'total', 'compra_total', 'compras_total', 'valor_total');
    if (t != null) return Number(t);
    const itens = valor(c, 'itens');
    return Array.isArray(itens) ? itens.reduce((a, i) => a + itemQtd(i) * itemCusto(i), 0) : null;
}

Telas.compras = {
    _fornecedores: [],
    _produtos: [],
    _locais: [],

    async carregar() {
        try {
            const [compras, forns] = await Promise.all([api('/compras'), api('/fornecedores').catch(() => [])]);
            this._fornecedores = listaDe(forns);
            const lista = listaDe(compras);
            $('lista-compras').innerHTML = lista.length ? lista.map(c => {
                const total = totalDaCompra(c);
                return `<tr class="hover:bg-vermelhao-20">
                    <td class="p-4 font-mono text-xs text-vermelhao-130">#${esc(compraId(c))}</td>
                    <td class="p-4">${dataBR(valor(c, 'compras_data', 'compra_data', 'data'))}</td>
                    <td class="p-4 font-semibold text-vermelhao-180">${esc(this._nomeFornecedor(c))}</td>
                    <td class="p-4">${esc(valor(c, 'compras_nota_fiscal', 'nota_fiscal') || '—')}</td>
                    <td class="p-4">${total == null ? '—' : moeda(total)}</td>
                    <td class="p-4 text-center"><button onclick="Telas.compras.ver(${Number(compraId(c))})" class="text-info-600 hover:text-info-800 text-xs font-semibold">Ver itens</button></td>
                </tr>`;
            }).join('') : '<tr class="linha-tabela-vazia"><td colspan="6">Nenhuma compra registrada.</td></tr>';
        } catch (erro) {
            $('lista-compras').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="6" class="text-danger-600">${esc(erro.message)}</td></tr>`;
        }
    },

    _nomeFornecedor(c) {
        const n = valor(c, 'fornecedor_nome');
        if (n) return n;
        const f = this._fornecedores.find(x =>
            String(valor(x, 'fornecedor_id', 'id')) === String(valor(c, 'fornecedor_id')));
        return f ? (valor(f, 'fornecedor_nome', 'nome') || 'Sem nome') : '—';
    },

    async ver(id) {
        try {
            const c = await api(`/compras/${id}`);
            const itens = listaDe(valor(c, 'itens') || []);
            $('det-titulo').innerText = `Compra #${compraId(c) ?? id}`;
            $('det-resumo').innerText =
                `${dataBR(valor(c, 'compras_data', 'compra_data', 'data'))} · ${this._nomeFornecedor(c)}` +
                (valor(c, 'compras_nota_fiscal', 'nota_fiscal') ? ` · NF ${valor(c, 'compras_nota_fiscal', 'nota_fiscal')}` : '');

            let total = 0;
            $('det-itens').innerHTML = itens.length ? itens.map(i => {
                const sub = itemQtd(i) * itemCusto(i);
                total += sub;
                return `<tr>
                    <td class="p-3 font-medium text-vermelhao-180">${esc(valor(i, 'produto_nome', 'nome') || ('Produto #' + valor(i, 'produto_id')))}</td>
                    <td class="p-3">${numero(itemQtd(i))}</td>
                    <td class="p-3">${moeda(itemCusto(i))}</td>
                    <td class="p-3">${moeda(sub)}</td>
                </tr>`;
            }).join('') : '<tr class="linha-tabela-vazia"><td colspan="4">Sem itens.</td></tr>';
            $('det-total').innerText = moeda(totalDaCompra(c) ?? total);
            UI.abrirModal('modal-compra-detalhe');
        } catch (erro) { UI.erro(erro); }
    },

    async preparar() {
        try {
            const [forns, prods, locais] = await Promise.all([api('/fornecedores'), api('/produtos'), api('/locais')]);
            this._fornecedores = listaDe(forns);
            this._produtos = listaDe(prods);
            this._locais = listaDe(locais);
        } catch (erro) { UI.erro(erro); }
        preencherSelect('compra-fornecedor', this._fornecedores,
            f => valor(f, 'fornecedor_id', 'id'), f => valor(f, 'fornecedor_nome', 'nome') || 'Sem nome', 'Selecione o fornecedor');
        $('compra-data').value = new Date().toLocaleDateString('sv-SE');
        $('compra-nf').value = '';
        // O destino padrão é o depósito (é para lá que a mercadoria comprada entra).
        const deposito = (this._locais || []).find(l => localTipo(l) === 'deposito');
        await carregarOpcoesLocais('compra-local', null, deposito ? localCodigo(deposito) : null);
        $('compra-itens').innerHTML = '';
        this.adicionarItem();
        this.atualizarTotal();
    },

    adicionarItem() {
        const opcoes = '<option value="">Selecione…</option>' + this._produtos.map(p =>
            `<option value="${esc(produtoId(p))}">${esc(produtoNome(p))}</option>`).join('');
        const linha = document.createElement('div');
        linha.className = 'item-compra grid grid-cols-12 gap-2 items-center';
        linha.innerHTML = `
            <select class="ic-produto col-span-6 bg-white border border-vermelhao-70 rounded-lg p-2 text-sm" onchange="Telas.compras._preencherCusto(this)">${opcoes}</select>
            <input type="number" min="0.000001" step="any" class="ic-qtd col-span-2 bg-white border border-vermelhao-70 rounded-lg p-2 text-sm" oninput="Telas.compras.atualizarTotal()">
            <input type="number" min="0" step="0.01" class="ic-custo col-span-3 bg-white border border-vermelhao-70 rounded-lg p-2 text-sm" oninput="Telas.compras.atualizarTotal()">
            <button type="button" title="Remover item" onclick="this.parentElement.remove(); Telas.compras.atualizarTotal()" class="col-span-1 text-danger-500 hover:text-danger-700 text-lg leading-none">&times;</button>`;
        $('compra-itens').appendChild(linha);
    },

    _preencherCusto(select) {
        const p = this._produtos.find(x => String(produtoId(x)) === select.value);
        const custo = p ? valor(p, 'produto_preco_custo', 'preco_custo') : null;
        if (custo != null) select.parentElement.querySelector('.ic-custo').value = custo;
        this.atualizarTotal();
    },

    _lerItens() {
        return [...document.querySelectorAll('#compra-itens .item-compra')].map(l => ({
            produto_id: Number(l.querySelector('.ic-produto').value),
            quantidade: Number(l.querySelector('.ic-qtd').value),
            custo_unit: l.querySelector('.ic-custo').value === '' ? NaN : Number(l.querySelector('.ic-custo').value),
        }));
    },

    atualizarTotal() {
        const total = this._lerItens().reduce((a, i) =>
            a + ((i.quantidade > 0 && i.custo_unit >= 0) ? i.quantidade * i.custo_unit : 0), 0);
        $('compra-total').innerText = moeda(total);
    },

    async salvar(evento) {
        evento.preventDefault();
        const itens = this._lerItens();
        if (!itens.length) return UI.erro(new Error('Adicione ao menos um item à compra.'));
        if (itens.some(i => !i.produto_id || !(i.quantidade > 0) || !(i.custo_unit >= 0))) {
            return UI.erro(new Error('Em cada item, escolha o produto e informe quantidade maior que zero e custo válido.'));
        }
        const payload = {
            fornecedor_id: Number($('compra-fornecedor').value),
            data: $('compra-data').value,
            nota_fiscal: $('compra-nf').value.trim() || null,
            local_destino: $('compra-local').value,
            registrado_por: Sessao.usuario() || $('compra-registrado-por').value.trim() || null,
            itens,
        };
        try {
            await api('/compras', { method: 'POST', body: JSON.stringify(payload) });
            UI.fecharModal('modal-compra');
            $('form-compra').reset();
            await this.carregar();
            Telas.produtos.carregar().catch(() => {});
            Telas.movimentacoes.carregar().catch(() => {});
            Telas.alertas.carregar().catch(() => {});
            Telas.dashboard.carregar();
            UI.sucesso('Compra registrada e estoque atualizado.');
        } catch (erro) { UI.erro(erro); }
    },
};

function adicionarItemCompra() { Telas.compras.adicionarItem(); }
function atualizarTotalCompra() { Telas.compras.atualizarTotal(); }
function salvarCompra(e) { return Telas.compras.salvar(e); }
function verCompra(id) { return Telas.compras.ver(id); }
