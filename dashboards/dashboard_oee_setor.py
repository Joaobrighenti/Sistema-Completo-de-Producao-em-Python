import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
from app import app
from banco_dados.banco import Banco
from sqlalchemy import text
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go

# =============================================================================
# FUNÇÕES DE CONSULTA AO BANCO
# =============================================================================

def get_stop_data_for_level(start_date, end_date, setor_id, level):
    banco = Banco()
    df_razao = banco.ler_tabela('razao')
    if df_razao.empty:
        return pd.DataFrame()

    level_col = f'ap_lv{level}'

    query = f"""
        SELECT ap.ap_tempo, ap.{level_col}
        FROM apontamento ap
        JOIN producao p ON ap.ap_pr = p.pr_id
        WHERE p.pr_data BETWEEN :start_date AND :end_date
          AND p.pr_setor_id = :setor_id
          AND ap.{level_col} IS NOT NULL
          AND ap.ap_tempo > 0
    """
    params = {'start_date': start_date, 'end_date': end_date, 'setor_id': setor_id}

    with banco.engine.connect() as conn:
        df_apontamento = pd.read_sql(text(query), conn, params=params)

    if df_apontamento.empty:
        return pd.DataFrame()

    df_merged = pd.merge(
        df_apontamento,
        df_razao[['ra_id', 'ra_razao']],
        left_on=level_col,
        right_on='ra_id',
        how='inner'
    )

    if df_merged.empty:
        return pd.DataFrame()
        
    df_grouped = df_merged.groupby(['ra_id', 'ra_razao'])['ap_tempo'].sum().reset_index()
    df_grouped.rename(columns={'ap_tempo': 'total_tempo'}, inplace=True)
        
    return df_grouped

def create_stop_bar_chart(df, title):
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=title,
            xaxis_visible=False,
            yaxis_visible=False,
            annotations=[dict(text="Sem dados", xref="paper", yref="paper", showarrow=False, font=dict(size=12))],
            height=240,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        return fig
    
    df = df.sort_values(by='total_tempo', ascending=False)
    fig = go.Figure(go.Bar(
        x=df['total_tempo'], y=df['ra_razao'], orientation='h',
        text=df['total_tempo'], textposition='inside', marker_color='red'
    ))
    fig.update_layout(
        title=title, xaxis_title=None, yaxis_title=None, height=240,
        margin=dict(l=10, r=10, t=30, b=10), yaxis={'autorange': 'reversed'}, font=dict(size=10)
    )
    return fig

def get_category_summary_data(start_date, end_date, setor_id):
    banco = Banco()
    query = """
        SELECT
            pcp.pcp_categoria as categoria_nome,
            SUM(ap.atp_qtd) as total_qtd_categoria
        FROM
            apontamento_produto ap
        JOIN
            producao p ON ap.atp_producao = p.pr_id
        JOIN
            pcp ON ap.atp_pcp = pcp.pcp_id
        WHERE
            p.pr_setor_id = :setor_id AND p.pr_data BETWEEN :start_date AND :end_date
            AND pcp.pcp_categoria IS NOT NULL
        GROUP BY
            pcp.pcp_categoria
        ORDER BY
            total_qtd_categoria DESC
    """
    params = {'start_date': start_date, 'end_date': end_date, 'setor_id': setor_id}
    with banco.engine.connect() as conn:
        df_categories = pd.read_sql(text(query), conn, params=params)
    return df_categories

def get_product_summary_data(start_date, end_date, setor_id):
    banco = Banco()
    query = """
        SELECT
            pcp.pcp_pcp,
            pr.nome as produto_nome,
            SUM(ap.atp_qtd) as total_qtd,
            SUM(COALESCE(ap.atp_refugos, 0)) as total_refugo,
            pcp.pcp_qtd,
            SUM((JULIANDAY(p.pr_termino) - JULIANDAY(p.pr_inicio)) * 24) as horas_gastas
        FROM
            apontamento_produto ap
        JOIN
            producao p ON ap.atp_producao = p.pr_id
        JOIN
            pcp ON ap.atp_pcp = pcp.pcp_id
        JOIN
            produtos pr ON pcp.pcp_produto_id = pr.produto_id
        WHERE pcp.pcp_pcp IS NOT NULL AND p.pr_setor_id = :setor_id
    """
    params = {'setor_id': setor_id}
    if start_date and end_date:
        query += " AND p.pr_data BETWEEN :start_date AND :end_date"
        params['start_date'] = start_date
        params['end_date'] = end_date
    
    query += " GROUP BY pcp.pcp_pcp, pr.nome, pcp.pcp_qtd"
    
    with banco.engine.connect() as conn:
        df_summary = pd.read_sql(text(query), conn, params=params)
        
    return df_summary

def calculate_oee_for_all_machines_in_sector(start_date, end_date, setor_id):
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

