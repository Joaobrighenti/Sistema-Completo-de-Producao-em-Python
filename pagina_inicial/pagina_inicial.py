from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import dash
import pandas as pd
import json
from math import ceil
from datetime import datetime, timedelta, date
import plotly.graph_objects as go

from app import app
from banco_dados.banco import Banco, listar_lembretes


# Layout: 3 linhas
layout = dbc.Container([
    # Linha 0: Avisos/ Lembretes
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Avisos Recentes"),
                dbc.CardBody([html.Ul(id="home-avisos-list", className="mb-0")])
            ], className="shadow-sm"),
            width=12
        )
    ], className="mb-3"),

    # Linhas 1 e 2: OEE por setor (somente OEE global, velocímetro) em duas linhas responsivas
    dbc.Row(id="home-oee-row-1", className="g-2 mb-2"),
    dbc.Row(id="home-oee-row-2", className="g-2 mb-3"),

    # Linha 3: KPIs PCP (somente números) ocupando a linha inteira
    dbc.Row(id="home-pcp-row", className="row row-cols-xxl-5 row-cols-lg-3 row-cols-md-2 row-cols-1 g-3 mb-3"),

    # Linha 4: Cards Qualidade (somente os exibidos) ocupando a linha inteira
    dbc.Row(id="home-quality-row", className="row row-cols-xxl-6 row-cols-lg-3 row-cols-md-2 row-cols-1 g-2 mb-3")
], fluid=True)


