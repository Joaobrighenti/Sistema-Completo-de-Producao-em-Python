from dash import html, dcc, Input, Output, State, callback_context
import dash
import dash_bootstrap_components as dbc
from app import app
from datetime import datetime
import pandas as pd
from banco_dados.banco import Banco
from sqlalchemy import text
import time

def create_form_producao():
    return dbc.Form([
        html.Div(id="producao-alert-message"),
        dbc.Row([
            dbc.Col([
                html.Label("PCP:"),
                dcc.Dropdown(
                    id="producao-pcp-dropdown",
                    placeholder="Selecione o PCP",
                    style={"width": "100%"}
                )
            ], width=12)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Quantidade:"),
                dbc.Input(
                    type="number",
                    id="producao-quantidade",
                    placeholder="Digite a quantidade produzida",
                    min=0
                )
            ], width=6),
            dbc.Col([
                html.Label("Refugo:"),
                dbc.Input(
                    type="number",
                    id="producao-refugo",
                    placeholder="Digite a quantidade de refugo",
                    min=0,
                    value=0
                )
            ], width=6)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Data:"),
                dcc.DatePickerSingle(
                    id='producao-data',
                    date=datetime.now().date(),
                    display_format='DD/MM/YYYY'
                )
            ], width=6)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Observação:"),
                dbc.Input(
                    type="text",
                    id="producao-obs",
                    placeholder="Digite uma observação"
                )
            ], width=6),
            dbc.Col([
                html.Label("Custo (R$):"),
                dbc.Input(
                    type="number",
                    id="producao-custo",
                    placeholder="Digite o custo",
                    min=0
                )
            ], width=6)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                html.Label("Plano:"),
                dcc.Dropdown(
                    id="producao-plano",
                    options=[
                        {"label": "Tampa", "value": 0},
                        {"label": "Fundo", "value": 1},
                        {"label": "Berço/Envelope", "value": 2},
                        {"label": "Lâmina", "value": 3}
                    ],
                    placeholder="Selecione o plano"
                )
            ], width=6),
            dbc.Col([
                html.Label("Repetições:"),
                dbc.Input(
                    type="number",
                    id="producao-repeticoes",
                    placeholder="Digite as repetições"
                )
            ], width=6)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Button("Salvar", id="btn-salvar-producao", color="success", className="me-2"),
                dbc.Button("Excluir", id="btn-excluir-producao", color="danger", className="me-2"),
                dbc.Button("Cancelar", id="btn-cancelar-producao", color="secondary")
            ])
        ])
    ])

# Callback para carregar as opções do dropdown de PCP
@app.callback(
    Output("producao-pcp-dropdown", "options"),
    [Input("modal-producao", "is_open")]
)
def carregar_opcoes_pcp(is_open):
    if not is_open:
        return []
    
    banco = Banco()
    try:
        with banco.engine.connect() as conn:
            query = """
                SELECT 
                    p.pcp_pcp,
                    p.pcp_id,
                    pr.nome as produto_nome,
                    p.pcp_qtd
                FROM pcp p
                JOIN produtos pr ON p.pcp_produto_id = pr.produto_id
                ORDER BY p.pcp_pcp DESC
            """
            df = pd.read_sql(text(query), conn)
            
            options = [
                {
                    "label": f"PCP: {row['pcp_pcp']} | {row['produto_nome']} | Qtd: {row['pcp_qtd']}",
                    "value": row['pcp_id']
                }
                for _, row in df.iterrows()
            ]
            
            return options
    except Exception as e:
        print(f"Erro ao carregar PCPs: {e}")
        return []

# Callback para salvar a produção
@app.callback(
    [Output("apontamentos-producao-table", "data", allow_duplicate=True),
     Output("modal-producao", "is_open", allow_duplicate=True),
     Output("producao-alert-message", "children", allow_duplicate=True)],
    [Input("btn-salvar-producao", "n_clicks")],
    [State("producao-pcp-dropdown", "value"),
     State("producao-quantidade", "value"),
     State("producao-data", "date"),
     State("producao-refugo", "value"),
     State("producao-obs", "value"),
     State("producao-custo", "value"),
     State("producao-plano", "value"),
     State("producao-repeticoes", "value"),
     State("production-table", "selected_rows"),
     State("production-table", "data")],
    prevent_initial_call=True
)
def salvar_producao(n_clicks, pcp_id, quantidade, data, refugo, obs, custo, plano, repeticoes, selected_rows, table_data):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update

    # Validar campos obrigatórios
    if not all([pcp_id, quantidade is not None, data, plano is not None, repeticoes is not None]):
        return dash.no_update, True, dbc.Alert("Preencha todos os campos obrigatórios (PCP, Quantidade, Data, Plano, Repetições).", color="danger", dismissable=True)

    if not selected_rows or not table_data:
        return dash.no_update, True, dbc.Alert("Por favor, selecione uma produção na tabela principal.", color="danger", dismissable=True)
    
    # Pegar o ID da produção selecionada
    selected_row = table_data[selected_rows[0]]
    producao_id = selected_row.get("pr_id")
    
    # Converter a data para o formato correto
    try:
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        print(f"Erro ao converter data: {data}")
        return dash.no_update, True, dbc.Alert("Formato de data inválido.", color="danger", dismissable=True)
    
    # Inserir a produção no banco
    banco = Banco()
    try:
        banco.inserir_dados(
            "apontamento_produto",
            atp_producao=producao_id,
            atp_pcp=pcp_id,
            atp_qtd=quantidade,
            atp_data=data_obj,
            atp_refugos=refugo if refugo else 0,
            atp_obs=obs,
            atp_custo=custo,
            atp_plano=plano,
            atp_repeticoes=repeticoes
        )
        
        # Buscar os dados atualizados
        query = """
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
                    ELSE ''
                END as atp_plano,
                ap.atp_repeticoes
            FROM apontamento_produto ap
            JOIN pcp ON ap.atp_pcp = pcp.pcp_id
            JOIN produtos prod ON pcp.pcp_produto_id = prod.produto_id
            WHERE atp_producao = :pr_id
            ORDER BY atp_id
        """
        
        with banco.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={"pr_id": producao_id})
            return df.to_dict('records'), False, None
            
    except Exception as e:
        print(f"Erro ao salvar produção: {e}")
        return dash.no_update, True, dbc.Alert(f"Erro ao salvar: {e}", color="danger", dismissable=True)

