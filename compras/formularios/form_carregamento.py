import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, dash_table
import pandas as pd
from datetime import datetime
from dash.exceptions import PreventUpdate

from banco_dados.banco import Banco

# Função para buscar opções de Ordem de Compra
def get_ordem_compra_options():
    try:
        banco = Banco()
        # Query para buscar ordens de compra abertas com nome do produto
        with banco.engine.connect() as conn:
            query = """
            SELECT 
                oc.oc_id, 
                oc.oc_qtd_solicitada,
                pc.nome as produto_nome
            FROM 
                ordem_compra oc
            LEFT JOIN 
                produto_compras pc ON oc.oc_produto_id = pc.prod_comp_id
            WHERE 
                oc.oc_status NOT IN ('Entregue Total', 'Cancelado')
            ORDER BY
                pc.nome
            """
            df_ocs = pd.read_sql(query, conn)
        
        if df_ocs.empty:
            return []
            
        options = [
            {"label": f"{row['produto_nome']} (Qtd: {row['oc_qtd_solicitada'] or 0}) - ID: {row['oc_id']}", "value": row['oc_id']}
            for index, row in df_ocs.iterrows()
        ]
        return options
    except Exception as e:
        print(f"Erro ao buscar opções de Ordem de Compra: {e}")
        return []

# Função para criar a tabela de carregamentos
def get_tabela_carregamentos():
    try:
        banco = Banco()
        with banco.engine.connect() as conn:
            query = """
            SELECT
                c.car_id,
                c.car_data,
                c.car_qtd,
                oc.oc_id as oc_id,
                pc.nome as produto_nome
            FROM
                carregamento c
            JOIN
                ordem_compra oc ON c.car_oc_id = oc.oc_id
            JOIN
                produto_compras pc ON oc.oc_produto_id = pc.prod_comp_id
            ORDER BY
                c.car_data DESC
            """
            df_carregamentos = pd.read_sql(query, conn)

        if df_carregamentos.empty:
            return html.Div("Nenhum carregamento cadastrado.", className="text-center my-4")

        # Formatar data
        df_carregamentos['car_data'] = pd.to_datetime(df_carregamentos['car_data']).dt.strftime('%d/%m/%Y')
        
        # Preparar dados para exibição
        df_exibicao = df_carregamentos[['car_id', 'produto_nome', 'oc_id', 'car_qtd', 'car_data']].copy()
        df_exibicao.columns = ['ID', 'Produto', 'ID Ordem Compra', 'Quantidade', 'Data']
        
        # Criar tabela
        tabela = dash_table.DataTable(
            id="tabela-carregamentos",
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
                dbc.Button("Editar Selecionado", id="btn-editar-carregamento", color="primary", className="me-2 mt-3"),
                dbc.Button("Excluir Selecionado", id="btn-excluir-carregamento", color="danger", className="mt-3")
            ], className="d-flex")
        ])
    
    except Exception as e:
        print(f"Erro ao carregar carregamentos: {e}")
        return html.Div(f"Erro ao carregar dados: {str(e)}", className="text-danger")

