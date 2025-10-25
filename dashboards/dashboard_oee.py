from dash import html, dcc, Input, Output, dash_table, State, callback_context
import dash_bootstrap_components as dbc
from app import app
from banco_dados.banco import Banco
from sqlalchemy import text
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go

def create_metric_card(title, body_id):
    return dbc.Card([
        dbc.CardHeader(title),
        dbc.CardBody(id=body_id)
    ], className="text-center m-1", style={"height": "125px"})

def get_custo_extra_details(start_date, end_date, setor_id, maquina_id):
    banco = Banco()
    query = """
        SELECT
            ap.atp_obs,
            ap.atp_custo
        FROM
            apontamento_produto ap
        JOIN
            producao p ON ap.atp_producao = p.pr_id
        WHERE
            ap.atp_custo IS NOT NULL AND ap.atp_custo > 0
    """
    params = {}
    if setor_id:
        query += " AND p.pr_setor_id = :setor_id"
        params['setor_id'] = setor_id
    if maquina_id:
        query += " AND p.pr_maquina_id = :maquina_id"
        params['maquina_id'] = maquina_id
    if start_date and end_date:
        query += " AND p.pr_data BETWEEN :start_date AND :end_date"
        params['start_date'] = start_date
        params['end_date'] = end_date
    
    with banco.engine.connect() as conn:
        df_details = pd.read_sql(text(query), conn, params=params)
        
    return df_details

def get_product_summary_data(start_date, end_date, setor_id, maquina_id):
    banco = Banco()
    query = """
        SELECT
            pcp.pcp_pcp,
            pr.nome as produto_nome,
            SUM(ap.atp_qtd * COALESCE(ap.atp_repeticoes, 1)) as total_qtd,
            SUM(COALESCE(ap.atp_refugos, 0)) as total_refugo,
            pcp.pcp_qtd,
            SUM((JULIANDAY(p.pr_termino) - JULIANDAY(p.pr_inicio)) * 24) as horas_gastas,
            CASE WHEN cp.cp_meta > 0 THEN pcp.pcp_qtd * 1.0 / cp.cp_meta ELSE 0 END as horas_previstas
        FROM
            apontamento_produto ap
        JOIN
            producao p ON ap.atp_producao = p.pr_id
        JOIN
            pcp ON ap.atp_pcp = pcp.pcp_id
        JOIN
            produtos pr ON pcp.pcp_produto_id = pr.produto_id
        JOIN
            categoria_produto cp ON p.pr_categoria_produto_id = cp.cp_id
        WHERE pcp.pcp_pcp IS NOT NULL
    """
    params = {}
    if setor_id:
        query += " AND p.pr_setor_id = :setor_id"
        params['setor_id'] = setor_id
    if maquina_id:
        query += " AND p.pr_maquina_id = :maquina_id"
        params['maquina_id'] = maquina_id
    if start_date and end_date:
        query += " AND p.pr_data BETWEEN :start_date AND :end_date"
        params['start_date'] = start_date
        params['end_date'] = end_date
    
    query += " GROUP BY pcp.pcp_pcp, pr.nome, pcp.pcp_qtd, cp.cp_meta"
    
    with banco.engine.connect() as conn:
        df_summary = pd.read_sql(text(query), conn, params=params)
        
    return df_summary

