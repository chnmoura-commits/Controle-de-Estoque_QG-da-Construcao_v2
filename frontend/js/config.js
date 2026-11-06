/* Configuração do frontend.
   A URL da API pode ser definida em window.QG_CONFIG antes deste script,
   ex.: <script>window.QG_CONFIG = { apiUrl: 'https://api.exemplo.com' };</script>
   Caso contrário usa o padrão de desenvolvimento local. */
const CONFIG = Object.freeze({
    apiUrl: (window.QG_CONFIG && window.QG_CONFIG.apiUrl) || 'http://127.0.0.1:8000',
    chaveSessao: 'qg_estoque_sessao',
});
