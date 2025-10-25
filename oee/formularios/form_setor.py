import dash
from dash import html, dcc, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
from banco_dados.banco import Banco  # Certifique-se de importar corretamente sua classe Banco
from app import app

banco = Banco()  # Instância do banco

# Layout do formulário de setor
layout = html.Div([
    dcc.Store(id="store-mensagem", data=""),

    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Gerenciar Setores")),
            dbc.ModalBody([
                html.Label("Adicionar Novo Setor:"),
                dbc.Input(id="input-setor-nome", type="text", placeholder="Nome do setor", className="mb-2"),
                dcc.Dropdown(
                    id='dropdown-tipo-plano-add',
                    options=[
                        {'label': 'Plano', 'value': 1},
                        {'label': 'Unidade', 'value': 2}
                    ],
                    placeholder="Selecione o tipo de plano",
                    className="mb-2"
                ),
                dcc.Dropdown(
                    id='dropdown-set-padrao-add',
                    options=[
                        {'label': 'Sim', 'value': 1},
                        {'label': 'Não', 'value': 2}
                    ],
                    placeholder="Setor Padrão?",
                    className="mb-2"
                ),
                dbc.Button("Adicionar Setor", id="btn-add-setor", color="success", className="w-100 mb-3"),

                html.Hr(),

                html.Label("Editar ou Excluir Setor Existente:"),
                dcc.Dropdown(id="dropdown-setor-manage", placeholder="Selecione um setor para gerenciar...", className="mb-2"),
                
                dbc.Input(id="input-setor-novo-nome", type="text", placeholder="Novo nome do setor", className="mb-2"),
                
                dcc.Dropdown(
                    id='dropdown-tipo-plano-edit',
                    options=[
                        {'label': 'Plano', 'value': 1},
                        {'label': 'Unidade', 'value': 2}
                    ],
                    placeholder="Selecione o novo tipo de plano",
                    className="mb-2"
                ),
                dcc.Dropdown(
                    id='dropdown-set-padrao-edit',
                    options=[
                        {'label': 'Sim', 'value': 1},
                        {'label': 'Não', 'value': 2}
                    ],
                    placeholder="Setor Padrão?",
                    className="mb-2"
                ),
                
                dbc.Row([
                    dbc.Col(dbc.Button("Salvar Edição", id="btn-edit-setor", color="primary", className="w-100"), width=6),
                    dbc.Col(dbc.Button("Excluir Setor", id="btn-delete-setor", color="danger", className="w-100"), width=6),
                ]),

                dbc.Alert(id="alert-mensagem", color="success", is_open=False, dismissable=True, className="mt-3"),

                html.Hr(),
                html.H4("Setores Cadastrados"),  # Título da tabela
                dash_table.DataTable(
                    id="table-setores",
                    columns=[
                        {"name": "ID", "id": "setor_id"},
                        {"name": "Nome do Setor", "id": "setor_nome"},
                        {"name": "Tipo Plano", "id": "tipo_plano"},
                        {"name": "Padrão", "id": "set_padrao"},
                    ],
                    data=[],  # Inicialmente, a tabela está vazia
                    style_table={'height': '300px', 'overflowY': 'auto'},
                    style_cell={'textAlign': 'center'},  # Estiliza as células
                    style_header={'backgroundColor': 'lightgray', 'fontWeight': 'bold'}
                ),
            ]),
 
        ],
        id="modal-setor",
        is_open=False,
    ),
])

# Callbacks para abrir/fechar o modal
@app.callback(
    Output("modal-setor", "is_open"),
    [Input("btn_add_setores", "n_clicks")],
    [State("modal-setor", "is_open")],
    prevent_initial_call=True
)
def toggle_modal(n_clicks, is_open):

    if n_clicks:
        return not is_open
    return is_open