def calculate_oee_metrics(start_date, end_date, setor_id, maquina_id):
    if not start_date or not end_date:
        return {'availability': 0, 'performance': 0, 'quality': 0, 'custo_oee': 0, 'custo_extra': 0, 'dataframe': pd.DataFrame()}

    banco = Banco()
    
    query = """
    WITH 
        SomaApontamentoProduto AS (
            SELECT
                atp_producao,
                SUM(atp_qtd) AS soma_atp_qtd,
                SUM(atp_refugos) AS soma_atp_refugo,
                SUM(COALESCE(atp_custo, 0)) AS soma_atp_custo
            FROM 
                apontamento_produto
            GROUP BY 
                atp_producao
        ),
        SomaApontamentoParadas AS (
            SELECT
                ap.ap_pr,
                SUM(CASE WHEN r.ra_tipo = 'PARADA REGISTRADA' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_registrada,
                SUM(CASE WHEN r.ra_tipo = 'DISPONIBILIDADE' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_disponibilidade,
                SUM(CASE WHEN r.ra_tipo = 'PERFORMANCE' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_performance
            FROM 
                apontamento ap
            JOIN 
                razao r ON ap.ap_lv1 = r.ra_id
            GROUP BY 
                ap.ap_pr
        )
    SELECT 
        p.pr_id,
        s.setor_nome,
        m.maquina_nome,
        m.maquina_custo,
        cp.cp_nome as categoria_nome,
        p.pr_data,
        p.pr_inicio,
        p.pr_termino,
        COALESCE(p.pr_fechado, 0) as pr_fechado,
        CASE WHEN COALESCE(p.pr_fechado, 0) = 1 THEN 0 ELSE COALESCE(cp.cp_meta, 0) END AS meta_producao,
        CASE WHEN COALESCE(p.pr_fechado, 0) = 1 THEN 0 ELSE COALESCE(sap.soma_atp_qtd, 0) END AS soma_atp_qtd,
        CASE WHEN COALESCE(p.pr_fechado, 0) = 1 THEN 0 ELSE COALESCE(sap.soma_atp_refugo, 0) END AS soma_atp_refugo,
        CASE WHEN COALESCE(p.pr_fechado, 0) = 1 THEN 0 ELSE COALESCE(sap.soma_atp_custo, 0) END AS soma_atp_custo,
        CASE WHEN COALESCE(p.pr_fechado, 0) = 1 THEN 0 ELSE COALESCE(spp.soma_parada_registrada, 0) END AS soma_parada_registrada,
        CASE WHEN COALESCE(p.pr_fechado, 0) = 1 THEN 0 ELSE COALESCE(spp.soma_parada_disponibilidade, 0) END AS soma_parada_disponibilidade,
        CASE WHEN COALESCE(p.pr_fechado, 0) = 1 THEN 0 ELSE COALESCE(spp.soma_parada_performance, 0) END AS soma_parada_performance
    FROM 
        producao p
    LEFT JOIN setor s ON p.pr_setor_id = s.setor_id
    LEFT JOIN maquina m ON p.pr_maquina_id = m.maquina_id
    LEFT JOIN categoria_produto cp ON p.pr_categoria_produto_id = cp.cp_id
    LEFT JOIN 
        SomaApontamentoProduto sap ON p.pr_id = sap.atp_producao
    LEFT JOIN 
        SomaApontamentoParadas spp ON p.pr_id = spp.ap_pr
    WHERE 1=1
    """

    params = {}
    if setor_id:
        query += " AND p.pr_setor_id = :setor_id"
        params['setor_id'] = setor_id
    if maquina_id:
        query += " AND p.pr_maquina_id = :maquina_id"
        params['maquina_id'] = maquina_id
    if start_date and end_date:
        query += " AND p.pr_data BETWEEN :start_date AND :end_date"
        params['start_date'] = start_date
        params['end_date'] = end_date
    elif start_date:
        query += " AND p.pr_data >= :start_date"
        params['start_date'] = start_date
    elif end_date:
        query += " AND p.pr_data <= :end_date"
        params['end_date'] = end_date
    
    with banco.engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    if df.empty:
        return {'availability': 0, 'performance': 0, 'quality': 0, 'custo_oee': 0, 'custo_extra': 0, 'dataframe': pd.DataFrame()}

    # Custo OEE
    df['maquina_custo'] = df['maquina_custo'].fillna(0)
    custo_oee = ((df['maquina_custo'] / 60) * (df['soma_parada_disponibilidade'] + df['soma_parada_performance'])).sum()

    # Custo Extra
    custo_extra = df['soma_atp_custo'].sum()

    # Disponibilidade
    tempo_planejado_producao = len(df[(df['pr_fechado'] != 1) & (df['meta_producao'] != 0)]) * 60
    total_parada_registrada = df['soma_parada_registrada'].sum()
    total_parada_disponibilidade = df['soma_parada_disponibilidade'].sum()

    denominador_disp = tempo_planejado_producao - total_parada_registrada
    tempo_operando = 0
    disponibilidade = 0
    if denominador_disp > 0:
        tempo_operando = denominador_disp - total_parada_disponibilidade
        disponibilidade = (tempo_operando / denominador_disp) * 100

    # Performance
    total_parada_performance = df['soma_parada_performance'].sum()
    performance = 0
    if tempo_operando > 0:
        performance = ((tempo_operando - total_parada_performance) / tempo_operando) * 100

    # Qualidade
    total_produzido = df['soma_atp_qtd'].sum()
    total_refugo = df['soma_atp_refugo'].sum()
    qualidade = 0
    if total_produzido > 0:
        qualidade = ((total_produzido - total_refugo) / total_produzido) * 100

    return {
        'availability': disponibilidade,
        'performance': performance,
        'quality': qualidade,
        'custo_oee': custo_oee,
        'custo_extra': custo_extra,
        'dataframe': df
    }

