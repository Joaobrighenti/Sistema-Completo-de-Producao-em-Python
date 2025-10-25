from dash import html, dcc, Input, Output, State, MATCH, callback_context, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from app import app
from banco_dados.banco import Banco
from sqlalchemy import text
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.graph_objects as go

def get_stop_data_lv2_for_sector(start_date, end_date, setor_id, maquina_id=None):
    banco = Banco()
    df_razao = banco.ler_tabela('razao')
    if df_razao.empty:
        return pd.DataFrame()

    query = """
        SELECT ap.ap_tempo, ap.ap_lv2
        FROM apontamento ap
        JOIN producao p ON ap.ap_pr = p.pr_id
        WHERE p.pr_data BETWEEN :start_date AND :end_date
          AND p.pr_setor_id = :setor_id
          AND ap.ap_lv2 IS NOT NULL
          AND ap.ap_tempo > 0
    """
    params = {'start_date': start_date, 'end_date': end_date, 'setor_id': setor_id}

    if maquina_id:
        query += " AND p.pr_maquina_id = :maquina_id"
        params['maquina_id'] = maquina_id

    with banco.engine.connect() as conn:
        df_apontamento = pd.read_sql(text(query), conn, params=params)

    if df_apontamento.empty:
        return pd.DataFrame()

    df_merged = pd.merge(
        df_apontamento,
        df_razao[['ra_id', 'ra_razao']],
        left_on='ap_lv2',
        right_on='ra_id',
        how='inner'
    )

    if df_merged.empty:
        return pd.DataFrame()
        
    df_grouped = df_merged.groupby(['ra_id', 'ra_razao'])['ap_tempo'].sum().reset_index()
    df_grouped.rename(columns={'ap_tempo': 'total_tempo'}, inplace=True)
        
    return df_grouped

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

def create_stop_bar_chart(df, title):
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=title,
            xaxis_visible=False,
            yaxis_visible=False,
            annotations=[dict(text="Sem dados", xref="paper", yref="paper", showarrow=False, font=dict(size=12))],
            height=250,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        return fig
    
    df = df.sort_values(by='total_tempo', ascending=False)
    fig = go.Figure(go.Bar(
        x=df['total_tempo'], y=df['ra_razao'], orientation='h',
        text=df['total_tempo'], textposition='inside', marker_color='red'
    ))
    fig.update_layout(
        title=title, xaxis_title=None, yaxis_title=None, height=250,
        margin=dict(l=10, r=10, t=30, b=10), yaxis={'autorange': 'reversed'}, font=dict(size=10)
    )
    return fig

