import dash
from dash import html, dcc, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from app import app
from banco_dados.banco import Banco
from datetime import datetime

banco = Banco()

table_style = {"maxHeight": "400px", "overflowY": "auto"}

modal_style = {
    "maxWidth": "90%",
    "width": "90%"
}

def get_valores_alvo_for_categoria(categoria_id):
    if not categoria_id:
        return pd.DataFrame()
        
    banco = Banco()
    df_valores = banco.ler_tabela("valor_alvo")

    if df_valores.empty:
        return pd.DataFrame()

    df_valores_filtrados = df_valores[df_valores['categoria_id'] == categoria_id].copy()

    if df_valores_filtrados.empty:
        return pd.DataFrame()
        
    # Format date for display
    df_valores_filtrados['data'] = pd.to_datetime(df_valores_filtrados['data']).dt.strftime('%d/%m/%Y')
    df_valores_filtrados['excluir'] = '🗑️'
    
    return df_valores_filtrados[['id_valor_alvo', 'preco', 'custo', 'data', 'excluir']]

layout = html.Div([
    dcc.Store(id="store-mensagem-categoriacompra", data=""),
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Gerenciar Categorias de Compras")),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Tabs([
                        dbc.Tab([
                            html.Label("Nome da Categoria:", className="mt-3"),
                            dbc.Input(id="input-categoriacompra-nome", type="text", className="mb-2"),
                            html.Label("Fator de Conversão:"),
                            dbc.Input(id="input-categoriacompra-conversao", type="number", step=0.01, className="mb-2"),
                            html.Label("Grupo:"),
                            dcc.Dropdown(id="dropdown-categoriacompra-grupo", className="mb-2"),
                            html.Label("Tipo de Frete:"),
                            dcc.Dropdown(id="dropdown-categoriacompra-tipo-frete", 
                                        options=[
                                            {"label": "CIF - Custo, Seguro e Frete", "value": "CIF"},
                                            {"label": "FOB - Free on Board", "value": "FOB"},
                                            {"label": "Por Conta do Fornecedor", "value": "FORNECEDOR"},
                                            {"label": "Por Conta do Cliente", "value": "CLIENTE"}
                                        ], className="mb-2"),
                            html.Label("Valor do Frete (R$):"),
                            dbc.Input(id="input-categoriacompra-valor-frete", type="number", step=0.01, className="mb-2"),
                            dbc.Button("Adicionar", id="btn-add-categoriacompra", color="success", className="w-100 mb-3"),
                        ], label="Adicionar"),
                        dbc.Tab([
                            html.Label("Selecionar Categoria:", className="mt-3"),
                            dcc.Dropdown(id="dropdown-categoriacompra-delete", className="mb-2"),
                            dbc.Button("Excluir", id="btn-delete-categoriacompra", color="danger", className="w-100"),
                        ], label="Excluir"),
                        dbc.Tab([
                            html.Label("Selecionar Categoria:", className="mt-3"),
                            dcc.Dropdown(id="dropdown-categoriacompra-edit", className="mb-2"),
                            html.Label("Novo Nome:"),
                            dbc.Input(id="input-categoriacompra-edit-nome", type="text", className="mb-2"),
                            html.Label("Nova Conversão:"),
                            dbc.Input(id="input-categoriacompra-edit-conversao", type="number", step=0.01, className="mb-2"),
                            html.Label("Novo Grupo:"),
                            dcc.Dropdown(id="dropdown-categoriacompra-edit-grupo", className="mb-2"),
                            html.Label("Novo Tipo de Frete:"),
                            dcc.Dropdown(id="dropdown-categoriacompra-edit-tipo-frete", 
                                        options=[
                                            {"label": "CIF - Custo, Seguro e Frete", "value": "CIF"},
                                            {"label": "FOB - Free on Board", "value": "FOB"},
                                            {"label": "Por Conta do Fornecedor", "value": "FORNECEDOR"},
                                            {"label": "Por Conta do Cliente", "value": "CLIENTE"}
                                        ], className="mb-2"),
                            html.Label("Novo Valor do Frete (R$):"),
                            dbc.Input(id="input-categoriacompra-edit-valor-frete", type="number", step=0.01, className="mb-2"),
                            dbc.Button("Salvar", id="btn-edit-categoriacompra", color="warning", className="w-100"),
                            
                            html.Div(id='valor-alvo-section-cat', className='mt-4', style={'display': 'none'}, children=[
                                html.Hr(),
                                html.H5("Adicionar Valor Alvo"),
                                html.Label("Novo Preço Alvo:"),
                                dbc.Input(id='input-valor-alvo-preco-cat', type='number', className='mb-2'),
                                dbc.Button("Adicionar Valor", id='btn-add-valor-alvo-cat', color='primary', className='w-100'),
                            ])
                        ], label="Editar"),
                    ])
                ], width=4),

                dbc.Col([
                    html.Label("Categorias Cadastradas:"),
                    dash_table.DataTable(id='tabela-categoriacompra',
                        columns=[
                            {"name": "ID", "id": "id_categoria"},
                            {"name": "Nome da Categoria", "id": "categoria_nome"},
                            {"name": "Conversão", "id": "conversao"},
                            {"name": "Grupo", "id": "nome_grupo"},
                            {"name": "Tipo Frete", "id": "tipo_frete"},
                            {"name": "Valor Frete", "id": "valor_frete"},
                            {"name": "Último Preço", "id": "ultimo_preco"}
                        ],
                        page_size=10,
                        style_table={"width": "100%", "overflowX": "auto"},
                    ),
                     html.Div(id='valores-alvo-table-container-cat', className='mt-4', style={'display': 'none'}, children=[
                        html.Hr(),
                        html.H5("Histórico de Valores Alvo para a Categoria"),
                        dash_table.DataTable(id='tabela-valores-alvo-cat',
                            columns=[
                                {'name': 'ID', 'id': 'id_valor_alvo'},
                                {'name': 'Preço', 'id': 'preco'},
                                {'name': 'Custo', 'id': 'custo'},
                                {'name': 'Data', 'id': 'data'},
                                {'name': '🗑️', 'id': 'excluir'}
                            ],
                            page_size=5,
                            style_table={"width": "100%", "overflowX": "auto"},
                            style_cell={'textAlign': 'center'},
                            style_data_conditional=[
                                {
                                    'if': {'column_id': 'excluir'},
                                    'backgroundColor': '#ff6b6b',
                                    'color': 'white',
                                    'cursor': 'pointer'
                                }
                            ]
                        )
                    ])
                ], width=8),
            ]),
        ]),
        dbc.ModalFooter([
            html.Div(id="alert-container-categoriacompra", className="me-auto"),
            dbc.Button("Fechar", id="btn_fechar_categoriacompra", color="secondary")
        ])
    ], id="modal-categoriacompra-item", is_open=False, className="custom-modal-categoriacompra"),
])