@app.callback(
    [dash.Output("home-avisos-list", "children"),
     dash.Output("home-oee-row-1", "children"),
     dash.Output("home-oee-row-2", "children"),
     dash.Output("home-pcp-row", "children"),
     dash.Output("home-quality-row", "children")],
    dash.Input("url", "pathname")
)
def carregar_home(pathname: str):
    if pathname != "/":
        raise PreventUpdate

    hoje = date.today()
    inicio = hoje - timedelta(days=7)

    banco = Banco()

    # Avisos
    try:
        df_avisos = listar_lembretes(status="pendente")
        if df_avisos is None or df_avisos.empty:
            avisos_children = [html.Li("Sem avisos pendentes.")]
        else:
            avisos_children = [html.Li(f"{str(r.get('data',''))} - {str(r.get('lembrete','')).strip()}") for _, r in df_avisos.iterrows()]
    except Exception:
        avisos_children = [html.Li("Erro ao carregar avisos.")]

    # 1) OEE por setor (usa função existente para cálculo agregado por setor)
    try:
        from dashboards.dashboard_oee_geral import calculate_oee_metrics_geral
        df_setores = banco.ler_tabela('setor')
        oee_cols = []
        if not df_setores.empty:
            for _, setor in df_setores.iterrows():
                setor_id = setor['setor_id']
                setor_nome = setor['setor_nome']
                metrics = calculate_oee_metrics_geral(inicio, hoje, setor_id)
                gauge_fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=metrics.get('oee', 0),
                    number={'suffix': "%"},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'steps': [
                            {'range': [0, 50], 'color': 'red'},
                            {'range': [50, 85], 'color': 'yellow'},
                            {'range': [85, 100], 'color': 'green'}
                        ],
                        'threshold': {'line': {'color': "purple", 'width': 4}, 'thickness': 0.75, 'value': 85},
                        'bar': {'color': 'black'}
                    }
                ))
                # Título no CardHeader, gráfico mais compacto
                gauge_fig.update_layout(height=90, margin={'l': 3, 'r': 3, 't': 6, 'b': 0}, font={'size': 9})
                oee_cols.append(dbc.Col(
                    dbc.Card([
                        dbc.CardHeader(html.H6(setor_nome, className="mb-0 text-center")),
                        dbc.CardBody(dcc.Graph(figure=gauge_fig, config={'displayModeBar': False}), className="p-1")
                    ], className="w-100 h-100"),
                    className="d-flex"
                ))
        else:
            oee_cols.append(dbc.Col(html.P("Sem setores")))
    except Exception:
        oee_cols = [dbc.Col(html.P("Erro ao calcular OEE"))]

    # distribuir em duas linhas
    metade = ceil(len(oee_cols) / 2) if oee_cols else 0
    oee_row_1 = oee_cols[:metade]
    oee_row_2 = oee_cols[metade:]

    # 2) KPIs PCP (números) - usa funções do dashboard PCP
    try:
        from dashboards.dashboard_pcp import calcular_aderencia_programacao, calcular_pedidos_atraso
        df_aderencia = calcular_aderencia_programacao()
        agora = datetime.now()
        semana_atual = f"{agora.isocalendar().year}-S{str(agora.isocalendar().week).zfill(2)}"
        dados_semana = df_aderencia[df_aderencia['ano_semana'] == semana_atual]
        if not dados_semana.empty:
            total_planejado = int(dados_semana['qtd_planejada'].iloc[0])
            total_executado = int(dados_semana['qtd_baixada'].iloc[0])
            total_geral_baixas = int(dados_semana['total_geral_baixas'].iloc[0]) if 'total_geral_baixas' in dados_semana else total_executado
            eficiencia_atual = float(dados_semana['aderencia'].iloc[0])
            producao_sem_pcp = total_geral_baixas - total_executado
            kpi_quantidade = (producao_sem_pcp / total_geral_baixas * 100) if total_geral_baixas > 0 else 0
        else:
            total_planejado = total_executado = total_geral_baixas = 0
            eficiencia_atual = kpi_quantidade = 0
        df_atraso = calcular_pedidos_atraso()
        qtd_atrasos = 0 if df_atraso is None or df_atraso.empty else len(df_atraso)

        def metric_card(title, value, color_class):
            return dbc.Card(
                dbc.CardBody([
                    html.H5(title, className="mb-1"),
                    html.H2(value, className=f"mb-0 {color_class}")
                ]), className="shadow-sm"
            )

        pcp_row = [
            dbc.Col(metric_card("Pedidos em Atraso", f"{qtd_atrasos:,}".replace(',', '.'), 'text-danger')),
            dbc.Col(metric_card("Total Planejado", f"{total_planejado:,}".replace(',', '.'), 'text-success')),
            dbc.Col(metric_card("Total Executado", f"{total_executado:,}".replace(',', '.'), 'text-warning')),
            dbc.Col(metric_card("Aderência", f"{eficiencia_atual:.1f}%", 'text-info')),
            dbc.Col(metric_card("KPI Quantidade", f"{kpi_quantidade:.1f}%", 'text-danger'))
        ]
    except Exception:
        pcp_row = [dbc.Col(html.P("Erro ao calcular KPIs PCP"))]

    # 3) Cards de Qualidade (mesmos do dashboard de qualidade)
    try:
        from dashboards.dashboard_quali import carregar_dados_brutos_inspecao, carregar_dados_pcp_e_retrabalho
        df_bruto = carregar_dados_brutos_inspecao()
        df_pcp_retrabalho = carregar_dados_pcp_e_retrabalho()
        # período: ano corrente
        if not df_bruto.empty:
            df_bruto['data'] = pd.to_datetime(df_bruto['data'], errors='coerce')
            dfb = df_bruto[(df_bruto['data'].dt.date >= inicio) & (df_bruto['data'].dt.date <= hoje)]
        else:
            dfb = pd.DataFrame()
        total_nao_conforme = 0
        total_inspecionado = 0
        if not dfb.empty:
            # checklist é JSON; contamos nao_conforme por quantidade quando disponível
            def extrair(df):
                registros = []
                for _, r in df.iterrows():
                    chk = r.get('checklist')
                    try:
                        while isinstance(chk, str):
                            chk = json.loads(chk)
                    except Exception:
                        chk = None
                    if isinstance(chk, dict):
                        for _, det in chk.items():
                            if isinstance(det, dict):
                                status = det.get('status')
                                quantidade = det.get('quantidade', 0)
                            else:
                                status = det
                                quantidade = 1 if status == 'nao_conforme' else 0
                            registros.append({'status': status, 'quantidade': quantidade, 'qtd_inspecionada': r.get('qtd_inspecionada', 0)})
                return pd.DataFrame(registros)
            df_proc = extrair(dfb)
            if not df_proc.empty:
                total_nao_conforme = int(df_proc[df_proc['status'] == 'nao_conforme']['quantidade'].sum())
                total_inspecionado = int(dfb.drop_duplicates(subset=['id'])['qtd_inspecionada'].sum())
        taxa_conformidade = ((total_inspecionado - total_nao_conforme) / total_inspecionado * 100) if total_inspecionado > 0 else 100

        # retrabalho
        num_retrabalhos = num_reprovas = num_aprov_concessao = 0
        valor_reprovas = 0.0
        if not df_pcp_retrabalho.empty:
            df_pcp_retrabalho['pcp_emissao'] = pd.to_datetime(df_pcp_retrabalho['pcp_emissao'], errors='coerce')
            dfp = df_pcp_retrabalho[(df_pcp_retrabalho['pcp_emissao'].dt.date >= inicio) & (df_pcp_retrabalho['pcp_emissao'].dt.date <= hoje)]
            if not dfp.empty:
                num_retrabalhos = int(dfp[dfp['status'] == 1].shape[0])
                df_rep = dfp[dfp['status'] == 3]
                num_reprovas = int(df_rep.shape[0])
                valor_reprovas = float((df_rep['quantidade_nao_conforme'] * df_rep['valor']).sum())
                num_aprov_concessao = int(dfp[dfp['status'] == 4].shape[0])

        def qual_card(titulo, valor, sub=None):
            # Padroniza o conteúdo principal para ser igual ao metric_card
            main_content = [
                html.H5(titulo, className="mb-1"),
                html.H2(valor, className="mb-0 text-dark"),
            ]

            # Envolve o conteúdo em divs e usa flexbox para alinhar
            body_elements = [html.Div(main_content)]
            if sub:
                body_elements.append(html.Small(sub, className="text-muted"))
            
            # Usa d-flex para forçar o alinhamento e a altura igual
            return dbc.Card(dbc.CardBody(body_elements, className="d-flex flex-column justify-content-between"), className="shadow-sm h-100")

        qual_row = [
            dbc.Col(qual_card("Total Não Conforme", f"{total_nao_conforme:,.0f}".replace(',', '.'))),
            dbc.Col(qual_card("Total Inspecionado", f"{total_inspecionado:,.0f}".replace(',', '.'))),
            dbc.Col(qual_card("Taxa de Conformidade", f"{taxa_conformidade:.2f}%")),
            dbc.Col(qual_card("Número Retrabalhos", f"{num_retrabalhos:,.0f}".replace(',', '.'))),
            dbc.Col(qual_card("Número Reprovas", f"{num_reprovas:,.0f}".replace(',', '.'), sub=f"R$ {valor_reprovas:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.')),),
            dbc.Col(qual_card("Sob Concessão", f"{num_aprov_concessao:,.0f}".replace(',', '.')))
        ]
    except Exception:
        qual_row = [dbc.Col(html.P("Erro ao calcular Qualidade"))]

    return avisos_children, oee_row_1, oee_row_2, pcp_row, qual_row

