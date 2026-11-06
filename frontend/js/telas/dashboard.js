/* Painel: contagens gerais. */
const Telas = {};  // registro de todas as telas

Telas.dashboard = {
    async carregar() {
        try {
            const [produtos, alertas, fornecedores, categorias] = await Promise.all([
                api('/produtos'),
                api('/alertas'),
                api('/fornecedores'),
                api('/categorias'),
            ]);
            const resumo = alertas?.resumo || {};
            const totalAlertas = Number(resumo.zerados || 0) + Number(resumo.baixos || 0);

            $('dash-total-produtos').innerText = listaDe(produtos).length;
            $('dash-alertas-count').innerText = totalAlertas;
            $('dash-fornecedores-count').innerText = listaDe(fornecedores).length;
            $('dash-categorias-count').innerText = listaDe(categorias).length;

            $('alert-badge').innerText = totalAlertas;
            $('alert-badge').classList.toggle('hidden', totalAlertas === 0);
        } catch (erro) {
            console.error('Falha ao carregar dashboard:', erro);
            ['dash-total-produtos', 'dash-alertas-count', 'dash-fornecedores-count', 'dash-categorias-count']
                .forEach(id => $(id).innerText = '—');
        }
    },
};