def create_oee_table():
    return dbc.Row([
        dbc.Col([
            dash_table.DataTable(
                id='oee-summary-table',
                columns=[
                    {"name": "ID Produção", "id": "pr_id"},
                    {"name": "Setor", "id": "setor_nome"},
                    {"name": "Máquina", "id": "maquina_nome"},
                    {"name": "Categoria", "id": "categoria_nome"},
                    {"name": "Meta", "id": "meta_producao"},
                    {"name": "Data", "id": "pr_data"},
                    {"name": "Início", "id": "pr_inicio"},
                    {"name": "Término", "id": "pr_termino"},
                    {"name": "Qtd Produzida", "id": "soma_atp_qtd"},
                    {"name": "Qtd Refugo", "id": "soma_atp_refugo"},
                    {"name": "Parada Registrada (min)", "id": "soma_parada_registrada"},
                    {"name": "Parada Disponibilidade (min)", "id": "soma_parada_disponibilidade"},
                    {"name": "Parada Performance (min)", "id": "soma_parada_performance"},
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                page_size=24,
            )
        ])
    ])

layout = dbc.Container([
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.Dropdown(id='setor-filter', placeholder='Selecione o Setor'),
                        lg=3, sm=6, xs=12, className="mb-2 mb-lg-0"),
                dbc.Col(dcc.Dropdown(id='maquina-filter', placeholder='Selecione a Máquina'),
                        lg=3, sm=6, xs=12, className="mb-2 mb-lg-0"),
                dbc.Col(dcc.DatePickerSingle(
                    id='start-date-picker', 
                    placeholder='Data Início',
                    date=datetime.now().date() - timedelta(days=3),
                    className="w-100"
                ), lg=3, sm=6, xs=12, className="mb-2 mb-sm-0"),
                dbc.Col(dcc.DatePickerSingle(
                    id='end-date-picker', 
                    placeholder='Data Fim',
                    date=datetime.now().date(),
                    className="w-100"
                ), lg=3, sm=6, xs=12)
            ])
        ])
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Custo OEE"),
                dbc.CardBody(id="custo-oee-body")
            ], className="text-center mb-2"),
            dbc.Card([
                dbc.CardHeader("Custo Extra"),
                dbc.CardBody(id="custo-extra-body")
            ], className="text-center"),
            html.Div(id='custo-extra-details-container', className="mt-2")
        ], md=2, xs=12, className="mb-3 mb-md-0"),
        dbc.Col(dbc.Card(dcc.Graph(id='oee-gauge-chart')), md=6, xs=12, className="mb-3 mb-md-0"),
        dbc.Col([
            create_metric_card("Disponibilidade", "availability-card-body"),
            create_metric_card("Performance", "performance-card-body"),
            create_metric_card("Qualidade", "quality-card-body"),
        ], md=4, xs=12, className="d-flex flex-column justify-content-evenly")
    ], className="mb-4 align-items-stretch"),
    dbc.Row([
        dbc.Col(html.Div(id='product-summary-container'), width=12)
    ]),
    # create_oee_table() # A tabela foi removida da visualização, mas a função permanece
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='stop-chart-lv1')), md=4, xs=12, className="mb-3 mb-md-0"),
        dbc.Col(dbc.Card(dcc.Graph(id='stop-chart-lv2')), md=4, xs=12, className="mb-3 mb-md-0"),
        dbc.Col(dbc.Card(dcc.Graph(id='stop-chart-lv3')), md=4, xs=12),
    ], className="mt-4"),
    dbc.Row([
        dbc.Col(dbc.Card(dcc.Graph(id='stop-chart-lv4')), md=4, xs=12, className="mb-3 mb-md-0"),
        dbc.Col(dbc.Card(dcc.Graph(id='stop-chart-lv5')), md=4, xs=12, className="mb-3 mb-md-0"),
        dbc.Col(dbc.Card(dcc.Graph(id='stop-chart-lv6')), md=4, xs=12),
    ], className="mt-4"),
    dcc.Store(id='selected-bar-filter'), # Store para o filtro de clique
], fluid=True)

