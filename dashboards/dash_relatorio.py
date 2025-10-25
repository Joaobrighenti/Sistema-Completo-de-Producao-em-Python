import dash
from dash import html, dcc, callback
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from sqlalchemy import func, text
from io import StringIO
import io
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
from datetime import date
from collections import defaultdict
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from app import app
from banco_dados.banco import Session, engine, APONTAMENTO_PRODUTO, PRODUCAO, SETOR, PCP, PRODUTO, CLIENTE, Banco, PLANEJAMENTO, listar_pcp
from pcp.planejamento import calcular_totais_categoria, calcular_totais_setor
from dashboards.dashboard_oee_setor import calculate_oee_for_all_machines_in_sector

# Layout
layout = dbc.Container([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                dbc.Col(dcc.Dropdown(id='relatorio-setor-filter', placeholder='Selecione o Setor'),
                        lg=3, sm=12, className="mb-2 mb-lg-0"),
                dbc.Col(dcc.Dropdown(id='relatorio-semana-filter', placeholder='Selecione a Semana'),
                        lg=3, sm=12, className="mb-2 mb-lg-0"),
                        dbc.Col([
                    dbc.Button("Exportar para PDF", id="btn-pdf", color="danger", className="me-1"),
                    dbc.Button("Exportar para Excel", id="btn-excel", color="success"),
                ], lg=6, sm=12, className="text-lg-end"),
            ]),
        ]),
    ], className="mb-4"),
    
    dbc.Row(id='relatorio-cards-container'),

    dcc.Download(id="download-pdf"),
    dcc.Download(id="download-excel"),
    dcc.Store(id='relatorio-data-store'),
    dcc.Store(id='relatorio-tabela-store'), # New store for the table data

], fluid=True)

@app.callback(
    Output('relatorio-setor-filter', 'options'),
    Input('url', 'pathname')
)
def populate_setor_filter(pathname):
    if pathname != '/compras/relatorio': # Update this to the correct path
        raise PreventUpdate
    
    banco = Banco()
    df_setores = banco.ler_tabela('setor')
    
    if df_setores.empty:
        return []
        
    return [{'label': row['setor_nome'], 'value': row['setor_id']} for _, row in df_setores.iterrows()]

@app.callback(
    Output('relatorio-semana-filter', 'options'),
    Input('url', 'pathname')
)
def populate_semana_filter(pathname):
    if pathname != '/compras/relatorio':
        raise PreventUpdate

    banco = Banco()
    df_plan = banco.ler_tabela('planejamento')
    
    if df_plan.empty or 'data_programacao' not in df_plan.columns:
        return []

    df_plan['data_programacao'] = pd.to_datetime(df_plan['data_programacao'], errors='coerce')
    df_plan.dropna(subset=['data_programacao'], inplace=True)

    df_plan['ano'] = df_plan['data_programacao'].dt.isocalendar().year
    df_plan['semana'] = df_plan['data_programacao'].dt.isocalendar().week

    df_plan['ano_semana'] = df_plan['ano'].astype(str) + '-' + df_plan['semana'].astype(str).str.zfill(2)

    semanas = sorted(df_plan['ano_semana'].unique(), reverse=True)
    
    return [{'label': f'Semana {s.split("-")[1]} ({s.split("-")[0]})', 'value': s} for s in semanas]

def parse_plano_setor(json_str):
    if not json_str or pd.isna(json_str):
        return {}
    try:
        if isinstance(json_str, dict):
            return json_str
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return {}

