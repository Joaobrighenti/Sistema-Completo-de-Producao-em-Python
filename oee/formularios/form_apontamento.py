from dash import html, dcc, Input, Output, State, dash_table, callback_context
import dash
import dash_bootstrap_components as dbc
from app import app
import pandas as pd
from banco_dados.banco import Banco
from datetime import datetime
from sqlalchemy import text
from .form_parada import create_form_parada
from .form_producao import create_form_producao
import time

def create_modal():
    return html.Div([
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Detalhes do Apontamento"), close_button=True),
                dbc.ModalBody([
                    dbc.Form([
                        dbc.Row([
                            dbc.Col([
                                html.Label("Data:"),
                                html.P(id="modal-data", className="lead")
                            ], width=1),
                            dbc.Col([
                                html.Label("Início:"),
                                html.P(id="modal-inicio", className="lead")
                            ], width=1),
                            dbc.Col([
                                html.Label("Término:"),
                                html.P(id="modal-termino", className="lead")
                            ], width=1),
                            dbc.Col([
                                html.Label("Setor:"),
                                html.P(id="modal-setor-ap", className="lead")
                            ], width=1),
                            dbc.Col([
                                html.Label("Máquina:"),
                                html.P(id="modal-maquina-ap", className="lead")
                            ], width=1),
                            dbc.Col([
                                html.Label("Categoria:"),
                                dcc.Dropdown(
                                    id="modal-categoria-dropdown",
                                    style={"width": "100%"}
                                )
                            ], width=2),
                            dbc.Col([
                                html.Label("Meta:"),
                                html.Div(id="modal-categoria-meta", className="lead", style={
                                    "border": "1px solid #ddd",
                                    "padding": "8px",
                                    "border-radius": "4px",
                                    "min-height": "38px"
                                })
                            ], width=1),
                            dbc.Col([
                                html.Label("Status:"),
                                html.Div(id="modal-status", className="lead", 
                                       style={
                                           "border": "1px solid #ddd",
                                           "padding": "8px",
                                           "border-radius": "4px",
                                           "min-height": "38px"  # Mesma altura do dropdown
                                       })
                            ], width=1),
                            dbc.Col([
                                html.Label("Apontamentos Faltantes:"),
                                html.Div(id="modal-apontamentos-faltantes", className="lead", 
                                       style={
                                           "border": "1px solid #ddd",
                                           "padding": "8px",
                                           "border-radius": "4px",
                                           "min-height": "38px"
                                       })
                            ], width=2),
                            dbc.Col([
                                html.Label("Fechada"),
                                dbc.Checkbox(id="modal-fechado-checkbox")
                            ], width=1, className="text-center", align="center")
                        ], className="mb-3"),
                        
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.Label("Apontamentos de Parada:", style={"display": "inline-block", "marginRight": "10px"}),
                                    dbc.Button("+ Adicionar Parada", 
                                             id="btn-add-parada", 
                                             color="primary", 
                                             size="sm",
                                             style={"display": "inline-block", "marginRight": "10px"}),
                                    dbc.Button("Limpar Seleção",
                                             id="btn-clear-selection",
                                             color="secondary",
                                             size="sm",
                                             style={"display": "inline-block"})
                                ], style={"marginBottom": "10px"}),
                                
                                dash_table.DataTable(
                                    id='apontamentos-table',
                                    columns=[
                                        {"name": "ID", "id": "ap_id"},
                                        {"name": "Produção ID", "id": "ap_pr"},
                                        {"name": "Tempo", "id": "ap_tempo"},
                                        {"name": "Nível 1", "id": "nivel1_nome"},
                                        {"name": "Nível 2", "id": "nivel2_nome"},
                                        {"name": "Nível 3", "id": "nivel3_nome"},
                                        {"name": "Nível 4", "id": "nivel4_nome"},
                                        {"name": "Nível 5", "id": "nivel5_nome"},
                                        {"name": "Nível 6", "id": "nivel6_nome"},
                                        # Colunas ocultas para os IDs dos níveis
                                        {"name": "Nível 1 ID", "id": "ap_lv1"},
                                        {"name": "Nível 2 ID", "id": "ap_lv2"},
                                        {"name": "Nível 3 ID", "id": "ap_lv3"},
                                        {"name": "Nível 4 ID", "id": "ap_lv4"},
                                        {"name": "Nível 5 ID", "id": "ap_lv5"},
                                        {"name": "Nível 6 ID", "id": "ap_lv6"}
                                    ],
                                    hidden_columns=[
                                        "ap_id", "ap_pr",
                                        "ap_lv1", "ap_lv2", "ap_lv3",
                                        "ap_lv4", "ap_lv5", "ap_lv6"
                                    ],
                                    style_table={'overflowX': 'auto'},
                                    style_cell={
                                        'textAlign': 'left',
                                        'padding': '10px'
                                    },
                                    style_header={
                                        'backgroundColor': 'rgb(230, 230, 230)',
                                        'fontWeight': 'bold'
                                    },
                                    row_selectable='single',
                                    selected_rows=[]
                                )
                            ], width=12)
                        ]),
                        
                        # Espaçador e linha divisória
                        dbc.Row([
                            dbc.Col(html.Hr(style={"margin": "20px 0"}), width=12)
                        ]),
                        
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.Label("Apontamentos de Produção:", style={"display": "inline-block", "marginRight": "10px"}),
                                    dbc.Button("+ Adicionar Produção", 
                                             id="btn-add-producao", 
                                             color="primary", 
                                             size="sm",
                                             style={"display": "inline-block", "marginRight": "10px"}),
                                    dbc.Button("Limpar Seleção",
                                             id="btn-clear-selection-producao",
                                             color="secondary",
                                             size="sm",
                                             style={"display": "inline-block"})
                                ], style={"marginBottom": "10px"}),
                                dash_table.DataTable(
                                    id='apontamentos-producao-table',
                                    columns=[
                                        {"name": "ID", "id": "atp_id"},
                                        {"name": "PCP", "id": "atp_pcp"},
                                        {"name": "Produto", "id": "produto_nome"},
                                        {"name": "Quantidade", "id": "atp_qtd"},
                                        {"name": "Plano", "id": "atp_plano"},
                                        {"name": "Repetições", "id": "atp_repeticoes"},
                                        {"name": "Data", "id": "atp_data"},
                                        {"name": "Refugo", "id": "atp_refugos"},
                                        {"name": "Observação", "id": "atp_obs"},
                                        {"name": "Custo", "id": "atp_custo"}
                                    ],
                                    style_table={'overflowX': 'auto'},
                                    style_cell={
                                        'textAlign': 'left',
                                        'padding': '10px'
                                    },
                                    style_header={
                                        'backgroundColor': 'rgb(230, 230, 230)',
                                        'fontWeight': 'bold'
                                    },
                                    row_selectable='single',
                                    selected_rows=[]
                                )
                            ], width=12)
                        ])
                    ])
                ])
            ],
            id="modal-apontamento",
            size="xl",
            is_open=False,
            backdrop="static"
        ),
        
        # Modal para adicionar produção
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Adicionar/Editar Produção")),
                dbc.ModalBody(create_form_producao()),
            ],
            id="modal-producao",
            size="lg",
            is_open=False,
            backdrop="static"
        ),

        # Modal para adicionar parada
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Adicionar Parada")),
                dbc.ModalBody(create_form_parada()),
            ],
            id="modal-parada",
            size="lg",
            is_open=False,
        )
    ])

