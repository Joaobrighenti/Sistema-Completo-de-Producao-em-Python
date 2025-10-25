from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from banco_dados.banco import Banco, engine
import json
from datetime import date
from io import StringIO
from app import app

banco = Banco()

def carregar_dados_pcp_e_retrabalho():
    try:
        # Subconsulta para obter o valor mais recente de cada produto
        query = """
        WITH LatestValor AS (
            SELECT
                vp.produto_id,
                vp.valor,
                ROW_NUMBER() OVER(PARTITION BY vp.produto_id ORDER BY vp.data DESC) as rn
            FROM valor_produto vp
        )
        SELECT
            p.pcp_id, p.pcp_emissao, p.pcp_retrabalho, p.pcp_produto_id,
            ar.quantidade_nao_conforme, ar.id as apontamento_id, ar.status,
            lv.valor
        FROM pcp p
        LEFT JOIN apontamento_retrabalho ar ON p.pcp_id = ar.pcp_id
        LEFT JOIN LatestValor lv ON p.pcp_produto_id = lv.produto_id AND lv.rn = 1
        """
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if not df.empty:
            df['pcp_emissao'] = pd.to_datetime(df['pcp_emissao'], errors='coerce')
            df['pcp_retrabalho'] = pd.to_numeric(df['pcp_retrabalho'], errors='coerce')
            df['quantidade_nao_conforme'] = pd.to_numeric(df['quantidade_nao_conforme'], errors='coerce').fillna(0)
            df['status'] = pd.to_numeric(df['status'], errors='coerce')
            df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0)

        return df
    except Exception as e:
        print(f"Erro ao carregar dados de PCP e retrabalho: {e}")
        return pd.DataFrame()

# Itens do Checklist por tipo de produto - copiados para evitar import circular
checklist_items_por_produto = {
    "Pote e Copo": {
        "pote_copo_dimensoes": "Dimensões (Diâmetro, comprimento e altura)",
        "pote_copo_selagem": "Selagem (Fundo e Lateral)",
        "pote_copo_resistencia_vazamento": "Resistência à vazamento",
        "pote_copo_ausencia_defeitos": "Ausência de amassados, rasgos e deformações",
        "pote_copo_impressao": "Impressão nítida e sem borrões",
        "pote_copo_limpeza": "Sem sujidades, contaminações ou mal odor",
        "pote_copo_colagem": "Colagem adequada sem falhas ou excessos",
        "pote_copo_empilhamento": "Suporta empilhamento especificado",
    },
    "Chapas Impressas": {
        "chapas_impressas_cromia": "Cromia (encaixe de cores)",
        "chapas_impressas_dimensoes": "Dimensões (Largura e comprimento)",
        "chapas_impressas_verificacao_visual": "Verificação visual",
    },
    "Chapas Acopladas": {
        "chapas_acopladas_adesao": "Adesão entre camadas (delaminação)",
    },
    "Chapas plastificadas": {
        "chapas_plastificadas_centralizacao": "Centralização das camadas",
        "chapas_plastificadas_adesao": "Adesão entre camadas (delaminação)",
        "chapas_plastificadas_verificacao_visual": "Verificação visual (formação de bolhas e/ou rugas)",
    },
    "Papel cortado": {
        "papel_cortado_sentido_corte": "Corte está no sentido correto?",
    },
    "Papel Colado": {
        "papel_colado_centralizacao": "Centralização da chapa",
        "papel_colado_colagem": "Colagem centralizada",
        "papel_colado_adesao": "Adesão da superfície",
    },
    "Guilhotina/Resmadeira/Rebobinadeira": {
        "guilhotina_verificacao_visual": "Verificação visual (Manchas, tonalidade e/ou manchas)",
        "guilhotina_dimensoes": "Dimensões (Largura e comprimento)",
        "guilhotina_aspecto_visual": "Aspecto visual (tonalidade e/ou manchas)",
    },
    "Caixas": {
        "caixas_verificacao_visual": "Verificação visual (bordas sujas de cola, má impressão, cores, rasgos, abas mal coladas)",
        "caixas_formacao": "Verificação se caixa esta se formando (arestas e vértices da caixa precisam estar retas)",
    }
}

