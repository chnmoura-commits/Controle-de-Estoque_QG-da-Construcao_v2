/* Funções utilitárias compartilhadas por todas as telas. */

const $ = (id) => document.getElementById(id);

/* Lê a primeira chave existente e preenchida de um objeto (tolerante a variações de nome). */
function valor(obj, ...chaves) {
    for (const chave of chaves) {
        if (obj && obj[chave] !== undefined && obj[chave] !== null) return obj[chave];
    }
    return null;
}

/* Escapa texto para uso seguro em HTML (evita XSS). */
function esc(v) {
    return String(v ?? '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

function numero(v) {
    return Number(v ?? 0).toLocaleString('pt-BR', { maximumFractionDigits: 3 });
}

function moeda(v) {
    return Number(v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function dataBR(v) {
    if (!v) return '—';
    const m = String(v).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (m) return `${m[3]}/${m[2]}/${m[1]}`;
    const d = new Date(v);
    return isNaN(d) ? esc(v) : d.toLocaleDateString('pt-BR');
}

/* Converte a resposta da API em lista, aceitando array puro ou objeto com .itens. */
function listaDe(d) {
    return Array.isArray(d) ? d : (d?.itens || []);
}

/* Preenche um <select> com opções de uma lista. */
function preencherSelect(id, lista, getId, getNome, vazio) {
    $(id).innerHTML = (vazio != null ? `<option value="">${esc(vazio)}</option>` : '') +
        lista.map(x => `<option value="${esc(getId(x))}">${esc(getNome(x))}</option>`).join('');
}