@app.callback(
    Output('relatorio-data-store', 'data'),
    [Input('relatorio-setor-filter', 'value'),
     Input('relatorio-semana-filter', 'value')]
)
def update_relatorio_data(setor_id, semana):
    if not setor_id or not semana:
        raise PreventUpdate

    year, week_num = map(int, semana.split('-'))

    banco = Banco()
    # Adapting logic from pcp/planejamento.py
    df_plan = banco.ler_tabela('planejamento')
    df_pcp_full = listar_pcp()
    df_setores = banco.ler_tabela('setor')
    df_produtos = banco.ler_tabela('produtos')
    df_partes = banco.ler_tabela('partes_produto')

    if df_plan.empty or df_pcp_full.empty:
        return pd.DataFrame().to_json(date_format='iso', orient='split')

    df_merged = pd.merge(df_plan, df_pcp_full, left_on='id_pcp', right_on='pcp_id', how='left')
    df_merged = pd.merge(df_merged, df_produtos[['produto_id', 'pap_id']], left_on='pcp_produto_id', right_on='produto_id', how='left')
    df_merged['pap_id'] = pd.to_numeric(df_merged['pap_id'], errors='coerce').astype('Int64')
    df_partes['pap_id'] = pd.to_numeric(df_partes['pap_id'], errors='coerce').astype('Int64')
    df_merged = pd.merge(df_merged, df_partes[['pap_id', 'pap_parte']], on='pap_id', how='left')

    df_merged['data_programacao'] = pd.to_datetime(df_merged['data_programacao'], errors='coerce')
    df_merged = df_merged.dropna(subset=['data_programacao'])

    # Row expansion logic
    expanded_rows = []
    for _, row in df_merged.iterrows():
        parent_row = row.copy()
        parent_row['is_part'] = False
        expanded_rows.append(parent_row)

        if 'pap_parte' in row and pd.notna(row['pap_parte']) and row['pap_parte']:
            try:
                partes_dict = json.loads(row['pap_parte']) if isinstance(row['pap_parte'], str) else row['pap_parte']
                if isinstance(partes_dict, dict):
                    for parte_nome, multiplicador in partes_dict.items():
                        new_row = row.copy()
                        new_row['is_part'] = True
                        new_row['produto_nome_original'] = new_row['produto_nome']
                        new_row['produto_nome'] = parte_nome
                        new_row['part_multiplier'] = multiplicador
                        expanded_rows.append(new_row)
            except (json.JSONDecodeError, TypeError):
                pass
    
    if not expanded_rows:
        return pd.DataFrame().to_json(date_format='iso', orient='split')

    df_expanded = pd.DataFrame(expanded_rows).reset_index(drop=True)
    
    df_expanded['semana_prog'] = df_expanded['data_programacao'].dt.isocalendar().week.astype('Int64')
    df_expanded['ano_prog'] = df_expanded['data_programacao'].dt.isocalendar().year

    df_expanded['plano_setor_dict'] = df_expanded['plano_setor'].apply(parse_plano_setor)

    # Filter by week
    df_filtered_week = df_expanded[(df_expanded['ano_prog'] == year) & (df_expanded['semana_prog'] == week_num)]

    if df_filtered_week.empty:
        return pd.DataFrame().to_json(date_format='iso', orient='split')

    # Sector Filtering Logic
    setor_id_to_tipo_plano = df_setores.set_index('setor_id')['tipo_plano'].to_dict()
    setor_id_to_set_padrao = df_setores.set_index('setor_id')['set_padrao'].to_dict()
    
    plan_ids_in_sector = set()

    for _, row in df_filtered_week.iterrows():
        # Case 1: Has saved JSON data
        if row['plano_setor_dict']:
            for part_name, sector_values in row['plano_setor_dict'].items():
                if isinstance(sector_values, dict):
                    if str(setor_id) in sector_values and int(sector_values[str(setor_id)] or 0) > 0:
                        plan_ids_in_sector.add(row['plan_id'])
                        break 
        
        # Case 2: No JSON, apply default logic
        else:
            if not row.get('is_part', True): # is_part might not exist, default to True to skip
                partes_dict = json.loads(row['pap_parte']) if isinstance(row['pap_parte'], str) else row.get('pap_parte', {})
                if isinstance(partes_dict, dict):
                    for parte_nome, multiplicador in partes_dict.items():
                        if setor_id_to_set_padrao.get(setor_id) != 2:
                            tipo_plano = setor_id_to_tipo_plano.get(setor_id)
                            parent_qty = row.get('quantidade', 0)
                            default_value = 0
                            if tipo_plano == 2: default_value = parent_qty
                            elif tipo_plano == 1: default_value = parent_qty // multiplicador if multiplicador > 0 else 0
                            
                            if default_value > 0:
                                plan_ids_in_sector.add(row['plan_id'])
                                break
                    if row['plan_id'] in plan_ids_in_sector:
                        continue

    df_final_filtered = df_filtered_week[df_filtered_week['plan_id'].isin(plan_ids_in_sector)]

    return df_final_filtered.to_json(date_format='iso', orient='split')