# Callbacks para o modal principal
@app.callback(
    [Output("modal-apontamento", "is_open"),
     Output("modal-data", "children"),
     Output("modal-inicio", "children"),
     Output("modal-termino", "children"),
     Output("modal-setor-ap", "children"),
     Output("modal-maquina-ap", "children"),
     Output("modal-categoria-dropdown", "options"),
     Output("modal-categoria-dropdown", "value"),
     Output("modal-fechado-checkbox", "value"),
     Output("apontamentos-table", "data"),
     Output("apontamentos-producao-table", "data", allow_duplicate=True)],
    [Input("production-table", "selected_rows"),
     Input("production-table", "data")],
    [State("modal-apontamento", "is_open")],
    prevent_initial_call=True
)
def toggle_modal(selected_rows, table_data, is_open):
    if not selected_rows or not table_data:
        return False, "", "", "", "", "", [], None, False, [], []
    
    # Pegar os dados da linha selecionada
    selected_row = table_data[selected_rows[0]]
    # Buscar apontamentos relacionados
    banco = Banco()
    query_paradas = """
        SELECT 
            a.ap_id,
            a.ap_pr,
            a.ap_tempo,
            a.ap_lv1,
            r1.ra_razao as nivel1_nome,
            a.ap_lv2,
            r2.ra_razao as nivel2_nome,
            a.ap_lv3,
            r3.ra_razao as nivel3_nome,
            a.ap_lv4,
            r4.ra_razao as nivel4_nome,
            a.ap_lv5,
            r5.ra_razao as nivel5_nome,
            a.ap_lv6,
            r6.ra_razao as nivel6_nome
        FROM apontamento a
        LEFT JOIN razao r1 ON a.ap_lv1 = r1.ra_id
        LEFT JOIN razao r2 ON a.ap_lv2 = r2.ra_id
        LEFT JOIN razao r3 ON a.ap_lv3 = r3.ra_id
        LEFT JOIN razao r4 ON a.ap_lv4 = r4.ra_id
        LEFT JOIN razao r5 ON a.ap_lv5 = r5.ra_id
        LEFT JOIN razao r6 ON a.ap_lv6 = r6.ra_id
        WHERE a.ap_pr = :pr_id
        ORDER BY a.ap_id
    """
    
    query_producao = """
        SELECT 
            ap.atp_id, 
            ap.atp_pcp, 
            prod.nome as produto_nome,
            ap.atp_qtd, 
            ap.atp_data, 
            ap.atp_refugos,
            ap.atp_obs,
            ap.atp_custo,
            CASE ap.atp_plano
                WHEN 0 THEN 'Tampa'
                WHEN 1 THEN 'Fundo'
                WHEN 2 THEN 'Berço/Envelope'
                WHEN 3 THEN 'Lâmina'
                ELSE ''
            END as atp_plano,
            ap.atp_repeticoes
        FROM apontamento_produto ap
        JOIN pcp ON ap.atp_pcp = pcp.pcp_id
        JOIN produtos prod ON pcp.pcp_produto_id = prod.produto_id
        WHERE ap.atp_producao = :pr_id
        ORDER BY ap.atp_id
    """
    
    # Buscar categorias da máquina
    query_categorias = """
        SELECT cp_id, cp_nome
        FROM categoria_produto cp
        JOIN maquina m ON cp.c_maq_id = m.maquina_id
        WHERE m.maquina_nome = :maquina_nome
        ORDER BY cp_nome
    """
    
    with banco.engine.connect() as conn:
        df_paradas = pd.read_sql(text(query_paradas), conn, params={"pr_id": selected_row["pr_id"]})
        df_producao = pd.read_sql(text(query_producao), conn, params={"pr_id": selected_row["pr_id"]})
        df_categorias = pd.read_sql(text(query_categorias), conn, params={"maquina_nome": selected_row["maquina_nome"]})
    
    # Criar opções do dropdown
    categoria_options = [{"label": row["cp_nome"], "value": row["cp_id"]} for _, row in df_categorias.iterrows()]
    categoria_value = selected_row.get("pr_categoria_produto_id")
    
    return (
        True,  # abrir modal
        selected_row["pr_data"],
        selected_row["pr_inicio"],
        selected_row["pr_termino"],
        selected_row["setor_nome"],
        selected_row["maquina_nome"],
        categoria_options,
        categoria_value,  # valor atual da categoria (id)
        selected_row.get("pr_fechado") == 1,
        df_paradas.to_dict('records'),
        df_producao.to_dict('records')
    )