# Layout do formulário de carregamento
layout = html.Div([
    # Modal para cadastro/edição de carregamento
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Gestão de Carregamentos"), close_button=True),
        dbc.ModalBody([
            # Tabs para alternar entre formulário e tabela
            dbc.Tabs([
                # Tab de cadastro
                dbc.Tab(label="Cadastro", tab_id="tab-cadastro-carregamento", children=[
                    # Formulário
                    dbc.Form([
                        # ID do carregamento (oculto)
                        dcc.Input(id="carregamento-id", type="hidden"),
                        
                        # Ordem de Compra
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Ordem de Compra *", html_for="carregamento-oc-id"),
                                dcc.Dropdown(
                                    id="carregamento-oc-id",
                                    options=get_ordem_compra_options(),
                                    placeholder="Selecione uma Ordem de Compra",
                                    clearable=True,
                                ),
                            ], width=12),
                        ], className="mb-3"),
                        
                        # Quantidade
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Quantidade Recebida *", html_for="carregamento-qtd"),
                                dbc.Input(
                                    type="number",
                                    id="carregamento-qtd",
                                    placeholder="Quantidade recebida",
                                    required=True
                                ),
                            ], width=12),
                        ], className="mb-3"),
                        
                        # Data
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Data do Carregamento *", html_for="carregamento-data"),
                                dcc.DatePickerSingle(
                                    id='carregamento-data',
                                    date=datetime.now().date(),
                                    display_format='DD/MM/YYYY',
                                    className="w-100"
                                ),
                            ], width=12),
                        ], className="mb-3"),
                        
                        # Mensagem de erro/sucesso
                        html.Div(id="carregamento-message", className="mt-3"),
                        
                        # Botões do formulário
                        html.Div([
                            dbc.Button("Limpar", id="carregamento-btn-limpar", className="me-2", color="warning"),
                            dbc.Button("Salvar", id="carregamento-btn-salvar", color="primary")
                        ], className="d-flex justify-content-end mt-4")
                    ]),
                ]),
                
                # Tab de listagem
                dbc.Tab(label="Carregamentos Cadastrados", tab_id="tab-listagem-carregamento", children=[
                    html.Div(id="tabela-carregamentos-container", className="mt-3")
                ]),
            ], id="tabs-carregamento", active_tab="tab-cadastro-carregamento"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Fechar", id="carregamento-btn-fechar", color="secondary"),
        ]),
    ], id="modal-carregamento", size="xl", is_open=False),
    
    # Modal de confirmação de exclusão
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Confirmar Exclusão"), close_button=True),
        dbc.ModalBody("Tem certeza que deseja excluir este carregamento?"),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="carregamento-confirmar-cancelar", className="me-2", color="secondary"),
            dbc.Button("Excluir", id="carregamento-confirmar-excluir", color="danger"),
        ]),
    ], id="modal-confirmar-exclusao-carregamento", is_open=False),
    
    # Store para ID do carregamento a ser excluído
    dcc.Store(id="store-carregamento-excluir", data=None),
])

# Callbacks

# Callback para carregar a tabela de carregamentos quando a tab for selecionada
@callback(
    Output("tabela-carregamentos-container", "children"),
    [Input("tabs-carregamento", "active_tab"),
     Input("carregamento-btn-salvar", "n_clicks")], # Recarrega ao salvar
    prevent_initial_call=True
)
def carregar_tabela_carregamentos(tab_ativo, n_clicks):
    if tab_ativo == "tab-listagem-carregamento":
        return get_tabela_carregamentos()
    if n_clicks: # Apos salvar, ele recarrega a tabela. Nao é a melhor solucao mas funciona
        return get_tabela_carregamentos()
    return dash.no_update

# Callback para salvar carregamento
@callback(
    [Output("carregamento-message", "children"),
     Output("carregamento-id", "value"),
     Output("tabs-carregamento", "active_tab")],
    Input("carregamento-btn-salvar", "n_clicks"),
    [State("carregamento-id", "value"),
     State("carregamento-oc-id", "value"),
     State("carregamento-qtd", "value"),
     State("carregamento-data", "date")],
    prevent_initial_call=True
)
def salvar_carregamento(n_clicks, id_carregamento, oc_id, qtd, data):
    if not n_clicks:
        raise PreventUpdate
    
    # Validação básica
    if not all([oc_id, qtd, data]):
        return dbc.Alert("Todos os campos com * são obrigatórios.", color="danger"), dash.no_update, dash.no_update
    
    try:
        banco = Banco()
        
        # Preparar dados
        dados = {
            "car_oc_id": oc_id,
            "car_qtd": qtd,
            "car_data": datetime.strptime(data, '%Y-%m-%d').date()
        }
        
        # Inserir ou atualizar
        if id_carregamento:
            # Atualizar carregamento existente
            banco.editar_dado("carregamento", id_carregamento, **dados)
            mensagem = "Carregamento atualizado com sucesso!"
        else:
            # Inserir novo carregamento
            banco.inserir_dados("carregamento", **dados)
            mensagem = "Carregamento cadastrado com sucesso!"
        
        # Mudar para a tab de listagem e limpar o formulário
        return dbc.Alert(mensagem, color="success"), None, "tab-listagem-carregamento"
    
    except Exception as e:
        print(f"Erro ao salvar carregamento: {e}")
        return dbc.Alert(f"Erro ao salvar: {str(e)}", color="danger"), dash.no_update, dash.no_update