# Callback para excluir um apontamento
@app.callback(
    [Output("apontamentos-producao-table", "data"),
     Output("modal-producao", "is_open", allow_duplicate=True)],
    [Input("btn-excluir-producao", "n_clicks")],
    [State("apontamentos-producao-table", "selected_rows"),
     State("apontamentos-producao-table", "data"),
     State("production-table", "selected_rows"),
     State("production-table", "data")],
    prevent_initial_call=True
)
def excluir_apontamento(n_clicks, selected_rows, table_data, prod_selected_rows, prod_table_data):
    if not n_clicks or not selected_rows or not table_data or not prod_selected_rows or not prod_table_data:
        return dash.no_update, dash.no_update
    
    selected_row = table_data[selected_rows[0]]
    producao_row = prod_table_data[prod_selected_rows[0]]
    producao_id = producao_row.get("pr_id")
    
    try:
        atp_id = selected_row["atp_id"]
    except KeyError:
        print("Erro: atp_id não encontrado nos dados da linha")
        
        return dash.no_update, dash.no_update
    
    banco = Banco()
    try:
        with banco.engine.connect() as conn:
            # Excluindo apenas o registro específico usando atp_id
            query = """
                DELETE FROM apontamento_produto 
                WHERE atp_id = :atp_id
            """
            conn.execute(text(query), {"atp_id": atp_id})
            conn.commit()
            
            # Atualizando a tabela após a exclusão
            query = """
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
                        ELSE ''
                    END as atp_plano,
                    ap.atp_repeticoes
                FROM apontamento_produto ap
                JOIN pcp ON ap.atp_pcp = pcp.pcp_id
                JOIN produtos prod ON pcp.pcp_produto_id = prod.produto_id
                WHERE atp_producao = :pr_id
                ORDER BY atp_data DESC, atp_id DESC
            """
            df = pd.read_sql(text(query), conn, params={"pr_id": producao_id})
            return df.to_dict("records"), False
    except Exception as e:
        print(f"Erro ao excluir apontamento: {e}")
        return dash.no_update, dash.no_update

# Callback para limpar a seleção da tabela de produção
@app.callback(
    Output("apontamentos-producao-table", "selected_rows"),
    Input("btn-clear-selection-producao", "n_clicks"),
    prevent_initial_call=True
)
def clear_selection_producao(n_clicks):
    if n_clicks:
        return []
    return dash.no_update

# Callback para preencher o formulário quando uma linha é selecionada
@app.callback(
    [Output("producao-pcp-dropdown", "value"),
     Output("producao-quantidade", "value"),
     Output("producao-data", "date"),
     Output("producao-refugo", "value"),
     Output("producao-obs", "value"),
     Output("producao-custo", "value"),
     Output("producao-plano", "value"),
     Output("producao-repeticoes", "value")],
    [Input("apontamentos-producao-table", "selected_rows")],
    [State("apontamentos-producao-table", "data")]
)
def preencher_form_producao(selected_rows, table_data):
    # Adiciona um delay de 1 segundo
    time.sleep(1)
    
    if not selected_rows or not table_data:
        return None, None, datetime.now().date(), 0, None, None, None, None
    
    selected_row = table_data[selected_rows[0]]
    
    
    try:
        
        data = datetime.strptime(selected_row.get("atp_data"), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        data = datetime.now().date()
        
    return (
        selected_row.get("atp_pcp"),
        selected_row.get("atp_qtd"),
        data,
        selected_row.get("atp_refugos"),
        selected_row.get("atp_obs"),
        selected_row.get("atp_custo"),
        selected_row.get("atp_plano"),
        selected_row.get("atp_repeticoes")
    )
