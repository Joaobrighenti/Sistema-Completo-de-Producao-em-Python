import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from banco_dados.banco import df_pcp, df_baixas, df_clientes, Banco
import time
from banco_dados.banco import authenticate_user
from compras.pages import page_principal_compras
from login import login
from app import *
from pcp import  pag_principal, sidebar
from pagina_inicial import pagina_inicial
from qualidade import page_qualidade
from qualidade import page_inpecao_processo
from qualidade.page_laudos import layout as page_laudos_layout
from compras.pages import page_descarregamento
from dashboards import dash_relatorio
from compras.pages.relatorio_estoque import layout as relatorio_estoque_layout
from login.formularios.form_controle_usuario import layout as controle_usuario_layout
from dashboards import dashboard_pcp
from oee.pagina_oee import layout as pagina_oee_layout
from dashboards.dashboard_oee import layout as dashboard_oee_layout
from dashboards import dashboard_oee_setor
from dashboards import dashboard_apontamento
from modulo_pizza.Entregas_pizza import layout_dashboard as pizza_layout
from dashboards import dashboard_dre, dashboard_oee_geral, dashboard_quali
from dashboards.dashboard_produtos import layout as dashboard_produtos_layout
from dashboards.carregamento import layout as carregamento_layout

#ESTRUTURA DE STORE INTERMEDIARIO==============
data_int = {
        'pcp_id': [], 
        'pcp_oc': [],
        'pcp_pcp': [],
        'pcp_categoria': [],
        'pcp_cliente_id': [],
        'pcp_produto_id': [],
        'pcp_qtd': [],
        'pcp_entrega': [],
        'pcp_odc': [],
        'pcp_observacao': [],
        'pcp_primiera_entrega': [],
        'pcp_emissao': [],
        'pcp_cod_prod': [],
        'pcp_imp': [],
        'pcp_aca': [],
        'cliente_nome': [],
        'pcp_chapa_id': [],
        'nome_produto': [],
        'ocorrencia_ordem_producao': [],
        'pcp_bopp': [],
        'pcp_terceirizacao': [], 
        'pcp_faca_id': [],      
        'disabled': []
   
    }

data_pote = {
    'po_id': [],            
    'po_pcp': [],           
    'po_tamanho': [],       
    'po_vendedor': [],      
    'po_cliente': [],         
    'po_qtd': [],           
    'po_data_emissao': [],  
    'po_data_entrega': [], 
    'po_codigo': [],         
    'po_obs': [],             
    'disabled': []
    }

data_baixa = {
    'baixa_id': [],
    'pcp': [],
    'qtd': [],
    'pallets': [],
    'turno': [],
    'maquina': [],
    'observacao': [],
    'data': [],
    'data': [],
    'categoria_qualidade': [],
    'ajuste': [],
    'disabled': []
}

data_retirada = {
    'ret_id': [],
    'ret_id_pcp': [],
    'ret_qtd': [],
    'ret_data': [],
    'ret_obs': [],
    'disabled': []
}

store_int = pd.DataFrame(data_int)
pote_int = pd.DataFrame(data_pote)
baixa_int = pd.DataFrame(data_baixa)
retirada_int = pd.DataFrame(data_retirada)
banco = Banco()

df_retirada = banco.ler_tabela('retirada')
app.title = "PCP"
app._favicon = "producao.png"

# =========  LAYOUT  =========== #
app.layout = dbc.Container(children=[

    #STORE INTERMEDIARIO
    dcc.Location(id="url"),
    dcc.Store(id='sidebar-state', data='open'),
    dcc.Store(id='store_intermedio', data=store_int.to_dict()),
    dcc.Store(id='store_int_pote', data=pote_int.to_dict()),
    dcc.Store(id='store_int_baixa', data=baixa_int.to_dict()),
    dcc.Store(id='store_int_retirada', data=retirada_int.to_dict()),
    
    #TABELAS SESSION
    dcc.Store(id='store_pcp', data=df_pcp.to_dict(), storage_type='session'),
    dcc.Store(id='store_cliente', data=df_clientes.to_dict(), storage_type='session'),
    dcc.Store(id='store_baixa', data=df_baixas.to_dict(), storage_type='session'),
    dcc.Store(id='store_retirada', data=df_retirada.to_dict(), storage_type='session'),
    
    
    dcc.Store(id="login-state", data=""),
    dcc.Store(id="register-state", data=""),

    html.Div(id='login-area', children=login.layout, style={"maxWidth": "400px", "margin": "0 auto", "paddingTop": "50px"}),

        html.Div(id='protected-content', children=[
        dcc.Store(id='store-login-state', storage_type='session'),

        dbc.Row([
            dbc.Col([sidebar.layout], id='sidebar-col', md=2, style={'padding': '0px', 'transition': 'width 0.5s'}),
            dbc.Col([dbc.Container(id="page-content", fluid=True)], id='content-col', md=10, style={'padding': '0px'}),
        ])
    ], style={"display": "none"}),  # Inicialmente escondido, é atualizado no callback
], fluid=True)
    

