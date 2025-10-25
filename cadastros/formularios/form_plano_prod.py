import dash
from dash import html, dcc, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from app import app
from banco_dados.banco import Banco
import json

banco = Banco()

partes_options = [
    {'label': 'Tampa', 'value': 'Tampa'},
    {'label': 'Fundo', 'value': 'Fundo'},
    {'label': 'Berço/Envelope', 'value': 'Berço/Envelope'},
    {'label': 'Lâmina', 'value': 'Lâmina'}
]

layout = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Configurar Partes do Produto")),
    dbc.ModalBody([
        dcc.Store(id='store-partes-produto-mensagem', data=''),
        dbc.Tabs([
            # Aba Adicionar
            dbc.Tab([
                html.Label("Nome da Configuração:", className="mt-3"),
                dbc.Input(id="input-parte-nome", type="text", className="mb-2"),
                html.Hr(),
                html.H5("Partes"),
                html.Div(id='container-partes-dinamicas', children=[]),
                dbc.Button("Adicionar Parte", id="btn-add-parte-dinamica", color="info", size="sm", className="mt-2 mb-3"),
                html.Br(),
                dbc.Button("Salvar Configuração", id="btn-add-configuracao-parte", color="success", className="w-100"),
            ], label="Adicionar"),

            # Aba Editar
            dbc.Tab([
                html.Label("Selecionar Configuração:", className="mt-3"),
                dcc.Dropdown(id="dropdown-parte-edit-select", className="mb-2"),
                html.Label("Novo Nome da Configuração:"),
                dbc.Input(id="input-parte-edit-nome", type="text", className="mb-2"),
                html.Hr(),
                html.H5("Editar Partes"),
                html.Div(id='container-partes-dinamicas-edit', children=[]),
                dbc.Button("Adicionar Nova Parte", id="btn-add-parte-dinamica-edit", color="info", size="sm", className="mt-2 mb-3"),
                html.Br(),
                dbc.Button("Salvar Alterações", id="btn-edit-configuracao-parte", color="warning", className="w-100"),
            ], label="Editar"),

            # Aba Excluir
            dbc.Tab([
                html.Label("Selecionar Configuração:", className="mt-3"),
                dcc.Dropdown(id="dropdown-parte-delete-select", className="mb-2"),
                dbc.Button("Excluir Configuração", id="btn-delete-configuracao-parte", color="danger", className="w-100 mt-2"),
            ], label="Excluir"),
        ]),
        html.Hr(),
        html.Label("Configurações Cadastradas:"),
        dash_table.DataTable(id='tabela-partes-produto',
            columns=[
                {"name": "ID", "id": "pap_id"},
                {"name": "Nome", "id": "pap_nome"},
                {"name": "Partes (JSON)", "id": "pap_parte"},
            ],
            page_size=10,
            style_table={"width": "100%", "overflowX": "auto"},
        )
    ]),
    dbc.ModalFooter([
        html.Div(id="alert-container-partes-produto", className="me-auto"),
        dbc.Button("Fechar", id="btn-fechar-partes-produto", color="secondary")
    ])
], id="modal-partes-produto", is_open=False, size="lg")

# Callbacks para abrir/fechar modal
@app.callback(
    Output("modal-partes-produto", "is_open"),
    Input("btn_configurar_partes", "n_clicks"),
    Input("btn-fechar-partes-produto", "n_clicks"),
    State("modal-partes-produto", "is_open"),
)
def toggle_modal_partes(n_open, n_close, is_open):
    if n_open or n_close:
        return not is_open
    return is_open

# Callback para adicionar campos de parte dinamicamente (Adicionar)
@app.callback(
    Output('container-partes-dinamicas', 'children'),
    Input('btn-add-parte-dinamica', 'n_clicks'),
    State('container-partes-dinamicas', 'children')
)
def add_parte_dinamica(n_clicks, children):
    if not n_clicks:
        return []
        
    new_input = dbc.Row([
        dbc.Col(dcc.Dropdown(options=partes_options, placeholder="Selecione a Parte"), width=6),
        dbc.Col(dbc.Input(type="number", placeholder="Quantidade", min=1, step=1), width=5),
        dbc.Col(dbc.Button("X", color="danger", size="sm", className="mt-1"), width=1)
    ], className="mb-2")
    
    children.append(new_input)
    return children


# Callback para adicionar campos de parte dinamicamente (Editar)
@app.callback(
    Output('container-partes-dinamicas-edit', 'children'),
    Input('btn-add-parte-dinamica-edit', 'n_clicks'),
    State('container-partes-dinamicas-edit', 'children')
)
def add_parte_dinamica_edit(n_clicks, children):
    if not n_clicks:
        return children # Não limpa ao abrir a aba

    new_input = dbc.Row([
        dbc.Col(dcc.Dropdown(options=partes_options, placeholder="Selecione a Parte"), width=6),
        dbc.Col(dbc.Input(type="number", placeholder="Quantidade", min=1, step=1), width=5),
        dbc.Col(dbc.Button("X", color="danger", size="sm", className="mt-1"), width=1)
    ], className="mb-2")

    children.append(new_input)
    return children