def calcular_totais_categoria_relatorio(df, setor_id, df_setores):
    if df.empty or setor_id is None:
        return []

    category_totals = defaultdict(int)
    
    setor_id_to_tipo_plano = df_setores.set_index('setor_id')['tipo_plano'].to_dict()
    setor_id_to_set_padrao = df_setores.set_index('setor_id')['set_padrao'].to_dict()

    df_parts = df[df['is_part'] == True].copy()

    for _, row in df_parts.iterrows():
        category = row['pcp_categoria']
        
        # Determine the quantity for the selected sector for this part
        final_value = 0
        plano_setor_dict = row.get('plano_setor_dict', {})
        part_name = row.get('produto_nome')
        part_plans = plano_setor_dict.get(part_name, {}) if isinstance(plano_setor_dict, dict) else {}
        
        saved_value = part_plans.get(str(setor_id)) if isinstance(part_plans, dict) else None

        if saved_value is not None and saved_value != '':
            final_value = saved_value
        else:
            if setor_id_to_set_padrao.get(setor_id) != 2:
                tipo_plano = setor_id_to_tipo_plano.get(setor_id)
                parent_planned_qty = row['quantidade']
                part_multiplier = row['part_multiplier']

                if tipo_plano == 2:
                    final_value = parent_planned_qty
                elif tipo_plano == 1:
                    final_value = parent_planned_qty // part_multiplier if part_multiplier > 0 else 0
        
        category_totals[category] += int(final_value or 0)

    return [{'categoria': cat, 'programado': total} for cat, total in category_totals.items()]

def calcular_totais_setor_relatorio(df_planejamento, df_setores, setor_id):
    if df_planejamento.empty or setor_id is None:
        return []

    setores_info = {
        row['setor_id']: {'id': row['setor_id'], 'nome': row['setor_nome'], 'setups': 0, 'unidades': 0}
        for _, row in df_setores.iterrows()
    }
    setor_id_to_tipo_plano = df_setores.set_index('setor_id')['tipo_plano'].to_dict()
    setor_id_to_set_padrao = df_setores.set_index('setor_id')['set_padrao'].to_dict()
    
    df_unique_plans = df_planejamento.drop_duplicates(subset=['plan_id'])

    df_com_json = df_unique_plans.dropna(subset=['plano_setor_dict'])
    df_com_json = df_com_json[df_com_json['plano_setor_dict'].apply(lambda d: isinstance(d, dict) and bool(d))]

    for _, row in df_com_json.iterrows():
        plano_setor = row['plano_setor_dict']
        for part_name, sector_values in plano_setor.items():
            if isinstance(sector_values, dict):
                for sector_id_str, quantity in sector_values.items():
                    try:
                        current_sector_id, qty_val = int(sector_id_str), int(quantity or 0)
                        if current_sector_id in setores_info and qty_val > 0:
                            setores_info[current_sector_id]['setups'] += 1
                            setores_info[current_sector_id]['unidades'] += qty_val
                    except (ValueError, TypeError):
                        continue

    df_sem_json = df_unique_plans[~df_unique_plans['plan_id'].isin(df_com_json['plan_id'])]
    df_sem_json = df_sem_json[df_sem_json.get('is_part', True) == False]

    for _, row in df_sem_json.iterrows():
        partes_dict = json.loads(row['pap_parte']) if isinstance(row['pap_parte'], str) else row.get('pap_parte')
        if not isinstance(partes_dict, dict):
            continue
        
        for parte_nome, multiplicador in partes_dict.items():
            for current_sector_id in setores_info.keys():
                if setor_id_to_set_padrao.get(current_sector_id) != 2:
                    tipo_plano = setor_id_to_tipo_plano.get(current_sector_id)
                    parent_qty = row.get('quantidade', 0)
                    
                    default_value = 0
                    if tipo_plano == 2:
                        default_value = parent_qty
                    elif tipo_plano == 1:
                        default_value = parent_qty // multiplicador if multiplicador > 0 else 0
                    
                    if default_value > 0:
                        setores_info[current_sector_id]['setups'] += 1
                        setores_info[current_sector_id]['unidades'] += default_value
    
    active_sectors_data = [info for info in setores_info.values() if info['unidades'] > 0 and info['id'] == setor_id]
    return active_sectors_data