def get_all_stop_data(start_date, end_date, setor_id, maquina_id, selected_razao_id=None, selected_level=None):
    banco = Banco()
    
    # 1. Fetch all reasons once
    df_razao = banco.ler_tabela('razao')
    if df_razao.empty:
        return {f'df_lv{i}': pd.DataFrame() for i in range(1, 7)}

    # 2. Fetch all relevant appointment data once
    query = """
        SELECT ap.ap_tempo, ap.ap_lv1, ap.ap_lv2, ap.ap_lv3, ap.ap_lv4, ap.ap_lv5, ap.ap_lv6
        FROM apontamento ap
        JOIN producao p ON ap.ap_pr = p.pr_id
        WHERE p.pr_data BETWEEN :start_date AND :end_date
    """
    params = {'start_date': start_date, 'end_date': end_date}
    if setor_id:
        query += " AND p.pr_setor_id = :setor_id"
        params['setor_id'] = setor_id
    if maquina_id:
        query += " AND p.pr_maquina_id = :maquina_id"
        params['maquina_id'] = maquina_id
        
    # Apply filter from clicked bar
    if selected_razao_id and selected_level:
        query += f" AND ap.{selected_level} = :selected_razao_id"
        params['selected_razao_id'] = selected_razao_id

    with banco.engine.connect() as conn:
        df_apontamento = pd.read_sql(text(query), conn, params=params)

    if df_apontamento.empty:
        return {f'df_lv{i}': pd.DataFrame() for i in range(1, 7)}

    # 3. Process data for each level in memory
    results = {}
    for i in range(1, 7):
        level_col = f'ap_lv{i}'
        
        # Filter appointments for the current level (non-null and tempo > 0)
        df_level_ap = df_apontamento.loc[df_apontamento[level_col].notna() & (df_apontamento['ap_tempo'] > 0)].copy()
        
        if df_level_ap.empty:
            results[level_col.replace('ap', 'df')] = pd.DataFrame()
            continue
            
        # Merge with reasons
        df_merged = pd.merge(
            df_level_ap,
            df_razao[['ra_id', 'ra_razao']],
            left_on=level_col,
            right_on='ra_id',
            how='inner'
        )

        # Group and sum
        df_grouped = df_merged.groupby(['ra_id', 'ra_razao'])['ap_tempo'].sum().reset_index()
        df_grouped.rename(columns={'ap_tempo': 'total_tempo'}, inplace=True)
        
        results[level_col.replace('ap', 'df')] = df_grouped
        
    return results

