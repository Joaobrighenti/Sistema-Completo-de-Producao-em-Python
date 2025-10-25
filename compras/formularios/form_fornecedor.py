import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, dash_table
import pandas as pd
from datetime import datetime
from dash.exceptions import PreventUpdate

from app import app
from banco_dados.banco import Banco

# Função para criar a tabela de fornecedores
def get_tabela_fornecedores():
    try:
        banco = Banco()
        df_fornecedores = banco.ler_tabela("fornecedores")
        
        if df_fornecedores.empty:
            return html.Div("Nenhum fornecedor cadastrado.", className="text-center my-4")
        
        # Preparar dados para exibição
        df_exibicao = df_fornecedores[['for_id', 'for_nome', 'for_prazo', 'for_forma_pagamento', 'for_observacao']].copy()
        df_exibicao.columns = ['ID', 'Nome', 'Prazo de Pagamento', 'Forma de Pagamento', 'Observações']
        
        # Criar tabela
        tabela = dash_table.DataTable(
            id="tabela-fornecedores",
            columns=[
                {"name": col, "id": col} for col in df_exibicao.columns
            ],
            data=df_exibicao.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '8px',
                'fontSize': '14px',
                'fontFamily': 'Arial'
            },
            style_header={
                'backgroundColor': '#f8f9fa',
                'fontWeight': 'bold',
                'border': '1px solid #ddd'
            },
            page_size=10,
            sort_action='native',
            filter_action='native',
            row_selectable='single',
        )
        
        return html.Div([
            tabela,
            html.Div([
                dbc.Button("Editar Selecionado", id="btn-editar-fornecedor", color="primary", className="me-2 mt-3"),
                dbc.Button("Excluir Selecionado", id="btn-excluir-fornecedor", color="danger", className="mt-3")
            ], className="d-flex")
        ])
    
    except Exception as e:
        print(f"Erro ao carregar fornecedores: {e}")
        return html.Div(f"Erro ao carregar dados: {str(e)}", className="text-danger")

# Layout do formulário de fornecedor
layout = html.Div([
    # Modal para cadastro/edição de fornecedor
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Gestão de Fornecedores"), close_button=True),
        dbc.ModalBody([
            # Tabs para alternar entre formulário e tabela
            dbc.Tabs([
                # Tab de cadastro
                dbc.Tab(label="Cadastro", tab_id="tab-cadastro", children=[
                    # Formulário
                    dbc.Form([
                        # ID do fornecedor (oculto)
                        dcc.Input(id="fornecedor-id", type="hidden"),
                        
                        # Nome do fornecedor
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Nome *", html_for="fornecedor-nome"),
                                dbc.Input(
                                    type="text",
                                    id="fornecedor-nome",
                                    placeholder="Nome do fornecedor",
                                    required=True
                                ),
                            ], width=12),
                        ], className="mb-3"),
                        
                        # Prazo de pagamento
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Prazo de Pagamento", html_for="fornecedor-prazo"),
                                dbc.Input(
                                    type="text",
                                    id="fornecedor-prazo",
                                    placeholder="Ex: 30/60/90 dias"
                                ),
                            ], width=12),
                        ], className="mb-3"),
                        
                        # Forma de pagamento
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Forma de Pagamento", html_for="fornecedor-forma-pagamento"),
                                dbc.Select(
                                    id="fornecedor-forma-pagamento",
                                    options=[
                                        {"label": "À vista", "value": "avista"},
                                        {"label": "Boleto", "value": "boleto"},
                                        {"label": "Cartão de Crédito", "value": "cartao_credito"},
                                        {"label": "Cartão de Débito", "value": "cartao_debito"},
                                        {"label": "Transferência Bancária", "value": "transferencia"},
                                        {"label": "PIX", "value": "pix"},
                                        {"label": "Cheque", "value": "cheque"},
                                        {"label": "Crediário", "value": "crediario"}
                                    ],
                                    placeholder="Selecione a forma de pagamento"
                                ),
                            ], width=12),
                        ], className="mb-3"),
                        
                        # Observações
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Observações", html_for="fornecedor-obs"),
                                dbc.Textarea(
                                    id="fornecedor-obs",
                                    placeholder="Observações sobre o fornecedor",
                                    rows=3
                                ),
                            ], width=12),
                        ], className="mb-3"),
                        
                        # Mensagem de erro/sucesso
                        html.Div(id="fornecedor-message", className="mt-3"),
                        
                        # Botões do formulário
                        html.Div([
                            dbc.Button("Limpar", id="fornecedor-btn-limpar", className="me-2", color="warning"),
                            dbc.Button("Salvar", id="fornecedor-btn-salvar", color="primary")
                        ], className="d-flex justify-content-end mt-4")
                    ]),
                ]),
                
                # Tab de listagem
                dbc.Tab(label="Fornecedores Cadastrados", tab_id="tab-listagem", children=[
                    html.Div(id="tabela-fornecedores-container", className="mt-3")
                ]),
            ], id="tabs-fornecedor", active_tab="tab-cadastro"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Fechar", id="fornecedor-btn-fechar", color="secondary"),
        ]),
    ], id="modal-fornecedor", size="xl", is_open=False),
    
    # Modal de confirmação de exclusão
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Confirmar Exclusão"), close_button=True),
        dbc.ModalBody("Tem certeza que deseja excluir este fornecedor?"),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="confirmar-cancelar", className="me-2", color="secondary"),
            dbc.Button("Excluir", id="confirmar-excluir", color="danger"),
        ]),
    ], id="modal-confirmar-exclusao", is_open=False),
    
    # Store para ID do fornecedor a ser excluído
    dcc.Store(id="store-fornecedor-excluir", data=None),
])

