import dash
from dash import html, dcc, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
from app import app
from banco_dados.banco import Banco  # Certifique-se de importar corretamente sua classe Banco
import pandas as pd

banco = Banco()  # Instância do banco

# Layout do formulário de máquinas com a opção de editar
table_style = {
    "maxHeight": "400px",  # Limita a altura da tabela
    "overflowY": "auto"
}

layout = html.Div([ 
    dcc.Store(id="store-mensagem-maquina", data=""), 

    dbc.Modal([ 
        dbc.ModalHeader(dbc.ModalTitle("Gerenciar Máquinas")), 
        dbc.ModalBody( 
            dbc.Row([ 
                dbc.Col([ 
                    # Adicionar Máquina 
                    html.Label("Adicionar Nova Máquina:"), 
                    dbc.Input(id="input-maquina-nome", type="text", placeholder="Nome da máquina", className="mb-2"), 
                    dcc.Dropdown(id="dropdown-setor-maquina", placeholder="Selecione um setor", className="mb-2"), 
                    dbc.Input(id="input-maquina-custo", type="number", placeholder="Custo da máquina", className="mb-2"),
                    dbc.Button("Adicionar Máquina", id="btn-add-maquina", color="success", className="w-100 mb-3"), 
                    html.Hr(), 

                    # Excluir Máquina 
                    html.Label("Excluir Máquina Existente:"), 
                    dcc.Dropdown(id="dropdown-maquina-delete", placeholder="Selecione uma máquina", className="mb-2"), 
                    dbc.Button("Excluir Máquina", id="btn-delete-maquina", color="danger", className="w-100"), 
                    html.Hr(), 

                    # Editar Máquina 
                    html.Label("Editar Máquina:"), 
                    dcc.Dropdown(id="dropdown-maquina-edit", placeholder="Selecione uma máquina", className="mb-2"), 
                    dbc.Input(id="input-maquina-edit-nome", type="text", placeholder="Novo nome da máquina", className="mb-2"), 
                    dcc.Dropdown(id="dropdown-setor-maquina-edit", placeholder="Novo setor", className="mb-2"), 
                    dbc.Input(id="input-maquina-edit-custo", type="number", placeholder="Novo custo da máquina", className="mb-2"),
                    dbc.Button("Salvar Edição", id="btn-edit-maquina", color="warning", className="w-100"), 
                    dbc.Alert(id="alert-mensagem-maquina", color="success", is_open=False, dismissable=True, className="mt-3"), 
                ], width=6),  # Ajuste de largura conforme necessário

                dbc.Col([ 
                    html.Label("Máquinas Cadastradas:"), 
                    dash_table.DataTable(id='tabela-maquinas', 
                        columns=[ 
                            {"name": "ID", "id": "maquina_id"}, 
                            {"name": "Nome", "id": "maquina_nome"}, 
                            {"name": "Setor", "id": "setor_nome"},
                            {"name": "Custo", "id": "maquina_custo"}
                        ], 
                        page_size=10, 
                        style_table=table_style 
                    ) 
                ], width=6)  # Ajuste de largura conforme necessário
            ]) 
        ), 
        dbc.ModalFooter( 
            dbc.Button("Fechar", id="close-modal-maquina", className="ms-auto", n_clicks=0) 
        ), 
    ], id="modal-maquina", is_open=False,className="modal-medio" , style={"maxWidth": "90%", "overflowY": "auto"}),  # Aumentando a largura do modal
])

