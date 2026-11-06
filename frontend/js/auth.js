const Sessao = {
    _chave: CONFIG.chaveSessao,

    salvar(dados) {
        localStorage.setItem(this._chave, JSON.stringify(dados));
    },
    obter() {
        try {
            return JSON.parse(localStorage.getItem(this._chave) || 'null');
        } catch { return null; }
    },
    token() {
        return this.obter()?.token || null;
    },
    usuario() {
        return this.obter()?.usuario || null;
    },
    perfil() {
        const dados = this.obter();
        if (!dados) return null;
        if (dados.perfil) return dados.perfil;
        // Sessão antiga (antes de guardarmos o perfil): lê do próprio token,
        // cujo payload traz o campo `perfil`, e atualiza a sessão.
        const doToken = this._perfilDoToken(dados.token);
        if (doToken) {
            dados.perfil = doToken;
            this.salvar(dados);
        }
        return doToken;
    },
    _perfilDoToken(token) {
        try {
            const payload = JSON.parse(atob((token || '').split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
            return payload?.perfil || null;
        } catch { return null; }
    },
    ehAdmin() {
        return this.perfil() === 'admin';
    },
    trocaPendente() {
        return !!this.obter()?.trocar_senha;
    },
    marcarTrocada() {
        const dados = this.obter();
        if (dados) { dados.trocar_senha = false; this.salvar(dados); }
    },
    ativa() {
        return !!this.obter();
    },
    encerrar() {
        localStorage.removeItem(this._chave);
    },
};

const TelaLogin = {
    exibir() {
        $('tela-login').classList.remove('oculto');
        $('tela-troca-senha').classList.add('oculto');
        $('app').classList.add('oculto');
        $('login-senha').value = '';
        if (window.lucide) lucide.createIcons();
        $('login-usuario').focus();
    },

    esconder() {
        $('tela-login').classList.add('oculto');
        $('app').classList.remove('oculto');
    },

    async entrar(evento) {
        evento.preventDefault();
        const botao = $('login-botao');
        const erroEl = $('login-erro');
        erroEl.classList.add('oculto');
        botao.disabled = true;
        botao.innerText = 'Entrando…';

        try {
            const dados = await api('/auth/login', {
                method: 'POST',
                body: JSON.stringify({
                    usuario: $('login-usuario').value.trim(),
                    senha: $('login-senha').value,
                }),
            });
            Sessao.salvar({
                usuario: dados.usuario,
                usuario_id: dados.usuario_id,
                perfil: dados.perfil || null,
                token: dados.access_token || null,
                trocar_senha: !!dados.trocar_senha,
            });
            if (dados.trocar_senha) {
                // Primeiro acesso: obriga a definir uma nova senha antes de usar o sistema.
                TelaTrocaSenha.exibir(dados.usuario);
                return;
            }
            this.esconder();
            App.iniciarPainel();
            UI.sucesso(`Bem-vindo, ${dados.usuario}!`);
        } catch (erro) {
            erroEl.innerText = erro.message || 'Não foi possível entrar.';
            erroEl.classList.remove('oculto');
        } finally {
            botao.disabled = false;
            botao.innerText = 'Entrar';
        }
    },

    sair() {
        Sessao.encerrar();
        this.exibir();
    },
};

/* Troca de senha obrigatória no primeiro acesso (senha provisória). */
const TelaTrocaSenha = {
    exibir(usuario) {
        $('tela-login').classList.add('oculto');
        $('app').classList.add('oculto');
        $('tela-troca-senha').classList.remove('oculto');
        $('form-troca-senha').reset();
        $('troca-erro').classList.add('oculto');
        if (window.lucide) lucide.createIcons();
        $('troca-senha-atual').focus();
        if (usuario) $('troca-senha-atual').dataset.usuario = usuario;
    },

    async enviar(evento) {
        evento.preventDefault();
        const erroEl = $('troca-erro');
        const botao = $('troca-botao');
        const atual = $('troca-senha-atual').value;
        const nova = $('troca-senha-nova').value;
        const conf = $('troca-senha-conf').value;
        erroEl.classList.add('oculto');

        if (nova !== conf) {
            erroEl.innerText = 'As senhas não conferem.';
            erroEl.classList.remove('oculto');
            return;
        }

        botao.disabled = true;
        botao.innerText = 'Salvando…';
        try {
            await api('/auth/trocar-senha', {
                method: 'POST',
                body: JSON.stringify({ senha_atual: atual, senha_nova: nova }),
            });
            Sessao.marcarTrocada();
            $('tela-troca-senha').classList.add('oculto');
            TelaLogin.esconder();
            App.iniciarPainel();
            UI.sucesso('Senha alterada com sucesso!');
        } catch (erro) {
            erroEl.innerText = erro.message || 'Não foi possível alterar a senha.';
            erroEl.classList.remove('oculto');
        } finally {
            botao.disabled = false;
            botao.innerText = 'Salvar nova senha';
        }
    },

    sair() {
        Sessao.encerrar();
        TelaLogin.exibir();
    },
};