@app.callback(
    [Output('login-feedback', 'children'),
     Output('protected-content', 'style'),
     Output('login-area', 'style'),
     Output('store-login-state', 'data'),
     Output('sidebar-username', 'children'),
     Output('url', 'pathname')],

    [Input('btn-login', 'n_clicks'),
     Input('btn-logout', 'n_clicks')],
    [State('input-username', 'value'),
     State('input-password', 'value'),
     State('store-login-state', 'data')]
)
def handle_login_logout(n_clicks_login, n_clicks_logout, username, password, login_state):
    from dash import callback_context
    ctx = callback_context

    # Se não há ação disparada, retorna o estado atual
    if not ctx.triggered:
        # Se houver um login válido no sessionStorage, carrega o estado
        if login_state and login_state.get('logged_in') == 'true':
            return "", {"display": "block"}, {"display": "none"}, login_state, f"Bem-vindo, {login_state.get('username')}!", dash.no_update
        # Caso contrário, retorna o estado de login com a área de login visível
        return "", {"display": "none"}, {"display": "block"}, login_state, "", dash.no_update

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Se for o botão de login
    if triggered_id == 'btn-login':
        user_level = authenticate_user(username, password)
        if user_level:
            login_state = {'logged_in': 'true', 'user_level': user_level, 'username': username}
            return "", {"display": "block"}, {"display": "none"}, login_state, f"Bem-vindo, {username}!", "/"
        return "Usuário ou senha inválidos.", {"display": "none"}, {"display": "block"}, None, "", dash.no_update

    # Se for o botão de logout
    if triggered_id == 'btn-logout':
        login_state = {'logged_in': 'false', 'user_level': '', 'username': ''}
        return None, {"display": "none"}, {"display": "block"}, login_state, "Usuário Desconhecido", dash.no_update

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output('sidebar-state', 'data'),
    Input('btn-toggle-sidebar', 'n_clicks'),
    State('sidebar-state', 'data'),
    prevent_initial_call=True
)
def toggle_sidebar_state(n_clicks, current_state):
    if n_clicks:
        return 'closed' if current_state == 'open' else 'open'
    return dash.no_update

@app.callback(
    [Output('sidebar-col', 'style'),
     Output('content-col', 'md')],
    Input('sidebar-state', 'data')
)
def toggle_sidebar_layout(state):
    if state == 'closed':
        return {'display': 'none'}, 12
    return {'display': 'block', 'padding': '0px', 'transition': 'width 0.5s ease-in-out'}, 10

# ======= CALLBACKS ======== #
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page_content(pathname):

    if pathname == "/pcp":
        return pag_principal.layout
    elif pathname == "/":
        return pagina_inicial.layout
    
    # Rota para o sistema de compras
    elif pathname == "/compras":
        return page_principal_compras.layout
    
    # Rota para a página de relatórios
    elif pathname == "/compras/relatorio":
        return dash_relatorio.layout

    # Nova rota para o relatório de estoque
    elif pathname == "/relatorioestoque":
        return relatorio_estoque_layout

    elif pathname == "/entregamercadoria":
        return page_descarregamento.layout

    elif pathname == "/dashpcp":
        return dashboard_pcp.layout

    elif pathname == "/qualidade":
        return page_qualidade.layout
    
    elif pathname == "/dashprodutosnicopel":
        return dashboard_produtos_layout
    
    elif pathname == "/inspecaoprocessos":
        return page_inpecao_processo.layout
    
    elif pathname == "/laudosqualidade":
        return page_laudos_layout
    
    # Rotas para o sistema OEE
    elif pathname == "/oee":
        return pagina_oee_layout
    
    elif pathname == "/dashboard-oee":
        return dashboard_oee_layout
    
    elif pathname == "/dashoeegeral":
        return dashboard_oee_geral.layout
    
    elif pathname == "/dashoeesetor":
        return dashboard_oee_setor.layout
    
    elif pathname == "/relatorioapontamento":
        return dashboard_apontamento.layout

    elif pathname == "/painelclientesestoque":
        return pizza_layout()
    
    elif pathname == "/dashboardqualidade":
        return dashboard_quali.layout
    
    elif pathname == "/demonstrativo":
        return dashboard_dre.layout

    elif pathname == "/controleusuarios":
        return controle_usuario_layout
    
    elif pathname == "/agendamentologistica":
        return carregamento_layout

    return dbc.Container(
        [
            html.H1("404: Not Found", className="text-danger"),
            html.Hr(),
            html.P(f"O caminho '{pathname}' não foi reconhecido."),
            html.P("Use a NavBar para retornar ao sistema."),
        ]
    )


if __name__ == '__main__':

    while True:
        try:
            # app.run(debug=True)
            app.run(host='0.0.0.0', port=8052, debug=False)

        except Exception as e:
            print(f"Erro encontrado: {e}. Reiniciando a aplicação em 5 segundos...")
            time.sleep(5)