# Callback para preencher o nome do setor ao selecionar para editar
@app.callback(
    [Output("input-setor-novo-nome", "value"),
     Output("dropdown-tipo-plano-edit", "value"),
     Output("dropdown-set-padrao-edit", "value")],
    Input("dropdown-setor-manage", "value"),
    State("dropdown-setor-manage", "options"),
    prevent_initial_call=True
)
def populate_edit_fields(setor_id, options):
    if not setor_id or not options:
        return "", None, None
    
    # Get sector name from dropdown options
    selected_option = next((opt for opt in options if opt['value'] == setor_id), None)
    setor_nome = selected_option['label'] if selected_option else ""

    # Get data from database
    setor_df = banco.ler_tabela("setor", setor_id=setor_id)
    if not setor_df.empty:
        tipo_plano = setor_df.iloc[0].get('tipo_plano')
        set_padrao = setor_df.iloc[0].get('set_padrao')
        return setor_nome, tipo_plano, set_padrao
    
    return setor_nome, None, None

# Callback único para adicionar, editar e excluir setores
@app.callback(
    [Output("dropdown-setor-manage", "options"),
     Output("store-mensagem", "data"),
     Output("table-setores", "data")],
    [Input("btn-add-setor", "n_clicks"), 
     Input("btn-edit-setor", "n_clicks"),
     Input("btn-delete-setor", "n_clicks"), 
     Input("modal-setor", "is_open")],
    [State("input-setor-nome", "value"), 
     State("dropdown-tipo-plano-add", "value"),
     State("dropdown-set-padrao-add", "value"),
     State("dropdown-setor-manage", "value"),
     State("input-setor-novo-nome", "value"),
     State("dropdown-tipo-plano-edit", "value"),
     State("dropdown-set-padrao-edit", "value")],
    prevent_initial_call=True
)
def manage_setor(n_add, n_edit, n_delete, is_open, nome_setor_add, tipo_plano_add, set_padrao_add, setor_id_manage, novo_nome_setor, tipo_plano_edit, set_padrao_edit):
    ctx = callback_context
    mensagem = ""

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "btn-add-setor" and nome_setor_add:
        banco.inserir_dados("setor", setor_nome=nome_setor_add, tipo_plano=tipo_plano_add, set_padrao=set_padrao_add)
        mensagem = f"Setor '{nome_setor_add}' adicionado com sucesso!"

    elif button_id == "btn-edit-setor" and setor_id_manage and novo_nome_setor:
        banco.editar_dado("setor", setor_id_manage, setor_nome=novo_nome_setor, tipo_plano=tipo_plano_edit, set_padrao=set_padrao_edit)
        mensagem = f"Setor atualizado para '{novo_nome_setor}'!"

    elif button_id == "btn-delete-setor" and setor_id_manage:
        maquinas = banco.ler_tabela("maquina")
        if not maquinas.empty and 'setor_id' in maquinas.columns:
            maquinas_no_setor = maquinas[maquinas['setor_id'] == setor_id_manage]
            if not maquinas_no_setor.empty:
                mensagem = "Não é possível excluir o setor, pois existem máquinas associadas a ele."
            else:
                banco.deletar_dado("setor", setor_id_manage)
                mensagem = "Setor excluído com sucesso!"
        else:
            banco.deletar_dado("setor", setor_id_manage)
            mensagem = "Setor excluído com sucesso!"

    setor_df = banco.ler_tabela("setor")
    setores = [{"label": row["setor_nome"], "value": row["setor_id"]} for _, row in setor_df.iterrows()]
    
    def map_tipo_plano(value):
        if value == 1:
            return "Plano"
        if value == 2:
            return "Unidade"
        return ""

    def map_set_padrao(value):
        if value == 1:
            return "Sim"
        if value == 2:
            return "Não"
        return ""

    if 'tipo_plano' in setor_df.columns:
        setor_df['tipo_plano'] = setor_df['tipo_plano'].apply(map_tipo_plano)
        
    if 'set_padrao' in setor_df.columns:
        setor_df['set_padrao'] = setor_df['set_padrao'].apply(map_set_padrao)
        
    dados_tabela = setor_df.to_dict('records')

    return setores, mensagem, dados_tabela

# Callback para exibir mensagem de sucesso
@app.callback(
    Output("alert-mensagem", "children"),
    Output("alert-mensagem", "is_open"),
    Input("store-mensagem", "data"),
    prevent_initial_call=True
)
def exibir_mensagem(mensagem):
    if mensagem:
        return mensagem, True
    return dash.no_update
