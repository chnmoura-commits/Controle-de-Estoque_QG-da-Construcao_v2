/* Tela de clientes: listagem, busca, cadastro/edição e ativar/desativar.
   Clientes não fazem login; são associados (opcionalmente) às vendas. */

function clienteId(c) { return valor(c, 'cliente_id', 'id'); }
function clienteNome(c) { return valor(c, 'cliente_nome', 'nome') || 'Sem nome'; }
function clienteAtivo(c) {
    const a = valor(c, 'cliente_ativo', 'ativo');
    return a !== 0 && a !== false;
}

Telas.clientes = {
    _lista: [],

    async carregar() {
        const busca = $('clientes-busca')?.value.trim();
        const inativos = $('clientes-mostrar-inativos')?.checked;
        const params = new URLSearchParams();
        if (busca) params.set('busca', busca);
        if (inativos) params.set('incluir_inativos', 'true');
        const qs = params.toString();
        try {
            this._lista = listaDe(await api('/clientes' + (qs ? '?' + qs : '')));
            $('lista-clientes').innerHTML = this._lista.length ? this._lista.map(c => {
                const id = Number(clienteId(c));
                const ativo = clienteAtivo(c);
                return `<tr class="hover:bg-vermelhao-20 ${ativo ? '' : 'opacity-60'}">
                    <td class="p-4 font-mono text-xs text-vermelhao-130">#${esc(id)}</td>
                    <td class="p-4 font-semibold text-vermelhao-180">${esc(clienteNome(c))}</td>
                    <td class="p-4">${esc(valor(c, 'cliente_cpf', 'cpf') || '—')}</td>
                    <td class="p-4">${esc(valor(c, 'cliente_telefone', 'telefone') || '—')}</td>
                    <td class="p-4">${esc(valor(c, 'cliente_email', 'email') || '—')}</td>
                    <td class="p-4"><span class="px-2 py-0.5 rounded text-xs font-semibold ${ativo ? 'bg-success-100 text-success-700' : 'bg-vermelhao-60 text-vermelhao-130'}">${ativo ? 'Ativo' : 'Inativo'}</span></td>
                    <td class="p-4 text-center space-x-3 whitespace-nowrap">
                        <button onclick="Telas.clientes.abrir(${id})" class="text-info-600 hover:text-info-800 text-xs font-semibold">Editar</button>
                        <button onclick="Telas.clientes.definirAtivo(${id}, ${!ativo})" class="${ativo ? 'text-danger-600 hover:text-danger-800' : 'text-success-600 hover:text-success-800'} text-xs font-semibold">${ativo ? 'Desativar' : 'Reativar'}</button>
                    </td>
                </tr>`;
            }).join('') : '<tr class="linha-tabela-vazia"><td colspan="7">Nenhum cliente encontrado.</td></tr>';
        } catch (erro) {
            $('lista-clientes').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="7" class="text-danger-600">${esc(erro.message)}</td></tr>`;
        }
    },

    abrir(id = null) {
        const c = id != null ? this._lista.find(x => String(clienteId(x)) === String(id)) : null;
        $('cli-id').value = c ? clienteId(c) : '';
        $('cli-titulo').innerText = c ? 'Editar Cliente' : 'Novo Cliente';
        $('cli-nome').value = c ? clienteNome(c) : '';
        $('cli-cpf').value = c ? (valor(c, 'cliente_cpf', 'cpf') || '') : '';
        $('cli-telefone').value = c ? (valor(c, 'cliente_telefone', 'telefone') || '') : '';
        $('cli-email').value = c ? (valor(c, 'cliente_email', 'email') || '') : '';
        $('cli-endereco').value = c ? (valor(c, 'cliente_endereco', 'endereco') || '') : '';
        UI.abrirModal('modal-cliente');
    },

    async salvar(evento) {
        evento.preventDefault();
        const id = $('cli-id').value;
        const payload = {
            nome: $('cli-nome').value.trim(),
            cpf: $('cli-cpf').value.trim() || null,
            telefone: $('cli-telefone').value.trim() || null,
            email: $('cli-email').value.trim() || null,
            endereco: $('cli-endereco').value.trim() || null,
        };
        try {
            await api(id ? `/clientes/${id}` : '/clientes', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
            UI.fecharModal('modal-cliente');
            await this.carregar();
            UI.sucesso(id ? 'Cliente atualizado.' : 'Cliente cadastrado.');
        } catch (erro) { UI.erro(erro); }
    },

    async definirAtivo(id, ativo) {
        if (!confirm(ativo ? 'Reativar este cliente?' : 'Desativar este cliente? As vendas antigas são mantidas.')) return;
        try {
            await api(`/clientes/${Number(id)}/ativo`, { method: 'POST', body: JSON.stringify({ ativo }) });
            await this.carregar();
            UI.sucesso(ativo ? 'Cliente reativado.' : 'Cliente desativado.');
        } catch (erro) { UI.erro(erro); }
    },
};

function abrirCliente(id = null) { return Telas.clientes.abrir(id); }
function salvarCliente(e) { return Telas.clientes.salvar(e); }