# Callback para abrir/fechar o modal
@app.callback(
    Output("modal-maquina", "is_open"),
    [Input("btn_add_maquinas", "n_clicks"), Input("close-modal-maquina", "n_clicks")],
    [State("modal-maquina", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_maquina(n_clicks_open, n_clicks_close, is_open):
    if n_clicks_open or n_clicks_close:
        return not is_open
    return is_open

# Callback para preencher o setor da máquina selecionada para edição
@app.callback(
    [Output("input-maquina-edit-nome", "value"),
     Output("dropdown-setor-maquina-edit", "value"),
     Output("input-maquina-edit-custo", "value"),
     Output("dropdown-setor-maquina-edit", "options")],
    [Input("dropdown-maquina-edit", "value")]
)
def preencher_dados_edicao(maquina_id_edit):
    if not maquina_id_edit:
        raise dash.exceptions.PreventUpdate
    
    # Obtém os detalhes da máquina selecionada
    maquina = banco.ler_tabela("maquina").query("maquina_id == @maquina_id_edit").iloc[0]
    setores = banco.ler_tabela("setor")
    
    return maquina["maquina_nome"], maquina["setor_id"], maquina["maquina_custo"], [
        {"label": row["setor_nome"], "value": row["setor_id"]} for _, row in setores.iterrows()
    ]

# Callback para adicionar/excluir/editar máquinas e atualizar os dropdowns e tabela
@app.callback(
    [Output("dropdown-setor-maquina", "options"),
     Output("dropdown-maquina-delete", "options"),
     Output("dropdown-maquina-edit", "options"),
     Output("tabela-maquinas", "data"),
     Output("store-mensagem-maquina", "data")],
    [Input("btn-add-maquina", "n_clicks"), 
     Input("btn-delete-maquina", "n_clicks"),
     Input("btn-edit-maquina", "n_clicks"),
     Input("modal-maquina", "is_open")],
    [State("input-maquina-nome", "value"), 
     State("input-maquina-custo", "value"),
     Input("dropdown-setor-maquina", "value"), 
     State("dropdown-maquina-delete", "value"),
     State("dropdown-maquina-edit", "value"),
     State("input-maquina-edit-nome", "value"),
     State("dropdown-setor-maquina-edit", "value"),
     State("input-maquina-edit-custo", "value")],
    prevent_initial_call=True
)
def manage_maquina(n_add, n_delete, n_edit, is_open, maquina_nome, maquina_custo, setor_id, maquina_id_delete, maquina_id_edit, novo_nome_maquina, novo_setor_id, novo_custo_maquina):
    ctx = callback_context
    mensagem = ""

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # Adicionar Máquina
    if button_id == "btn-add-maquina" and maquina_nome and setor_id:
        banco.inserir_dados("maquina", maquina_nome=maquina_nome, setor_id=setor_id, maquina_custo=maquina_custo)
        mensagem = f"Máquina '{maquina_nome}' adicionada com sucesso!"

    # Excluir Máquina
    elif button_id == "btn-delete-maquina" and maquina_id_delete:
        banco.deletar_dado("maquina", maquina_id_delete)
        mensagem = "Máquina excluída com sucesso!"

    # Editar Máquina
    elif button_id == "btn-edit-maquina" and maquina_id_edit:
        banco.editar_dado("maquina", maquina_id_edit, 
                           maquina_nome=novo_nome_maquina if novo_nome_maquina else None,
                           setor_id=novo_setor_id if novo_setor_id else None,
                           maquina_custo=novo_custo_maquina if novo_custo_maquina else None)
        mensagem = f"Máquina '{novo_nome_maquina}' editada com sucesso!"

    # Atualiza os dropdowns e tabela
    setores = banco.ler_tabela("setor")
    maquinas = banco.ler_tabela("maquina")
    
    # Criar DataFrames com as colunas necessárias
    setores_df = pd.DataFrame({
        'setor_id': setores['setor_id'],
        'setor_nome': setores['setor_nome']
    })
    
    # Inicializar maquinas_df vazio com as colunas corretas
    maquinas_df = pd.DataFrame(columns=['maquina_id', 'maquina_nome', 'setor_id', 'maquina_custo'])
    
    # Se houver dados em maquinas, criar o DataFrame
    if not maquinas.empty:
        maquinas_df = pd.DataFrame({
            'maquina_id': maquinas['id'] if 'id' in maquinas.columns else maquinas['maquina_id'],
            'maquina_nome': maquinas['nome'] if 'nome' in maquinas.columns else maquinas['maquina_nome'],
            'setor_id': maquinas['setor'] if 'setor' in maquinas.columns else maquinas['setor_id'],
            'maquina_custo': maquinas['custo'] if 'custo' in maquinas.columns else maquinas['maquina_custo']
        })
    
    # Merge com as colunas corretas
    df_maquinas = maquinas_df.merge(setores_df, on="setor_id", how="left") if not maquinas_df.empty else pd.DataFrame()

    if setor_id and not df_maquinas.empty:
        df_maquinas = df_maquinas[df_maquinas["setor_id"] == setor_id]
    
    return (
        [{"label": row["setor_nome"], "value": row["setor_id"]} for _, row in setores_df.iterrows()],
        [{"label": row["maquina_nome"], "value": row["maquina_id"]} for _, row in maquinas_df.iterrows()],
        [{"label": row["maquina_nome"], "value": row["maquina_id"]} for _, row in maquinas_df.iterrows()],
        df_maquinas.to_dict("records"),
        mensagem
    )