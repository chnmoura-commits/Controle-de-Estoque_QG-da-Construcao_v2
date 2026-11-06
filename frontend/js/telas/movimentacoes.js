/* Tela de movimentações: listagem e registro. */

function localRotulo(l) {
    const tipo = valor(l, 'local_tipo');
    return localNome(l) + (tipo ? ` (${TipoLocal.rotulo(tipo)})` : '');
}

Telas.movimentacoes = {
    _produtos: [],

    async carregar() {
        try {
            const lista = listaDe(await api('/movimentacoes?limite=200'));
            $('lista-movimentacoes').innerHTML = lista.length ? lista.map(m => {
                const dataHora = valor(m, 'criado_em', 'data_hora', 'movimentacao_data_hora', 'data');
                const tipo = valor(m, 'tipo', 'movimentacao_tipo') || '—';
                const nome = valor(m, 'produto_nome', 'nome_produto') || '—';
                const classeTipo = tipo.includes('ENTRADA') ? 'bg-success-100 text-success-700'
                    : (tipo.includes('SAIDA') || tipo === 'PERDA') ? 'bg-danger-100 text-danger-700'
                    : 'bg-info-100 text-info-700';
                return `<tr class="hover:bg-vermelhao-20">
                    <td class="p-4 text-xs text-vermelhao-130">${dataHora ? new Date(dataHora).toLocaleString('pt-BR') : '—'}</td>
                    <td class="p-4 font-medium text-vermelhao-180">${esc(nome)}</td>
                    <td class="p-4 font-mono text-xs text-vermelhao-130">${esc(valor(m, 'estoque_local') || '—')}</td>
                    <td class="p-4"><span class="px-2 py-0.5 rounded text-xs font-semibold ${classeTipo}">${esc(tipo)}</span></td>
                    <td class="p-4">${numero(valor(m, 'quantidade', 'movimentacao_quantidade'))}</td>
                    <td class="p-4 text-xs">${esc(valor(m, 'observacao', 'movimentacao_observacao') || '—')}</td>
                </tr>`;
            }).join('') : '<tr class="linha-tabela-vazia"><td colspan="6">Nenhuma movimentação encontrada.</td></tr>';
        } catch (erro) {
            $('lista-movimentacoes').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="6" class="text-danger-600">${esc(erro.message)}</td></tr>`;
        }
    },

    /* Prepara o modal: produtos e locais vindos dos respectivos cadastros. */
    async preparar() {
        try {
            const [produtos, locais] = await Promise.all([api('/produtos'), api('/locais')]);
            this._produtos = listaDe(produtos);
            this._locais = listaDe(locais);
            $('mov-produto').innerHTML = this._produtos.length
                ? this._produtos.map(p => `<option value="${esc(produtoId(p))}">${esc(produtoNome(p))}</option>`).join('')
                : '<option value="">Cadastre um produto primeiro</option>';
            $('mov-local').innerHTML = this._locais.length
                ? this._locais.map(l => `<option value="${esc(localCodigo(l))}">${esc(localRotulo(l))}</option>`).join('')
                : '<option value="">Cadastre um local primeiro</option>';
            // Vindo do Inventário, mantém o local da contagem selecionado.
            const preferido = Telas.inventario?.localSelecionado?.();
            if (preferido && this._locais.some(l => String(localCodigo(l)) === String(preferido))) {
                $('mov-local').value = preferido;
            }
            this.atualizarSaldoLocal();
        } catch (erro) {
            $('mov-produto').innerHTML = '<option value="">Não foi possível carregar produtos</option>';
            UI.erro(erro);
        }
    },

    /* Mostra o saldo do produto NO LOCAL escolhido (não o saldo total). */
    atualizarSaldoLocal() {
        const produto = this._produtos.find(p => String(produtoId(p)) === $('mov-produto').value);
        const local = $('mov-local').value;
        const saldo = produto ? Number((produto.saldos || {})[local] || 0) : 0;
        const el = $('mov-saldo-local');
        if (el) el.innerText = produto ? `${numero(saldo)} no local selecionado` : '';
    },

    async salvar(evento) {
        evento.preventDefault();
        const payload = {
            produto_id: Number($('mov-produto').value),
            local: $('mov-local').value,
            tipo: $('mov-tipo').value,
            quantidade: Number($('mov-quantidade').value),
            observacao: $('mov-observacao').value.trim() || null,
            registrado_por: Sessao.usuario() || $('mov-registrado-por').value.trim() || null,
        };
        try {
            await api('/movimentacoes', { method: 'POST', body: JSON.stringify(payload) });
            UI.fecharModal('modal-movimentacao');
            $('form-movimentacao').reset();
            await this.carregar();
            Telas.produtos.carregar().catch(() => {});
            Telas.alertas.carregar().catch(() => {});
            UI.sucesso('Movimentação registrada.');
        } catch (erro) { UI.erro(erro); }
    },
};

function salvarMovimentacao(e) { return Telas.movimentacoes.salvar(e); }