# Callback para atualizar o status e meta quando a categoria mudar
@app.callback(
    [Output("modal-categoria-meta", "children"),
     Output("modal-status", "children"),
     Output("modal-apontamentos-faltantes", "children"),
     Output("modal-status", "style")],
    [Input("modal-categoria-dropdown", "value"),
     Input("modal-parada", "is_open"),
     Input("modal-producao", "is_open"),
     Input("production-table", "selected_rows")],
    [State("production-table", "data")]
)
def update_status_and_meta(categoria_id, modal_parada_is_open, modal_producao_is_open, selected_rows, table_data):
    if not selected_rows or not table_data:
        return "", "", "", {}
    
    selected_row = table_data[selected_rows[0]]
    producao_id = selected_row.get("pr_id")
    maquina_nome = selected_row.get("maquina_nome")
    pr_fechado = selected_row.get("pr_fechado")
    
    # Buscar a meta da categoria selecionada
    banco = Banco()

    meta = "-"
    if categoria_id:
        query_meta = """
            SELECT cp_meta FROM categoria_produto cp
            JOIN maquina m ON cp.c_maq_id = m.maquina_id
            WHERE cp.cp_id = :categoria_id AND m.maquina_nome = :maquina_nome
        """
        with banco.engine.connect() as conn:
            result = conn.execute(text(query_meta), {"categoria_id": categoria_id, "maquina_nome": maquina_nome}).fetchone()
            if result:
                meta = result[0]
    
    if pr_fechado == 1:
        return meta, "FABRICA FECHADA", "-", {"color": "white", "backgroundColor": "green", "fontWeight": "bold"}
        
    if not categoria_id:
        return "", "Selecione Categoria", "", {}

    # Aqui você pode adicionar a lógica para calcular o status
    query_apontamentos = """
        SELECT SUM(ap_tempo) as total_tempo
        FROM apontamento
        WHERE ap_pr = :producao_id
    """
    with banco.engine.connect() as conn:
        result_apontamentos = conn.execute(text(query_apontamentos), {"producao_id": producao_id}).fetchone()
        total_tempo = result_apontamentos[0] if result_apontamentos and result_apontamentos[0] else 0
    
    # Buscar a soma de atp_qtd da tabela apontamento_producao
    query_producao = """
        SELECT SUM(atp_qtd) as total_producao
        FROM apontamento_produto
        WHERE atp_producao = :producao_id
    """
    with banco.engine.connect() as conn:
        result_producao = conn.execute(text(query_producao), {"producao_id": producao_id}).fetchone()
        total_producao = result_producao[0] if result_producao and result_producao[0] else 0
    
    apontamentos_faltantes = int(60 - (total_producao / (meta / 60)) - total_tempo)
    
    # Aqui você pode adicionar a lógica para calcular o status
    if apontamentos_faltantes > 0:
        status = "FALTANDO"
        status_color = "orange"
    elif apontamentos_faltantes == 0:
        status = "OK"
        status_color = "green"
    else:
        status = "ERRADO"
        status_color = "red"
    
    return meta, status, apontamentos_faltantes, {"color": "white", "backgroundColor": status_color, "fontWeight": "bold"}

