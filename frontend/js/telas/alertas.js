/* Tela de alertas de estoque (zerados, baixos, excesso). */

Telas.alertas = {
    async carregar() {
        try {
            const resposta = await api('/alertas');
            const grupos = [
                ...(resposta?.zerados || []).map(p => ({ ...p, _tipo: 'Estoque zerado' })),
                ...(resposta?.baixos || []).map(p => ({ ...p, _tipo: 'Estoque baixo' })),
                ...(resposta?.excesso || []).map(p => ({ ...p, _tipo: 'Estoque em excesso' })),
            ];
            $('lista-alertas').innerHTML = grupos.length ? grupos.map(a => {
                const baixo = a._tipo !== 'Estoque em excesso';
                const maximo = valor(a, 'produto_estoque_maximo', 'estoque_maximo');
                return `<div class="${baixo ? 'bg-danger-50 border-danger-200' : 'bg-warn-50 border-warn-200'} border rounded-lg p-4 flex justify-between items-center">
                    <div>
                        <h4 class="font-bold ${baixo ? 'text-danger-800' : 'text-warn-800'}">${esc(produtoNome(a))}</h4>
                        <p class="text-xs ${baixo ? 'text-danger-600' : 'text-warn-700'}">Saldo: ${numero(produtoSaldo(a))} | Mínimo: ${numero(valor(a, 'produto_estoque_minimo', 'estoque_minimo'))} | Máximo: ${maximo == null ? '—' : numero(maximo)}</p>
                    </div>
                    <span class="${baixo ? 'bg-danger-200 text-danger-800' : 'bg-warn-200 text-warn-800'} text-xs px-2 py-1 rounded font-semibold">${esc(a._tipo)}</span>
                </div>`;
            }).join('') : '<p class="text-vermelhao-130 text-sm">Nenhum alerta de estoque no momento.</p>';

            const resumo = resposta?.resumo || {};
            const total = Number(resumo.zerados || 0) + Number(resumo.baixos || 0);
            $('alert-badge').innerText = total;
            $('alert-badge').classList.toggle('hidden', total === 0);
            $('dash-alertas-count').innerText = total;
        } catch (erro) {
            $('lista-alertas').innerHTML = `<p class="text-danger-600 text-sm">${esc(erro.message)}</p>`;
            throw erro;
        }
    },
};
