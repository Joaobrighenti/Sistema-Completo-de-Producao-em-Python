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
form_categoria = dbc.Row([
    dbc.Col([
        dbc.Label("Linha/Categoria", html_for="categoria-linha"),
        dbc.Input(id="categoria-linha", type="text", placeholder="Ex: FITA ADESIVA")
    ], width=6),
    dbc.Col([
        dbc.Label("Consumo Mensal (unid.)", html_for="categoria-consumo"),
        dbc.Input(id="categoria-consumo", type="number", placeholder="Ex: 15000", min=0)
    ], width=6)
])

# Tabela de categorias
tabela_categorias = html.Div(id='tabela-categorias-estoque')

# Layout do modal
layout = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Cadastro de Categorias de Estoque")),
    dbc.ModalBody([
        dcc.Store(id='edit-cat-id-store', data=None),
        form_categoria,
        html.Br(),
        dbc.Button("Salvar", id="categoria-btn-salvar", color="primary", className="me-1", n_clicks=0),
        dbc.Button("Limpar", id="categoria-btn-limpar", color="info", outline=True, className="me-1", n_clicks=0),
        html.Div(id='feedback-categoria', className="mt-3"),
        html.Hr(),
        tabela_categorias
    ]),
    dbc.ModalFooter(
        dbc.Button("Fechar", id="categoria-btn-fechar", color="secondary")
    )
], id="modal-categoria", size="lg", is_open=False)

# --- Callbacks ---

@app.callback(
    Output('tabela-categorias-estoque', 'children'),
    Input('modal-categoria', 'is_open'),
    Input('feedback-categoria', 'children') # Refresh on save/delete
)
def atualizar_tabela_categorias(is_open, feedback):
    if is_open:
        try:
            df_cat = pd.read_sql('SELECT * FROM categoria_estoque ORDER BY cae_linha', engine)
        except Exception as e:
            return dbc.Alert(f"Erro ao ler categorias: {e}", color="danger")
            
        if df_cat.empty:
            return dbc.Alert("Nenhuma categoria cadastrada.", color="info", className="mt-3")

        rows = []
        for i, row in df_cat.iterrows():
            consumo = row.get('cae_consumo_mensal', 0)
            consumo_formatado = f"{consumo:,.0f}".replace(",", ".") if consumo else "0"
            rows.append(html.Tr([
                html.Td(row['cae_linha']),
                html.Td(consumo_formatado),
                html.Td([
                    dbc.Button(html.I(className="fas fa-edit"), id={'type': 'edit-cat', 'index': row['cae_id']}, color="warning", size="sm", className="me-1", n_clicks=0),
                    dbc.Button(html.I(className="fas fa-trash-alt"), id={'type': 'delete-cat', 'index': row['cae_id']}, color="danger", size="sm", n_clicks=0)
                ], style={'textAlign': 'center'})
            ]))

        return dbc.Table([
            html.Thead(html.Tr([
                html.Th("Linha/Categoria"),
                html.Th("Consumo Mensal"),
                html.Th("Ações", style={'textAlign': 'center'})
            ])),
            html.Tbody(rows)
        ], striped=True, bordered=True, hover=True, className="mt-3")
    return ""

@app.callback(
    Output('categoria-linha', 'value'),
    Output('categoria-consumo', 'value'),
    Output('edit-cat-id-store', 'data'),
    Input('categoria-btn-limpar', 'n_clicks'),
    prevent_initial_call=True
)
def limpar_form_categoria(n_clicks):
    if n_clicks > 0:
        return "", None, None
    return dash.no_update

@app.callback(
    Output('feedback-categoria', 'children', allow_duplicate=True),
    Output('edit-cat-id-store', 'data', allow_duplicate=True),
    Output('categoria-linha', 'value', allow_duplicate=True),
    Output('categoria-consumo', 'value', allow_duplicate=True),
    Input('categoria-btn-salvar', 'n_clicks'),
    State('categoria-linha', 'value'),
    State('categoria-consumo', 'value'),
    State('edit-cat-id-store', 'data'),
    prevent_initial_call=True
)
def salvar_categoria(n_clicks, linha, consumo, edit_id):
    if n_clicks == 0:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not linha:
        return dbc.Alert("O nome da linha/categoria é obrigatório.", color="warning", dismissable=True), dash.no_update, dash.no_update, dash.no_update

    consumo_val = consumo if consumo else 0.0
    
    try:
        with engine.connect() as conn:
            if edit_id:
                query = text("UPDATE categoria_estoque SET cae_linha = :linha, cae_consumo_mensal = :consumo WHERE cae_id = :id")
                conn.execute(query, {"linha": linha, "consumo": consumo_val, "id": edit_id})
                msg = "Categoria atualizada com sucesso!"
            else:
                query = text("INSERT INTO categoria_estoque (cae_linha, cae_consumo_mensal) VALUES (:linha, :consumo)")
                conn.execute(query, {"linha": linha, "consumo": consumo_val})
                msg = "Categoria adicionada com sucesso!"
            conn.commit()
        
        return dbc.Alert(msg, color="success", dismissable=True), None, "", None
    except Exception as e:
        return dbc.Alert(f"Erro ao salvar: {e}", color="danger", dismissable=True), edit_id, linha, consumo

@app.callback(
    Output('categoria-linha', 'value', allow_duplicate=True),
    Output('categoria-consumo', 'value', allow_duplicate=True),
    Output('edit-cat-id-store', 'data', allow_duplicate=True),
    Input({'type': 'edit-cat', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def preencher_form_edicao(n_clicks):
    ctx = callback_context
    if not ctx.triggered_id or not any(c > 0 for c in n_clicks):
        return dash.no_update, dash.no_update, dash.no_update

    cat_id = ctx.triggered_id['index']
    
    try:
        df_cat = pd.read_sql(f'SELECT * FROM categoria_estoque WHERE cae_id = {cat_id}', engine)
        if not df_cat.empty:
            categoria = df_cat.iloc[0]
            return categoria['cae_linha'], categoria['cae_consumo_mensal'], cat_id
    except Exception as e:
        return "", None, None
        
    return dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output('feedback-categoria', 'children', allow_duplicate=True),
    Input({'type': 'delete-cat', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def deletar_categoria(n_clicks):
    ctx = callback_context
    if not ctx.triggered_id or not any(c > 0 for c in n_clicks):
        return dash.no_update

    cat_id = ctx.triggered_id['index']

    try:
        df_estudos = pd.read_sql(f'SELECT ese_id FROM estudo_estoque WHERE ese_cae_id = {cat_id}', engine)
        if not df_estudos.empty:
            return dbc.Alert("Não é possível deletar. Existem estudos vinculados a esta categoria.", color="danger", dismissable=True)

        with engine.connect() as conn:
            query = text("DELETE FROM categoria_estoque WHERE cae_id = :id")
            conn.execute(query, {"id": cat_id})
            conn.commit()
        return dbc.Alert("Categoria deletada com sucesso.", color="success", dismissable=True)
    except Exception as e:
        return dbc.Alert(f"Erro ao deletar: {e}", color="danger", dismissable=True)