def get_week_dates(year, week):
    d = datetime(year, 1, 1)
    if d.weekday() <= 3:
        d = d - timedelta(d.weekday())
    else:
        d = d + timedelta(6 - d.weekday())
    dlt = timedelta(days=(week - 1) * 7)
    return d + dlt, d + dlt + timedelta(days=6)

def get_previous_week(year, week):
    if week == 1:
        return year - 1, 52
    else:
        return year, week - 1

def calculate_oee_for_all_machines_in_sector(start_date, end_date, setor_id):
    # This function will be a direct copy from dashboard_oee_setor.py to ensure all metrics are calculated
    banco = Banco()
    query = """
    WITH 
        apontamentos_producao AS (
            SELECT 
                atp_producao as pr_id,
                SUM(atp_qtd) as total_producao,
                SUM(atp_refugos) as total_refugo
            FROM apontamento_produto
            GROUP BY atp_producao
        ),
        apontamentos_parada AS (
            SELECT 
                ap_pr as pr_id,
                SUM(CASE WHEN r.ra_tipo = 'PARADA REGISTRADA' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_registrada,
                SUM(CASE WHEN r.ra_tipo = 'DISPONIBILIDADE' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_disponibilidade,
                SUM(CASE WHEN r.ra_tipo = 'PERFORMANCE' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_performance
            FROM apontamento ap
            JOIN razao r ON ap.ap_lv1 = r.ra_id
            GROUP BY ap_pr
        )
    SELECT
        p.pr_maquina_id,
        m.maquina_nome,
        SUM(
            CASE 
                WHEN p.pr_fechado = 1 THEN 0 
                ELSE (60 - COALESCE(apt.soma_parada_registrada, 0)) * (COALESCE(cp.cp_meta, 0) / 60.0) 
            END
        ) as total_meta,
        COUNT(CASE WHEN p.pr_fechado != 1 AND cp.cp_meta > 0 THEN p.pr_id END) * 60 AS tempo_planejado_producao,
        SUM(COALESCE(apt.soma_parada_registrada, 0)) AS total_parada_registrada,
        SUM(COALESCE(apt.soma_parada_disponibilidade, 0)) AS total_parada_disponibilidade,
        SUM(COALESCE(apt.soma_parada_performance, 0)) AS total_parada_performance,
        SUM(COALESCE(ap.total_producao, 0)) AS total_produzido,
        SUM(COALESCE(ap.total_refugo, 0)) AS total_refugo
    FROM producao p
    JOIN maquina m ON p.pr_maquina_id = m.maquina_id
    LEFT JOIN categoria_produto cp ON p.pr_categoria_produto_id = cp.cp_id
    LEFT JOIN apontamentos_producao ap ON p.pr_id = ap.pr_id
    LEFT JOIN apontamentos_parada apt ON p.pr_id = apt.pr_id
    WHERE p.pr_data BETWEEN :start_date AND :end_date
      AND p.pr_setor_id = :setor_id
    GROUP BY p.pr_maquina_id, m.maquina_nome
    """
    params = {'start_date': start_date, 'end_date': end_date, 'setor_id': setor_id}
    with banco.engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    if df.empty:
        return pd.DataFrame()

    results = []
    for _, row in df.iterrows():
        denominador_disp = row['tempo_planejado_producao'] - row['total_parada_registrada']
        tempo_operando = 0
        availability = 0
        if denominador_disp > 0:
            tempo_operando = denominador_disp - row['total_parada_disponibilidade']
            availability = (tempo_operando / denominador_disp)

        performance = 0
        if tempo_operando > 0:
            performance = ((tempo_operando - row['total_parada_performance']) / tempo_operando)

        quality = 0
        if row['total_produzido'] > 0:
            quality = ((row['total_produzido'] - row['total_refugo']) / row['total_produzido'])

        oee = availability * performance * quality

        horas_produtivas = denominador_disp / 60 if denominador_disp > 0 else 0

        results.append({
            'maquina_nome': row['maquina_nome'],
            'availability': availability * 100,
            'performance': performance * 100,
            'quality': quality * 100,
            'oee': oee * 100,
            'horas_produtivas': horas_produtivas,
            'total_produzido': row['total_produzido'],
            'total_refugo': row['total_refugo'],
            'total_meta': row['total_meta']
        })
        
    return pd.DataFrame(results)