# Callbacks

# Callback para carregar a tabela de fornecedores quando a tab for selecionada
@app.callback(
    Output("tabela-fornecedores-container", "children", allow_duplicate=True),
    Input("tabs-fornecedor", "active_tab"),
    prevent_initial_call=True
)
def carregar_tabela_fornecedores(tab_ativo):
    if tab_ativo == "tab-listagem":
        return get_tabela_fornecedores()
    return html.Div()

# Callback para salvar fornecedor
@app.callback(
    [Output("fornecedor-message", "children"),
     Output("fornecedor-id", "value"),
     Output("tabs-fornecedor", "active_tab")],
    Input("fornecedor-btn-salvar", "n_clicks"),
    [State("fornecedor-id", "value"),
     State("fornecedor-nome", "value"),
     State("fornecedor-prazo", "value"),
     State("fornecedor-forma-pagamento", "value"),
     State("fornecedor-obs", "value")],
    prevent_initial_call=True
)
def salvar_fornecedor(n_clicks, id_fornecedor, nome, prazo, forma_pagamento, obs):
    if not n_clicks:
        raise PreventUpdate
    
    # Validação básica
    if not nome:
        return dbc.Alert("Por favor, informe o nome do fornecedor", color="danger"), dash.no_update, dash.no_update
    
    try:
        banco = Banco()
        
        # Preparar dados
        dados = {
            "for_nome": nome,
            "for_prazo": prazo if prazo else "30/60/90 dias",
            "for_forma_pagamento": forma_pagamento if forma_pagamento else "avista",
            "for_observacao": obs if obs else ""
        }
        
        # Inserir ou atualizar
        if id_fornecedor:
            # Atualizar fornecedor existente
            banco.editar_dado("fornecedores", id_fornecedor, **dados)
            mensagem = "Fornecedor atualizado com sucesso!"
        else:
            # Inserir novo fornecedor
            banco.inserir_dados("fornecedores", **dados)
            mensagem = "Fornecedor cadastrado com sucesso!"
        
        # Mudar para a tab de listagem e limpar o formulário
        return dbc.Alert(mensagem, color="success"), None, "tab-listagem"
    
    except Exception as e:
        print(f"Erro ao salvar fornecedor: {e}")
        return dbc.Alert(f"Erro ao salvar: {str(e)}", color="danger"), dash.no_update, dash.no_update