def create_stop_bar_chart(df, title):
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=title,
            xaxis_visible=False,
            yaxis_visible=False,
            annotations=[
                dict(
                    text="Sem dados para exibir",
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=16)
                )
            ],
            height=450
        )
        return fig
    
    df = df.sort_values(by='total_tempo', ascending=False)

    fig = go.Figure(go.Bar(
        x=df['total_tempo'],
        y=df['ra_razao'],
        orientation='h',
        text=df['total_tempo'],
        textposition='inside',
        marker_color='red',
        customdata=df['ra_id']
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Tempo Total (min)",
        yaxis_title="Razão da Parada",
        height=450,
        margin=dict(l=40, r=40, t=40, b=40),
        yaxis={'autorange': 'reversed'}
    )
    return fig

# Callback to populate sectors
@app.callback(
    [Output("setor-filter", "options"),
     Output("setor-filter", "value")],
    Input("setor-filter", "id")
)
def load_sectors_dashboard(trigger):
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
    [Output("maquina-filter", "options"),
     Output("maquina-filter", "value")],
    Input("setor-filter", "value")
)
def load_machines_dashboard(setor_id):
    if not setor_id:
        return [], None
        
    banco = Banco()
    df_maquinas = banco.ler_tabela("maquina")
    
    if df_maquinas.empty:
        return [], None
        
    maquinas = [
        {"label": row["maquina_nome"], "value": row["maquina_id"]} 
        for _, row in df_maquinas.query(f"setor_id == {setor_id}").iterrows()
    ]
    return maquinas, maquinas[0]["value"] if maquinas else None

@app.callback(
    Output('selected-bar-filter', 'data'),
    [
        Input('stop-chart-lv1', 'clickData'),
        Input('stop-chart-lv2', 'clickData'),
        Input('stop-chart-lv3', 'clickData'),
        Input('stop-chart-lv4', 'clickData'),
        Input('stop-chart-lv5', 'clickData'),
        Input('stop-chart-lv6', 'clickData'),
        
    ],
    [State('selected-bar-filter', 'data')]
)
def update_selected_bar_filter(clickData_lv1, clickData_lv2, clickData_lv3, clickData_lv4, clickData_lv5, clickData_lv6, current_filter_data):
    ctx = callback_context

    if not ctx.triggered:
        return None

    # Se o botão de limpar foi clicado, reseta o filtro
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]


    # Determina qual gráfico foi clicado
    input_id = triggered_id
    clicked_data = ctx.triggered[0]['value']
    
    # Mapeia o ID do gráfico para a coluna de nível correspondente
    level_map = {
        'stop-chart-lv1': 'ap_lv1',
        'stop-chart-lv2': 'ap_lv2',
        'stop-chart-lv3': 'ap_lv3',
        'stop-chart-lv4': 'ap_lv4',
        'stop-chart-lv5': 'ap_lv5',
        'stop-chart-lv6': 'ap_lv6'
    }
    selected_level = level_map.get(input_id)

    if clicked_data and clicked_data['points']:
        point = clicked_data['points'][0]
        clicked_razao_id = point['customdata']
        
        # Se a mesma barra for clicada novamente, limpa o filtro
        if current_filter_data and \
           current_filter_data.get('razao_id') == clicked_razao_id and \
           current_filter_data.get('level_column') == selected_level:
            return None
        else:
            return {'razao_id': clicked_razao_id, 'level_column': selected_level}
    
    return None