# Callback para salvar a categoria selecionada na tabela producao
@app.callback(
    Output("modal-categoria-dropdown", "value", allow_duplicate=True),
    [Input("modal-categoria-dropdown", "value")],
    [State("production-table", "selected_rows"),
     State("production-table", "data")],
    prevent_initial_call=True
)
def salvar_categoria_producao(categoria_id, selected_rows, table_data):
    if not categoria_id or not selected_rows or not table_data:
        return dash.no_update
    selected_row = table_data[selected_rows[0]]
    producao_id = selected_row.get("pr_id")
    if not producao_id:
        return dash.no_update
    banco = Banco()
    try:
        with banco.engine.connect() as conn:
            conn.execute(text("UPDATE producao SET pr_categoria_produto_id = :categoria_id WHERE pr_id = :producao_id"), {"categoria_id": categoria_id, "producao_id": producao_id})
            conn.commit()
        return categoria_id
    except Exception as e:
        print(f"Erro ao salvar categoria na producao: {e}")
        return dash.no_update

# Callback para abrir/fechar o modal de parada
@app.callback(
    Output("modal-parada", "is_open"),
    [Input("btn-add-parada", "n_clicks"),
     Input("btn-salvar-parada", "n_clicks"),
     Input("btn-excluir-parada", "n_clicks"),
     Input("apontamentos-table", "selected_rows")],
    [State("modal-parada", "is_open")]
)
def toggle_modal_parada(n_add, n_save, n_exc, selected_rows, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id in ["btn-salvar-parada", "btn-excluir-parada"]:
        return False
    elif button_id == "btn-add-parada" or selected_rows:
        return True
    elif button_id in ["btn-salvar-parada", "btn-excluir-parada"]:
        return False
    return is_open

@app.callback(
    Output("modal-producao", "is_open", allow_duplicate=True),
    [Input("btn-add-producao", "n_clicks"),
     Input("btn-salvar-producao", "n_clicks"),
     Input("btn-excluir-producao", "n_clicks"),
     Input("btn-cancelar-producao", "n_clicks"),
     Input("apontamentos-producao-table", "selected_rows")],
    [State("modal-producao", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_producao(n_add, n_save, n_exc, n_cancel, selected_rows, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id in ["btn-excluir-producao", "btn-cancelar-producao"]:
        return False
    elif button_id == "btn-add-producao" or selected_rows:
        return True
    return is_open

# Callback para mostrar/esconder o formulário de parada
@app.callback(
    Output("form-parada-container", "style"),
    [Input("btn-add-parada", "n_clicks")],
    [State("form-parada-container", "style")]
)
def toggle_form_parada(n_clicks, current_style):
    if not n_clicks:
        return {"display": "none", "marginBottom": "20px"}
    
    ctx = callback_context
    if not ctx.triggered:
        return {"display": "none", "marginBottom": "20px"}
    
    if current_style and current_style.get("display") == "block":
        return {"display": "none", "marginBottom": "20px"}
    return {"display": "block", "marginBottom": "20px"}

# Callback para salvar os dados do formulário de parada no banco de dados
@app.callback(
    Output("apontamentos-table", "data", allow_duplicate=True),
    [Input("btn-salvar-parada", "n_clicks")],
    [State("parada-tempo", "value"),
     State("parada-nivel1", "value"),
     State("parada-nivel2", "value"),
     State("parada-nivel3", "value"),
     State("parada-nivel4", "value"),
     State("parada-nivel5", "value"),
     State("parada-nivel6", "value"),
     State("production-table", "selected_rows"),
     State("production-table", "data")],
    prevent_initial_call=True
)
def save_parada(n_clicks, tempo, nivel1, nivel2, nivel3, nivel4, nivel5, nivel6, selected_rows, table_data):
    if not n_clicks or not tempo or not nivel1 or not selected_rows or not table_data:
        return dash.no_update
    
    # Pegar o ID da produção selecionada
    selected_row = table_data[selected_rows[0]]
    producao_id = selected_row.get("pr_id")
    
    # Inserir a parada no banco
    banco = Banco()
    try:
        banco.inserir_dados(
            "apontamento",
            ap_tempo=tempo,
            ap_pr=producao_id,
            ap_lv1=nivel1,
            ap_lv2=nivel2 if nivel2 else None,
            ap_lv3=nivel3 if nivel3 else None,
            ap_lv4=nivel4 if nivel4 else None,
            ap_lv5=nivel5 if nivel5 else None,
            ap_lv6=nivel6 if nivel6 else None
        )
        
        # Buscar os dados atualizados
        query = """
            SELECT 
                a.ap_id,
                a.ap_pr,
                a.ap_tempo,
                a.ap_lv1,
                r1.ra_razao as nivel1_nome,
                a.ap_lv2,
                r2.ra_razao as nivel2_nome,
                a.ap_lv3,
                r3.ra_razao as nivel3_nome,
                a.ap_lv4,
                r4.ra_razao as nivel4_nome,
                a.ap_lv5,
                r5.ra_razao as nivel5_nome,
                a.ap_lv6,
                r6.ra_razao as nivel6_nome
            FROM apontamento a
            LEFT JOIN razao r1 ON a.ap_lv1 = r1.ra_id
            LEFT JOIN razao r2 ON a.ap_lv2 = r2.ra_id
            LEFT JOIN razao r3 ON a.ap_lv3 = r3.ra_id
            LEFT JOIN razao r4 ON a.ap_lv4 = r4.ra_id
            LEFT JOIN razao r5 ON a.ap_lv5 = r5.ra_id
            LEFT JOIN razao r6 ON a.ap_lv6 = r6.ra_id
            WHERE a.ap_pr = :pr_id
            ORDER BY a.ap_id
        """
        
        with banco.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={"pr_id": producao_id})
            updated_data = df.to_dict('records')
            
        return updated_data
        
    except Exception as e:
        print(f"Erro ao salvar parada: {e}")
        return dash.no_update

# Callback para excluir o apontamento
@app.callback(
    Output("apontamentos-table", "data", allow_duplicate=True),
    [Input("btn-excluir-parada", "n_clicks")],
    [State("apontamentos-table", "selected_rows"),
     State("apontamentos-table", "data")],
    prevent_initial_call=True
)
def excluir_parada(n_clicks, selected_rows, table_data):
    if not n_clicks or not selected_rows or not table_data:
        return dash.no_update
    
    # Pegar o ID do apontamento selecionado
    selected_row = table_data[selected_rows[0]]
    apontamento_id = selected_row.get("ap_id")
    producao_id = selected_row.get("ap_pr")
    
    if not apontamento_id or not producao_id:
        return dash.no_update
    
    # Excluir o apontamento do banco
    banco = Banco()
    try:
        with banco.engine.connect() as conn:
            # Excluir o apontamento
            conn.execute(text("DELETE FROM apontamento WHERE ap_id = :ap_id"), {"ap_id": apontamento_id})
            conn.commit()
            
            # Buscar os dados atualizados
            query = """
                SELECT 
                    a.ap_id,
                    a.ap_pr,
                    a.ap_tempo,
                    a.ap_lv1,
                    r1.ra_razao as nivel1_nome,
                    a.ap_lv2,
                    r2.ra_razao as nivel2_nome,
                    a.ap_lv3,
                    r3.ra_razao as nivel3_nome,
                    a.ap_lv4,
                    r4.ra_razao as nivel4_nome,
                    a.ap_lv5,
                    r5.ra_razao as nivel5_nome,
                    a.ap_lv6,
                    r6.ra_razao as nivel6_nome
                FROM apontamento a
                LEFT JOIN razao r1 ON a.ap_lv1 = r1.ra_id
                LEFT JOIN razao r2 ON a.ap_lv2 = r2.ra_id
                LEFT JOIN razao r3 ON a.ap_lv3 = r3.ra_id
                LEFT JOIN razao r4 ON a.ap_lv4 = r4.ra_id
                LEFT JOIN razao r5 ON a.ap_lv5 = r5.ra_id
                LEFT JOIN razao r6 ON a.ap_lv6 = r6.ra_id
                WHERE a.ap_pr = :pr_id
                ORDER BY a.ap_id
            """
            
            df = pd.read_sql(text(query), conn, params={"pr_id": producao_id})
            return df.to_dict('records')
            
    except Exception as e:
        print(f"Erro ao excluir parada: {e}")
        return dash.no_update

# Callback para limpar a seleção da tabela
@app.callback(
    Output("apontamentos-table", "selected_rows"),
    Input("btn-clear-selection", "n_clicks"),
    prevent_initial_call=True
)
def clear_selection(n_clicks):
    if n_clicks:
        return []
    return dash.no_update

# Callback to update pr_fechado in the database
@app.callback(
    Output("production-table", "data", allow_duplicate=True),
    Input("modal-fechado-checkbox", "value"),
    [State("production-table", "selected_rows"),
     State("production-table", "data")],
    prevent_initial_call=True
)
def update_pr_fechado(checked, selected_rows, table_data):
    if checked is None or not selected_rows or not table_data:
        return dash.no_update

    selected_row_index = selected_rows[0]
    selected_row = table_data[selected_row_index]
    producao_id = selected_row.get("pr_id")

    if not producao_id:
        return dash.no_update

    banco = Banco()
    fechado_value = 1 if checked else 0
    
    try:
        with banco.engine.connect() as conn:
            conn.execute(text("UPDATE producao SET pr_fechado = :fechado WHERE pr_id = :producao_id"), 
                         {"fechado": fechado_value, "producao_id": producao_id})
            conn.commit()
        
        # Update the table data in the frontend
        table_data[selected_row_index]['pr_fechado'] = fechado_value
        return table_data
    except Exception as e:
        print(f"Erro ao salvar o status de fechado: {e}")
        return dash.no_update


