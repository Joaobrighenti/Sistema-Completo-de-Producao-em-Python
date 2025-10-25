from dash import html, dcc, Input, Output, dash_table
import dash_bootstrap_components as dbc
from datetime import date
from app import app
import pandas as pd
from banco_dados.banco import Banco
from sqlalchemy import text
from oee.formularios.form_apontamento import create_modal
import dash

layout = dbc.Container([
    # Filter Card
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Setor:"),
                            dcc.Dropdown(
                                id="dropdown-setor-filter",
                                placeholder="Selecione um setor",
                                className="mb-3",
                                clearable=False
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Máquina:"),
                            dcc.Dropdown(
                                id="dropdown-maquina-filter",
                                placeholder="Selecione uma máquina",
                                className="mb-3",
                                clearable=False
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Data:"),
                            dcc.DatePickerSingle(
                                id='date-picker-filter',
                                date=date.today(),
                                display_format='DD/MM/YYYY',
                                className="mb-3"
                            )
                        ], width=4)
                    ])
                ])
            ], className="mb-4")
        ])
    ], className="mt-4"),

    # Production Table
    dbc.Row([
        dbc.Col([
            dash_table.DataTable(
                id='production-table',
                columns=[
                    {"name": "ID", "id": "pr_id"},
                    {"name": "Data", "id": "pr_data"},
                    {"name": "Início", "id": "pr_inicio"},
                    {"name": "Término", "id": "pr_termino"},
                    {"name": "Setor", "id": "setor_nome"},
                    {"name": "Máquina", "id": "maquina_nome"},
                    {"name": "Categoria", "id": "categoria_nome"},
                    {"name": "Status", "id": "status"},
                    {"name": "Meta", "id": "meta"},
                    {"name": "Produção Total", "id": "producao_total"},
                    {"name": "Soma Paradas", "id": "soma_paradas"},
                    {"name": "Status do Apontamento", "id": "status_apontamento"}
                ],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'textAlign': 'left',
                    'padding': '10px',
                    'minWidth': '100px'
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                style_data_conditional=[
                    {
                        'if': {'state': 'selected'},
                        'backgroundColor': 'rgba(0, 116, 217, 0.3)',
                        'border': '1px solid blue'
                    },
                    {
                        'if': {
                            'filter_query': '{status_apontamento} = "FABRICA FECHADA"',
                            'column_id': 'status_apontamento'
                        },
                        'backgroundColor': 'green',
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{status_apontamento} = "FALTANDO"',
                            'column_id': 'status_apontamento'
                        },
                        'backgroundColor': 'orange',
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{status_apontamento} = "OK"',
                            'column_id': 'status_apontamento'
                        },
                        'backgroundColor': 'green',
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{status_apontamento} = "ERRADO"',
                            'column_id': 'status_apontamento'
                        },
                        'backgroundColor': 'red',
                        'color': 'white',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{status_apontamento} = "SEM APONTAMENTO"',
                            'column_id': 'status_apontamento'
                        },
                        'backgroundColor': 'gray',
                        'color': 'white',
                        'fontWeight': 'bold'
                    }
                ],
                page_size=24,
                row_selectable='single',  # Permite selecionar uma linha por vez
                selected_rows=[],  # Inicialmente nenhuma linha selecionada
                tooltip_data=[{ 'meta': ''} for _ in range(24)],
                tooltip_duration=None
            )
        ])
    ]),
    
    # Modal para detalhes do apontamento
    create_modal()
], fluid=True)

# Callback to populate sectors
@app.callback(
    [Output("dropdown-setor-filter", "options"),
     Output("dropdown-setor-filter", "value")],
    Input("dropdown-setor-filter", "id")
)
def load_sectors(trigger):
    from banco_dados.banco import Banco
    banco = Banco()
    df_setores = banco.ler_tabela("setor")
    
    if df_setores.empty:
        return [], None
    
    setores = [
        {"label": row["setor_nome"], "value": row["setor_id"]} 
        for _, row in df_setores.iterrows()
    ]
    return setores, setores[0]["value"] if setores else None

