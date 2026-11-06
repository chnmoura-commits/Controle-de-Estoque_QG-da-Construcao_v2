/* Tela de fornecedores: listagem e cadastro/edição. */

function fornecedorId(f) { return valor(f, 'fornecedor_id', 'id'); }
function fornecedorNomeDe(f) { return valor(f, 'fornecedor_nome', 'nome') || 'Sem nome'; }

Telas.fornecedores = {
    _lista: [],

    async carregar() {
        try {
            this._lista = listaDe(await api('/fornecedores'));
            $('lista-fornecedores').innerHTML = this._lista.length ? this._lista.map(f => `
                <tr class="hover:bg-vermelhao-20">
                    <td class="p-4 font-mono text-xs text-vermelhao-130">#${esc(fornecedorId(f))}</td>
                    <td class="p-4 font-semibold text-vermelhao-180">${esc(fornecedorNomeDe(f))}</td>
                    <td class="p-4">${esc(valor(f, 'fornecedor_cnpj', 'cnpj') || '—')}</td>
                    <td class="p-4">${esc(valor(f, 'fornecedor_telefone', 'telefone') || '—')}</td>
                    <td class="p-4">${esc(valor(f, 'fornecedor_email', 'email') || '—')}</td>
                    <td class="p-4 text-center"><button onclick="Telas.fornecedores.abrir(${Number(fornecedorId(f))})" class="text-info-600 hover:text-info-800 text-xs font-semibold">Editar</button></td>
                </tr>`).join('')
                : '<tr class="linha-tabela-vazia"><td colspan="6">Nenhum fornecedor cadastrado.</td></tr>';
            $('dash-fornecedores-count').innerText = this._lista.length;
        } catch (erro) {
            $('lista-fornecedores').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="6" class="text-danger-600">${esc(erro.message)}</td></tr>`;
        }
    },

    abrir(id = null) {
        const f = id != null ? this._lista.find(x => String(fornecedorId(x)) === String(id)) : null;
        $('forn-id').value = f ? fornecedorId(f) : '';
        $('forn-titulo').innerText = f ? 'Editar Fornecedor' : 'Adicionar Fornecedor';
        $('forn-nome').value = f ? fornecedorNomeDe(f) : '';
        $('forn-cnpj').value = f ? (valor(f, 'fornecedor_cnpj', 'cnpj') || '') : '';
        $('forn-telefone').value = f ? (valor(f, 'fornecedor_telefone', 'telefone') || '') : '';
        $('forn-email').value = f ? (valor(f, 'fornecedor_email', 'email') || '') : '';
        UI.abrirModal('modal-fornecedor');
    },

    async salvar(evento) {
        evento.preventDefault();
        const id = $('forn-id').value;
        const payload = {
            nome: $('forn-nome').value.trim(),
            cnpj: $('forn-cnpj').value.trim() || null,
            telefone: $('forn-telefone').value.trim() || null,
            email: $('forn-email').value.trim() || null,
        };
        try {
            await api(id ? `/fornecedores/${id}` : '/fornecedores', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
            UI.fecharModal('modal-fornecedor');
            await this.carregar();
            Telas.compras.carregar().catch(() => {});
            UI.sucesso(id ? 'Fornecedor atualizado.' : 'Fornecedor cadastrado.');
        } catch (erro) { UI.erro(erro); }
    },
};

function abrirFornecedor(id = null) { return Telas.fornecedores.abrir(id); }
function salvarFornecedor(e) { return Telas.fornecedores.salvar(e); }
