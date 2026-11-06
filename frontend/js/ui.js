/* Componentes de interface: notificações, modais e navegação entre telas. */

const UI = {
    /* Exibe notificação temporária. tipo: 'sucesso' | 'erro' | 'info'. */
    toast(mensagem, tipo = 'info') {
        const area = $('area-toasts');
        const el = document.createElement('div');
        el.className = `toast ${tipo}`;
        el.innerHTML = `<i data-lucide="${tipo === 'sucesso' ? 'check-circle' : tipo === 'erro' ? 'alert-circle' : 'info'}" class="w-4 h-4 mt-0.5 flex-shrink-0"></i><span>${esc(mensagem)}</span>`;
        area.appendChild(el);
        if (window.lucide) lucide.createIcons();
        setTimeout(() => el.remove(), 4000);
    },

    sucesso(mensagem) { this.toast(mensagem, 'sucesso'); },
    erro(erro) {
        console.error(erro);
        this.toast(erro.message || 'Ocorreu um erro inesperado.', 'erro');
    },

    abrirModal(id) {
        const el = $(id);
        el.classList.remove('hidden');
        el.classList.add('flex');
        ModalHooks.aoAbrir(id);
    },

    fecharModal(id) {
        const el = $(id);
        el.classList.add('hidden');
        el.classList.remove('flex');
    },

    /* Troca a tela visível e dispara o carregamento correspondente. */
    trocarTela(idTela) {
        document.querySelectorAll('.content-view').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active-tab'));
        $(`view-${idTela}`).classList.remove('hidden');
        $(`tab-${idTela}`).classList.add('active-tab');

        const carregadores = {
            dashboard: () => Telas.dashboard.carregar(),
            produtos: () => Telas.produtos.carregar(),
            reativar: () => Telas.reativar.carregar(),
            movimentacoes: () => Telas.inventario.carregar(),
            alertas: () => Telas.alertas.carregar(),
            compras: () => Telas.compras.carregar(),
            fornecedores: () => Telas.fornecedores.carregar(),
            clientes: () => Telas.clientes.carregar(),
            colaboradores: () => Telas.colaboradores.carregar(),
            categorias: () => Telas.categorias.carregar(),
            locais: () => Telas.locais.carregar($('locais-mostrar-inativos')?.checked),
            inventario: () => Telas.inventario.carregar(),
            vendas: () => Telas.vendas.carregar(),
        };
        carregadores[idTela]?.();

        // Recria os ícones da tela que acabou de ser exibida.
        if (window.lucide) lucide.createIcons();
    },
};

/* Ganchos executados ao abrir alguns modais (dependentes da tela). */
const ModalHooks = {
    aoAbrir(id) {
        if (id === 'modal-movimentacao') Telas.movimentacoes.preparar();
        if (id === 'modal-produto') Telas.produtos.carregarOpcoesFormulario();
        if (id === 'modal-compra') Telas.compras.preparar();
    },
};

/* Atalho global usado no HTML (onclick="openModal(...)"). */
function openModal(id) { UI.abrirModal(id); }
function closeModal(id) { UI.fecharModal(id); }
function switchTab(id) { UI.trocarTela(id); }
