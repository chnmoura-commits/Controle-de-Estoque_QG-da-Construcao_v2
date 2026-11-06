/* Cliente HTTP da API. Centraliza fetch, tratamento de erro e cabeçalhos. */

async function api(path, options = {}) {
    const cabecalhos = { ...(options.headers || {}) };
    if (options.body) cabecalhos['Content-Type'] = 'application/json';

    const token = Sessao.token();
    if (token) cabecalhos['Authorization'] = `Bearer ${token}`;

    let response;
    try {
        response = await fetch(`${CONFIG.apiUrl}${path}`, { ...options, headers: cabecalhos });
    } catch (erro) {
        throw new Error(`Não foi possível conectar à API. Confira se o backend está rodando em ${CONFIG.apiUrl}.`);
    }

    const raw = await response.text();
    let body = null;
    try { body = raw ? JSON.parse(raw) : null; } catch { body = raw; }

    if (response.status === 401) {
        Sessao.encerrar();
        TelaLogin.exibir();
        throw new Error('Sessão expirada. Faça login novamente.');
    }

    if (!response.ok) {
        const detail = body?.erro || body?.detail || body?.mensagem ||
            (typeof body === 'string' ? body : `Erro HTTP ${response.status}`);
        throw new Error(detail);
    }
    return body;
}