@app.callback(
    [Output('custo-oee-body', 'children'),
     Output('custo-extra-body', 'children'),
     Output('custo-extra-details-container', 'children'),
     Output('product-summary-container', 'children'),
     Output('availability-card-body', 'children'),
     Output('performance-card-body', 'children'),
     Output('quality-card-body', 'children'),
     Output('oee-gauge-chart', 'figure'),
     Output('stop-chart-lv1', 'figure'),
     Output('stop-chart-lv2', 'figure'),
     Output('stop-chart-lv3', 'figure'),
     Output('stop-chart-lv4', 'figure'),
     Output('stop-chart-lv5', 'figure'),
     Output('stop-chart-lv6', 'figure')],
    [Input('setor-filter', 'value'),
     Input('maquina-filter', 'value'),
     Input('start-date-picker', 'date'),
     Input('end-date-picker', 'date'),
     Input('selected-bar-filter', 'data')]
)
def update_oee_dashboard(setor_id, maquina_id, start_date_str, end_date_str, selected_bar_filter_data):
    if not start_date_str or not end_date_str:
        no_data_card = html.Div([html.H4("N/A", className="card-title")])
        empty_fig = go.Figure()
        empty_bar_chart = create_stop_bar_chart(pd.DataFrame(), "")
        return (no_data_card, no_data_card, None, None, no_data_card, no_data_card, no_data_card, empty_fig,
                empty_bar_chart, empty_bar_chart, empty_bar_chart, empty_bar_chart, empty_bar_chart, empty_bar_chart)

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    # Dados não filtrados para os cards principais
    current_metrics = calculate_oee_metrics(start_date, end_date, setor_id, maquina_id)
    df_custo_extra_details = get_custo_extra_details(start_date, end_date, setor_id, maquina_id)
    df_product_summary = get_product_summary_data(start_date, end_date, setor_id, maquina_id)
    
    # Extrai o filtro do dcc.Store
    selected_razao_id = None
    selected_level = None
    if selected_bar_filter_data:
        selected_razao_id = selected_bar_filter_data.get('razao_id')
        selected_level = selected_bar_filter_data.get('level_column')

    # Busca dados para os gráficos de parada (com ou sem filtro)
    all_stop_data = get_all_stop_data(start_date, end_date, setor_id, maquina_id, selected_razao_id, selected_level)
    df_lv1 = all_stop_data.get('df_lv1', pd.DataFrame())
    df_lv2 = all_stop_data.get('df_lv2', pd.DataFrame())
    df_lv3 = all_stop_data.get('df_lv3', pd.DataFrame())
    df_lv4 = all_stop_data.get('df_lv4', pd.DataFrame())
    df_lv5 = all_stop_data.get('df_lv5', pd.DataFrame())
    df_lv6 = all_stop_data.get('df_lv6', pd.DataFrame())

    # Dados do período anterior (não filtrados)
    period_duration = (end_date - start_date)
    previous_end_date = start_date - timedelta(days=1)
    previous_start_date = previous_end_date - period_duration
    previous_metrics = calculate_oee_metrics(previous_start_date, previous_end_date, setor_id, maquina_id)

    # OEE Global Calculation
    oee_availability = current_metrics.get('availability', 0) / 100
    oee_performance = current_metrics.get('performance', 0) / 100
    oee_quality = current_metrics.get('quality', 0) / 100
    oee_global = oee_availability * oee_performance * oee_quality * 100

    # Gauge Chart Figure
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=oee_global,
        title={'text': "OEE Global"},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "black"},
            'steps': [
                {'range': [0, 50], 'color': "red"},
                {'range': [50, 85], 'color': "yellow"},
                {'range': [85, 100], 'color': "green"}
            ],
            'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': 90}
        }
    ))
    gauge_fig.update_layout(height=400) # Definindo a altura do gráfico

    # Helper to generate card content
    def generate_card_content(current_val, previous_val):
        current_display = f"{current_val:.1f}%"
        
        if previous_val > 0:
            change = ((current_val - previous_val) / previous_val) * 100
            change_display = f"{change:+.1f}% vs. período anterior"
            if change > 0:
                change_color = "success"
            elif change < 0:
                change_color = "danger"
            else:
                change_color = "secondary"
        elif current_val > 0:
            change_display = "Período anterior foi 0"
            change_color = "success"
        else:
            change_display = "Sem dados para comparar"
            change_color = "secondary"

        return html.Div([
            html.H4(current_display, className="card-title"),
            html.P(change_display, className=f"text-{change_color} small")
        ])

    availability_card = generate_card_content(current_metrics['availability'], previous_metrics['availability'])
    performance_card = generate_card_content(current_metrics['performance'], previous_metrics['performance'])
    quality_card = generate_card_content(current_metrics['quality'], previous_metrics['quality'])

    # Custo OEE Card
    custo_oee = current_metrics.get('custo_oee', 0)
    custo_oee_card = html.Div([html.H4(f"R$ {custo_oee:,.2f}", className="card-title")])

    # Custo Extra Card Body
    custo_extra = current_metrics.get('custo_extra', 0)
    custo_extra_card_body = html.Div([html.H4(f"R$ {custo_extra:,.2f}", className="card-title")])

    # Custo Extra Details Container
    custo_extra_details_content = None
    if not df_custo_extra_details.empty:
        rows = [html.Tr([html.Td(row['atp_obs']), html.Td(f"R$ {row['atp_custo']:,.2f}")]) for _, row in df_custo_extra_details.iterrows()]
        
        details_table = dbc.Table([
            html.Thead(html.Tr([html.Th("Obs"), html.Th("Custo")])),
            html.Tbody(rows)
        ], bordered=True, striped=True, hover=True, size='sm')

        custo_extra_details_content = html.Div(
            details_table, 
            style={'maxHeight': '190px', 'overflowY': 'auto', 'fontSize': '0.8rem'}
        )

    # Product Summary Table
    product_summary_content = None
    if not df_product_summary.empty:
        # Calcular totais
        total_qtd = df_product_summary['total_qtd'].sum()
        total_refugo = df_product_summary['total_refugo'].sum()
        
        # Criar linhas de dados
        rows = [html.Tr([
            html.Td(row['pcp_pcp']),
            html.Td(row['produto_nome']),
            html.Td(row['total_qtd']),
            html.Td(row['total_refugo']),
            html.Td(row['pcp_qtd']),
            html.Td(f"{row['horas_gastas']:.2f}"),
            html.Td(f"{row['horas_previstas']:.2f}")
        ]) for _, row in df_product_summary.iterrows()]
        
        # Adicionar linha de totais
        total_row = html.Tr([
            html.Td("TOTAL", colSpan=2, style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'}),
            html.Td(total_qtd, style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'}),
            html.Td(total_refugo, style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'}),
            html.Td("", style={'backgroundColor': '#f8f9fa'}),
            html.Td("", style={'backgroundColor': '#f8f9fa'}),
            html.Td("", style={'backgroundColor': '#f8f9fa'})
        ])
        
        summary_table = dbc.Table([
            html.Thead(html.Tr([html.Th("PCP"), html.Th("Produto"), html.Th("Qtd"), html.Th("Refugo"), html.Th("Qtd PCP"), html.Th("Horas Gastas"), html.Th("Horas Previstas")])),
            html.Tbody(rows + [total_row])
        ], bordered=True, striped=True, hover=True, size='sm')

        product_summary_content = html.Div(
            summary_table,
            style={'maxHeight': '200px', 'overflowY': 'auto', 'fontSize': '0.8rem'}
        )

    # Create stop charts
    fig_lv1 = create_stop_bar_chart(df_lv1, "Paradas - Nível 1")
    fig_lv2 = create_stop_bar_chart(df_lv2, "Paradas - Nível 2")
    fig_lv3 = create_stop_bar_chart(df_lv3, "Paradas - Nível 3")
    fig_lv4 = create_stop_bar_chart(df_lv4, "Paradas - Nível 4")
    fig_lv5 = create_stop_bar_chart(df_lv5, "Paradas - Nível 5")
    fig_lv6 = create_stop_bar_chart(df_lv6, "Paradas - Nível 6")

    return (
        custo_oee_card, 
        custo_extra_card_body, 
        custo_extra_details_content, 
        product_summary_content,
        availability_card, 
        performance_card, 
        quality_card, 
        gauge_fig,
        fig_lv1, fig_lv2, fig_lv3,
        fig_lv4, fig_lv5, fig_lv6
    )
