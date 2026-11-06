/* Tela de locais: depósito e lojas (onde o estoque fica e de onde ele sai). */

function localCodigo(l) { return valor(l, 'local_codigo', 'codigo'); }
function localNome(l) { return valor(l, 'local_nome', 'nome') || 'Sem nome'; }
function localTipo(l) { return valor(l, 'local_tipo', 'tipo') || 'loja'; }
function localAtivo(l) { return Number(valor(l, 'local_ativo', 'ativo') ?? 1) === 1; }

const TipoLocal = {
    rotulo(tipo) { return tipo === 'deposito' ? 'Depósito' : 'Loja'; },
    classe(tipo) {
        return tipo === 'deposito' ? 'bg-info-100 text-info-700' : 'bg-success-100 text-success-700';
    },
};

Telas.locais = {
    _lista: [],

    async carregar(incluirInativos = false) {
        try {
            const url = '/locais' + (incluirInativos ? '?incluir_inativos=true' : '');
            this._lista = listaDe(await api(url));
            $('lista-locais').innerHTML = this._lista.length ? this._lista.map(l => {
                const codigo = localCodigo(l);
                const tipo = localTipo(l);
                const ativo = localAtivo(l);
                const podeExcluir = Number(valor(l, 'pode_excluir') ?? 0) === 1;
                const acoes = [`<button onclick="Telas.locais.abrir('${esc(codigo)}')" class="text-info-600 hover:text-info-800 text-xs font-semibold">Editar</button>`];
                if (tipo !== 'deposito') {
                    acoes.push(ativo
                        ? `<button onclick="Telas.locais.definirAtivo('${esc(codigo)}', false)" class="text-warning-600 hover:text-warning-800 text-xs font-semibold">Desativar</button>`
                        : `<button onclick="Telas.locais.definirAtivo('${esc(codigo)}', true)" class="text-success-600 hover:text-success-800 text-xs font-semibold">Reativar</button>`);
                    if (podeExcluir) {
                        acoes.push(`<button onclick="Telas.locais.excluir('${esc(codigo)}')" class="text-danger-600 hover:text-danger-800 text-xs font-semibold">Excluir</button>`);
                    }
                }
                const contato = [valor(l, 'local_telefone'), valor(l, 'local_email')].filter(Boolean).join(' · ') || '—';
                return `<tr class="hover:bg-vermelhao-20 ${ativo ? '' : 'opacity-60'}">
                    <td class="p-4 font-semibold text-vermelhao-180">
                        ${esc(localNome(l))}
                        <div class="text-xs font-normal text-vermelhao-110 font-mono">${esc(codigo)}</div>
                    </td>
                    <td class="p-4"><span class="px-2 py-0.5 rounded text-xs font-semibold ${TipoLocal.classe(tipo)}">${TipoLocal.rotulo(tipo)}</span></td>
                    <td class="p-4 text-xs">${esc(valor(l, 'local_cnpj') || '—')}${valor(l, 'local_endereco') ? '<div class="text-vermelhao-110">' + esc(valor(l, 'local_endereco')) + '</div>' : ''}</td>
                    <td class="p-4 text-xs">${esc(contato)}</td>
                    <td class="p-4 font-semibold">${numero(valor(l, 'saldo_total') ?? 0)}</td>
                    <td class="p-4"><span class="text-xs font-semibold ${ativo ? 'text-success-600' : 'text-vermelhao-110'}">${ativo ? 'Ativo' : 'Inativo'}</span></td>
                    <td class="p-4 text-center space-x-3 whitespace-nowrap">${acoes.join('')}</td>
                </tr>`;
            }).join('') : '<tr class="linha-tabela-vazia"><td colspan="7">Nenhum local cadastrado.</td></tr>';
        } catch (erro) {
            $('lista-locais').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="7" class="text-danger-600">${esc(erro.message)}</td></tr>`;
        }
    },

    abrir(codigo = null) {
        const l = codigo != null ? this._lista.find(x => String(localCodigo(x)) === String(codigo)) : null;
        const editando = !!l;
        $('local-codigo-original').value = editando ? localCodigo(l) : '';
        $('local-titulo').innerText = editando ? 'Editar Local' : 'Novo Local';
        $('local-nome').value = editando ? localNome(l) : '';
        $('local-codigo').value = editando ? localCodigo(l) : '';
        $('local-tipo').value = editando ? localTipo(l) : 'loja';
        $('local-tipo').disabled = editando && localTipo(l) === 'deposito';
        $('local-cnpj').value = editando ? (valor(l, 'local_cnpj') || '') : '';
        $('local-endereco').value = editando ? (valor(l, 'local_endereco') || '') : '';
        $('local-telefone').value = editando ? (valor(l, 'local_telefone') || '') : '';
        $('local-email').value = editando ? (valor(l, 'local_email') || '') : '';
        $('local-dica-codigo').innerText = editando
            ? 'O código é a identificação do local no histórico. Só altere se for necessário.'
            : 'Opcional: se vazio, é gerado a partir do nome (ex.: "Loja Centro" → loja-centro).';
        UI.abrirModal('modal-local');
    },

    async salvar(evento) {
        evento.preventDefault();
        const original = $('local-codigo-original').value;
        const limpo = id => $(id).value.trim() || null;
        const payload = {
            nome: $('local-nome').value.trim(),
            tipo: $('local-tipo').value,
            codigo: limpo('local-codigo'),
            cnpj: limpo('local-cnpj'),
            endereco: limpo('local-endereco'),
            telefone: limpo('local-telefone'),
            email: limpo('local-email'),
        };
        try {
            await api(original ? `/locais/${encodeURIComponent(original)}` : '/locais', {
                method: original ? 'PUT' : 'POST', body: JSON.stringify(payload),
            });
            UI.fecharModal('modal-local');
            await this.carregar(true);
            UI.sucesso(original ? 'Local atualizado.' : 'Local cadastrado.');
        } catch (erro) { UI.erro(erro); }
    },

    async definirAtivo(codigo, ativo) {
        if (!confirm(`${ativo ? 'Reativar' : 'Desativar'} o local "${codigo}"?` +
            (ativo ? '' : ' Locais inativos não recebem estoque nem aparecem nas escolhas.'))) return;
        try {
            await api(`/locais/${encodeURIComponent(codigo)}/${ativo ? 'reativar' : 'desativar'}`, { method: 'POST' });
            await this.carregar(true);
            UI.sucesso(`Local ${ativo ? 'reativado' : 'desativado'}.`);
        } catch (erro) { UI.erro(erro); }
    },

    async excluir(codigo) {
        if (!confirm(`Excluir o local "${codigo}"? Essa ação não pode ser desfeita.`)) return;
        try {
            await api(`/locais/${encodeURIComponent(codigo)}`, { method: 'DELETE' });
            await this.carregar(true);
            UI.sucesso('Local excluído.');
        } catch (erro) { UI.erro(erro); }
    },
};

/* Opções de local para os <select> de movimentação/compra/venda.
   `filtro` permite, por exemplo, listar apenas o depósito ou apenas as lojas. */
async function carregarOpcoesLocais(idSelect, filtro = null, valorPadrao = null) {
    const locais = listaDe(await api('/locais')).filter(filtro || (() => true));
    const select = $(idSelect);
    if (!select) return locais;
    select.innerHTML = locais.map(l =>
        `<option value="${esc(localCodigo(l))}">${esc(localNome(l))} (${TipoLocal.rotulo(localTipo(l))})</option>`
    ).join('') || '<option value="">Cadastre um local primeiro</option>';
    if (valorPadrao && locais.some(l => String(localCodigo(l)) === String(valorPadrao))) {
        select.value = valorPadrao;
    }
    return locais;
}

function abrirLocal(codigo = null) { return Telas.locais.abrir(codigo); }
function salvarLocal(e) { return Telas.locais.salvar(e); }