# Função para carregar os dados de inspeção do banco (retorna dados brutos)
def carregar_dados_brutos_inspecao():
    try:
        query = """
        SELECT
            ip.id, ip.data, ip.tipo_produto, ip.checklist,
            s.setor_nome, m.maquina_nome, ip.qtd_inspecionada
        FROM inspecao_processo ip
        LEFT JOIN setor s ON ip.setor_id = s.setor_id
        LEFT JOIN maquina m ON ip.maquina_id = m.maquina_id
        """
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        print(f"Erro ao carregar dados de inspeção brutos: {e}")
        return pd.DataFrame()

# Layout do Dashboard
layout = dbc.Container([
    dcc.Store(id='qualidade-dados-brutos'), # Armazenará os dados brutos
    dcc.Store(id='qualidade-dados-pcp-retrabalho'),

    # Cabeçalho
    dbc.Row([
        dbc.Col(html.H1("Dashboard de Qualidade", className="text-white"), width=12)
    ], style={'background-color': '#02083d'}, className="p-3 mb-4 rounded"),

    # Filtros
    dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Período"),
                    dcc.DatePickerRange(
                        id='qualidade-filtro-data',
                        min_date_allowed=date(2023, 1, 1),
                        max_date_allowed=date.today(),
                        start_date=date(date.today().year, 1, 1),
                        end_date=date.today(),
                        display_format='DD/MM/YYYY'
                    )
                ], md=4),
                dbc.Col([
                    html.Label("Produto"),
                    dcc.Dropdown(id='qualidade-filtro-produto', placeholder="Todos", clearable=True)
                ], md=3),
                dbc.Col([
                    html.Label("Setor"),
                    dcc.Dropdown(id='qualidade-filtro-setor', placeholder="Todos", clearable=True)
                ], md=3),
                dbc.Col([
                    html.Label("Máquina"),
                    dcc.Dropdown(id='qualidade-filtro-maquina', placeholder="Todas", clearable=True)
                ], md=2)
            ])
        ]),
        className="mb-4 border-dark shadow-sm"
    ),

    # KPIs
    dbc.Row(id='qualidade-kpis', className="mb-2 g-2"),

    # Cards por Setor
    dbc.Row(id='qualidade-cards-setor', className="g-2 mb-4"),

    # Gráficos
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='grafico-nao-conformidade-produto')), className="border-dark shadow-sm"), md=6),
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='grafico-nao-conformidade-item')), className="border-dark shadow-sm"), md=6)
    ], className="mb-2 g-2"),
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(dcc.Graph(id='grafico-nao-conformidade-maquina')), className="border-dark shadow-sm"), md=12)
    ])
], fluid=True)


# Callback para carregar dados brutos e popular os filtros
@app.callback(
    [Output('qualidade-dados-brutos', 'data'),
     Output('qualidade-dados-pcp-retrabalho', 'data'),
     Output('qualidade-filtro-produto', 'options'),
     Output('qualidade-filtro-setor', 'options'),
     Output('qualidade-filtro-maquina', 'options')],
    Input('url', 'pathname')
)
def carregar_dados_e_filtros(pathname):
    if pathname != '/dashboardqualidade':
        return None, None, [], [], []
    
    # Carregar dados brutos de inspeção
    df_bruto = carregar_dados_brutos_inspecao()
    
    # Carregar dados de pcp e retrabalho
    df_pcp_retrabalho = carregar_dados_pcp_e_retrabalho()

    # --- Popular filtros a partir de fontes mestre ---
    # Produtos
    produtos = [{'label': i, 'value': i} for i in sorted(checklist_items_por_produto.keys())]

    # Setores e Máquinas
    setores, maquinas = [], []
    try:
        with engine.connect() as conn:
            df_setores = pd.read_sql_table('setor', conn)
            setores = [{'label': row['setor_nome'], 'value': row['setor_nome']} for _, row in df_setores.sort_values('setor_nome').iterrows()]
            
            df_maquinas = pd.read_sql_table('maquina', conn)
            maquinas = [{'label': row['maquina_nome'], 'value': row['maquina_nome']} for _, row in df_maquinas.sort_values('maquina_nome').iterrows()]
            
    except Exception as e:
        print(f"Erro ao carregar filtros de setor/máquina: {e}")

    # Retorna os dados brutos e as opções de filtro
    json_bruto = df_bruto.to_json(date_format='iso', orient='split') if not df_bruto.empty else None
    json_pcp_retrabalho = df_pcp_retrabalho.to_json(date_format='iso', orient='split') if not df_pcp_retrabalho.empty else None
    
    return json_bruto, json_pcp_retrabalho, produtos, setores, maquinas