def criar_cards_oee_relatorio(df_machines_oee):
    if df_machines_oee.empty:
        return []

    cards = []
    for _, row in df_machines_oee.iterrows():
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number", value=row['oee'], number={'suffix': "%"},
            gauge={'axis': {'range': [None, 100]},
                   'steps': [{'range': [0, 50], 'color': 'red'}, {'range': [50, 85], 'color': 'yellow'}, {'range': [85, 100], 'color': 'green'}],
                   'bar': {'color': 'black'}}))
        gauge_fig.update_layout(height=150, margin=dict(l=10, r=10, t=40, b=10))

        card_content = [
            dbc.CardHeader(html.Div([
                html.Span(row['maquina_nome'], className="fw-bold"),
                html.Span(f"Meta: {row.get('total_meta', 0):,.0f}".replace(',', '.'), className="float-end text-muted")
            ])),
            dbc.CardBody(dbc.Row([
                dbc.Col(dcc.Graph(figure=gauge_fig, config={'displayModeBar': False}), md=4),
                dbc.Col([
                    html.P(f"Disponibilidade: {row['availability']:.1f}%"),
                    html.P(f"Performance: {row['performance']:.1f}%"),
                    html.P(f"Qualidade: {row['quality']:.1f}%"),
                ], md=4),
                dbc.Col([
                    html.P(f"Horas Produtivas: {row.get('horas_produtivas', 0):.2f}"),
                    html.P(f"Qtd Produzida: {row.get('total_produzido', 0):,.0f}".replace(',', '.')),
                    html.P(f"Total Refugo: {row.get('total_refugo', 0):,.0f}".replace(',', '.')),
                ], md=4),
            ], align="center"))
        ]
        cards.append(dbc.Col(dbc.Card(card_content), md=4, className="mb-3"))
    return cards