# Callback para limpar formulário
@callback(
    [Output("carregamento-oc-id", "value"),
     Output("carregamento-qtd", "value"),
     Output("carregamento-data", "date"),
     Output("carregamento-message", "children", allow_duplicate=True)],
    [Input("carregamento-btn-limpar", "n_clicks"),
     Input("carregamento-btn-fechar", "n_clicks")],
    prevent_initial_call=True
)
def limpar_formulario_carregamento(n_limpar, n_fechar):
    # Limpar campos
    return None, None, datetime.now().date(), None

# Callback para editar carregamento selecionado
@callback(
    [Output("carregamento-id", "value", allow_duplicate=True),
     Output("carregamento-oc-id", "value", allow_duplicate=True),
     Output("carregamento-qtd", "value", allow_duplicate=True),
     Output("carregamento-data", "date", allow_duplicate=True),
     Output("tabs-carregamento", "active_tab", allow_duplicate=True)],
    [Input("btn-editar-carregamento", "n_clicks")],
    [State("tabela-carregamentos", "selected_rows"),
     State("tabela-carregamentos", "data")],
    prevent_initial_call=True
)
def editar_carregamento(n_clicks, selected_rows, data):
    if not n_clicks or not selected_rows:
        raise PreventUpdate
    
    # Obter dados do carregamento selecionado
    carregamento_id = data[selected_rows[0]]["ID"]
    
    try:
        # Buscar dados completos do carregamento
        banco = Banco()
        df_carregamento = banco.ler_tabela("carregamento")
        df_carregamento = df_carregamento[df_carregamento['car_id'] == carregamento_id]
        
        if df_carregamento.empty:
            raise PreventUpdate
        
        carregamento = df_carregamento.iloc[0]
        
        # Preencher formulário com dados do carregamento e mudar para a tab de cadastro
        return (
            carregamento_id,
            carregamento['car_oc_id'],
            carregamento['car_qtd'],
            carregamento['car_data'],
            "tab-cadastro-carregamento"  # Alterar para a tab de cadastro
        )
    
    except Exception as e:
        print(f"Erro ao editar carregamento: {e}")
        raise PreventUpdate

# Callback para preparar exclusão de carregamento
@callback(
    [Output("modal-confirmar-exclusao-carregamento", "is_open"),
     Output("store-carregamento-excluir", "data")],
    [Input("btn-excluir-carregamento", "n_clicks"),
     Input("carregamento-confirmar-cancelar", "n_clicks")],
    [State("tabela-carregamentos", "selected_rows"),
     State("tabela-carregamentos", "data")],
    prevent_initial_call=True
)
def confirmar_exclusao_carregamento(n_excluir, n_cancelar, selected_rows, data):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == "btn-excluir-carregamento":
        if not selected_rows:
            raise PreventUpdate
        
        carregamento_id = data[selected_rows[0]]["ID"]
        return True, carregamento_id
    
    elif trigger_id == "carregamento-confirmar-cancelar":
        return False, None
    
    raise PreventUpdate

# Callback para excluir carregamento
@callback(
    [Output("modal-confirmar-exclusao-carregamento", "is_open", allow_duplicate=True),
     Output("tabela-carregamentos-container", "children", allow_duplicate=True)],
    Input("carregamento-confirmar-excluir", "n_clicks"),
    State("store-carregamento-excluir", "data"),
    prevent_initial_call=True
)
def excluir_carregamento(n_clicks, carregamento_id):
    if not n_clicks or not carregamento_id:
        raise PreventUpdate
    
    try:
        banco = Banco()
        banco.deletar_dado("carregamento", carregamento_id)
        
        # Atualizar tabela
        return False, get_tabela_carregamentos()
    
    except Exception as e:
        print(f"Erro ao excluir carregamento: {e}")
        return False, html.Div([
            html.Div(f"Erro ao excluir carregamento: {str(e)}", className="alert alert-danger"),
            get_tabela_carregamentos()
        ])