# Callback para limpar formulário
@app.callback(
    [Output("fornecedor-nome", "value"),
     Output("fornecedor-prazo", "value"),
     Output("fornecedor-forma-pagamento", "value"),
     Output("fornecedor-obs", "value"),
     Output("fornecedor-message", "children", allow_duplicate=True)],
    [Input("fornecedor-btn-limpar", "n_clicks"),
     Input("fornecedor-btn-fechar", "n_clicks")],
    prevent_initial_call=True
)
def limpar_formulario(n_limpar, n_fechar):
    # Limpar campos
    return None, None, None, None, None

# Callback para editar fornecedor selecionado
@app.callback(
    [Output("fornecedor-id", "value", allow_duplicate=True),
     Output("fornecedor-nome", "value", allow_duplicate=True),
     Output("fornecedor-prazo", "value", allow_duplicate=True),
     Output("fornecedor-forma-pagamento", "value", allow_duplicate=True),
     Output("fornecedor-obs", "value", allow_duplicate=True),
     Output("tabs-fornecedor", "active_tab", allow_duplicate=True)],
    [Input("btn-editar-fornecedor", "n_clicks")],
    [State("tabela-fornecedores", "selected_rows"),
     State("tabela-fornecedores", "data")],
    prevent_initial_call=True
)
def editar_fornecedor(n_clicks, selected_rows, data):
    if not n_clicks or not selected_rows:
        raise PreventUpdate
    
    # Obter dados do fornecedor selecionado
    fornecedor_id = data[selected_rows[0]]["ID"]
    
    try:
        # Buscar dados completos do fornecedor
        banco = Banco()
        df_fornecedor = banco.ler_tabela("fornecedores")
        df_fornecedor = df_fornecedor[df_fornecedor['for_id'] == fornecedor_id]
        
        if df_fornecedor.empty:
            raise PreventUpdate
        
        fornecedor = df_fornecedor.iloc[0]
        
        # Preencher formulário com dados do fornecedor e mudar para a tab de cadastro
        return (
            fornecedor_id,
            fornecedor['for_nome'],
            fornecedor['for_prazo'],
            fornecedor['for_forma_pagamento'],
            fornecedor['for_observacao'],
            "tab-cadastro"  # Alterar para a tab de cadastro
        )
    
    except Exception as e:
        print(f"Erro ao editar fornecedor: {e}")
        raise PreventUpdate

# Callback para preparar exclusão de fornecedor
@app.callback(
    [Output("modal-confirmar-exclusao", "is_open", allow_duplicate=True),
     Output("store-fornecedor-excluir", "data")],
    [Input("btn-excluir-fornecedor", "n_clicks"),
     Input("confirmar-cancelar", "n_clicks")],
    [State("tabela-fornecedores", "selected_rows"),
     State("tabela-fornecedores", "data")],
    prevent_initial_call=True
)
def confirmar_exclusao(n_excluir, n_cancelar, selected_rows, data):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == "btn-excluir-fornecedor":
        if not selected_rows:
            raise PreventUpdate
        
        fornecedor_id = data[selected_rows[0]]["ID"]
        return True, fornecedor_id
    
    elif trigger_id == "confirmar-cancelar":
        return False, None
    
    raise PreventUpdate

# Callback para excluir fornecedor
@app.callback(
    [Output("modal-confirmar-exclusao", "is_open", allow_duplicate=True),
     Output("tabela-fornecedores-container", "children", allow_duplicate=True)],
    Input("confirmar-excluir", "n_clicks"),
    State("store-fornecedor-excluir", "data"),
    prevent_initial_call=True
)
def excluir_fornecedor(n_clicks, fornecedor_id):
    if not n_clicks or not fornecedor_id:
        raise PreventUpdate
    
    try:
        banco = Banco()
        banco.deletar_dado("fornecedores", fornecedor_id)
        
        # Atualizar tabela
        return False, get_tabela_fornecedores()
    
    except Exception as e:
        print(f"Erro ao excluir fornecedor: {e}")
        return False, html.Div([
            html.Div(f"Erro ao excluir fornecedor: {str(e)}", className="alert alert-danger"),
            get_tabela_fornecedores()
        ])