def create_programming_table_df(df, setor_id, df_setores):
    # This function creates and returns the DataFrame for the programming table
    if df.empty or setor_id is None:
        return pd.DataFrame()

    setor_id_to_tipo_plano = df_setores.set_index('setor_id')['tipo_plano'].to_dict()
    setor_id_to_set_padrao = df_setores.set_index('setor_id')['set_padrao'].to_dict()

    table_rows_data = []
    df_parts = df[df['is_part'] == True].copy()

    for _, row in df_parts.iterrows():
        planned_qty = 0
        plano_setor_dict = row.get('plano_setor_dict', {})
        part_name = row.get('produto_nome')
        part_plans = plano_setor_dict.get(part_name, {}) if isinstance(plano_setor_dict, dict) else {}
        saved_value = part_plans.get(str(setor_id)) if isinstance(part_plans, dict) else None

        if saved_value is not None and saved_value != '':
            planned_qty = saved_value
        else:
            if setor_id_to_set_padrao.get(setor_id) != 2:
                tipo_plano = setor_id_to_tipo_plano.get(setor_id)
                parent_planned_qty = row['quantidade']
                part_multiplier = row.get('part_multiplier', 1)

                if tipo_plano == 2:
                    planned_qty = parent_planned_qty
                elif tipo_plano == 1:
                    planned_qty = parent_planned_qty // part_multiplier if part_multiplier > 0 else 0
        
        if planned_qty and int(planned_qty) > 0:
            new_row = {
                'PCP OS': row.get('pcp_pcp'), 'CLIENTE': row.get('cliente_nome'),
                'PRODUTO': row.get('produto_nome_original'), 'PARTE': row.get('produto_nome'),
                'QTD PLANEJADA': int(planned_qty),
                'DATA': pd.to_datetime(row.get('data_programacao')).strftime('%d/%m/%Y'),
                'CATEGORIA': row.get('pcp_categoria')
            }
            table_rows_data.append(new_row)

    if not table_rows_data:
        return pd.DataFrame()

    df_display = pd.DataFrame(table_rows_data)
    return df_display.sort_values(by=['CATEGORIA', 'PARTE'])

def build_programming_table_component(df_display):
    # This function takes a DataFrame and returns a dbc.Table component
    if df_display.empty:
        return dbc.Alert("Nenhuma peça programada para este setor na semana selecionada.", color="info")

    colunas_tabela = ['PCP OS', 'CLIENTE', 'PRODUTO', 'PARTE', 'QTD PLANEJADA', 'DATA']
    header = html.Thead(html.Tr([html.Th(col) for col in colunas_tabela]))
    body_rows = []
    for _, row in df_display.iterrows():
        cells = [html.Td(row.get(col, '')) for col in colunas_tabela]
        body_rows.append(html.Tr(cells))
    body = html.Tbody(body_rows)
    return dbc.Table([header, body], bordered=True, striped=True, hover=True, responsive=True, size='sm')

@app.callback(
    [Output('relatorio-cards-container', 'children'),
     Output('relatorio-tabela-store', 'data')], # Output to the new store
    [Input('relatorio-data-store', 'data'),
     State('relatorio-setor-filter', 'value'),
     State('relatorio-semana-filter', 'value')]
)
def update_relatorio_display(data, setor_id, semana):
    if not data or not setor_id or not semana:
        raise PreventUpdate

    df = pd.read_json(io.StringIO(data), orient='split')

    if df.empty:
        return dbc.Alert("Nenhum dado encontrado para os filtros selecionados.", color="warning"), pd.DataFrame().to_json(orient='split')

    banco = Banco()
    df_setores = banco.ler_tabela('setor')
    
    # Data for cards
    categorias_data = calcular_totais_categoria_relatorio(df, setor_id, df_setores)
    setups_data = calcular_totais_setor_relatorio(df, df_setores, setor_id)

    # Build cards
    all_cards = []

    cards_categorias = [
        dbc.Col(dbc.Card([
            dbc.CardHeader(f"Categoria: {total['categoria']}"),
            dbc.CardBody([
                html.H5(f"Programado: {total['programado']:,.0f}".replace(',', '.')),
            ])
        ]), md=2) for total in categorias_data
    ]
    all_cards.extend(cards_categorias)

    cards_setups = [
        dbc.Col(dbc.Card([
            dbc.CardHeader(f"Setor: {sector['nome']}"),
            dbc.CardBody([
                html.H5(f"Setups: {sector['setups']}"),
                html.H5(f"Unidades: {sector['unidades']:,.0f}".replace(',', '.')),
            ])
        ]), md=2) for sector in setups_data
    ]
    all_cards.extend(cards_setups)

    # OEE Cards for the PREVIOUS week
    year, week_num = map(int, semana.split('-'))
    prev_year, prev_week = get_previous_week(year, week_num)
    start_date_prev, end_date_prev = get_week_dates(prev_year, prev_week)
    oee_data = calculate_oee_for_all_machines_in_sector(start_date_prev, end_date_prev, setor_id)
    cards_oee = criar_cards_oee_relatorio(oee_data)

    # Programming table for the SELECTED week
    tabela_programacao_df = create_programming_table_df(df, setor_id, df_setores)
    tabela_component = build_programming_table_component(tabela_programacao_df)

    final_layout = html.Div([
        dbc.Row(all_cards),
        html.Hr(),
        dbc.Row(cards_oee),
        html.Hr(),
        tabela_component
    ])
    
    return final_layout, tabela_programacao_df.to_json(orient='split')