# Callback to populate machines based on selected sector
@app.callback(
    [Output("dropdown-maquina-filter", "options"),
     Output("dropdown-maquina-filter", "value")],
    Input("dropdown-setor-filter", "value")
)
def load_machines(setor_id):
    if not setor_id:
        return [], None
        
    from banco_dados.banco import Banco
    banco = Banco()
    df_maquinas = banco.ler_tabela("maquina")
    
    if df_maquinas.empty:
        return [], None
        
    maquinas = [
        {"label": row["maquina_nome"], "value": row["maquina_id"]} 
        for _, row in df_maquinas.query(f"setor_id == {setor_id}").iterrows()
    ]
    return maquinas, maquinas[0]["value"] if maquinas else None

# Callback to update production table based on filters
@app.callback(
    [Output('production-table', 'data'),
     Output('production-table', 'tooltip_data')],
    [Input('dropdown-setor-filter', 'value'),
     Input('dropdown-maquina-filter', 'value'),
     Input('date-picker-filter', 'date')]
)
def update_production_table(setor_id, maquina_id, selected_date):
    if not setor_id or not maquina_id:
        return [], []
        
    banco = Banco()
    
    # Base query
    query = """
    WITH apontamentos_producao AS (
        SELECT 
            atp_producao as pr_id,
            CAST(SUM(atp_qtd) AS INTEGER) as total_producao,
            GROUP_CONCAT(
                '| ' || IFNULL(ap.atp_id, '') || ' | ' ||
                IFNULL(ap.atp_pcp, '') || ' | ' ||
                IFNULL(prod.nome, '') || ' | ' ||
                IFNULL(ap.atp_qtd, '') || ' | ' ||
                IFNULL(CASE ap.atp_plano WHEN 0 THEN 'Tampa' WHEN 1 THEN 'Fundo' WHEN 2 THEN 'Berço/Envelope' WHEN 3 THEN 'Lâmina' ELSE '' END, '') || ' | ' ||
                IFNULL(ap.atp_repeticoes, '') || ' | ' ||
                IFNULL(ap.atp_data, '') || ' | ' ||
                IFNULL(ap.atp_refugos, '') || ' | ' ||
                IFNULL(ap.atp_obs, '') || ' | ' ||
                IFNULL(ap.atp_custo, '') || ' |',
                '&&&'
            ) as producao_details
        FROM apontamento_produto ap
        LEFT JOIN pcp ON ap.atp_pcp = pcp.pcp_id
        LEFT JOIN produtos prod ON pcp.pcp_produto_id = prod.produto_id
        GROUP BY ap.atp_producao
    ),
    apontamentos_parada AS (
        SELECT 
            ap_pr as pr_id,
            CAST(SUM(ap_tempo) AS INTEGER) as total_tempo,
            GROUP_CONCAT(
                '| ' || IFNULL(a.ap_tempo, '') || ' | ' ||
                IFNULL(r1.ra_razao, '') || ' | ' ||
                IFNULL(r2.ra_razao, '') || ' | ' ||
                IFNULL(r3.ra_razao, '') || ' | ' ||
                IFNULL(r4.ra_razao, '') || ' | ' ||
                IFNULL(r5.ra_razao, '') || ' | ' ||
                IFNULL(r6.ra_razao, '') || ' |',
                '&&&'
            ) as parada_details
        FROM apontamento a
        LEFT JOIN razao r1 ON a.ap_lv1 = r1.ra_id
        LEFT JOIN razao r2 ON a.ap_lv2 = r2.ra_id
        LEFT JOIN razao r3 ON a.ap_lv3 = r3.ra_id
        LEFT JOIN razao r4 ON a.ap_lv4 = r4.ra_id
        LEFT JOIN razao r5 ON a.ap_lv5 = r5.ra_id
        LEFT JOIN razao r6 ON a.ap_lv6 = r6.ra_id
        GROUP BY a.ap_pr
    )
    SELECT 
        p.pr_id,
        p.pr_data,
        p.pr_inicio,
        p.pr_termino,
        s.setor_nome,
        m.maquina_nome,
        cp.cp_nome as categoria_nome,
        p.pr_categoria_produto_id as pr_categoria_produto_id,
        p.pr_fechado,
        CASE 
            WHEN p.pr_termino IS NOT NULL THEN 'Finalizado'
            ELSE 'Em Andamento'
        END as status,
        CAST(COALESCE(cp.cp_meta, 0) AS INTEGER) as meta,
        COALESCE(ap.total_producao, 0) as producao_total,
        COALESCE(apt.total_tempo, 0) as soma_paradas,
        CASE 
            WHEN p.pr_fechado = 1 THEN 'FABRICA FECHADA'
            WHEN ap.total_producao IS NOT NULL THEN
                CASE 
                    WHEN CAST(60 - (CAST(ap.total_producao AS FLOAT) / (NULLIF(CAST(cp.cp_meta AS FLOAT), 0) / 60)) - CAST(apt.total_tempo AS FLOAT) AS INTEGER) > 0 THEN 'FALTANDO'
                    WHEN CAST(60 - (CAST(ap.total_producao AS FLOAT) / (NULLIF(CAST(cp.cp_meta AS FLOAT), 0) / 60)) - CAST(apt.total_tempo AS FLOAT) AS INTEGER) = 0 THEN 'OK'
                    ELSE 'ERRADO'
                END
            ELSE 'SEM APONTAMENTO'
        END as status_apontamento,
        ap.producao_details,
        apt.parada_details
    FROM producao p
    LEFT JOIN setor s ON p.pr_setor_id = s.setor_id
    LEFT JOIN maquina m ON p.pr_maquina_id = m.maquina_id
    LEFT JOIN categoria_produto cp ON p.pr_categoria_produto_id = cp.cp_id
    LEFT JOIN apontamentos_producao ap ON p.pr_id = ap.pr_id
    LEFT JOIN apontamentos_parada apt ON p.pr_id = apt.pr_id
    WHERE 1=1
    """
    
    # Add filters
    params = {}
    if setor_id:
        query += " AND p.pr_setor_id = :setor_id"
        params['setor_id'] = setor_id
    if maquina_id:
        query += " AND p.pr_maquina_id = :maquina_id"
        params['maquina_id'] = maquina_id
    if selected_date:
        query += " AND p.pr_data = :selected_date"
        params['selected_date'] = selected_date
    
    query += " ORDER BY p.pr_data DESC, p.pr_inicio ASC"
    
    # Execute query
    with banco.engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    
    # Format date and time columns
    if not df.empty:
        df['pr_data'] = pd.to_datetime(df['pr_data']).dt.strftime('%d/%m/%Y')
        df['pr_inicio'] = pd.to_datetime(df['pr_inicio'], format='mixed').dt.strftime('%H:%M')
        df['pr_termino'] = pd.to_datetime(df['pr_termino'], format='mixed').dt.strftime('%H:%M')

    tooltip_data = []
    if not df.empty:
        for _, row in df.iterrows():
            # Parada
            parada_header = "| Tempo | Nível 1 | Nível 2 | Nível 3 | Nível 4 | Nível 5 | Nível 6 |\n|:---|:---|:---|:---|:---|:---|:---|\n"
            parada_details_str = row.get('parada_details', '') or ''
            parada_rows = parada_details_str.replace('&&&', '\n')
            parada_table = parada_header + parada_rows if parada_rows else 'Nenhuma parada.'

            # Produção
            producao_header = "| ID | PCP | Produto | Qtd | Plano | Rep | Data | Refugo | Obs | Custo |\n|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|\n"
            producao_details_str = row.get('producao_details', '') or ''
            producao_rows = producao_details_str.replace('&&&', '\n')
            producao_table = producao_header + producao_rows if producao_rows else 'Nenhuma produção.'

            tooltip_value = (
                '**Apontamentos de Parada:**\n' + parada_table +
                '\n\n---\n\n' +
                '**Apontamentos de Produção:**\n' + producao_table
            )
            
            tooltip_data.append({'meta': {'value': tooltip_value, 'type': 'markdown'}})

    return df.to_dict('records'), tooltip_data



@app.callback(
    Output("production-table", "selected_rows"),
    Input("dropdown-setor-filter", "value"),
    Input("dropdown-maquina-filter", "value"),
    Input("date-picker-filter", "date")
    
)
def clear_selection_producao(setor_id, maquina_id, selected_date):
    if setor_id or maquina_id or selected_date:
        return []
    return dash.no_update