def calculate_oee_metrics_geral(start_date, end_date, setor_id):
    base_metrics = {'availability': 0, 'performance': 0, 'quality': 0, 'oee': 0, 'total_produzido': 0, 'total_refugo': 0, 'horas_produtivas': 0, 'produzido_por_hora': 0}
    if not start_date or not end_date or not setor_id:
        return base_metrics

    banco = Banco()
    query = """
    WITH 
        apontamentos_producao AS (SELECT atp_producao as pr_id, SUM(atp_qtd) as total_producao, SUM(atp_refugos) as total_refugo FROM apontamento_produto GROUP BY atp_producao),
        apontamentos_parada AS (
            SELECT ap_pr as pr_id,
                   SUM(CASE WHEN r.ra_tipo = 'PARADA REGISTRADA' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_registrada,
                   SUM(CASE WHEN r.ra_tipo = 'DISPONIBILIDADE' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_disponibilidade,
                   SUM(CASE WHEN r.ra_tipo = 'PERFORMANCE' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_performance
            FROM apontamento ap JOIN razao r ON ap.ap_lv1 = r.ra_id GROUP BY ap_pr
        )
    SELECT
        p.pr_fechado, cp.cp_meta, ap.total_producao, ap.total_refugo,
        apt.soma_parada_registrada, apt.soma_parada_disponibilidade, apt.soma_parada_performance
    FROM producao p
    LEFT JOIN categoria_produto cp ON p.pr_categoria_produto_id = cp.cp_id
    LEFT JOIN apontamentos_producao ap ON p.pr_id = ap.pr_id
    LEFT JOIN apontamentos_parada apt ON p.pr_id = apt.pr_id
    WHERE p.pr_data BETWEEN :start_date AND :end_date AND p.pr_setor_id = :setor_id
    """
    params = {'start_date': start_date, 'end_date': end_date, 'setor_id': setor_id}
    
    with banco.engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    if df.empty:
        return base_metrics

    df.fillna(0, inplace=True)
    
    tempo_planejado_producao = len(df[(df['pr_fechado'] != 1) & (df['cp_meta'] > 0)]) * 60
    total_parada_registrada = df['soma_parada_registrada'].sum()
    total_parada_disponibilidade = df['soma_parada_disponibilidade'].sum()

    denominador_disp = tempo_planejado_producao - total_parada_registrada
    tempo_operando = 0
    disponibilidade = 0
    if denominador_disp > 0:
        tempo_operando = denominador_disp - total_parada_disponibilidade
        disponibilidade = (tempo_operando / denominador_disp)

    total_parada_performance = df['soma_parada_performance'].sum()
    performance = 0
    if tempo_operando > 0:
        performance = ((tempo_operando - total_parada_performance) / tempo_operando)

    total_produzido = df['total_producao'].sum()
    total_refugo = df['total_refugo'].sum()
    qualidade = 0
    if total_produzido > 0:
        qualidade = ((total_produzido - total_refugo) / total_produzido)

    oee = disponibilidade * performance * qualidade

    horas_produtivas = denominador_disp / 60 if denominador_disp > 0 else 0
    produzido_por_hora = total_produzido / horas_produtivas if horas_produtivas > 0 else 0
    
    return {
        'availability': disponibilidade * 100,
        'performance': performance * 100,
        'quality': qualidade * 100,
        'oee': oee * 100,
        'total_produzido': total_produzido,
        'total_refugo': total_refugo,
        'horas_produtivas': horas_produtivas,
        'produzido_por_hora': produzido_por_hora,
    }

# =============================================================================
# LAYOUT
# =============================================================================

layout = dbc.Container([
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.Dropdown(id='setor-filter-setor-dash', placeholder='Selecione o Setor'),
                        lg=4, sm=12, className="mb-2 mb-lg-0"),
                dbc.Col(dcc.DatePickerSingle(
                    id='start-date-picker-setor-dash',
                    placeholder='Data Início',
                    date=datetime.now().date() - timedelta(days=7),
                    display_format='DD/MM/YYYY',
                    className="w-100"
                ), lg=4, sm=6, xs=12, className="mb-2 mb-sm-0"),
                dbc.Col(dcc.DatePickerSingle(
                    id='end-date-picker-setor-dash',
                    placeholder='Data Fim',
                    date=datetime.now().date(),
                    display_format='DD/MM/YYYY',
                    className="w-100"
                ), lg=4, sm=6, xs=12)
            ])
        ])
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            #html.H5("Visão Geral do Setor", className="text-center"),
            html.Div(id='setor-indicators-content')
        ], md=4),

        dbc.Col([
            #html.H5("Desempenho por Máquina", className="text-center"),
            html.Div(id='machine-info-content')
        ], md=4, style={'overflowY': 'auto', 'height': '930px'}),

        dbc.Col([
            #html.H5("Ordens de Produção Executadas", className="text-center"),
            html.Div(id='pcp-table-content')
        ], md=4, style={'overflowY': 'auto'}),
    ], align="stretch", className="flex-grow-1")
], fluid=True, className="d-flex flex-column vh-100")


