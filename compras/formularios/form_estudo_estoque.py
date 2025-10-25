from dash import html, dcc, callback_context, dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
from banco_dados.banco import Banco
import pandas as pd
from sqlalchemy import text
from app import app

banco = Banco()
engine = banco.engine

# Layout do formulário
form_estudo = dbc.Row([
    dbc.Col([
        dbc.Label("Categoria", html_for="estudo-categoria"),
        dcc.Dropdown(id="estudo-categoria-dropdown", placeholder="Selecione a categoria")
    ], width=4),
    dbc.Col([
        dbc.Label("Subtipo", html_for="estudo-subtipo"),
        dbc.Input(id="estudo-subtipo", type="text", placeholder="Ex: TRANSP_500X800_C_TESTE")
    ], width=5),
    dbc.Col([
        dbc.Label("Peso Médio (Kg)", html_for="estudo-peso"),
        dbc.Input(id="estudo-peso", type="number", placeholder="Ex: 0.5", min=0, step=0.000001)
    ], width=3)
])

# Tabela de estudos
tabela_estudos = html.Div(id='tabela-estudos-estoque')

# Layout do modal
layout = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Cadastro de Estudos de Estoque")),
    dbc.ModalBody([
        dcc.Store(id='edit-estudo-id-store', data=None),
        form_estudo,
        html.Br(),
        dbc.Button("Salvar", id="estudo-btn-salvar", color="primary", className="me-1", n_clicks=0),
        dbc.Button("Limpar", id="estudo-btn-limpar", color="info", outline=True, className="me-1", n_clicks=0),
        html.Div(id='feedback-estudo', className="mt-3"),
        html.Hr(),
        tabela_estudos
    ]),
    dbc.ModalFooter(
        dbc.Button("Fechar", id="estudo-btn-fechar", color="secondary")
    )
], id="modal-estudo", size="xl", is_open=False)

# --- Callbacks ---

def get_category_options():
    try:
        df_cat = pd.read_sql('SELECT cae_id, cae_linha FROM categoria_estoque ORDER BY cae_linha', engine)
        options = [{'label': row['cae_linha'], 'value': row['cae_id']} for _, row in df_cat.iterrows()]
        return options
    except Exception:
        return []

@app.callback(
    Output('estudo-categoria-dropdown', 'options'),
    Input('modal-estudo', 'is_open')
)
def carregar_categorias_dropdown(is_open):
    if is_open:
        return get_category_options()
    return []

@app.callback(
    Output('tabela-estudos-estoque', 'children'),
    Input('modal-estudo', 'is_open'),
    Input('feedback-estudo', 'children')
)
def atualizar_tabela_estudos(is_open, feedback):
    if is_open:
        try:
            query = """
                SELECT 
                    e.ese_id,
                    e.ese_subtipo,
                    e.ese_peso_medio,
                    c.cae_linha
                FROM estudo_estoque e
                LEFT JOIN categoria_estoque c ON e.ese_cae_id = c.cae_id
                ORDER BY c.cae_linha, e.ese_subtipo
            """
            df_merged = pd.read_sql(query, engine)

            if df_merged.empty:
                return dbc.Alert("Nenhum estudo cadastrado.", color="info", className="mt-3")
        except Exception as e:
            return dbc.Alert(f"Erro ao ler estudos: {e}", color="danger")
        
        rows = []
        for i, row in df_merged.iterrows():
            peso_medio = row.get('ese_peso_medio', 0)
            peso_formatado = f"{peso_medio:,.6f}".replace(".", ",") if peso_medio is not None else "0,000000"
            rows.append(html.Tr([
                html.Td(row.get('cae_linha', 'N/A')),
                html.Td(row['ese_subtipo']),
                html.Td(peso_formatado),
                html.Td([
                    dbc.Button(html.I(className="fas fa-edit"), id={'type': 'edit-estudo', 'index': row['ese_id']}, color="warning", size="sm", className="me-1", n_clicks=0),
                    dbc.Button(html.I(className="fas fa-trash-alt"), id={'type': 'delete-estudo', 'index': row['ese_id']}, color="danger", size="sm", n_clicks=0)
                ], style={'textAlign': 'center'})
            ]))

        return dbc.Table([
            html.Thead(html.Tr([
                html.Th("Categoria"),
                html.Th("Subtipo"),
                html.Th("Peso Médio (Kg)"),
                html.Th("Ações", style={'textAlign': 'center'})
            ])),
            html.Tbody(rows)
        ], striped=True, bordered=True, hover=True, className="mt-3")
    return ""

