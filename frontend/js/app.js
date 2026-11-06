/* Inicialização do painel: exibe usuário logado e carrega a tela inicial. */

const App = {
    iniciar() {
        if (Sessao.ativa() && Sessao.trocaPendente()) {
            // Sessão iniciada, mas a senha provisória ainda não foi trocada.
            TelaTrocaSenha.exibir(Sessao.usuario());
        } else if (Sessao.ativa()) {
            TelaLogin.esconder();
            this.iniciarPainel();
        } else {
            TelaLogin.exibir();
        }
    },

    iniciarPainel() {
        const usuario = Sessao.usuario();
        const el = $('usuario-logado');
        if (el) el.innerText = usuario || '';
        // Colaboradores é exclusivo do administrador: esconde o menu para os
        // demais perfis (o backend também barra com 403).
        const menuColaboradores = $('tab-colaboradores');
        if (menuColaboradores) menuColaboradores.classList.toggle('hidden', !Sessao.ehAdmin());
        if (window.lucide) lucide.createIcons();
        Telas.dashboard.carregar();
        Telas.reativar.carregar().catch(() => {});
    },
};

window.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) lucide.createIcons();
    App.iniciar();
});

