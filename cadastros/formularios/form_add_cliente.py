
from dash import html, dcc, callback, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from app import app
from dash.exceptions import PreventUpdate
import dash

from banco_dados.banco import Banco

def get_tabela_clientes():
    """Cria a tabela de clientes para exibição."""
    try:
        banco = Banco()
        df_clientes = banco.ler_tabela("clientes")
        
        if df_clientes.empty:
            return html.Div("Nenhum cliente cadastrado.", className="text-center my-4")

        df_exibicao = df_clientes[['cliente_id', 'nome', 'cli_prazo', 'cli_forma_pagamento']].copy()
        df_exibicao.columns = ['ID', 'Nome', 'Prazo', 'Forma de Pagamento']

        tabela = dash_table.DataTable(
            id="tabela-clientes",
            columns=[{"name": col, "id": col} for col in df_exibicao.columns],
            data=df_exibicao.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '14px'},
            style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
            page_size=10,
            sort_action='native',
            filter_action='native',
            row_selectable='single',
        )
        
        return html.Div([
            tabela,
            html.Div([
                dbc.Button("Editar Selecionado", id="btn-editar-cliente", color="primary", className="me-2 mt-3"),
                dbc.Button("Excluir Selecionado", id="btn-excluir-cliente", color="danger", className="mt-3")
            ], className="d-flex")
        ])
    except Exception as e:
        return html.Div(f"Erro ao carregar clientes: {str(e)}", className="text-danger")

modal_principal = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle('GESTÃO DE CLIENTES')),
    dbc.ModalBody([
        dbc.Tabs([
            dbc.Tab(label="Cadastro", tab_id="tab-cadastro-cliente", children=[
                dbc.Form([
                    dcc.Input(id="cliente-id", type="hidden"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("NOME DO CLIENTE"),
                            dbc.Input(id="cliente_label", placeholder="Digite o nome do cliente...", type="text", required=True)
                        ], width=12),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("PRAZO DE PAGAMENTO"),
                            dbc.Input(id="cliente-prazo", placeholder="Ex: 30,60,90", type="text")
                        ], width=6),
                        dbc.Col([
                            dbc.Label("FORMA DE PAGAMENTO"),
                            dbc.Input(id="cliente-forma-pagamento", placeholder="Ex: Boleto", type="text")
                        ], width=6),
                    ], className="mb-3"),
                    html.Div(id='div_erro3', className="mt-3"),
                    html.Div([
                        dbc.Button("Limpar", id="cliente-btn-limpar", className="me-2", color="warning"),
                        dbc.Button('Salvar', id="incluir_cliente", color="success")
                    ], className="d-flex justify-content-end mt-4"),
                ]),
            ]),
            dbc.Tab(label="Clientes Cadastrados", tab_id="tab-listagem-clientes", children=[
                html.Div(id="tabela-clientes-container", className="mt-3")
            ]),
        ], id="tabs-cliente", active_tab="tab-cadastro-cliente"),
    ]),
    dbc.ModalFooter([
        dbc.Button("Fechar", id="cliente-btn-fechar-modal", n_clicks=0)
    ]),
], id='modal_inclusao_cliente', size='lg', is_open=False)

modal_confirmacao_exclusao = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Confirmar Exclusão")),
    dbc.ModalBody("Tem certeza que deseja excluir este cliente?"),
    dbc.ModalFooter([
        dbc.Button("Cancelar", id="cancel-delete-cliente", color="secondary"),
        dbc.Button("Excluir", id="confirm-delete-cliente", color="danger"),
    ]),
], id="modal-confirmar-exclusao-cliente", is_open=False)

layout = html.Div([
    modal_principal,
    modal_confirmacao_exclusao,
    dcc.Store(id='store-cliente-excluir', data=None)
])

@app.callback(
    Output("tabela-clientes-container", "children"),
    [Input("tabs-cliente", "active_tab"),
     Input("store_cliente", "data")]
)
def carregar_tabela_clientes(active_tab, data_store):
    ctx = dash.callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'No trigger'
    
    if active_tab == "tab-listagem-clientes" or triggered_id == "store_cliente":
        return get_tabela_clientes()
    return html.Div()