@app.callback(
    Output("modal-categoriacompra-item", "is_open"),
    [Input("btn_abrir_categoria", "n_clicks"), Input("btn_fechar_categoriacompra", "n_clicks")],
    [State("modal-categoriacompra-item", "is_open")]
)
def toggle_modal_categoria(n_abrir, n_fechar, is_open):
    if n_abrir or n_fechar:
        return not is_open
    return is_open

@app.callback(
    Output("alert-container-categoriacompra", "children"),
    Input("store-mensagem-categoriacompra", "data"),
    prevent_initial_call=True
)
def show_alert_categoria(mensagem):
    if mensagem:
        return dbc.Alert(mensagem, color="success", duration=4000, dismissable=True)
    return []

@app.callback(
    [Output("dropdown-categoriacompra-delete", "options"),
     Output("dropdown-categoriacompra-edit", "options"),
     Output("dropdown-categoriacompra-grupo", "options"),
     Output("dropdown-categoriacompra-edit-grupo", "options"),
     Output("tabela-categoriacompra", "data"),
     Output("store-mensagem-categoriacompra", "data"),
     Output("input-categoriacompra-nome", "value"),
     Output("input-categoriacompra-conversao", "value"),
     Output("dropdown-categoriacompra-grupo", "value"),
     Output("dropdown-categoriacompra-tipo-frete", "value"),
     Output("input-categoriacompra-valor-frete", "value"),
     Output("dropdown-categoriacompra-delete", "value"),
     Output("dropdown-categoriacompra-edit", "value"),
     Output("input-categoriacompra-edit-nome", "value"),
     Output("input-categoriacompra-edit-conversao", "value"),
     Output("dropdown-categoriacompra-edit-grupo", "value"),
     Output("dropdown-categoriacompra-edit-tipo-frete", "value"),
     Output("input-categoriacompra-edit-valor-frete", "value")],
    [Input("btn-add-categoriacompra", "n_clicks"),
     Input("btn-delete-categoriacompra", "n_clicks"),
     Input("btn-edit-categoriacompra", "n_clicks"),
     Input("modal-categoriacompra-item", "is_open"),
     Input("dropdown-categoriacompra-edit", "value")],
    [State("input-categoriacompra-nome", "value"),
     State("input-categoriacompra-conversao", "value"),
     State("dropdown-categoriacompra-grupo", "value"),
     State("dropdown-categoriacompra-tipo-frete", "value"),
     State("input-categoriacompra-valor-frete", "value"),
     State("dropdown-categoriacompra-delete", "value"),
     State("input-categoriacompra-edit-nome", "value"),
     State("input-categoriacompra-edit-conversao", "value"),
     State("dropdown-categoriacompra-edit-grupo", "value"),
     State("dropdown-categoriacompra-edit-tipo-frete", "value"),
     State("input-categoriacompra-edit-valor-frete", "value")],
    prevent_initial_call=True
)
def manage_categoria(n_add, n_delete, n_edit, is_open, categoria_id_edit, 
                     nome, conversao, grupo_id, tipo_frete, valor_frete, categoria_id_del, 
                     novo_nome, nova_conversao, novo_grupo_id, novo_tipo_frete, novo_valor_frete):
    ctx = callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    mensagem = ""

    # Initialize all return values to no_update
    (
        dropdown_opts_del, dropdown_opts_edit, dropdown_opts_grupo, dropdown_opts_edit_grupo, 
        table_data, msg_data, add_nome, add_conversao, add_grupo, add_tipo_frete, add_valor_frete,
        del_dropdown, edit_dropdown, edit_nome, edit_conversao, edit_grupo, edit_tipo_frete, edit_valor_frete
    ) = [dash.no_update] * 18

    # When opening modal or performing an action, update the table and dropdowns
    if triggered_id in ["modal-categoriacompra-item", "btn-add-categoriacompra", "btn-delete-categoriacompra", "btn-edit-categoriacompra"]:
        if triggered_id == "btn-add-categoriacompra" and nome:
            banco.inserir_dados("categoria_compras", categoria_nome=nome, conversao=conversao, grupo_id=grupo_id, 
                               tipo_frete=tipo_frete, valor_frete=valor_frete)
            mensagem = f"Categoria '{nome}' adicionada com sucesso!"
            add_nome, add_conversao, add_grupo, add_tipo_frete, add_valor_frete = "", None, None, None, None
        
        elif triggered_id == "btn-delete-categoriacompra" and categoria_id_del:
            banco.deletar_dado("categoria_compras", categoria_id_del)
            mensagem = "Categoria excluída com sucesso!"
            del_dropdown = None
        
        elif triggered_id == "btn-edit-categoriacompra" and categoria_id_edit:
            banco.editar_dado("categoria_compras", categoria_id_edit, categoria_nome=novo_nome, conversao=nova_conversao, 
                             grupo_id=novo_grupo_id, tipo_frete=novo_tipo_frete, valor_frete=novo_valor_frete)
            mensagem = f"Categoria '{novo_nome}' editada com sucesso!"
            edit_dropdown, edit_nome, edit_conversao, edit_grupo, edit_tipo_frete, edit_valor_frete = None, "", None, None, None, None
        
        # Buscar grupos para os dropdowns
        grupos = banco.ler_tabela("grupo_categoria")
        grupos_options = [{"label": row["nome_grupo"], "value": row["id_grupo"]} for _, row in grupos.iterrows()]
        
        # Buscar categorias com join para mostrar nome do grupo e último preço
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine("sqlite:///banco_dados/bd_pcp.sqlite")
            with engine.connect() as conn:
                query = """
                WITH LatestValorAlvo AS (
                    SELECT
                        categoria_id,
                        preco,
                        ROW_NUMBER() OVER(PARTITION BY categoria_id ORDER BY data DESC, id_valor_alvo DESC) as rn
                    FROM valor_alvo
                )
                SELECT 
                    c.*, 
                    g.nome_grupo,
                    lva.preco as ultimo_preco
                FROM categoria_compras c 
                LEFT JOIN grupo_categoria g ON c.grupo_id = g.id_grupo
                LEFT JOIN LatestValorAlvo lva ON c.id_categoria = lva.categoria_id AND lva.rn = 1
                """
                categorias = pd.read_sql(query, conn)
        except Exception as e:
            print(f"Erro ao buscar categorias com preço: {e}")
            categorias = banco.ler_tabela("categoria_compras")
            categorias['nome_grupo'] = None
            categorias['ultimo_preco'] = None

        dropdown_options = [{"label": row["categoria_nome"], "value": row["id_categoria"]} for _, row in categorias.iterrows()]
        
        dropdown_opts_del = dropdown_options
        dropdown_opts_edit = dropdown_options
        dropdown_opts_grupo = grupos_options
        dropdown_opts_edit_grupo = grupos_options
        table_data = categorias.to_dict("records")
        msg_data = mensagem
        
    # When selecting a category to edit, fill the form
    elif triggered_id == "dropdown-categoriacompra-edit" and categoria_id_edit:
        categoria = banco.ler_tabela("categoria_compras").set_index("id_categoria").loc[categoria_id_edit]
        edit_nome = categoria["categoria_nome"]
        edit_conversao = categoria["conversao"]
        edit_grupo = categoria["grupo_id"]
        edit_tipo_frete = categoria.get("tipo_frete", None)
        edit_valor_frete = categoria.get("valor_frete", None)

    return (
        dropdown_opts_del, dropdown_opts_edit, dropdown_opts_grupo, dropdown_opts_edit_grupo,
        table_data, msg_data, add_nome, add_conversao, add_grupo, add_tipo_frete, add_valor_frete,
        del_dropdown, edit_dropdown, edit_nome, edit_conversao, edit_grupo, edit_tipo_frete, edit_valor_frete
    )

