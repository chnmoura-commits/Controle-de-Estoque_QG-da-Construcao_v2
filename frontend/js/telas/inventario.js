/* Tela de inventário: conferência por local (contagem e transferência) e
   histórico das movimentações. Lançar entrada/saída/perda segue no modal
   compartilhado com Telas.movimentacoes. */

Telas.inventario = {
    _produtos: [],
    _locais: [],
    _historicoCarregado: false,

    async carregar() {
        // Junta em uma única tela o que antes estava espalhado (movimentações
        // e contagem). As abas reaproveitam a lista e o modal já existentes.
        await Promise.all([this.preparar(), this.mostrarAbaAtual()]);
    },

    async preparar() {
        try {
            const [produtos, locais] = await Promise.all([api('/produtos'), api('/locais')]);
            this._produtos = listaDe(produtos);
            this._locais = listaDe(locais);
        } catch (erro) { UI.erro(erro); }

        const atual = $('inv-local')?.value;
        await carregarOpcoesLocais('inv-local', null, atual || null);
        if ($('inv-local')?.value) {
            this.renderContagem();
        } else {
            $('lista-contagem').innerHTML = '<tr class="linha-tabela-vazia"><td colspan="6">Nenhum local cadastrado.</td></tr>';
        }
    },

    trocarAba(aba) {
        const contagem = aba === 'contagem';
        $('inv-painel-contagem').classList.toggle('hidden', !contagem);
        $('inv-painel-historico').classList.toggle('hidden', contagem);
        for (const [id, ativa] of [['inv-aba-contagem', contagem], ['inv-aba-historico', !contagem]]) {
            const botao = $(id);
            botao.classList.toggle('border-vermelhao-140', ativa);
            botao.classList.toggle('text-vermelhao-180', ativa);
            botao.classList.toggle('border-transparent', !ativa);
            botao.classList.toggle('text-vermelhao-120', !ativa);
        }
        this.mostrarAbaAtual();
    },

    mostrarAbaAtual() {
        const historico = $('inv-painel-historico') && !$('inv-painel-historico').classList.contains('hidden');
        if (historico) {
            this._historicoCarregado = true;
            return Telas.movimentacoes.carregar();
        }
        this.renderContagem();
    },

    /* Saldo do produto no local selecionado (usa o mapa `saldos` da API). */
    _saldoLocal(produto, local) {
        return Number((produto.saldos || {})[local] || 0);
    },

    renderContagem() {
        const local = $('inv-local').value;
        const termo = $('inv-busca').value.trim().toLowerCase();
        const produtos = this._produtos.filter(p =>
            !termo || produtoNome(p).toLowerCase().includes(termo) ||
            String(valor(p, 'produto_sku', 'sku') || '').toLowerCase().includes(termo));

        // Só oferece transferência para outros locais.
        const destinos = this._locais.filter(l => String(localCodigo(l)) !== String(local));

        $('lista-contagem').innerHTML = produtos.length ? produtos.map(p => {
            const id = produtoId(p);
            const saldo = this._saldoLocal(p, local);
            const opcoes = destinos.length
                ? destinos.map(l => `<option value="${esc(localCodigo(l))}">${esc(localNome(l))}</option>`).join('')
                : '<option value="">—</option>';
            return `<tr class="hover:bg-vermelhao-20">
                <td class="p-4"><div class="font-semibold text-vermelhao-180">${esc(produtoNome(p))}</div>
                    <div class="text-xs text-vermelhao-110">${esc(valor(p, 'produto_sku', 'sku') || '')}</div></td>
                <td class="p-4 font-semibold">${numero(saldo)}</td>
                <td class="p-4">
                    <input type="number" min="0" step="any" class="contado campo w-24 py-1.5"
                        data-produto="${Number(id)}" oninput="Telas.inventario.marcarDiferenca(this)">
                </td>
                <td class="p-4 diferenca text-vermelhao-110 text-xs">—</td>
                <td class="p-4">
                    <div class="flex items-center gap-1">
                        <input type="number" min="0.000001" step="any" placeholder="Qtd." class="transferir campo w-20 py-1.5"
                            data-produto="${Number(id)}">
                        <select class="transf-destino campo w-28 py-1.5">${opcoes}</select>
                    </div>
                </td>
                <td class="p-4 text-center space-x-2 whitespace-nowrap">
                    <button ${destinos.length ? '' : 'disabled'} onclick="Telas.inventario.transferir(this)"
                        class="text-info-600 hover:text-info-800 text-xs font-semibold disabled:opacity-40">Transferir</button>
                    <button onclick="Telas.inventario.contar(this)" data-produto="${Number(id)}" data-saldo="${saldo}"
                        class="text-vermelhao-140 hover:text-vermelhao-160 text-xs font-semibold">Contar</button>
                </td>
            </tr>`;
        }).join('') : '<tr class="linha-tabela-vazia"><td colspan="6">Nenhum produto encontrado.</td></tr>';

        const nomeLocal = (this._locais.find(l => String(localCodigo(l)) === String(local)) || {});
        $('inv-resumo').innerText = produtos.length
            ? `${produtos.length} produto(s) — contagem em ${localNome(nomeLocal) || local}`
            : '';
    },

    /* Mostra ao vivo a diferença entre o contado e o saldo do sistema. */
    marcarDiferenca(input) {
        const celula = input.closest('tr').querySelector('.diferenca');
        if (input.value === '') { celula.innerText = '—'; celula.className = 'p-4 diferenca text-vermelhao-110 text-xs'; return; }
        const botao = input.closest('tr').querySelector('button[data-saldo]');
        const saldo = Number(botao?.dataset.saldo || 0);
        const dif = Number(input.value) - saldo;
        celula.innerText = (dif > 0 ? '+' : '') + numero(dif);
        celula.className = 'p-4 diferenca text-xs font-semibold ' +
            (dif === 0 ? 'text-vermelhao-110' : dif > 0 ? 'text-success-600' : 'text-danger-600');
    },

    async contar(botao) {
        const linha = botao.closest('tr');
        const campo = linha.querySelector('.contado');
        const quantidade = campo.value;
        if (quantidade === '') { UI.erro(new Error('Informe a quantidade contada.')); campo.focus(); return; }
        const produtoId = botao.dataset.produto;
        const local = $('inv-local').value;
        try {
            const r = await api('/movimentacoes/inventario', {
                method: 'POST',
                body: JSON.stringify({ produto_id: Number(produtoId), local, quantidade_contada: Number(quantidade) }),
            });
            const divergencia = Number((r && r.divergencia) ?? 0);
            UI.sucesso(divergencia === 0
                ? 'Contagem confere com o sistema; nada a ajustar.'
                : `Contagem registrada: ajuste de ${divergencia > 0 ? '+' : ''}${numero(divergencia)}.`);
            await this.recarregar();
        } catch (erro) { UI.erro(erro); }
    },

    async transferir(botao) {
        const linha = botao.closest('tr');
        const quantidade = linha.querySelector('.transferir').value;
        const destino = linha.querySelector('.transf-destino').value;
        if (!quantidade || Number(quantidade) <= 0) { UI.erro(new Error('Informe a quantidade a transferir.')); return; }
        if (!destino) { UI.erro(new Error('Escolha o local de destino.')); return; }
        try {
            await api('/movimentacoes/transferencia', {
                method: 'POST',
                body: JSON.stringify({
                    produto_id: Number(linha.querySelector('.transferir').dataset.produto),
                    origem: $('inv-local').value, destino, quantidade: Number(quantidade),
                }),
            });
            UI.sucesso('Transferência registrada.');
            await this.recarregar();
        } catch (erro) { UI.erro(erro); }
    },

    /* Atualiza produtos (saldos mudaram) e a tabela sem perder o filtro. */
    async recarregar() {
        try {
            this._produtos = listaDe(await api('/produtos'));
        } catch (erro) { UI.erro(erro); }
        this.renderContagem();
        Telas.produtos.carregar().catch(() => {});
        Telas.alertas.carregar().catch(() => {});
    },

    abrirMovimentacao() {
        // Abre o modal de entrada/saída/perda já no local selecionado na contagem.
        this._localParaMovimentacao = $('inv-local').value || null;
        openModal('modal-movimentacao');
    },

    localSelecionado() {
        return this._localParaMovimentacao;
    },
};