# Callback principal para CRUD e atualização da interface
@app.callback(
    [Output("tabela-partes-produto", "data"),
     Output("dropdown-parte-edit-select", "options"),
     Output("dropdown-parte-delete-select", "options"),
     Output("alert-container-partes-produto", "children"),
     Output("input-parte-nome", "value"),
     Output("container-partes-dinamicas", "children", allow_duplicate=True),
     Output("dropdown-parte-edit-select", "value"),
     Output("dropdown-parte-delete-select", "value"),
     Output("input-parte-edit-nome", "value")],
    [Input("btn-add-configuracao-parte", "n_clicks"),
     Input("btn-edit-configuracao-parte", "n_clicks"),
     Input("btn-delete-configuracao-parte", "n_clicks"),
     Input("modal-partes-produto", "is_open")],
    [State("input-parte-nome", "value"),
     State("container-partes-dinamicas", "children"),
     State("dropdown-parte-edit-select", "value"),
     State("input-parte-edit-nome", "value"),
     State("container-partes-dinamicas-edit", "children"),
     State("dropdown-parte-delete-select", "value")],
    prevent_initial_call=True
)
def manage_partes_produto(n_add, n_edit, n_delete, is_open,
                         nome_add, partes_add_children,
                         id_edit, nome_edit, partes_edit_children,
                         id_delete):
    ctx = callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    alert_msg = None

    if triggered_id == "btn-add-configuracao-parte" and nome_add:
        partes = {}
        for row in partes_add_children:
            nome_parte = row['props']['children'][0]['props']['children']['props']['value']
            qtd_parte = row['props']['children'][1]['props']['children']['props']['value']
            if nome_parte and qtd_parte:
                partes[nome_parte] = qtd_parte
        
        banco.inserir_dados("partes_produto", pap_nome=nome_add, pap_parte=json.dumps(partes))
        alert_msg = dbc.Alert(f"Configuração '{nome_add}' salva com sucesso!", color="success", duration=4000)

    elif triggered_id == "btn-edit-configuracao-parte" and id_edit and nome_edit:
        partes = {}
        if partes_edit_children:
            for row in partes_edit_children:
                nome_parte = row['props']['children'][0]['props']['children']['props']['value']
                qtd_parte = row['props']['children'][1]['props']['children']['props']['value']
                if nome_parte and qtd_parte is not None:
                     partes[nome_parte] = qtd_parte
        
        banco.editar_dado("partes_produto", id_edit, pap_nome=nome_edit, pap_parte=json.dumps(partes))
        alert_msg = dbc.Alert(f"Configuração '{nome_edit}' atualizada com sucesso!", color="warning", duration=4000)

    elif triggered_id == "btn-delete-configuracao-parte" and id_delete:
        banco.deletar_dado("partes_produto", id_delete)
        alert_msg = dbc.Alert("Configuração excluída com sucesso!", color="danger", duration=4000)

    # Atualiza a tabela e os dropdowns
    df = banco.ler_tabela("partes_produto")
    table_data = df.to_dict('records')
    options = [{"label": row['pap_nome'], "value": row['pap_id']} for _, row in df.iterrows()]

    # Limpar campos após a ação
    nome_add_clear = "" if triggered_id == "btn-add-configuracao-parte" else dash.no_update
    partes_add_clear = [] if triggered_id == "btn-add-configuracao-parte" else dash.no_update
    id_edit_clear = None if triggered_id in ["btn-edit-configuracao-parte", "btn-delete-configuracao-parte"] else dash.no_update
    id_delete_clear = None if triggered_id == "btn-delete-configuracao-parte" else dash.no_update
    nome_edit_clear = "" if triggered_id == "btn-edit-configuracao-parte" else dash.no_update

    return table_data, options, options, alert_msg, nome_add_clear, partes_add_clear, id_edit_clear, id_delete_clear, nome_edit_clear

# Callback para carregar os dados na aba de edição
@app.callback(
    [Output("input-parte-edit-nome", "value", allow_duplicate=True),
     Output("container-partes-dinamicas-edit", "children", allow_duplicate=True)],
    Input("dropdown-parte-edit-select", "value"),
    prevent_initial_call=True
)
def load_data_for_edit(config_id):
    if not config_id:
        return "", []

    df = banco.ler_tabela("partes_produto", pap_id=config_id)
    if not df.empty:
        config = df.iloc[0]
        nome = config['pap_nome']
        partes_json = config['pap_parte']
        
        children = []
        if partes_json:
            try:
                partes = json.loads(partes_json)
                for nome_parte, qtd_parte in partes.items():
                    new_input = dbc.Row([
                        dbc.Col(dcc.Dropdown(options=partes_options, placeholder="Selecione a Parte", value=nome_parte), width=6),
                        dbc.Col(dbc.Input(type="number", placeholder="Quantidade", min=1, step=1, value=qtd_parte), width=5),
                        dbc.Col(dbc.Button("X", color="danger", size="sm", className="mt-1"), width=1)
                    ], className="mb-2")
                    children.append(new_input)
            except json.JSONDecodeError:
                pass # Lidar com JSON inválido se necessário
        return nome, children
    return "", []
