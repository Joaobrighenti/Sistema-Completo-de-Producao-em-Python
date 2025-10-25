import dash
from dash import html, dcc, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from app import app
from banco_dados.banco import Banco

banco = Banco()

table_style = {"maxHeight": "400px", "overflowY": "auto"}

modal_style = {
    "maxWidth": "90%",
    "width": "90%"
}

layout = html.Div([
    dcc.Store(id="store-mensagem-grupo", data=""),
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Gerenciar Grupos de Categoria")),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Tabs([
                        dbc.Tab([
                            html.Label("Nome do Grupo:", className="mt-3"),
                            dbc.Input(id="input-grupo-nome", type="text", className="mb-2"),
                            html.Label("Unidade:"),
                            dbc.Input(id="input-grupo-unidade", type="text", placeholder="Ex: kg, litro, und", className="mb-2"),
                            dbc.Button("Adicionar", id="btn-add-grupo", color="success", className="w-100 mb-3"),
                        ], label="Adicionar"),
                        dbc.Tab([
                            html.Label("Selecionar Grupo:", className="mt-3"),
                            dcc.Dropdown(id="dropdown-grupo-delete", className="mb-2"),
                            dbc.Button("Excluir", id="btn-delete-grupo", color="danger", className="w-100"),
                        ], label="Excluir"),
                        dbc.Tab([
                            html.Label("Selecionar Grupo:", className="mt-3"),
                            dcc.Dropdown(id="dropdown-grupo-edit", className="mb-2"),
                            html.Label("Novo Nome:"),
                            dbc.Input(id="input-grupo-edit-nome", type="text", className="mb-2"),
                            html.Label("Nova Unidade:"),
                            dbc.Input(id="input-grupo-edit-unidade", type="text", className="mb-2"),
                            dbc.Button("Salvar", id="btn-edit-grupo", color="warning", className="w-100"),
                        ], label="Editar"),
                    ])
                ], width=4),

                dbc.Col([
                    html.Label("Grupos Cadastrados:"),
                    dash_table.DataTable(id='tabela-grupos',
                        columns=[
                            {"name": "ID", "id": "id_grupo"},
                            {"name": "Nome do Grupo", "id": "nome_grupo"},
                            {"name": "Unidade", "id": "unidade"}
                        ],
                        page_size=20,
                        style_table={"width": "100%", "overflowX": "auto"},
                    )
                ], width=8),
            ]),
        ]),
        dbc.ModalFooter([
            html.Div(id="alert-container-grupo", className="me-auto"),
            dbc.Button("Fechar", id="btn_fechar_grupo", color="secondary")
        ])
    ], id="modal-grupo-item", is_open=False, className="custom-modal-grupo"),
])

@app.callback(
    Output("modal-grupo-item", "is_open"),
    [Input("btn_abrir_grupo", "n_clicks"), Input("btn_fechar_grupo", "n_clicks")],
    [State("modal-grupo-item", "is_open")]
)
def toggle_modal_grupo(n_abrir, n_fechar, is_open):
    if n_abrir or n_fechar:
        return not is_open
    return is_open

@app.callback(
    Output("alert-container-grupo", "children"),
    Input("store-mensagem-grupo", "data"),
    prevent_initial_call=True
)
def show_alert_grupo(mensagem):
    if mensagem:
        return dbc.Alert(mensagem, color="success", duration=4000, dismissable=True)
    return []

@app.callback(
    [Output("dropdown-grupo-delete", "options"),
     Output("dropdown-grupo-edit", "options"),
     Output("tabela-grupos", "data"),
     Output("store-mensagem-grupo", "data"),
     Output("input-grupo-nome", "value"),
     Output("input-grupo-unidade", "value"),
     Output("dropdown-grupo-delete", "value"),
     Output("dropdown-grupo-edit", "value"),
     Output("input-grupo-edit-nome", "value"),
     Output("input-grupo-edit-unidade", "value")],
    [Input("btn-add-grupo", "n_clicks"),
     Input("btn-delete-grupo", "n_clicks"),
     Input("btn-edit-grupo", "n_clicks"),
     Input("modal-grupo-item", "is_open"),
     Input("dropdown-grupo-edit", "value")],
    [State("input-grupo-nome", "value"),
     State("input-grupo-unidade", "value"),
     State("dropdown-grupo-delete", "value"),
     State("input-grupo-edit-nome", "value"),
     State("input-grupo-edit-unidade", "value")],
    prevent_initial_call=True
)
def manage_grupo(n_add, n_delete, n_edit, is_open, grupo_id_edit, 
                 nome, unidade, grupo_id_del, novo_nome, nova_unidade):
    ctx = callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    mensagem = ""

    # Initialize all return values to no_update
    (
        dropdown_opts_del, dropdown_opts_edit, table_data, msg_data,
        add_nome, add_unidade, del_dropdown, edit_dropdown, edit_nome, edit_unidade
    ) = [dash.no_update] * 10

    # When opening modal or performing an action, update the table and dropdowns
    if triggered_id in ["modal-grupo-item", "btn-add-grupo", "btn-delete-grupo", "btn-edit-grupo"]:
        if triggered_id == "btn-add-grupo" and nome:
            banco.inserir_dados("grupo_categoria", nome_grupo=nome, unidade=unidade)
            mensagem = f"Grupo '{nome}' adicionado com sucesso!"
            add_nome, add_unidade = "", ""
        
        elif triggered_id == "btn-delete-grupo" and grupo_id_del:
            banco.deletar_dado("grupo_categoria", grupo_id_del)
            mensagem = "Grupo excluído com sucesso!"
            del_dropdown = None
        
        elif triggered_id == "btn-edit-grupo" and grupo_id_edit:
            banco.editar_dado("grupo_categoria", grupo_id_edit, nome_grupo=novo_nome, unidade=nova_unidade)
            mensagem = f"Grupo '{novo_nome}' editado com sucesso!"
            edit_dropdown, edit_nome, edit_unidade = None, "", ""
        
        grupos = banco.ler_tabela("grupo_categoria")
        dropdown_options = [{"label": row["nome_grupo"], "value": row["id_grupo"]} for _, row in grupos.iterrows()]
        
        dropdown_opts_del = dropdown_options
        dropdown_opts_edit = dropdown_options
        table_data = grupos.to_dict("records")
        msg_data = mensagem
        
    # When selecting a group to edit, fill the form
    elif triggered_id == "dropdown-grupo-edit" and grupo_id_edit:
        grupo = banco.ler_tabela("grupo_categoria").set_index("id_grupo").loc[grupo_id_edit]
        edit_nome = grupo["nome_grupo"]
        edit_unidade = grupo["unidade"]

    return (
        dropdown_opts_del, dropdown_opts_edit, table_data, msg_data,
        add_nome, add_unidade, del_dropdown, edit_dropdown, edit_nome, edit_unidade
    )
