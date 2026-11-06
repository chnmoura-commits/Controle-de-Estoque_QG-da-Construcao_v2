/* Tela de produtos desativados: listagem e reativação. */

Telas.reativar = {
    _produtos: [],

    async carregar() {
        try {
            const todos = listaDe(await api('/produtos?incluir_desativados=true'));
            this._produtos = todos.filter(p => !produtoAtivo(p));
            this._atualizarBadge();
            this.render();
        } catch (erro) {
            $('lista-desativados').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="6" class="text-danger-600">${esc(erro.message)}</td></tr>`;
            throw erro;
        }
    },

    _atualizarBadge() {
        const badge = $('reativar-badge');
        badge.innerText = this._produtos.length;
        badge.classList.toggle('hidden', this._produtos.length === 0);
    },

    render() {
        const termo = $('reativar-busca').value.trim().toLowerCase();
        const lista = this._produtos.filter(p =>
            !termo ||
            produtoNome(p).toLowerCase().includes(termo) ||
            String(valor(p, 'produto_sku', 'sku') || '').toLowerCase().includes(termo));

        $('lista-desativados').innerHTML = lista.length ? lista.map(p => {
            const id = produtoId(p);
            const sku = valor(p, 'produto_sku', 'sku') || '—';
            return `<tr class="hover:bg-vermelhao-20">
                <td class="p-4 font-mono text-xs text-vermelhao-130">#${esc(id)}</td>
                <td class="p-4"><div class="font-semibold text-vermelhao-180">${esc(produtoNome(p))}</div><div class="text-xs text-vermelhao-110">${esc(sku)}</div></td>
                <td class="p-4">${esc(produtoCategoria(p))}</td>
                <td class="p-4">${numero(produtoSaldo(p))} ${esc(valor(p, 'produto_unidade', 'unidade') || '')}</td>
                <td class="p-4">${moeda(produtoPreco(p))}</td>
                <td class="p-4 text-center">
                    <button onclick="Telas.reativar.reativar(${Number(id)})" class="inline-flex items-center gap-1 bg-success-500 hover:bg-success-600 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition">
                        <i data-lucide="rotate-ccw" class="w-3 h-3"></i> Reativar
                    </button>
                </td>
            </tr>`;
        }).join('') : `<tr class="linha-tabela-vazia"><td colspan="6">${
            this._produtos.length ? 'Nenhum produto desativado corresponde à busca.' : 'Nenhum produto desativado.'}</td></tr>`;
        if (window.lucide) lucide.createIcons();
    },

    async reativar(id) {
        if (!confirm('Deseja reativar este produto? Ele voltará às listagens e poderá ser movimentado.')) return;
        try {
            await api(`/produtos/${id}/reativar`, { method: 'POST' });
            await this.carregar();
            Telas.produtos.carregar().catch(() => {});
            Telas.dashboard.carregar();
            Telas.alertas.carregar().catch(() => {});
            UI.sucesso('Produto reativado.');
        } catch (erro) { UI.erro(erro); }
    },
};

function renderDesativados() { Telas.reativar.render(); }
