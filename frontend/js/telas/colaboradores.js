/* Tela de colaboradores (usuários do sistema) — exclusiva do administrador.
   A senha é sempre gerada pelo backend e mostrada uma única vez. */

function colabId(c) { return valor(c, 'usuario_id', 'id'); }
function colabUsuario(c) { return valor(c, 'usuario_nome', 'usuario') || ''; }
function colabNome(c) { return valor(c, 'usuario_nome_completo', 'nome_completo', 'nome') || colabUsuario(c); }
function colabAtivo(c) { const a = valor(c, 'usuario_ativo', 'ativo'); return a !== 0 && a !== false; }

const PERFIL_ROTULO = { admin: 'Administrador', gerente: 'Gerente', vendedor: 'Vendedor' };

Telas.colaboradores = {
    _lista: [],

    async carregar() {
        const busca = $('colab-busca')?.value.trim();
        try {
            this._lista = listaDe(await api('/colaboradores' + (busca ? '?busca=' + encodeURIComponent(busca) : '')));
            const eu = (window.Sessao && Sessao.obter && Sessao.obter()) || {};
            const meuId = eu.usuario_id;
            $('lista-colaboradores').innerHTML = this._lista.length ? this._lista.map(c => {
                const id = Number(colabId(c));
                const ativo = colabAtivo(c);
                const provisoria = Number(valor(c, 'usuario_senha_provisoria', 'senha_provisoria') || 0) === 1;
                const souEu = String(id) === String(meuId);
                const perfil = valor(c, 'usuario_perfil', 'perfil') || '';
                return `<tr class="hover:bg-vermelhao-20 ${ativo ? '' : 'opacity-60'}">
                    <td class="p-4 font-mono text-xs text-vermelhao-130">#${esc(id)}</td>
                    <td class="p-4 font-semibold text-vermelhao-180">${esc(colabNome(c))}${souEu ? ' <span class="text-xs font-normal text-vermelhao-110">(você)</span>' : ''}</td>
                    <td class="p-4 font-mono text-xs">${esc(colabUsuario(c))}</td>
                    <td class="p-4"><span class="px-2 py-0.5 rounded text-xs font-semibold bg-vermelhao-40 text-vermelhao-150">${esc(PERFIL_ROTULO[perfil] || perfil || '—')}</span></td>
                    <td class="p-4">${esc(valor(c, 'usuario_cpf', 'cpf') || '—')}</td>
                    <td class="p-4"><div>${esc(valor(c, 'usuario_telefone', 'telefone') || '—')}</div><div class="text-xs text-vermelhao-110">${esc(valor(c, 'usuario_email', 'email') || '')}</div></td>
                    <td class="p-4"><span class="px-2 py-0.5 rounded text-xs font-semibold ${ativo ? 'bg-success-100 text-success-700' : 'bg-vermelhao-60 text-vermelhao-130'}">${ativo ? 'Ativo' : 'Inativo'}</span>${provisoria ? ' <span class="text-xs text-info-600" title="Senha provisória ainda não trocada">· senha provisória</span>' : ''}</td>
                    <td class="p-4 text-center space-x-3 whitespace-nowrap">
                        <button onclick="Telas.colaboradores.abrir(${id})" class="text-info-600 hover:text-info-800 text-xs font-semibold">Editar</button>
                        <button onclick="Telas.colaboradores.resetarSenha(${id})" class="text-vermelhao-140 hover:text-vermelhao-160 text-xs font-semibold">Resetar senha</button>
                        ${souEu ? '' : `<button onclick="Telas.colaboradores.definirAtivo(${id}, ${!ativo})" class="${ativo ? 'text-danger-600 hover:text-danger-800' : 'text-success-600 hover:text-success-800'} text-xs font-semibold">${ativo ? 'Desativar' : 'Reativar'}</button>`}
                    </td>
                </tr>`;
            }).join('') : '<tr class="linha-tabela-vazia"><td colspan="8">Nenhum colaborador encontrado.</td></tr>';
        } catch (erro) {
            $('lista-colaboradores').innerHTML = `<tr class="linha-tabela-vazia"><td colspan="8" class="text-danger-600">${esc(erro.message)}</td></tr>`;
        }
    },

    abrir(id = null) {
        const c = id != null ? this._lista.find(x => String(colabId(x)) === String(id)) : null;
        $('colab-id').value = c ? colabId(c) : '';
        $('colab-titulo').innerText = c ? 'Editar Colaborador' : 'Novo Colaborador';
        $('colab-nome').value = c ? colabNome(c) : '';
        $('colab-usuario').value = c ? colabUsuario(c) : '';
        $('colab-cpf').value = c ? (valor(c, 'usuario_cpf', 'cpf') || '') : '';
        $('colab-telefone').value = c ? (valor(c, 'usuario_telefone', 'telefone') || '') : '';
        $('colab-email').value = c ? (valor(c, 'usuario_email', 'email') || '') : '';
        $('colab-perfil').value = c ? (valor(c, 'usuario_perfil', 'perfil') || 'vendedor') : 'vendedor';
        // O login (usuario) é imutável: some do formulário na edição.
        $('colab-campo-usuario').classList.toggle('hidden', !!c);
        if (c) $('colab-usuario').removeAttribute('required');
        else $('colab-usuario').setAttribute('required', '');
        UI.abrirModal('modal-colaborador');
    },

    async salvar(evento) {
        evento.preventDefault();
        const id = $('colab-id').value;
        // Na edição, o backend recebe ColaboradorIn (sem `usuario`).
        const payload = {
            nome_completo: $('colab-nome').value.trim(),
            cpf: $('colab-cpf').value.trim(),
            telefone: $('colab-telefone').value.trim(),
            email: $('colab-email').value.trim(),
            perfil: $('colab-perfil').value,
        };
        if (!id) payload.usuario = $('colab-usuario').value.trim();
        try {
            const r = await api(id ? `/colaboradores/${id}` : '/colaboradores', {
                method: id ? 'PUT' : 'POST', body: JSON.stringify(payload),
            });
            UI.fecharModal('modal-colaborador');
            await this.carregar();
            if (!id && r && r.senha_provisoria) this._mostrarSenha(r.senha_provisoria, 'Colaborador criado');
            else UI.sucesso('Colaborador atualizado.');
        } catch (erro) { UI.erro(erro); }
    },

    async resetarSenha(id) {
        if (!confirm('Gerar uma nova senha provisória para este colaborador? A senha atual deixa de funcionar.')) return;
        try {
            const r = await api(`/colaboradores/${Number(id)}/resetar-senha`, { method: 'POST' });
            await this.carregar();
            this._mostrarSenha(r.senha_provisoria, 'Nova senha provisória');
        } catch (erro) { UI.erro(erro); }
    },

    async definirAtivo(id, ativo) {
        if (!confirm(ativo ? 'Reativar este colaborador?' : 'Desativar este colaborador? Ele não poderá mais entrar no sistema.')) return;
        try {
            await api(`/colaboradores/${Number(id)}/ativo`, { method: 'POST', body: JSON.stringify({ ativo }) });
            await this.carregar();
            UI.sucesso(ativo ? 'Colaborador reativado.' : 'Colaborador desativado.');
        } catch (erro) { UI.erro(erro); }
    },

    _mostrarSenha(senha, titulo) {
        $('colab-senha-valor').innerText = senha || '';
        const aviso = $('colab-senha-aviso');
        aviso.querySelector('.font-semibold').innerText = titulo || 'Senha provisória gerada';
        aviso.classList.remove('hidden');
        UI.sucesso(titulo ? `${titulo}. Senha: ${senha}` : 'Senha provisória gerada.');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },
};

function abrirColaborador(id = null) { return Telas.colaboradores.abrir(id); }
function salvarColaborador(e) { return Telas.colaboradores.salvar(e); }
