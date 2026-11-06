/* Tela de vendas: listagem, registro (com local) e cancelamento.
   A baixa (e o estorno no cancelamento) acontece no local escolhido. */

function vendaId(v) { return valor(v, 'venda_id', 'id'); }

Telas.vendas = {
    _produtos: [],
    _locais: [],
    _clientes: [],

    async carregar() {
        try {
            const lista = listaDe(await api('/vendas?limite=200'));
            $('lista-vendas').innerHTML = lista.length ? lista.map(v => {
                const id = vendaId(v);
                const local = valor(v, 'venda_local', 'local') || '—';
                const situacao = valor(v, 'venda_status', 'status') || 'CONCLUIDA';
                const cancelada = situacao === 'CANCELADA';
                const cliente = valor(v, 'cliente_nome', 'nome_cliente') || '—';
                const total = Number(valor(v, 'venda_total', 'total') || 0);
                return `<tr class="hover:bg-vermelhao-20 ${cancelada ? 'opacity-60' : ''}">
                    <td class="p-4 font-mono text-xs text-vermelhao-130">${esc(valor(v, 'venda_numero', 'numero') || ('#' + id))}</td>
                    <td class="p-4">${dataBR(valor(v, 'criado_em', 'venda_data', 'data'))}</td>
                    <td class="p-4">${esc(cliente)}</td>
                    <td class="p-4 font-mono text-xs">${esc(local)}</td>
                    <td class="p-4 font-semibold">${moeda(total)}</td>
                    <td class="p-4"><span class="px-2 py-0.5 rounded text-xs font-semibold ${cancelada ? 'bg-danger-100 text-danger-700' : 'bg-success-100 text-success-700'}">${cancelada ? 'Cancelada' : 'Concluída'}</span></td>
                    <td class="p-4 text-center">${cancelada ? '<span class="text-xs text-vermelhao-110">—</span>'
                        : `<button onclick="Telas.vendas.cancelar(${Number(id)})" class="text-danger-600 hover:text-danger-800 text-xs font-semibold">Cancelar</button>`}</td>
                </tr>`;
            }).join('') : '<tr class="linha-tabela-vazia"><td colspan="7">Nenhuma venda registrada.</td></tr>';
        } catch (erro) {
            $('lista-vendas').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="7" class="text-danger-600">${esc(erro.message)}</td></tr>`;
        }
    },

    async abrir() {
        try {
            const [produtos, locais, clientes] = await Promise.all([
                api('/produtos'), api('/locais'), api('/clientes').catch(() => []),
            ]);
            this._produtos = listaDe(produtos);
            this._locais = listaDe(locais);
            this._clientes = listaDe(clientes);
        } catch (erro) { UI.erro(erro); return; }

        await carregarOpcoesLocais('venda-local');
        const deposito = this._locais.find(l => localTipo(l) === 'deposito');
        if (deposito) $('venda-local').value = localCodigo(deposito);
        preencherSelect('venda-cliente', this._clientes,
            c => valor(c, 'cliente_id', 'id'), c => valor(c, 'cliente_nome', 'nome') || 'Cliente', 'Sem cliente');
        $('venda-desconto').value = 0;
        $('venda-observacao').value = '';
        $('venda-itens').innerHTML = '';
        this.adicionarItem();
        this.atualizarTotal();
        openModal('modal-venda');
    },

    adicionarItem() {
        const opcoes = '<option value="">Selecione.</option>' + this._produtos.map(p =>
            `<option value="${esc(produtoId(p))}" data-preco="${Number(valor(p, 'produto_preco_venda', 'preco_venda') || 0)}">${esc(produtoNome(p))}</option>`).join('');
        const linha = document.createElement('div');
        linha.className = 'item-venda grid grid-cols-12 gap-2 items-center';
        linha.innerHTML = `
            <select class="iv-produto col-span-6 bg-white border border-vermelhao-70 rounded-lg p-2 text-sm" onchange="Telas.vendas.atualizarLinhas()">${opcoes}</select>
            <input type="number" min="0.000001" step="any" class="iv-qtd col-span-2 bg-white border border-vermelhao-70 rounded-lg p-2 text-sm" placeholder="Qtd." oninput="Telas.vendas.atualizarTotal()">
            <input type="number" min="0" step="0.01" class="iv-preco col-span-3 bg-white border border-vermelhao-70 rounded-lg p-2 text-sm" oninput="Telas.vendas.atualizarTotal()">
            <button type="button" title="Remover item" onclick="this.parentElement.remove(); Telas.vendas.atualizarTotal()" class="col-span-1 text-danger-500 hover:text-danger-700 text-lg leading-none">&times;</button>`;
        $('venda-itens').appendChild(linha);
    },

    /* Preenche o preço de venda do produto e mostra o saldo no local. */
    atualizarLinhas() {
        const local = $('venda-local').value;
        for (const linha of $('venda-itens').querySelectorAll('.item-venda')) {
            const select = linha.querySelector('.iv-produto');
            const preco = linha.querySelector('.iv-preco');
            const opcao = select.selectedOptions[0];
            if (opcao && opcao.dataset.preco && preco.value === '') preco.value = opcao.dataset.preco;
            const produto = this._produtos.find(p => String(produtoId(p)) === select.value);
            select.title = produto ? `Saldo neste local: ${numero((produto.saldos || {})[local] || 0)}` : '';
        }
        this.atualizarTotal();
    },

    _itensDoFormulario() {
        return [...$('venda-itens').querySelectorAll('.item-venda')].map(linha => {
            const produto_id = Number(linha.querySelector('.iv-produto').value);
            const quantidade = Number(linha.querySelector('.iv-qtd').value);
            const preco = linha.querySelector('.iv-preco').value;
            if (!produto_id || !quantidade) return null;
            return { produto_id, quantidade, preco_unitario: preco === '' ? null : Number(preco) };
        }).filter(Boolean);
    },

    atualizarTotal() {
        const bruto = this._itensDoFormulario().reduce((soma, i) => {
            const produto = this._produtos.find(p => String(produtoId(p)) === String(i.produto_id));
            const preco = i.preco_unitario ?? Number(valor(produto || {}, 'produto_preco_venda', 'preco_venda') || 0);
            return soma + i.quantidade * preco;
        }, 0);
        const desconto = Number($('venda-desconto').value || 0);
        $('venda-total').innerText = moeda(Math.max(0, bruto - desconto));
    },

    async salvar(evento) {
        evento.preventDefault();
        const itens = this._itensDoFormulario();
        if (!itens.length) { UI.erro(new Error('Adicione ao menos um item com quantidade.')); return; }
        const cliente = $('venda-cliente').value;
        const payload = {
            local: $('venda-local').value,
            cliente_id: cliente ? Number(cliente) : null,
            desconto: Number($('venda-desconto').value || 0),
            observacao: $('venda-observacao').value.trim() || null,
            itens,
        };
        try {
            await api('/vendas', { method: 'POST', body: JSON.stringify(payload) });
            UI.fecharModal('modal-venda');
            await this.carregar();
            Telas.produtos.carregar().catch(() => {});
            Telas.alertas.carregar().catch(() => {});
            UI.sucesso('Venda registrada.');
        } catch (erro) { UI.erro(erro); }
    },

    async cancelar(id) {
        if (!confirm('Cancelar esta venda? As quantidades voltam ao local da venda.')) return;
        try {
            await api(`/vendas/${Number(id)}/cancelar`, { method: 'POST' });
            await this.carregar();
            Telas.produtos.carregar().catch(() => {});
            UI.sucesso('Venda cancelada e estoque estornado.');
        } catch (erro) { UI.erro(erro); }
    },
};

function salvarVenda(e) { return Telas.vendas.salvar(e); }
