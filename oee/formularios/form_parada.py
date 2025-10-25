from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from app import app
from datetime import datetime
from banco_dados.banco import Banco
import pandas as pd
from sqlalchemy import text
import dash

def create_form_parada():
    return html.Div([
        # Campo oculto para armazenar o setor_id
        dcc.Store(id='parada-setor-id'),
        
        dbc.Form([
            dbc.Row([
                dbc.Col([
                    html.Label("Tempo (minutos):"),
                    dbc.Input(
                        type="number",
                        id="parada-tempo",
                        placeholder="Digite o tempo em minutos",
                        min=1
                    )
                ], width=6)
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Nível 1:"),
                    dbc.Select(
                        id="parada-nivel1",
                        options=[],  # Será preenchido via callback
                        placeholder="Selecione o nível 1"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Nível 2:"),
                    dbc.Select(
                        id="parada-nivel2",
                        options=[],
                        placeholder="Selecione o nível 2",
                        disabled=True
                    )
                ], width=6)
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Nível 3:"),
                    dbc.Select(
                        id="parada-nivel3",
                        options=[],
                        placeholder="Selecione o nível 3",
                        disabled=True
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Nível 4:"),
                    dbc.Select(
                        id="parada-nivel4",
                        options=[],
                        placeholder="Selecione o nível 4",
                        disabled=True
                    )
                ], width=6)
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    html.Label("Nível 5:"),
                    dbc.Select(
                        id="parada-nivel5",
                        options=[],
                        placeholder="Selecione o nível 5",
                        disabled=True
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Nível 6:"),
                    dbc.Select(
                        id="parada-nivel6",
                        options=[],
                        placeholder="Selecione o nível 6",
                        disabled=True
                    )
                ], width=6)
            ], className="mb-3"),
        ]),

        dbc.ModalFooter([
            dbc.Button("Salvar", id="btn-salvar-parada", color="success", className="me-2"),
            dbc.Button("Excluir", id="btn-excluir-parada", color="danger", className="me-2"),
        ])
    ])

# Callback para inicializar o setor_id e carregar as opções de nível 1
@app.callback(
    [Output("parada-setor-id", "data"),
     Output("parada-nivel1", "options")],
    [Input("modal-parada", "is_open")],
    [State("production-table", "selected_rows"),
    #  Input("btn-excluir-parada", "n_clicks"),
    #  Input("btn-salvar-parada", "n_clicks"),
     State("production-table", "data")]
)
def initialize_parada_form(is_open, selected_rows, table_data):
    
    if not is_open or not selected_rows or not table_data:
        
        return None, []
    
    # Pegar o nome da máquina da linha selecionada
    selected_row = table_data[selected_rows[0]]
    maquina_nome = selected_row.get("maquina_nome")
    
    
    if not maquina_nome:
        print("Nome da máquina não encontrado na linha selecionada")
        return None, []
    
    # Primeiro buscar o setor_id através da máquina
    banco = Banco()
    query_setor = """
        SELECT setor_id, maquina_nome
        FROM maquina
        WHERE maquina_nome = :maquina_nome
    """
    
    with banco.engine.connect() as conn:
        # Buscar o setor_id
        df_setor = pd.read_sql(text(query_setor), conn, params={"maquina_nome": maquina_nome})

        
        if df_setor.empty:
            print("Nenhuma máquina encontrada!")
            return None, []
        
        setor_id = int(df_setor.iloc[0]['setor_id'])
       
        
        # Agora buscar as razões de nível 1 para este setor
        query_razoes = """
            SELECT ra_id, ra_razao
            FROM razao
            WHERE setor_id = :setor_id
            AND ra_level = 1
            ORDER BY ra_razao
        """
        
        df_razoes = pd.read_sql(text(query_razoes), conn, params={"setor_id": setor_id})
   
    options = [{"label": row["ra_razao"], "value": row["ra_id"]} for _, row in df_razoes.iterrows()]
   
    return setor_id, options

# Callback para atualizar os níveis subsequentes
@app.callback(
    [Output(f"parada-nivel{i}", "options") for i in range(2, 7)] +
    [Output(f"parada-nivel{i}", "disabled") for i in range(2, 7)],
    [Input("parada-nivel1", "value")] +
    [Input(f"parada-nivel{i}", "value") for i in range(2, 6)],
    [State("parada-setor-id", "data")]
)
def update_nivel_options(nivel1_value, *args):
    nivel_values = list(args[:4])  # Valores dos níveis 2-5
    setor_id = args[-1]  # Último argumento é o setor_id
    
    if not nivel1_value or not setor_id:
        return [[], [], [], [], []] + [True] * 5
    
    outputs = []
    disabled = []
    last_selected = nivel1_value
    
    banco = Banco()
    
    # Para cada nível subsequente
    for i in range(5):  # níveis 2-6
        if not last_selected:
            outputs.append([])
            disabled.append(True)
            continue
            
        query = """
            SELECT ra_id, ra_razao
            FROM razao
            WHERE setor_id = :setor_id
            AND ra_sub = :ra_sub
            ORDER BY ra_razao
        """
        
        with banco.engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params={
                "setor_id": setor_id,
                "ra_sub": str(last_selected)
            })
        
        options = [{"label": row["ra_razao"], "value": row["ra_id"]} for _, row in df.iterrows()]
        outputs.append(options)
        disabled.append(len(options) == 0)
        
        # Atualizar last_selected para o próximo nível
        if i < 4:  # Não precisamos do último valor
            last_selected = nivel_values[i]
    
    return outputs + disabled

# Callback para preencher os campos quando uma linha é selecionada na tabela de apontamentos ou limpar quando o botão de adicionar parada é clicado
@app.callback(
    [Output("parada-tempo", "value"),
     Output("parada-nivel1", "value"),
     Output("parada-nivel2", "value"),
     Output("parada-nivel3", "value"),
     Output("parada-nivel4", "value"),
     Output("parada-nivel5", "value"),
     Output("parada-nivel6", "value")],
    [Input("apontamentos-table", "selected_rows"),
     Input("btn-add-parada", "n_clicks")],
    [State("apontamentos-table", "data")],
    prevent_initial_call=True
)
def fill_or_clear_parada_form(selected_rows, n_clicks_add, table_data):
    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    # Check which input triggered the callback
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if triggered_id == "btn-add-parada":
        # Clear the form fields
        return None, None, None, None, None, None, None
    
    if not selected_rows or not table_data:
        return None, None, None, None, None, None, None
    
    # Fill the form fields with the selected row data
    selected_row = table_data[selected_rows[0]]
    
    return (
        selected_row.get("ap_tempo"),
        selected_row.get("ap_lv1"),
        selected_row.get("ap_lv2"),
        selected_row.get("ap_lv3"),
        selected_row.get("ap_lv4"),
        selected_row.get("ap_lv5"),
        selected_row.get("ap_lv6")
    )