# Função auxiliar para processar o checklist
def processar_checklist(df_bruto):
    registros = []
    for _, row in df_bruto.iterrows():
        try:
            checklist = row['checklist']
            
            # Lida com casos em que o checklist é uma string JSON (potencialmente codificada duas vezes)
            while isinstance(checklist, str):
                try:
                    checklist = json.loads(checklist)
                except json.JSONDecodeError:
                    # Se a decodificação falhar, não é uma string JSON válida, então quebre
                    # print(f"Aviso: Não foi possível decodificar a string do checklist para a linha ID {row.get('id', 'N/A')}.")
                    checklist = None  # Define como None para ser pulado mais tarde
                    break

            # Ignora se não for um dicionário
            if not isinstance(checklist, dict):
                continue

            for item, detalhes in checklist.items():
                if isinstance(detalhes, dict):
                    status = detalhes.get('status', 'N/A')
                    quantidade = detalhes.get('quantidade', 0)
                else: # Lida com formato antigo
                    status = detalhes
                    quantidade = 1 if status == 'nao_conforme' else 0

                registros.append({
                    'id': row['id'],
                    'data': row['data'],
                    'tipo_produto': row['tipo_produto'],
                    'setor_nome': row['setor_nome'],
                    'maquina_nome': row['maquina_nome'],
                    'qtd_inspecionada': row['qtd_inspecionada'],
                    'item_checklist': item,
                    'status': status,
                    'quantidade': quantidade
                })
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
    
    df_processado = pd.DataFrame(registros)
    if 'data' in df_processado.columns and not df_processado.empty:
        df_processado['data'] = pd.to_datetime(df_processado['data'])
        
    return df_processado