# =============================================================================
# CALLBACKS
# =============================================================================

@app.callback(
    Output("setor-filter-setor-dash", "options"),
    Output("setor-filter-setor-dash", "value"),
    Input("setor-filter-setor-dash", "id")
)
def load_sectors_dashboard(_):
    banco = Banco()
    df_setores = banco.ler_tabela("setor")
    
    if df_setores.empty:
        return [], None
    
    setores = [{"label": row["setor_nome"], "value": row["setor_id"]} for _, row in df_setores.iterrows()]
    return setores, setores[0]["value"] if setores else None


@app.callback(
    Output('setor-indicators-content', 'children'),
    Output('machine-info-content', 'children'),
    Output('pcp-table-content', 'children'),
    [Input('setor-filter-setor-dash', 'value'),
     Input('start-date-picker-setor-dash', 'date'),
     Input('end-date-picker-setor-dash', 'date')]
)
def update_setor_dashboard(setor_id, start_date_str, end_date_str):
    if not all([setor_id, start_date_str, end_date_str]):
        return "Selecione um setor e o período.", "", ""

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    # --- Coluna 1: Indicadores do Setor ---
    metrics = calculate_oee_metrics_geral(start_date, end_date, setor_id)
    df_paradas_lv2 = get_stop_data_for_level(start_date, end_date, setor_id, 2)
    df_paradas_lv3 = get_stop_data_for_level(start_date, end_date, setor_id, 3)

    fig_paradas_lv2 = create_stop_bar_chart(df_paradas_lv2, "Principais Paradas Nível 2")
    fig_paradas_lv3 = create_stop_bar_chart(df_paradas_lv3, "Principais Paradas Nível 3")
    
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number", value=metrics['oee'], number={'suffix': "%"},
        title={'text': "OEE Global do Setor"},
        gauge={'axis': {'range': [None, 100]},
               'steps': [{'range': [0, 50], 'color': 'red'}, {'range': [50, 85], 'color': 'yellow'}, {'range': [85, 100], 'color': 'green'}],
               'bar': {'color': 'black'}}
    ))
    gauge_fig.update_layout(height=200, margin={'l': 10, 'r': 10, 't': 40, 'b': 10})

    indicators_content = html.Div([
        dbc.Card(dbc.CardBody([
            dcc.Graph(figure=gauge_fig, config={'displayModeBar': False}),
            html.Hr(className="my-2"),
            html.Div([
                dbc.Row([
                    dbc.Col(
                        html.Div([
                            html.P("Disponibilidade", className="mb-0 text-muted small"),
                            html.H5(f"{metrics['availability']:.2f}%", className="fw-bold")
                        ], className="text-center p-1 border rounded"),
                        md=4
                    ),
                    dbc.Col(
                        html.Div([
                            html.P("Performance", className="mb-0 text-muted small"),
                            html.H5(f"{metrics['performance']:.2f}%", className="fw-bold")
                        ], className="text-center p-1 border rounded"),
                        md=4
                    ),
                    dbc.Col(
                        html.Div([
                            html.P("Qualidade", className="mb-0 text-muted small"),
                            html.H5(f"{metrics['quality']:.2f}%", className="fw-bold")
                        ], className="text-center p-1 border rounded"),
                        md=4
                    ),
                ], className="mb-2 g-1"),
                
                html.Hr(className="my-2"),

                dbc.Row([
                    dbc.Col(html.P([html.B("Qtd Produzida: "), f"{metrics.get('total_produzido', 0):,.0f}".replace(',', '.')], className="mb-1 small text-nowrap"), md=6),
                    dbc.Col(html.P([html.B("Horas Produtivas: "), f"{metrics.get('horas_produtivas', 0):.2f}"], className="mb-1 small text-nowrap"), md=6),
                ]),
                dbc.Row([
                    dbc.Col(html.P([html.B("Total Refugo: "), f"{metrics.get('total_refugo', 0):,.0f}".replace(',', '.')], className="mb-0 small text-nowrap"), md=6),
                    dbc.Col(html.P([html.B("Produzido p/ Hora: "), f"{metrics.get('produzido_por_hora', 0):,.0f}".replace(',', '.')], className="mb-0 small text-nowrap"), md=6),
                ])
            ])
        ]), className="mb-2"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_paradas_lv2, config={'displayModeBar': False})), className="mb-2"),
        dbc.Card(dbc.CardBody(dcc.Graph(figure=fig_paradas_lv3, config={'displayModeBar': False}))),
    ])

    # --- Coluna 2: Informações das Máquinas ---
    df_machines = calculate_oee_for_all_machines_in_sector(start_date, end_date, setor_id)
    if not df_machines.empty:
        machine_cards_list = []
        for _, row in df_machines.iterrows():
            gauge_fig_machine = go.Figure(go.Indicator(
                mode="gauge+number",
                value=row['oee'],
                number={'suffix': "%", 'font': {'size': 24}},
                gauge={
                    'axis': {'range': [None, 100], 'tickwidth': 1},
                    'steps': [
                        {'range': [0, 50], 'color': 'red'},
                        {'range': [50, 85], 'color': 'yellow'},
                        {'range': [85, 100], 'color': 'green'}
                    ],
                    'bar': {'color': 'black'}
                }
            ))
            gauge_fig_machine.update_layout(
                height=100,
                margin=dict(l=10, r=10, t=10, b=10)
            )

            indicators = dbc.Row([
                dbc.Col([
                    html.P([html.B("Disponibilidade: "), f"{row['availability']:.1f}%"], className="mb-1"),
                    html.P([html.B("Performance: "), f"{row['performance']:.1f}%"], className="mb-1"),
                    html.P([html.B("Qualidade: "), f"{row['quality']:.1f}%"], className="mb-0"),
                ], md=6),
                dbc.Col([
                    html.P([html.B("Horas Produtivas: "), f"{row.get('horas_produtivas', 0):.2f}"], className="mb-1"),
                    html.P([html.B("Qtd Produzida: "), f"{row.get('total_produzido', 0):,.0f}".replace(',', '.')], className="mb-1"),
                    html.P([html.B("Total Refugo: "), f"{row.get('total_refugo', 0):,.0f}".replace(',', '.')], className="mb-0"),
                ], md=6, className="text-muted"),
            ], className="small")

            header_content = dbc.Row([
                dbc.Col(row['maquina_nome'], width="auto", className="fw-bold text-truncate"),
                dbc.Col(f"Meta: {row.get('total_meta', 0):,.0f}".replace(',', '.'), width="auto", className="text-muted small")
            ], justify="between", align="center", className="p-1")

            card = dbc.Card(
                [
                    dbc.CardHeader(header_content, className="p-0"),
                    dbc.CardBody(
                        dbc.Row(
                            [
                                dbc.Col(dcc.Graph(figure=gauge_fig_machine, config={'displayModeBar': False}), md=4),
                                dbc.Col(indicators, md=8, className="d-flex flex-column justify-content-center"),
                            ],
                            align="center",
                        )
                    ),
                ],
                className="mb-2",
                style={"height": "150px"}
            )
            machine_cards_list.append(card)

        machine_cards = html.Div(machine_cards_list)
    else:
        machine_cards = dbc.Alert("Sem dados de máquinas para o período.", color="warning")

    # --- Coluna 3: Tabela de PCP ---
    df_categories = get_category_summary_data(start_date, end_date, setor_id)
    
    third_column_content = []
    if not df_categories.empty:
        #third_column_content.append(html.H6("Produção por Categoria", className="text-center mb-2"))
        
        cards = []
        for _, row in df_categories.iterrows():
            card = dbc.Card(
                dbc.CardBody(
                    [
                        html.P(row['categoria_nome'], className="card-title text-center small mb-1 text-truncate"),
                        html.H5(f"{row['total_qtd_categoria']:,.0f}".replace(',', '.'), className="card-text text-center fw-bold")
                    ],
                    className="p-2"
                ),
                className="h-100"
            )
            cards.append(card)

        for i in range(0, len(cards), 5):
            row_of_cards = [dbc.Col(card, className="mb-2") for card in cards[i:i+5]]
            third_column_content.append(dbc.Row(row_of_cards, className="g-1"))
            
        third_column_content.append(html.Hr())

    df_pcp = get_product_summary_data(start_date, end_date, setor_id)
    if not df_pcp.empty:
        table_header = [html.Thead(html.Tr([html.Th("PCP"), html.Th("Produto"), html.Th("Qtd Produzida")]))]
        table_body = [html.Tbody([
            html.Tr([
                html.Td(row['pcp_pcp']),
                html.Td(row['produto_nome']),
                html.Td(f"{row['total_qtd']:.0f}")
            ]) for _, row in df_pcp.iterrows()
        ])]
        pcp_table = dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, size='sm')
        pcp_table_container = html.Div(pcp_table, style={'maxHeight': '750px', 'overflowY': 'auto'})
        third_column_content.append(pcp_table_container)
    else:
        pcp_table = dbc.Alert("Nenhuma ordem de produção encontrada.", color="info")
        third_column_content.append(pcp_table)
    
    pcp_table_content = html.Div(third_column_content)

    return indicators_content, machine_cards, pcp_table_content