def calculate_oee_for_all_machines_in_sector(start_date, end_date, setor_id):
    banco = Banco()
    query = """
    WITH 
        apontamentos_producao AS (
            SELECT 
                atp_producao as pr_id,
                SUM(atp_qtd) as total_producao,
                SUM(atp_refugos) as total_refugo,
                SUM(COALESCE(atp_custo, 0)) AS soma_atp_custo
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
        COUNT(CASE WHEN p.pr_fechado != 1 AND cp.cp_meta > 0 THEN p.pr_id END) * 60 AS tempo_planejado_producao,
        SUM(COALESCE(apt.soma_parada_registrada, 0)) AS total_parada_registrada,
        SUM(COALESCE(apt.soma_parada_disponibilidade, 0)) AS total_parada_disponibilidade,
        SUM(COALESCE(apt.soma_parada_performance, 0)) AS total_parada_performance,
        SUM(COALESCE(ap.total_producao, 0)) AS total_produzido,
        SUM(COALESCE(ap.total_refugo, 0)) AS total_refugo,
        SUM((m.maquina_custo / 60) * (COALESCE(apt.soma_parada_disponibilidade, 0) + COALESCE(apt.soma_parada_performance, 0))) as custo_oee,
        SUM(COALESCE(ap.soma_atp_custo, 0)) as custo_extra
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
        # Disponibilidade
        denominador_disp = row['tempo_planejado_producao'] - row['total_parada_registrada']
        tempo_operando = 0
        availability = 0
        if denominador_disp > 0:
            tempo_operando = denominador_disp - row['total_parada_disponibilidade']
            availability = (tempo_operando / denominador_disp)

        # Performance
        performance = 0
        if tempo_operando > 0:
            performance = ((tempo_operando - row['total_parada_performance']) / tempo_operando)

        # Qualidade
        quality = 0
        if row['total_produzido'] > 0:
            quality = ((row['total_produzido'] - row['total_refugo']) / row['total_produzido'])

        oee = availability * performance * quality

        horas_produtivas = denominador_disp / 60

        results.append({
            'maquina_id': row['pr_maquina_id'],
            'maquina_nome': row['maquina_nome'],
            'availability': availability * 100,
            'performance': performance * 100,
            'quality': quality * 100,
            'oee': oee * 100,
            'horas_produtivas': horas_produtivas,
            'total_qtd': row['total_produzido'],
            'total_refugo': row['total_refugo'],
            'custo_oee': row['custo_oee'],
            'custo_extra': row['custo_extra']
        })
        
    return pd.DataFrame(results)

def calculate_oee_metrics_geral(start_date, end_date, setor_id, maquina_id=None):
    base_metrics = {
        'availability': 0, 'performance': 0, 'quality': 0, 'oee': 0, 
        'total_qtd': 0, 'total_refugo': 0, 'status_ok': 0, 'status_faltando': 0,
        'status_errado': 0, 'status_sem_apontamento': 0, 'custo_oee': 0, 'custo_extra': 0,
        'horas_produtivas': 0, 'produzido_por_hora': 0
    }
    if not start_date or not end_date:
        return base_metrics

    banco = Banco()
    
    query = """
    WITH 
        apontamentos_producao AS (
            SELECT 
                atp_producao as pr_id,
                SUM(atp_qtd) as total_producao,
                SUM(atp_refugos) as total_refugo,
                SUM(COALESCE(atp_custo, 0)) AS soma_atp_custo
            FROM apontamento_produto
            GROUP BY atp_producao
        ),
        apontamentos_parada AS (
            SELECT 
                ap_pr as pr_id,
                SUM(ap_tempo) as total_tempo,
                SUM(CASE WHEN r.ra_tipo = 'PARADA REGISTRADA' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_registrada,
                SUM(CASE WHEN r.ra_tipo = 'DISPONIBILIDADE' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_disponibilidade,
                SUM(CASE WHEN r.ra_tipo = 'PERFORMANCE' THEN ap.ap_tempo ELSE 0 END) AS soma_parada_performance
            FROM apontamento ap
            JOIN razao r ON ap.ap_lv1 = r.ra_id
            GROUP BY ap_pr
        )
    SELECT
        p.pr_fechado,
        cp.cp_meta,
        m.maquina_custo,
        ap.total_producao,
        ap.total_refugo,
        ap.soma_atp_custo,
        apt.total_tempo,
        apt.soma_parada_registrada,
        apt.soma_parada_disponibilidade,
        apt.soma_parada_performance
    FROM producao p
    LEFT JOIN categoria_produto cp ON p.pr_categoria_produto_id = cp.cp_id
    LEFT JOIN maquina m ON p.pr_maquina_id = m.maquina_id
    LEFT JOIN apontamentos_producao ap ON p.pr_id = ap.pr_id
    LEFT JOIN apontamentos_parada apt ON p.pr_id = apt.pr_id
    WHERE p.pr_data BETWEEN :start_date AND :end_date
    """

    params = {'start_date': start_date, 'end_date': end_date}
    if setor_id:
        query += " AND p.pr_setor_id = :setor_id"
        params['setor_id'] = setor_id

    if maquina_id:
        query += " AND p.pr_maquina_id = :maquina_id"
        params['maquina_id'] = maquina_id

    with banco.engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    if df.empty:
        return base_metrics

    # Calculate Status
    def get_status(row):
        if row['pr_fechado'] == 1:
            return 'FABRICA FECHADA'
        if pd.isna(row['total_producao']):
             return 'SEM APONTAMENTO'
        
        meta_por_hora = row['cp_meta']
        if pd.isna(meta_por_hora) or meta_por_hora == 0:
            return 'ERRADO'

        meta_por_min = meta_por_hora / 60.0
        tempo_gasto_produzindo = row['total_producao'] / meta_por_min
        
        tempo_parada = row['total_tempo']
        if pd.isna(tempo_parada):
            tempo_parada = 0
            
        saldo_minutos = 60 - tempo_gasto_produzindo - tempo_parada
        saldo_minutos_int = int(saldo_minutos)
        
        if saldo_minutos_int > 0:
            return 'FALTANDO'
        elif saldo_minutos_int == 0:
            return 'OK'
        else:
            return 'ERRADO'

    df['status_apontamento'] = df.apply(get_status, axis=1)
    status_counts = df['status_apontamento'].value_counts()

    # Calculate OEE metrics
    numeric_cols_to_fill = [
        'cp_meta', 'maquina_custo', 'total_producao', 'total_refugo', 'soma_atp_custo',
        'total_tempo', 'soma_parada_registrada', 'soma_parada_disponibilidade', 'soma_parada_performance'
    ]
    for col in numeric_cols_to_fill:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Custo OEE
    custo_oee = ((df['maquina_custo'] / 60) * (df['soma_parada_disponibilidade'] + df['soma_parada_performance'])).sum()

    # Custo Extra
    custo_extra = df['soma_atp_custo'].sum()

    # Disponibilidade
    tempo_planejado_producao = len(df[(df['pr_fechado'] != 1) & (df['cp_meta'] > 0)]) * 60
    total_parada_registrada = df['soma_parada_registrada'].sum()
    total_parada_disponibilidade = df['soma_parada_disponibilidade'].sum()

    denominador_disp = tempo_planejado_producao - total_parada_registrada
    tempo_operando = 0
    disponibilidade = 0
    if denominador_disp > 0:
        tempo_operando = denominador_disp - total_parada_disponibilidade
        disponibilidade = (tempo_operando / denominador_disp)

    # Performance
    total_parada_performance = df['soma_parada_performance'].sum()
    performance = 0
    if tempo_operando > 0:
        performance = ((tempo_operando - total_parada_performance) / tempo_operando)

    # Qualidade
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
        'horas_produtivas': horas_produtivas,
        'produzido_por_hora': produzido_por_hora,
        'total_qtd': total_produzido,
        'total_refugo': total_refugo,
        'status_ok': status_counts.get('OK', 0),
        'status_faltando': status_counts.get('FALTANDO', 0),
        'status_errado': status_counts.get('ERRADO', 0),
        'status_sem_apontamento': status_counts.get('SEM APONTAMENTO', 0),
        'custo_oee': custo_oee,
        'custo_extra': custo_extra
    }

def get_weekly_production_data(end_date, setor_id=None):
    banco = Banco()
    # The range should start 5 weeks before the end date's week start
    end_of_week = end_date
    start_of_week = end_of_week - timedelta(days=end_of_week.weekday())
    start_date = start_of_week - timedelta(weeks=4) # 5 weeks in total including the current one

    query = """
        SELECT 
            p.pr_data,
            ap.atp_qtd
        FROM producao p
        JOIN apontamento_produto ap ON p.pr_id = ap.atp_producao
        WHERE p.pr_data BETWEEN :start_date AND :end_date
          AND ap.atp_qtd > 0
    """
    params = {'start_date': start_date, 'end_date': end_date}
    if setor_id:
        query += " AND p.pr_setor_id = :setor_id"
        params['setor_id'] = setor_id
    
    with banco.engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)

    if df.empty:
        return pd.DataFrame()

    df['pr_data'] = pd.to_datetime(df['pr_data'])
    df['week'] = df['pr_data'].dt.isocalendar().week
    df['year'] = df['pr_data'].dt.isocalendar().year
    
    df_weekly = df.groupby(['year', 'week'])['atp_qtd'].sum().reset_index()
    # Ensure we only have the last 5 entries if there are more
    df_weekly = df_weekly.sort_values(['year', 'week'], ascending=False).head(5).sort_values(['year', 'week'])
    
    df_weekly['week_year'] = df_weekly['year'].astype(str) + '-S' + df_weekly['week'].astype(str).str.zfill(2)
    
    return df_weekly

def create_weekly_production_chart(df):
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title="Produção Semanal (Últimas 5 Semanas)",
            xaxis_visible=False,
            yaxis_visible=False,
            annotations=[dict(text="Sem dados", xref="paper", yref="paper", showarrow=False, font=dict(size=12))],
            height=250,
            margin=dict(l=10, r=10, t=30, b=10)
        )
        return fig
    
    df = df.sort_values(by=['year', 'week'], ascending=True)

    fig = go.Figure(go.Bar(
        x=df['atp_qtd'], 
        y=df['week_year'],
        orientation='h',
        text=df['atp_qtd'].apply(lambda x: f'{x:,.0f}'.replace(',', '.')), 
        textposition='auto',
        marker_color='blue'
    ))
    fig.update_layout(
        title="Produção Semanal (Últimas 5 Semanas)",
        xaxis_title="Quantidade Produzida",
        yaxis_title="Semana",
        font=dict(size=10),
        height=250,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis={'autorange': 'reversed', 'automargin': True}
    )
    return fig


layout = dbc.Container([
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.DatePickerRange(
                    id='geral-date-picker-range',
                    start_date=date.today() - timedelta(days=7),
                    end_date=date.today(),
                    display_format='DD/MM/YYYY',
                ), lg=4, md=6, xs=12),
            ])
        ])
    ], className="mb-4"),
    dbc.Row(id='geral-oee-content', className="g-3"),
    dbc.Modal([
        dbc.ModalHeader(id='machine-modal-header'),
        dbc.ModalBody(id='machine-modal-body'),
        dbc.ModalFooter(dbc.Button("Fechar", id="close-machine-modal", className="ms-auto", n_clicks=0))
    ], id='machine-detail-modal', size='xl', is_open=False)
], fluid=True)

@app.callback(
    Output('geral-oee-content', 'children'),
    [Input('geral-date-picker-range', 'start_date'),
     Input('geral-date-picker-range', 'end_date')]
)
def update_geral_oee_dashboard(start_date_str, end_date_str):
    if not start_date_str or not end_date_str:
        return []

    start_date = datetime.strptime(start_date_str.split('T')[0], '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str.split('T')[0], '%Y-%m-%d').date()
    
    banco = Banco()
    df_setores = banco.ler_tabela('setor')
    
    cols = []
    if df_setores.empty:
        cols.append(dbc.Col(html.P("Nenhum setor encontrado.")))
    else:
        for index, setor in df_setores.iterrows():
            setor_id = setor['setor_id']
            setor_nome = setor['setor_nome']
            
            metrics = calculate_oee_metrics_geral(start_date, end_date, setor_id)
            
            gauge_fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=metrics['oee'],
                number={'suffix': "%"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'steps': [
                        {'range': [0, 50], 'color': 'red'},
                        {'range': [50, 85], 'color': 'yellow'},
                        {'range': [85, 100], 'color': 'green'}
                    ],
                    'threshold': {
                        'line': {'color': "purple", 'width': 4},
                        'thickness': 0.75,
                        'value': 85
                    },
                    'bar': {'color': 'black'}
                }
            ))
            gauge_fig.update_layout(height=150, margin={'l': 5, 'r': 5, 't': 25, 'b': 5}, font={'size': 10})
            
            df_weekly = get_weekly_production_data(end_date, setor_id)
            fig_weekly = create_weekly_production_chart(df_weekly)
            fig_lv2 = create_stop_bar_chart(get_stop_data_lv2_for_sector(start_date, end_date, setor_id), f"Paradas Nível 2 - {setor_nome}")
            
            card_content = [
                dcc.Graph(figure=gauge_fig, config={'displayModeBar': False}),
                dbc.CardBody([
                    html.P(f"Disponibilidade: {metrics['availability']:.2f}%", className="card-text small"),
                    html.P(f"Performance: {metrics['performance']:.2f}%", className="card-text small"),
                    html.P(f"Qualidade: {metrics['quality']:.2f}%", className="card-text small"),
                    html.Hr(className="my-1"),
                    dbc.Button(
                        "Status Apontamentos",
                        id={'type': 'collapse-button', 'index': setor_id},
                        color="secondary",
                        size="sm",
                        className="w-100 mb-1"
                    ),
                    dbc.Collapse(
                        [
                            html.P(f"Apont. OK: {metrics.get('status_ok', 0)}", className="card-text small"),
                            html.P(f"Apont. Faltando: {metrics.get('status_faltando', 0)}", className="card-text small"),
                            html.P(f"Apont. Errado: {metrics.get('status_errado', 0)}", className="card-text small"),
                            html.P(f"Sem Apontamento: {metrics.get('status_sem_apontamento', 0)}", className="card-text small"),
                        ],
                        id={'type': 'status-collapse', 'index': setor_id},
                        is_open=False,
                    ),
                    html.Hr(className="my-1"),
                    dbc.Button(
                        "Paradas Nível 2",
                        id={'type': 'parada-collapse-button', 'index': setor_id},
                        color="info",
                        size="sm",
                        className="w-100 mb-1"
                    ),
                    dbc.Collapse(
                        dcc.Graph(figure=fig_lv2, config={'displayModeBar': False}),
                        id={'type': 'parada-collapse', 'index': setor_id},
                        is_open=False,
                    ),
                    html.Hr(className="my-1"),
                    dbc.Button(
                        "Produção Semanal",
                        id={'type': 'semanal-collapse-button', 'index': setor_id},
                        color="primary",
                        size="sm",
                        className="w-100 mb-1"
                    ),
                    dbc.Collapse(
                        dcc.Graph(figure=fig_weekly, config={'displayModeBar': False}),
                        id={'type': 'semanal-collapse', 'index': setor_id},
                        is_open=False,
                    ),
                    html.Hr(className="my-1"),
                    html.P(f"Horas Produtivas: {metrics.get('horas_produtivas', 0):.2f}", className="card-text small"),
                    dbc.Row([
                        dbc.Col(html.P(f"Total Produzido: {int(metrics.get('total_qtd', 0)):,}".replace(',', '.'), className="mb-0 card-text small"), width="auto"),
                        dbc.Col(html.P(f"{int(metrics.get('produzido_por_hora', 0)):,} p/h".replace(',', '.'), className="mb-0 card-text small"), width="auto")
                    ], justify="between"),
                    html.P(f"Total Refugo: {int(metrics.get('total_refugo', 0)):,}".replace(',', '.'), className="card-text small"),
                    html.Hr(className="my-1"),
                    html.P(f"Custo OEE: R$ {metrics['custo_oee']:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.'), className="card-text small fw-bold text-danger"),
                    html.P(f"Custo Extra: R$ {metrics['custo_extra']:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.'), className="card-text small fw-bold text-danger"),
                ], className="p-2")
            ]
            
            card = dbc.Card(card_content, color="light", outline=True)
            
            header = dbc.Row([
                dbc.Col(setor_nome, width='auto', className="p-1 text-center small fw-bold"),
                dbc.Col(dbc.Button(html.I(className="fa fa-search"), id={'type': 'open-machine-modal-btn', 'index': setor_id}, color="link", size="sm", className="p-0"), width='auto')
            ], justify="center", align="center")

            cols.append(dbc.Col(dbc.Card([dbc.CardHeader(header, className="p-1"), dbc.CardBody(card, className="p-0")]),
                            xl=2, lg=3, md=4, sm=6, xs=12))
        
    return cols

@app.callback(
    [Output('machine-detail-modal', 'is_open'),
     Output('machine-modal-header', 'children'),
     Output('machine-modal-body', 'children')],
    [Input({'type': 'open-machine-modal-btn', 'index': ALL}, 'n_clicks'),
     Input('close-machine-modal', 'n_clicks')],
    [State('geral-date-picker-range', 'start_date'),
     State('geral-date-picker-range', 'end_date'),
     State('machine-detail-modal', 'is_open')],
    prevent_initial_call=True
)
def handle_machine_modal(open_clicks, close_click, start_date_str, end_date_str, is_open):
    ctx = callback_context
    if not ctx.triggered or not ctx.triggered_id:
        raise PreventUpdate

    triggered_id = ctx.triggered_id

    if triggered_id == 'close-machine-modal':
        return False, "", ""

    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'open-machine-modal-btn':
        if not ctx.triggered[0]['value']:
            raise PreventUpdate
            
        setor_id = triggered_id['index']
        start_date = datetime.strptime(start_date_str.split('T')[0], '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str.split('T')[0], '%Y-%m-%d').date()
        
        banco = Banco()
        df_setor = banco.ler_tabela('setor')
        setor_nome = df_setor.query(f'setor_id == {setor_id}')['setor_nome'].iloc[0]
        
        # Performance: Use the new optimized function
        df_metrics = calculate_oee_for_all_machines_in_sector(start_date, end_date, setor_id)
        
        if df_metrics.empty:
            return True, f"Detalhes por Máquina - {setor_nome}", html.P("Nenhuma máquina ou dados de produção encontrados para este setor no período selecionado.")
            
        modal_body_content = []
        for _, metrics in df_metrics.iterrows():
            maquina_id = metrics['maquina_id']
            maquina_nome = metrics['maquina_nome']
            
            # Performance: Get stop data for the specific machine
            fig_lv2 = create_stop_bar_chart(get_stop_data_lv2_for_sector(start_date, end_date, setor_id, maquina_id), f"Paradas - {maquina_nome}")

            df_summary = get_product_summary_data(start_date, end_date, setor_id, maquina_id)
            
            summary_table_component = html.Div("Sem dados de produção detalhada.")
            if not df_summary.empty:
                total_qtd = df_summary['total_qtd'].sum()
                total_refugo = df_summary['total_refugo'].sum()

                rows = [html.Tr([
                    html.Td(row['pcp_pcp']),
                    html.Td(row['produto_nome']),
                    html.Td(f"{row['total_qtd']:.0f}"),
                    html.Td(f"{row['total_refugo']:.0f}"),
                    html.Td(f"{row['pcp_qtd']:.0f}"),
                    html.Td(f"{row.get('horas_gastas', 0):.2f}"),
                    html.Td(f"{row.get('horas_previstas', 0):.2f}"),
                ]) for _, row in df_summary.iterrows()]
                
                total_row = html.Tr([
                    html.Td("TOTAL", colSpan=2, style={'fontWeight': 'bold'}),
                    html.Td(f"{total_qtd:.0f}", style={'fontWeight': 'bold'}),
                    html.Td(f"{total_refugo:.0f}", style={'fontWeight': 'bold'}),
                    html.Td(""),
                    html.Td(""),
                    html.Td(""),
                ])

                summary_table_component = html.Div(
                    dbc.Table([
                        html.Thead(html.Tr([html.Th("PCP"), html.Th("Produto"), html.Th("Qtd"), html.Th("Refugo"), html.Th("Qtd PCP"), html.Th("Horas Gastas"), html.Th("Horas Previstas")])),
                        html.Tbody(rows + [total_row])
                    ], bordered=True, striped=True, hover=True, size='sm'),
                    style={'maxHeight': '200px', 'overflowY': 'auto', 'fontSize': '0.8rem'}
                )

            gauge_fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=metrics['oee'],
                number={'suffix': "%", 'font': {'size': 24}},
                title={'text': maquina_nome, 'font': {'size': 14}},
                gauge={'axis': {'range': [None, 100]}, 'bar': {'color': 'black'},
                       'steps': [{'range': [0, 50], 'color': 'red'}, {'range': [50, 85], 'color': 'yellow'}, {'range': [85, 100], 'color': 'green'}]}
            ))
            gauge_fig.update_layout(height=150, margin={'l': 15, 'r': 15, 't': 40, 'b': 15})

            col_content = dbc.Col([
                dbc.Card([
                    dbc.CardHeader(dcc.Graph(figure=gauge_fig, config={'displayModeBar': False}), className="p-0"),
                    dbc.CardBody([
                        html.P(f"Disponibilidade: {metrics['availability']:.2f}%", className="card-text small"),
                        html.P(f"Performance: {metrics['performance']:.2f}%", className="card-text small"),
                        html.P(f"Qualidade: {metrics['quality']:.2f}%", className="card-text small"),
                        html.Hr(className="my-1"),
                        dcc.Graph(figure=fig_lv2, config={'displayModeBar': False}),
                        html.Hr(className="my-1"),
                        dbc.Button(
                            "Produção Detalhada",
                            id={'type': 'summary-collapse-button', 'index': maquina_id},
                            color="success",
                            size="sm",
                            className="w-100 mb-1"
                        ),
                        dbc.Collapse(
                            summary_table_component,
                            id={'type': 'summary-collapse', 'index': maquina_id},
                            is_open=False,
                        ),
                        html.Hr(className="my-1"),
                        html.P(f"Horas Produtivas: {metrics.get('horas_produtivas', 0):.2f}", className="card-text small"),
                        html.P(f"Total Produzido: {int(metrics['total_qtd']):,}".replace(',', '.'), className="card-text small"),
                        html.P(f"Total Refugo: {int(metrics['total_refugo']):,}".replace(',', '.'), className="card-text small"),
                        html.Hr(className="my-1"),
                        html.P(f"Custo OEE: R$ {metrics['custo_oee']:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.'), className="card-text small fw-bold text-danger"),
                        html.P(f"Custo Extra: R$ {metrics['custo_extra']:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.'), className="card-text small fw-bold text-danger"),
                    ], className="p-2")
                ], color="dark", outline=True) # Styling: Added outline
            ], width=4)
            modal_body_content.append(col_content)
        
        return True, f"Detalhes por Máquina - {setor_nome}", dbc.Row(modal_body_content, className="g-3")

    return is_open, "", ""

@app.callback(
    Output({'type': 'status-collapse', 'index': MATCH}, 'is_open'),
    Input({'type': 'collapse-button', 'index': MATCH}, 'n_clicks'),
    State({'type': 'status-collapse', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True
)
def toggle_collapse(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output({'type': 'parada-collapse', 'index': MATCH}, 'is_open'),
    Input({'type': 'parada-collapse-button', 'index': MATCH}, 'n_clicks'),
    State({'type': 'parada-collapse', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True
)
def toggle_parada_collapse(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output({'type': 'semanal-collapse', 'index': MATCH}, 'is_open'),
    Input({'type': 'semanal-collapse-button', 'index': MATCH}, 'n_clicks'),
    State({'type': 'semanal-collapse', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True
)
def toggle_semanal_collapse(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output({'type': 'summary-collapse', 'index': MATCH}, 'is_open'),
    Input({'type': 'summary-collapse-button', 'index': MATCH}, 'n_clicks'),
    State({'type': 'summary-collapse', 'index': MATCH}, 'is_open'),
    prevent_initial_call=True
)
def toggle_summary_collapse(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open