@app.callback(
    Output('estudo-categoria-dropdown', 'value'),
    Output('estudo-subtipo', 'value'),
    Output('estudo-peso', 'value'),
    Output('edit-estudo-id-store', 'data'),
    Input('estudo-btn-limpar', 'n_clicks'),
    prevent_initial_call=True
)
def limpar_form_estudo(n_clicks):
    if n_clicks > 0:
        return None, "", None, None
    return dash.no_update

@app.callback(
    Output('feedback-estudo', 'children', allow_duplicate=True),
    Output('edit-estudo-id-store', 'data', allow_duplicate=True),
    Output('estudo-categoria-dropdown', 'value', allow_duplicate=True),
    Output('estudo-subtipo', 'value', allow_duplicate=True),
    Output('estudo-peso', 'value', allow_duplicate=True),
    Input('estudo-btn-salvar', 'n_clicks'),
    State('estudo-categoria-dropdown', 'value'),
    State('estudo-subtipo', 'value'),
    State('estudo-peso', 'value'),
    State('edit-estudo-id-store', 'data'),
    prevent_initial_call=True
)
def salvar_estudo(n_clicks, categoria_id, subtipo, peso, edit_id):
    if n_clicks == 0:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if not categoria_id or not subtipo:
        return dbc.Alert("Categoria e Subtipo são obrigatórios.", color="warning", dismissable=True), dash.no_update, dash.no_update, dash.no_update, dash.no_update

    peso_val = peso if peso else 0.0
    
    try:
        with engine.connect() as conn:
            if edit_id:
                query = text("""
                    UPDATE estudo_estoque 
                    SET ese_cae_id = :cat_id, ese_subtipo = :subtipo, ese_peso_medio = :peso 
                    WHERE ese_id = :id
                """)
                conn.execute(query, {"cat_id": categoria_id, "subtipo": subtipo, "peso": peso_val, "id": edit_id})
                msg = "Estudo atualizado com sucesso!"
            else:
                query = text("""
                    INSERT INTO estudo_estoque (ese_cae_id, ese_subtipo, ese_peso_medio) 
                    VALUES (:cat_id, :subtipo, :peso)
                """)
                conn.execute(query, {"cat_id": categoria_id, "subtipo": subtipo, "peso": peso_val})
                msg = "Estudo adicionado com sucesso!"
            conn.commit()
        
        return dbc.Alert(msg, color="success", dismissable=True), None, None, "", None
    except Exception as e:
        return dbc.Alert(f"Erro ao salvar: {e}", color="danger", dismissable=True), edit_id, categoria_id, subtipo, peso

@app.callback(
    Output('estudo-categoria-dropdown', 'value', allow_duplicate=True),
    Output('estudo-subtipo', 'value', allow_duplicate=True),
    Output('estudo-peso', 'value', allow_duplicate=True),
    Output('edit-estudo-id-store', 'data', allow_duplicate=True),
    Input({'type': 'edit-estudo', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def preencher_form_edicao_estudo(n_clicks):
    ctx = callback_context
    if not ctx.triggered_id or not any(c > 0 for c in n_clicks):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    estudo_id = ctx.triggered_id['index']
    
    try:
        df_estudo = pd.read_sql(f'SELECT * FROM estudo_estoque WHERE ese_id = {estudo_id}', engine)
        if not df_estudo.empty:
            estudo = df_estudo.iloc[0]
            return estudo['ese_cae_id'], estudo['ese_subtipo'], estudo['ese_peso_medio'], estudo_id
    except Exception as e:
        return None, "", None, None
        
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output('feedback-estudo', 'children', allow_duplicate=True),
    Input({'type': 'delete-estudo', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def deletar_estudo(n_clicks):
    ctx = callback_context
    if not ctx.triggered_id or not any(c > 0 for c in n_clicks):
        return dash.no_update

    estudo_id = ctx.triggered_id['index']

    try:
        with engine.connect() as conn:
            query = text("DELETE FROM estudo_estoque WHERE ese_id = :id")
            conn.execute(query, {"id": estudo_id})
            conn.commit()
        return dbc.Alert("Estudo deletado com sucesso.", color="success", dismissable=True)
    except Exception as e:
        return dbc.Alert(f"Erro ao deletar: {e}", color="danger", dismissable=True)