# Callback principal para atualizar o dashboard
@app.callback(
    [Output('qualidade-kpis', 'children'),
     Output('qualidade-cards-setor', 'children'),
     Output('grafico-nao-conformidade-produto', 'figure'),
     Output('grafico-nao-conformidade-item', 'figure'),
     Output('grafico-nao-conformidade-maquina', 'figure')],
    [Input('qualidade-dados-brutos', 'data'),
     Input('qualidade-dados-pcp-retrabalho', 'data'),
     Input('qualidade-filtro-data', 'start_date'),
     Input('qualidade-filtro-data', 'end_date'),
     Input('qualidade-filtro-produto', 'value'),
     Input('qualidade-filtro-setor', 'value'),
     Input('qualidade-filtro-maquina', 'value')]
)
def atualizar_dashboard(json_data_bruto, json_pcp_retrabalho, start_date, end_date, produto, setor, maquina):
    empty_fig = go.Figure().update_layout(
        title_text="Nenhum dado para exibir",
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{"text": "Sem dados com os filtros atuais.", "xref": "paper", "yref": "paper", "showarrow": False, "font": {"size": 16}}]
    )
    
    df_bruto = pd.read_json(StringIO(json_data_bruto), orient='split') if json_data_bruto else pd.DataFrame()
    df_pcp_retrabalho = pd.read_json(StringIO(json_pcp_retrabalho), orient='split') if json_pcp_retrabalho else pd.DataFrame()

    if 'pcp_emissao' in df_pcp_retrabalho.columns:
        df_pcp_retrabalho['pcp_emissao'] = pd.to_datetime(df_pcp_retrabalho['pcp_emissao'])

    df_processado = processar_checklist(df_bruto)

    if df_processado.empty and df_pcp_retrabalho.empty:
        return [], [], empty_fig, empty_fig, empty_fig
        
    df_processado['data'] = pd.to_datetime(df_processado['data'])
    
    # Aplicar filtro de data
    mask_data = (df_processado['data'].dt.date >= pd.to_datetime(start_date).date()) & \
                (df_processado['data'].dt.date <= pd.to_datetime(end_date).date())
    df_filtrado_data = df_processado[mask_data]

    # --- Cards de Conformidade por Setor ---
    setor_cards = []
    if not df_filtrado_data.empty:
        setores = sorted(df_filtrado_data['setor_nome'].dropna().unique())
        for setor_nome in setores:
            df_setor = df_filtrado_data[df_filtrado_data['setor_nome'] == setor_nome]

            df_inspecoes_unicas_setor = df_setor.drop_duplicates(subset=['id'])
            total_inspecionado_setor = df_inspecoes_unicas_setor['qtd_inspecionada'].sum()

            df_nao_conforme_setor = df_setor[df_setor['status'] == 'nao_conforme']
            total_nao_conforme_setor = df_nao_conforme_setor['quantidade'].sum()

            taxa_conformidade_setor = ((total_inspecionado_setor - total_nao_conforme_setor) / total_inspecionado_setor * 100) if total_inspecionado_setor > 0 else 100

            card = dbc.Col(dbc.Card([
                dbc.CardHeader(html.H5(setor_nome, className="mb-0 text-center")),
                dbc.CardBody([
                    html.Div([
                        html.Span(f"{taxa_conformidade_setor:.2f}%", className="fs-2"),
                        html.Span(f"({total_inspecionado_setor:,.0f} inspec.)", className="text-muted ms-2", style={'fontSize': '0.9rem'})
                    ], className="d-flex justify-content-center align-items-baseline"),
                    html.P(f"Não Conforme: {total_nao_conforme_setor:,.0f}", className="card-text text-center text-danger mt-1", style={'fontSize': '0.9rem'})
                ])
            ], className="border-dark shadow-sm"), style={'minWidth': '400px'})
            setor_cards.append(card)

    # Aplicar filtros de produto, setor e máquina para KPIs e gráficos principais
    df_filtrado = df_filtrado_data.copy()
    if produto: df_filtrado = df_filtrado[df_filtrado['tipo_produto'] == produto]
    if setor: df_filtrado = df_filtrado[df_filtrado['setor_nome'] == setor]
    if maquina: df_filtrado = df_filtrado[df_filtrado['maquina_nome'] == maquina]

    # --- KPIs ---
    total_nao_conforme = 0
    total_inspecionado = 0
    if not df_filtrado.empty:
        df_nao_conforme = df_filtrado[df_filtrado['status'] == 'nao_conforme']
        total_nao_conforme = df_nao_conforme['quantidade'].sum()
        
        df_inspecoes_unicas = df_filtrado.drop_duplicates(subset=['id'])
        total_inspecionado = df_inspecoes_unicas['qtd_inspecionada'].sum()
    
    taxa_conformidade = ((total_inspecionado - total_nao_conforme) / total_inspecionado * 100) if total_inspecionado > 0 else 100

    # --- Novos KPIs de Retrabalho ---
    num_retrabalhos = 0
    num_reprovas = 0
    valor_reprovas = 0
    num_aprov_concessao = 0
    
    if not df_pcp_retrabalho.empty:
        mask_data_pcp = (df_pcp_retrabalho['pcp_emissao'].dt.date >= pd.to_datetime(start_date).date()) & \
                        (df_pcp_retrabalho['pcp_emissao'].dt.date <= pd.to_datetime(end_date).date())
        df_pcp_filtrado = df_pcp_retrabalho[mask_data_pcp]

        if not df_pcp_filtrado.empty:
            # Contagens baseadas no status do apontamento de retrabalho
            num_retrabalhos = df_pcp_filtrado[df_pcp_filtrado['status'] == 1].shape[0]
            
            df_reprovas = df_pcp_filtrado[df_pcp_filtrado['status'] == 3]
            num_reprovas = df_reprovas.shape[0]
            valor_reprovas = (df_reprovas['quantidade_nao_conforme'] * df_reprovas['valor']).sum()

            num_aprov_concessao = df_pcp_filtrado[df_pcp_filtrado['status'] == 4].shape[0]

    kpi_layout = [
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H4("Total Não Conforme", className="card-title"),
            html.P(f"{total_nao_conforme:,.0f}", className="card-text fs-2")
        ]), className="border-dark shadow-sm"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H4("Total Inspecionado", className="card-title"),
            html.P(f"{total_inspecionado:,.0f}", className="card-text fs-2")
        ]), className="border-dark shadow-sm"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H4("Taxa de Conformidade", className="card-title"),
            html.P(f"{taxa_conformidade:.2f}%", className="card-text fs-2")
        ]), className="border-dark shadow-sm"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H4("Número Retrabalhos", className="card-title"),
            html.P(f"{num_retrabalhos:,.0f}", className="card-text fs-2")
        ]), className="border-dark shadow-sm"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H4("Número Reprovas", className="card-title"),
            html.Div([
                html.Span(f"{num_reprovas:,.0f}", className="fs-2"),
                html.Span(f"(R$ {valor_reprovas:,.2f})", className="text-muted ms-2", style={'fontSize': '0.9rem'})
            ], className="d-flex justify-content-center align-items-baseline")
        ]), className="border-dark shadow-sm"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H4("Sob Concessão", className="card-title"),
            html.P(f"{num_aprov_concessao:,.0f}", className="card-text fs-2")
        ]), className="border-dark shadow-sm"), md=2),
    ]
    
    # --- Lógica de Gráficos (começa aqui) ---
    df_graficos = df_filtrado.copy()
    if df_graficos.empty:
        # Se não houver dados de inspeção para os filtros, retorne os KPIs e gráficos vazios
        return kpi_layout, setor_cards, empty_fig, empty_fig, empty_fig

    df_nao_conforme = df_graficos[df_graficos['status'] == 'nao_conforme']

    if df_nao_conforme.empty:
        return kpi_layout, setor_cards, empty_fig, empty_fig, empty_fig

    # Não conformidades por produto
    df_produto = df_nao_conforme.groupby('tipo_produto')['quantidade'].sum().nlargest(10).reset_index()
    fig_produto = px.bar(
        df_produto, x='tipo_produto', y='quantidade',
        title="Top 10 Produtos com Mais Não Conformidades",
        labels={'tipo_produto': 'Produto', 'quantidade': 'Quantidade'},
        text_auto=True
    )
    fig_produto.update_traces(textposition='outside')
    fig_produto.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    # Não conformidades por item de checklist
    df_item = df_nao_conforme.groupby('item_checklist')['quantidade'].sum().nlargest(10).reset_index()
    fig_item = px.pie(
        df_item, names='item_checklist', values='quantidade',
        title="Top 10 Razões de Não Conformidade",
        hole=0.4
    )
    fig_item.update_traces(textposition='inside', textinfo='value+percent')

    # Não conformidades por máquina
    df_maquina = df_nao_conforme.groupby('maquina_nome')['quantidade'].sum().nlargest(10).reset_index()
    fig_maquina = px.bar(
        df_maquina, x='maquina_nome', y='quantidade',
        title="Top 10 Máquinas com Mais Não Conformidades",
        labels={'maquina_nome': 'Máquina', 'quantidade': 'Quantidade'},
        text_auto=True
    )
    fig_maquina.update_traces(textposition='outside')
    fig_maquina.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')

    return kpi_layout, setor_cards, fig_produto, fig_item, fig_maquina