@app.callback(
    Output("download-excel", "data"),
    Input("btn-excel", "n_clicks"),
    State('relatorio-data-store', 'data'),
    prevent_initial_call=True,
)
def export_excel(n_clicks, data):
    if not data:
        raise PreventUpdate
    df = pd.read_json(io.StringIO(data), orient='split')
    output = io.BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    for r in dataframe_to_rows(df, index=False, header=True):
        sheet.append(r)
    workbook.save(output)
    output.seek(0)
    return dcc.send_bytes(output.getvalue(), "relatorio_programacao.xlsx")

@app.callback(
    Output("download-pdf", "data"),
    Input("btn-pdf", "n_clicks"),
    [State('relatorio-data-store', 'data'),
     State('relatorio-tabela-store', 'data'),
     State('relatorio-setor-filter', 'value'),
     State('relatorio-semana-filter', 'value')],
    prevent_initial_call=True,
)
def export_pdf(n_clicks, card_data, table_data, setor_id, semana):
    if not table_data or setor_id is None or semana is None:
        raise PreventUpdate

    df_table = pd.read_json(io.StringIO(table_data), orient='split')
    if df_table.empty:
        raise PreventUpdate

    banco = Banco()
    df_setores = banco.ler_tabela('setor')

    # --- Build PDF ---
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []
    
    page_width, page_height = landscape(letter)
    available_width = page_width - 1*inch # margins

    setor_nome_series = df_setores[df_setores['setor_id'] == setor_id]['setor_nome']
    setor_nome = setor_nome_series.iloc[0] if not setor_nome_series.empty else 'Desconhecido'
    title = f"Relatório de Programação - Setor: {setor_nome} | Semana: {semana.split('-')[1]}/{semana.split('-')[0]}"
    elements.append(Paragraph(title, styles['h1']))
    elements.append(Spacer(1, 0.2*inch))

    # Programming Table
    elements.append(Paragraph("Programação Detalhada", styles['h2']))
    elements.append(Spacer(1, 0.1*inch))
    
    col_widths_detail = [0.6*inch, 1.5*inch, 2.5*inch, 1.5*inch, 1*inch, 1*inch, 1*inch]
    df_table['CATEGORIA'] = df_table['CATEGORIA'].astype(str)
    table_content_data = [df_table.columns.tolist()] + df_table.values.tolist()
    
    table = Table(table_content_data, colWidths=col_widths_detail)
    table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('GRID', (0,0), (-1,-1), 1, colors.black), ('FONTSIZE', (0,0), (-1,-1), 7), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elements.append(table)
    
    doc.build(elements)
    output.seek(0)
    return dcc.send_bytes(output.getvalue(), f"relatorio_{setor_nome}_{semana}.pdf")
