/* Tela de produtos: listagem, cadastro e ativação/desativação. */

function produtoId(p) { return valor(p, 'produto_id', 'id'); }
function produtoNome(p) { return valor(p, 'produto_nome', 'nome') || 'Produto sem nome'; }
function produtoSaldo(p) { return valor(p, 'saldo_total', 'quantidade_total', 'quantidade') ?? 0; }
function produtoPreco(p) { return valor(p, 'produto_preco_venda', 'preco_venda', 'preco') ?? 0; }
function produtoCategoria(p) { return valor(p, 'categoria_nome', 'produto_categoria_nome', 'categoria') || '—'; }
function produtoAtivo(p) {
    const a = valor(p, 'produto_ativo', 'ativo');
    return a !== 0 && a !== false;
}

Telas.produtos = {
    async carregar() {
        try {
            const produtos = listaDe(await api('/produtos'));
            $('lista-produtos').innerHTML = produtos.length ? produtos.map(p => {
                const id = produtoId(p);
                const ativo = produtoAtivo(p);
                const sku = valor(p, 'produto_sku', 'sku') || '—';
                return `<tr class="hover:bg-vermelhao-20">
                    <td class="p-4 font-mono text-xs text-vermelhao-130">#${esc(id)}</td>
                    <td class="p-4"><div class="font-semibold text-vermelhao-180">${esc(produtoNome(p))}</div><div class="text-xs text-vermelhao-110">${esc(sku)}</div></td>
                    <td class="p-4">${esc(produtoCategoria(p))}</td>
                    <td class="p-4">${numero(produtoSaldo(p))} ${esc(valor(p, 'produto_unidade', 'unidade') || '')}</td>
                    <td class="p-4">${moeda(produtoPreco(p))}</td>
                    <td class="p-4 text-center">
                        <button onclick="${ativo ? 'Telas.produtos.desativar' : 'Telas.produtos.reativar'}(${Number(id)})" class="${ativo ? 'text-danger-600 hover:text-danger-800' : 'text-success-600 hover:text-success-800'} text-xs font-semibold">${ativo ? 'Desativar' : 'Reativar'}</button>
                    </td>
                </tr>`;
            }).join('') : '<tr class="linha-tabela-vazia"><td colspan="6">Nenhum produto cadastrado.</td></tr>';

            $('dash-total-produtos').innerText = produtos.length;
            return produtos;
        } catch (erro) {
            $('lista-produtos').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="6" class="text-danger-600">${esc(erro.message)}</td></tr>`;
            throw erro;
        }
    },

    async salvar(evento) {
        evento.preventDefault();
        const opcional = id => $(id).value.trim() === '' ? null : Number($(id).value);
        const payload = {
            sku: $('prod-sku').value.trim() || null,
            nome: $('prod-nome').value.trim(),
            descricao: $('prod-descricao').value.trim() || null,
            unidade: $('prod-unidade').value.trim() || 'un',
            preco_custo: opcional('prod-custo'),
            preco_venda: opcional('prod-venda'),
            estoque_minimo: Number($('prod-minimo').value || 0),
            estoque_maximo: opcional('prod-maximo'),
            categoria_id: opcional('prod-categoria'),
            fornecedor_id: opcional('prod-fornecedor'),
        };
        try {
            await api('/produtos', { method: 'POST', body: JSON.stringify(payload) });
            UI.fecharModal('modal-produto');
            $('form-produto').reset();
            $('prod-unidade').value = 'un';
            $('prod-minimo').value = '0';
            await this.carregar();
            Telas.dashboard.carregar();
            UI.sucesso('Produto cadastrado. Registre uma entrada em Movimentações para adicionar saldo.');
        } catch (erro) { UI.erro(erro); }
    },

    async desativar(id) {
        if (!confirm('Deseja desativar este produto? O histórico e os saldos serão preservados.')) return;
        try {
            await api(`/produtos/${id}/desativar`, { method: 'POST' });
            await this.carregar();
            Telas.dashboard.carregar();
            Telas.reativar.carregar().catch(() => {});
            UI.sucesso('Produto desativado.');
        } catch (erro) { UI.erro(erro); }
    },

    async reativar(id) {
        try {
            await api(`/produtos/${id}/reativar`, { method: 'POST' });
            await this.carregar();
            Telas.dashboard.carregar();
            UI.sucesso('Produto reativado.');
        } catch (erro) { UI.erro(erro); }
    },

    async carregarOpcoesFormulario() {
        try {
            const [cats, forns] = await Promise.all([api('/categorias'), api('/fornecedores')]);
            const categorias = listaDe(cats);
            const fornecedores = listaDe(forns);
            preencherSelect('prod-categoria', categorias,
                c => valor(c, 'categoria_id', 'id'), c => valor(c, 'categoria_nome', 'nome') || 'Sem nome', 'Sem categoria');
            preencherSelect('prod-fornecedor', fornecedores,
                f => valor(f, 'fornecedor_id', 'id'), f => valor(f, 'fornecedor_nome', 'nome') || 'Sem nome', 'Sem fornecedor');
        } catch (erro) { UI.erro(erro); }
    },
};

/* Atalhos globais para os onclick do HTML. */
function salvarProduto(e) { return Telas.produtos.salvar(e); }
function desativarProduto(id) { return Telas.produtos.desativar(id); }
function reativarProduto(id) { return Telas.produtos.reativar(id); }
