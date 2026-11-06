/* Tela de categorias: listagem e cadastro/edição. */

function categoriaId(c) { return valor(c, 'categoria_id', 'id'); }
function categoriaNomeDe(c) { return valor(c, 'categoria_nome', 'nome') || 'Sem nome'; }

Telas.categorias = {
    _lista: [],

    async carregar() {
        try {
            this._lista = listaDe(await api('/categorias'));
            $('lista-categorias').innerHTML = this._lista.length ? this._lista.map(c => `
                <tr class="hover:bg-vermelhao-20">
                    <td class="p-4 font-mono text-xs text-vermelhao-130">#${esc(categoriaId(c))}</td>
                    <td class="p-4 font-semibold text-vermelhao-180">${esc(categoriaNomeDe(c))}</td>
                    <td class="p-4">${esc(valor(c, 'categoria_descricao', 'descricao') || '—')}</td>
                    <td class="p-4 text-center"><button onclick="Telas.categorias.abrir(${Number(categoriaId(c))})" class="text-info-600 hover:text-info-800 text-xs font-semibold">Editar</button></td>
                </tr>`).join('')
                : '<tr class="linha-tabela-vazia"><td colspan="4">Nenhuma categoria cadastrada.</td></tr>';
            $('dash-categorias-count').innerText = this._lista.length;
        } catch (erro) {
            $('lista-categorias').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="4" class="text-danger-600">${esc(erro.message)}</td></tr>`;
        }
    },

    abrir(id = null) {
        const c = id != null ? this._lista.find(x => String(categoriaId(x)) === String(id)) : null;
        $('cat-id').value = c ? categoriaId(c) : '';
        $('cat-titulo').innerText = c ? 'Editar Categoria' : 'Adicionar Categoria';
        $('cat-nome').value = c ? categoriaNomeDe(c) : '';
        $('cat-descricao').value = c ? (valor(c, 'categoria_descricao', 'descricao') || '') : '';
        UI.abrirModal('modal-categoria');
    },

    async salvar(evento) {
        evento.preventDefault();
        const id = $('cat-id').value;
        const payload = {
            nome: $('cat-nome').value.trim(),
            descricao: $('cat-descricao').value.trim() || null,
        };
        try {
            await api(id ? `/categorias/${id}` : '/categorias', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
            UI.fecharModal('modal-categoria');
            await this.carregar();
            Telas.produtos.carregar().catch(() => {});
            UI.sucesso(id ? 'Categoria atualizada.' : 'Categoria cadastrada.');
        } catch (erro) { UI.erro(erro); }
    },
};

function abrirCategoria(id = null) { return Telas.categorias.abrir(id); }
function salvarCategoria(e) { return Telas.categorias.salvar(e); }