@app.callback(
    [Output("valor-alvo-section-cat", "style"),
     Output("valores-alvo-table-container-cat", "style"),
     Output("tabela-valores-alvo-cat", "data"),
     Output("input-valor-alvo-preco-cat", "value"),
     Output("store-mensagem-categoriacompra", "data", allow_duplicate=True)],
    [Input("dropdown-categoriacompra-edit", "value"),
     Input("btn-add-valor-alvo-cat", "n_clicks"),
     Input("tabela-valores-alvo-cat", "active_cell")],
    [State("input-valor-alvo-preco-cat", "value"),
     State("tabela-valores-alvo-cat", "data")],
    prevent_initial_call=True
)
def manage_valores_alvo_categoria(categoria_id, n_add, active_cell, preco, table_data):
    ctx = callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    no_display = {'display': 'none'}
    display = {'display': 'block'}

    if not categoria_id:
        return no_display, no_display, [], None, ""

    mensagem = ""
    updated_table_data = dash.no_update
    preco_value = dash.no_update
    
    # Logic to handle different triggers
    if triggered_id == "dropdown-categoriacompra-edit":
        df_valores = get_valores_alvo_for_categoria(categoria_id)
        return display, display, df_valores.to_dict('records'), None, ""

    elif triggered_id == "btn-add-valor-alvo-cat":
        if preco is None:
            mensagem = "Insira um preço."
        else:
            banco.inserir_dados("valor_alvo", categoria_id=categoria_id, preco=preco, custo=None, data=datetime.now().date())
            mensagem = "Valor alvo adicionado com sucesso!"
            preco_value = None  # Clear input
        
        df_valores = get_valores_alvo_for_categoria(categoria_id)
        updated_table_data = df_valores.to_dict('records')
        return display, display, updated_table_data, preco_value, mensagem
        
    elif triggered_id == 'tabela-valores-alvo-cat' and active_cell and table_data:
        if active_cell.get('column_id') == 'excluir':
            row_index = active_cell.get('row')
            if row_index is not None and row_index < len(table_data):
                valor_id = table_data[row_index]['id_valor_alvo']
                try:
                    banco.deletar_dado("valor_alvo", valor_id)
                    mensagem = "Valor alvo excluído com sucesso!"
                except Exception as e:
                    mensagem = f"Erro ao excluir: {e}"
                
                df_valores = get_valores_alvo_for_categoria(categoria_id)
                updated_table_data = df_valores.to_dict('records')
                return display, display, updated_table_data, None, mensagem

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