@app.callback(
    [Output('store_cliente', 'data', allow_duplicate=True),
     Output('div_erro3', "children", allow_duplicate=True),
     Output('tabs-cliente', 'active_tab')],
    [Input('incluir_cliente', 'n_clicks')],
    [State('cliente-id', 'value'),
     State('cliente_label', 'value'),
     State('cliente-prazo', 'value'),
     State('cliente-forma-pagamento', 'value')],
    prevent_initial_call=True
)
def salvar_cliente(n, cliente_id, cliente_nome, cliente_prazo, cliente_forma_pagamento):
    if not n:
        raise PreventUpdate

    if not cliente_nome:
        return dash.no_update, dbc.Alert("O nome do cliente é obrigatório!", color="danger"), "tab-cadastro-cliente"
    
    banco = Banco()
    
    dados_cliente = {
        "nome": cliente_nome,
        "cli_prazo": cliente_prazo,
        "cli_forma_pagamento": cliente_forma_pagamento
    }

    try:
        if cliente_id:
            banco.editar_dado("clientes", cliente_id, **dados_cliente)
            mensagem = "Cliente atualizado com sucesso!"
        else:
            banco.inserir_dados("clientes", **dados_cliente) 
            mensagem = "O cliente foi adicionado com sucesso!"
        
        dataset = banco.ler_tabela('clientes')
        dataset_serialized = dataset.to_dict('records')
        return dataset_serialized, dbc.Alert(mensagem, color="success"), "tab-listagem-clientes"

    except Exception as e:
        return dash.no_update, dbc.Alert(f"Erro ao salvar: {e}", color="danger"), "tab-cadastro-cliente"

@app.callback(
    [Output('cliente-id', 'value', allow_duplicate=True),
     Output('cliente_label', 'value', allow_duplicate=True),
     Output('cliente-prazo', 'value', allow_duplicate=True),
     Output('cliente-forma-pagamento', 'value', allow_duplicate=True),
     Output('tabs-cliente', 'active_tab', allow_duplicate=True)],
    Input('btn-editar-cliente', 'n_clicks'),
    [State('tabela-clientes', 'selected_rows'),
     State('tabela-clientes', 'data')],
    prevent_initial_call=True
)
def preencher_form_edicao(n, selected_rows, data):
    if not n or not selected_rows:
        raise PreventUpdate
    
    cliente_selecionado = data[selected_rows[0]]
    return cliente_selecionado['ID'], cliente_selecionado['Nome'], cliente_selecionado.get('Prazo'), cliente_selecionado.get('Forma de Pagamento'), 'tab-cadastro-cliente'

@app.callback(
    [Output("modal-confirmar-exclusao-cliente", "is_open"),
     Output("store-cliente-excluir", "data")],
    [Input("btn-excluir-cliente", "n_clicks"),
     Input("cancel-delete-cliente", "n_clicks"),
     Input("confirm-delete-cliente", "n_clicks")],
    [State("tabela-clientes", "selected_rows"),
     State("tabela-clientes", "data"),
     State("modal-confirmar-exclusao-cliente", "is_open")],
    prevent_initial_call=True
)
def controlar_modal_exclusao(n_excluir, n_cancel, n_confirm, selected_rows, data, is_open):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'btn-excluir-cliente' and selected_rows:
        cliente_id = data[selected_rows[0]]['ID']
        return True, cliente_id
    
    return False, dash.no_update

@app.callback(
    Output('store_cliente', 'data', allow_duplicate=True),
    Input('confirm-delete-cliente', 'n_clicks'),
    State('store-cliente-excluir', 'data'),
    prevent_initial_call=True
)
def excluir_cliente(n, cliente_id):
    if not n or not cliente_id:
        raise PreventUpdate
    
    banco = Banco()
    banco.deletar_dado("clientes", cliente_id)
    dataset = banco.ler_tabela('clientes')
    return dataset.to_dict('records')

@app.callback(
    [Output('cliente-id', 'value'),
     Output('cliente_label', 'value'),
     Output('cliente-prazo', 'value'),
     Output('cliente-forma-pagamento', 'value'),
     Output('div_erro3', 'children', allow_duplicate=True)],
    [Input('cliente-btn-limpar', 'n_clicks'),
     Input('cliente-btn-fechar-modal', 'n_clicks')],
    prevent_initial_call=True
)
def limpar_formulario(n_limpar, n_fechar):
    if n_limpar or n_fechar:
        return None, '', None, None, None
    raise PreventUpdate