import dash
from dash import html, dcc, Input, Output, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
from banco_dados.banco import Banco, engine
from app import app
import sqlite3
import calendar

# Dicionário de metas mensais por categoria
METAS_MENSAIS = {
    'CAIXA 10L': 400000,
    'CAIXA 5L': 200000,
    'CAIXA 7L': 0,
    'CINTA': 600000,
    'COPO 100ML': 300000,
    'COPO 200ML': 100000,
    'ESPECIAL': 100000,
    'PIZZA': 200000,
    'POTE 120ML': 300000,
    'POTE 150ML': 300000,
    'POTE 180ML': 300000,
    'POTE 1L': 300000,
    'POTE 240ML': 400000,
    'POTE 360ML': 300000,
    'POTE 480ML': 400000,
    'POTE 500ML': 3500000,
    'POTE 80ML': 300000,
    'TAMPA 10L': 120000,
    'TAMPA 5L': 0
}

def calcular_aderencia_programacao():
    """
    Calcula a aderência à programação comparando planejamento vs baixas por semana
    """
    try:
        # Conectar ao banco de dados
        with engine.connect() as conn:
            # Query para obter dados de planejamento com semana do ano
            query_planejamento = """
            SELECT 
                p.id_pcp,
                p.quantidade as qtd_planejada,
                p.data_programacao
            FROM planejamento p
            """
            
            df_planejamento = pd.read_sql(query_planejamento, conn)
            
            # Query para obter dados de baixa com semana do ano
            query_baixa = """
            SELECT 
                b.pcp_id,
                b.qtd as qtd_baixada,
                b.data,
                CASE WHEN b.pcp_id IS NULL OR b.pcp_id = '' THEN b.qtd ELSE 0 END as qtd_sem_pcp
            FROM baixa b
            WHERE (b.ajuste != 1 OR b.ajuste IS NULL)
            """
            
            df_baixa = pd.read_sql(query_baixa, conn)
        
        if df_planejamento.empty:
            return pd.DataFrame()
        
        # Converter para datetime se necessário
        df_planejamento['data_programacao'] = pd.to_datetime(df_planejamento['data_programacao'])
        if not df_baixa.empty:
            df_baixa['data'] = pd.to_datetime(df_baixa['data'])
        
        # Criar chave ano-semana usando isocalendar para maior precisão
        df_planejamento['ano_semana'] = df_planejamento['data_programacao'].dt.isocalendar().year.astype(str) + '-S' + df_planejamento['data_programacao'].dt.isocalendar().week.astype(str).str.zfill(2)
        if not df_baixa.empty:
            df_baixa['ano_semana'] = df_baixa['data'].dt.isocalendar().year.astype(str) + '-S' + df_baixa['data'].dt.isocalendar().week.astype(str).str.zfill(2)
        
        # 1. Somar quantidade planejada por semana (denominador)
        planejamento_por_semana = df_planejamento.groupby('ano_semana')['qtd_planejada'].sum().reset_index()
        
        # Calcular também o total geral de baixas por semana e baixas sem PCP
        total_baixas_semana = pd.DataFrame()
        if not df_baixa.empty:
            total_baixas_semana = df_baixa.groupby('ano_semana').agg({
                'qtd_baixada': 'sum',  # Total geral de baixas
                'qtd_sem_pcp': 'sum'   # Total de baixas sem PCP
            }).reset_index()
            total_baixas_semana.rename(columns={'qtd_baixada': 'total_geral_baixas'}, inplace=True)
        
        # 2. Para cada semana, pegar os id_pcp planejados
        resultado_final = []
        
        for _, row_semana in planejamento_por_semana.iterrows():
            semana = row_semana['ano_semana']
            qtd_planejada_total = row_semana['qtd_planejada']
            
            # Pegar todos os id_pcp planejados nesta semana
            ids_pcp_planejados = df_planejamento[df_planejamento['ano_semana'] == semana]['id_pcp'].unique()
            
            # 3. Ver se esses id_pcp tiveram baixas na mesma semana
            qtd_baixada_total = 0
            if not df_baixa.empty:
                baixas_semana = df_baixa[
                    (df_baixa['ano_semana'] == semana) & 
                    (df_baixa['pcp_id'].isin(ids_pcp_planejados))
                ]
                qtd_baixada_total = baixas_semana['qtd_baixada'].sum()
            
            # Pegar o total geral de baixas e baixas sem PCP da semana
            total_geral = 0
            total_sem_pcp = 0
            if not total_baixas_semana.empty:
                linha_total = total_baixas_semana[total_baixas_semana['ano_semana'] == semana]
                if not linha_total.empty:
                    total_geral = linha_total['total_geral_baixas'].iloc[0]
                    total_sem_pcp = linha_total['qtd_sem_pcp'].iloc[0]
            
            # 4. Calcular aderência
            aderencia = (qtd_baixada_total / qtd_planejada_total * 100) if qtd_planejada_total > 0 else 0
            
            resultado_final.append({
                'ano_semana': semana,
                'qtd_planejada': qtd_planejada_total,
                'qtd_baixada': qtd_baixada_total,
                'total_geral_baixas': total_geral,
                'qtd_sem_pcp': total_sem_pcp,
                'aderencia': round(aderencia, 2)
            })
        
        # Converter para DataFrame e ordenar
        resultado_semanal = pd.DataFrame(resultado_final)
        resultado_semanal = resultado_semanal.sort_values('ano_semana')
        
        return resultado_semanal
        
    except Exception as e:
        print(f"Erro ao calcular aderência: {e}")
        return pd.DataFrame()

def calcular_dados_categoria_por_semana():
    """
    Calcula os dados de planejamento e execução por categoria e semana
    """
    try:
        # Conectar ao banco de dados
        with engine.connect() as conn:
            # Query para obter dados de planejamento com categoria
            query_planejamento = """
            SELECT 
                p.id_pcp,
                p.quantidade as qtd_planejada,
                p.data_programacao,
                pcp.pcp_categoria as pcp_categoria
            FROM planejamento p
            LEFT JOIN pcp ON p.id_pcp = pcp.pcp_id
            """
            
            df_planejamento = pd.read_sql(query_planejamento, conn)
            
            # Query para obter dados de baixa
            query_baixa = """
            SELECT 
                b.pcp_id,
                b.qtd as qtd_baixada,
                b.data,
                pcp.pcp_categoria as pcp_categoria
            FROM baixa b
            LEFT JOIN pcp ON b.pcp_id = pcp.pcp_id
            WHERE (b.ajuste != 1 OR b.ajuste IS NULL)
            """
            
            df_baixa = pd.read_sql(query_baixa, conn)
        
        if df_planejamento.empty:
            return pd.DataFrame()
        
        # Converter para datetime
        df_planejamento['data_programacao'] = pd.to_datetime(df_planejamento['data_programacao'])
        if not df_baixa.empty:
            df_baixa['data'] = pd.to_datetime(df_baixa['data'])
        
        # Criar chave ano-semana
        df_planejamento['ano_semana'] = df_planejamento['data_programacao'].dt.isocalendar().year.astype(str) + '-S' + df_planejamento['data_programacao'].dt.isocalendar().week.astype(str).str.zfill(2)
        if not df_baixa.empty:
            df_baixa['ano_semana'] = df_baixa['data'].dt.isocalendar().year.astype(str) + '-S' + df_baixa['data'].dt.isocalendar().week.astype(str).str.zfill(2)
        
        # Calcular totais por categoria e semana
        resultado_final = []
        
        # Agrupar planejamento por categoria e semana
        plan_por_cat_sem = df_planejamento.groupby(['pcp_categoria', 'ano_semana'])['qtd_planejada'].sum().reset_index()
        
        # Agrupar baixas por categoria e semana (apenas com PCP ID que existe no planejamento)
        baixas_vinculadas = []
        for _, row in df_planejamento.groupby(['pcp_categoria', 'ano_semana']):
            semana = row['ano_semana'].iloc[0]
            categoria = row['pcp_categoria'].iloc[0]
            # Pegar os ids planejados desta categoria nesta semana
            ids_planejados = df_planejamento[
                (df_planejamento['ano_semana'] == semana) & 
                (df_planejamento['pcp_categoria'] == categoria)
            ]['id_pcp'].unique()
            
            # Filtrar baixas desta semana que têm pcp_id no planejamento
            baixas_semana = df_baixa[
                (df_baixa['ano_semana'] == semana) & 
                (df_baixa['pcp_id'].isin(ids_planejados))
            ]
            
            if not baixas_semana.empty:
                baixas_vinculadas.append({
                    'pcp_categoria': categoria,
                    'ano_semana': semana,
                    'qtd_baixada': baixas_semana['qtd_baixada'].sum()
                })
        
        baixas_com_pcp = pd.DataFrame(baixas_vinculadas) if baixas_vinculadas else pd.DataFrame(columns=['pcp_categoria', 'ano_semana', 'qtd_baixada'])
        
        # Total de todas as baixas por categoria
        todas_baixas = df_baixa.groupby(['pcp_categoria', 'ano_semana'])['qtd_baixada'].sum().reset_index()
        
        # Combinar os dados
        categorias = pd.concat([
            plan_por_cat_sem['pcp_categoria'],
            baixas_com_pcp['pcp_categoria'],
            todas_baixas['pcp_categoria']
        ]).unique()
        
        semanas = pd.concat([
            plan_por_cat_sem['ano_semana'],
            baixas_com_pcp['ano_semana'],
            todas_baixas['ano_semana']
        ]).unique()
        
        for categoria in categorias:
            for semana in semanas:
                # Dados planejados
                plan = plan_por_cat_sem[
                    (plan_por_cat_sem['pcp_categoria'] == categoria) &
                    (plan_por_cat_sem['ano_semana'] == semana)
                ]['qtd_planejada'].sum()
                
                # Dados baixados com PCP
                feito = baixas_com_pcp[
                    (baixas_com_pcp['pcp_categoria'] == categoria) &
                    (baixas_com_pcp['ano_semana'] == semana)
                ]['qtd_baixada'].sum()
                
                # Total geral de baixas
                total = todas_baixas[
                    (todas_baixas['pcp_categoria'] == categoria) &
                    (todas_baixas['ano_semana'] == semana)
                ]['qtd_baixada'].sum()
                
                resultado_final.append({
                    'pcp_categoria': categoria,
                    'ano_semana': semana,
                    'planejado': int(plan),
                    'feito': int(feito),
                    'total': int(total)
                })
        #print(resultado_final)
        return pd.DataFrame(resultado_final)
        
    except Exception as e:
        print(f"Erro ao calcular dados por categoria: {e}")
        return pd.DataFrame()

# Layout do Dashboard
layout = dbc.Container([
    # Título
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div([
                    html.H1("Painel de Controle PCP", 
                           className="mb-0",
                           style={
                               'color': '#2c3e50',
                               'font-weight': '600',
                               'font-size': '28px',
                               'letter-spacing': '0.5px'
                           })
                ], style={'margin-right': '20px'}),
                html.Div([
                    dbc.Checkbox(
                        id="usar-semana-anterior",
                        label="Usar semana anterior como referência",
                        value=False,
                        className="custom-checkbox"
                    )
                ])
            ], className="d-flex align-items-center justify-content-center py-3",
               style={
                   'background': 'linear-gradient(to right, #f8f9fa, #ffffff, #f8f9fa)',
                   'border': '2px solid #e0e0e0',
                   'border-radius': '15px',
                   'margin-top': '20px',
                   'margin-bottom': '20px',
                   'box-shadow': '0 2px 4px rgba(0,0,0,0.05)'
               })
        ], width=12)
    ]),
    
    # Conteúdo principal dividido em duas colunas
    dbc.Row([

        dbc.Col([
            # Pedidos em Atraso (card métrico)
            html.Div(id="pedidos-atraso", className="mb-3"),
            # Gráfico de atrasos por semana (horizontal) em card com header (mesmo estilo)
            dbc.Card([
                dbc.CardHeader([
                    html.H4("Atrasos por Semana (últimas 10)", className="mb-0")
                ]),
                dbc.CardBody([
                    dcc.Graph(id="grafico-atrasos-semana")
                ], style={'padding': '10px'})
            ])
        ], lg=3, xs=12, className="mb-3 mb-lg-0"),
        
        # Coluna da direita - Resto do conteúdo
        dbc.Col([
            # Cartões de métricas
            dbc.Row([
                # Cartão de pedidos em atraso (primeiro, à esquerda de Total Planejado)
        
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-tasks me-2", 
                                      style={'font-size': '24px', 'color': '#2ecc71'}),
                                html.H4("Total Planejado", className="card-title d-inline")
                            ], style={'margin-bottom': '10px'}),
                            html.H2(id="total-planejado", className="text-success mb-0"),
                            html.P("Semana atual", 
                                  className="card-text text-muted",
                                  style={'margin-top': '5px'})
                        ])
                    ], className="h-100 shadow-sm",
                       style={'border-radius': '10px', 'border': '1px solid #e0e0e0'})
                ], xl=3, md=6, xs=12),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-check-circle me-2", 
                                      style={'font-size': '24px', 'color': '#f39c12'}),
                                html.H4("Total Executado", className="card-title d-inline")
                            ], style={'margin-bottom': '10px'}),
                            html.Div([
                                html.H2(id="total-executado", 
                                       className="text-warning mb-1",
                                       style={'font-size': '2rem'}),
                                html.Div([
                                    html.I(className="fas fa-info-circle me-2",
                                          style={'color': '#7f8c8d'}),
                                    html.P(id="total-geral-baixas",
                                          className="mb-0",
                                          style={
                                              'font-size': '1.1rem',
                                              'color': '#7f8c8d',
                                              'font-weight': '500',
                                              'display': 'inline'
                                          })
                                ], style={'display': 'flex', 'align-items': 'center'})
                            ]),
                            html.P("Semana atual", 
                                  className="card-text text-muted",
                                  style={'margin-top': '5px'})
                        ])
                    ], className="h-100 shadow-sm",
                       style={'border-radius': '10px', 'border': '1px solid #e0e0e0'})
                ], xl=3, md=6, xs=12),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-tachometer-alt me-2", 
                                      style={'font-size': '24px', 'color': '#3498db'}),
                                html.H4("Aderência", className="card-title d-inline")
                            ], style={'margin-bottom': '10px'}),
                            html.H2(id="eficiencia-atual", className="text-info mb-0"),
                            html.Div([
                                html.P("Semana atual", 
                                      className="card-text text-muted mb-0",
                                      style={'margin-top': '5px'}),
                                html.P("Meta: 100%", 
                                      className="card-text",
                                      style={
                                          'color': '#27ae60',
                                          'font-weight': 'bold',
                                          'font-size': '0.9rem',
                                          'margin-top': '2px'
                                      })
                            ])
                        ])
                    ], className="h-100 shadow-sm",
                       style={'border-radius': '10px', 'border': '1px solid #e0e0e0'})
                ], xl=3, md=6, xs=12),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-percentage me-2", 
                                      style={'font-size': '24px', 'color': '#9b59b6'}),
                                html.H4("KPI Quantidade", className="card-title d-inline")
                            ], style={'margin-bottom': '10px'}),
                            html.H2(id="kpi-quantidade", className="text-purple mb-0"),
                            html.Div([
                                html.P("Produção sem PCP / Total", 
                                      className="card-text text-muted mb-0",
                                      style={'margin-top': '5px'}),
                                html.P("Meta: 0%", 
                                      className="card-text",
                                      style={
                                          'color': '#27ae60',
                                          'font-weight': 'bold',
                                          'font-size': '0.9rem',
                                          'margin-top': '2px'
                                      })
                            ])
                        ])
                    ], className="h-100 shadow-sm",
                       style={'border-radius': '10px', 'border': '1px solid #e0e0e0'})
                ], xl=3, md=6, xs=12)
            ], className="mb-3 g-3"),
            
            # Gráfico principal de aderência
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4("Aderência à Programação por Semana", className="mb-0")
                        ]),
                        dbc.CardBody([
                            dcc.Graph(id="grafico-aderencia-programacao")
                        ], style={'padding': '10px'})
                    ], style={'margin-top': '0px'})
                ])
            ], className="mb-4"),
            
            # Tabela de categorias por semana
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Acompanhamento por Categoria", className="mb-0")
                        ]),
                        dbc.CardBody([
                            html.Div(id="tabela-categorias")
                        ])
                    ])
                ])
            ], className="mb-4"),

            # Gráfico de pendências por semana (por categoria)
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.Div([
                                html.H5("Planejado pendente por semana (Status ≠ FEITO)", className="mb-0"),
                                dcc.Dropdown(
                                    id='nf-cat-filter',
                                    options=[{'label': k, 'value': k} for k in METAS_MENSAIS.keys()],
                                    placeholder='Selecione uma ou mais categorias',
                                    multi=True,
                                    style={'width': '380px'}
                                )
                            ], className='d-flex justify-content-between align-items-center')
                        ]),
                        dbc.CardBody([
                            dcc.Graph(id="grafico-nao-feito-semana")
                        , html.Div(id='lista-nao-feito', className='mt-3')
                        ], style={'padding': '10px'})
                    ])
                ])
            ], className="mb-4"),
            

        ], lg=9, xs=12)
    ])
], fluid=True)

# Função para calcular pedidos em atraso
def calcular_pedidos_atraso():
    """
    Calcula pedidos em atraso baseado nos critérios:
    - status diferente de 'FEITO'
    - pcp_correncia igual a NULL
    - fluxo_producao = 'Puxado'
    - data menor que hoje
    """
    try:
        with engine.connect() as conn:
            query = """
            SELECT 
                p.pcp_id,
                p.pcp_oc,
                p.pcp_pcp,
                p.pcp_categoria,
                p.pcp_qtd,
                p.pcp_entrega,
                p.pcp_observacao,
                p.pcp_emissao,
                c.nome as cliente_nome,
                prod.nome as produto_nome
            FROM pcp p
            LEFT JOIN clientes c ON p.pcp_cliente_id = c.cliente_id
            LEFT JOIN produtos prod ON p.pcp_produto_id = prod.produto_id
            WHERE p.pcp_correncia IS NULL
              AND prod.fluxo_producao = 'Puxado'
              AND p.pcp_entrega < date('now')
              AND (
                    SELECT COALESCE(SUM(b.qtd), 0)
                    FROM baixa b
                    WHERE b.pcp_id = p.pcp_id
                      AND (b.ajuste != 1 OR b.ajuste IS NULL)
                  ) < (0.9 * p.pcp_qtd)
            ORDER BY p.pcp_entrega ASC
            """
            
            df_atraso = pd.read_sql(query, conn)
            
        return df_atraso
    except Exception as e:
        print(f"Erro ao calcular pedidos em atraso: {e}")
        return pd.DataFrame()

# Função auxiliar para calcular métricas mensais por categoria
def calcular_metricas_mensais():
    try:
        # Conectar ao banco de dados
        with engine.connect() as conn:
            # Obter mês atual e anterior
            hoje = datetime.now()
            primeiro_dia_mes_atual = hoje.replace(day=1)
            ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
            primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
            
            # Query para obter baixas do mês atual
            query_mes_atual = f"""
            SELECT 
                p.pcp_categoria,
                SUM(b.qtd) as total_baixas
            FROM baixa b
            JOIN pcp p ON b.pcp_id = p.pcp_id
            WHERE b.data >= '{primeiro_dia_mes_atual.strftime('%Y-%m-%d')}'
            AND b.data <= '{hoje.strftime('%Y-%m-%d')}'
            AND (b.ajuste != 1 OR b.ajuste IS NULL)
            GROUP BY p.pcp_categoria
            """
            
            # Query para obter baixas do mês anterior até o mesmo dia
            dia_mes_anterior = min(hoje.day, ultimo_dia_mes_anterior.day)
            data_limite_mes_anterior = primeiro_dia_mes_anterior.replace(day=dia_mes_anterior)
            
            query_mes_anterior = f"""
            SELECT 
                p.pcp_categoria,
                SUM(b.qtd) as total_baixas
            FROM baixa b
            JOIN pcp p ON b.pcp_id = p.pcp_id
            WHERE b.data >= '{primeiro_dia_mes_anterior.strftime('%Y-%m-%d')}'
            AND b.data <= '{data_limite_mes_anterior.strftime('%Y-%m-%d')}'
            AND (b.ajuste != 1 OR b.ajuste IS NULL)
            GROUP BY p.pcp_categoria
            """
            
            df_mes_atual = pd.read_sql(query_mes_atual, conn)
            df_mes_anterior = pd.read_sql(query_mes_anterior, conn)
            
            # Criar dicionário com os resultados
            resultados = {}
            for categoria in METAS_MENSAIS.keys():
                meta = METAS_MENSAIS[categoria]
                
                # Dados do mês atual
                total_atual = df_mes_atual[
                    df_mes_atual['pcp_categoria'] == categoria
                ]['total_baixas'].iloc[0] if not df_mes_atual[
                    df_mes_atual['pcp_categoria'] == categoria
                ].empty else 0
                
                # Dados do mês anterior
                total_anterior = df_mes_anterior[
                    df_mes_anterior['pcp_categoria'] == categoria
                ]['total_baixas'].iloc[0] if not df_mes_anterior[
                    df_mes_anterior['pcp_categoria'] == categoria
                ].empty else 0
                
                # Calcular percentuais
                perc_meta = (total_atual / meta * 100) if meta > 0 else 0
                
                # Calcular variação em relação ao mês anterior
                var_mes_anterior = (
                    ((total_atual - total_anterior) / total_anterior * 100)
                    if total_anterior > 0 else 0
                )
                
                resultados[categoria] = {
                    'meta': meta,
                    'total_atual': total_atual,
                    'perc_meta': perc_meta,
                    'var_mes_anterior': var_mes_anterior
                }
            
            return resultados
    except Exception as e:
        print(f"Erro ao calcular métricas mensais: {e}")
        return {}

# Callbacks
@app.callback(
    [Output('grafico-aderencia-programacao', 'figure'),
     Output('total-planejado', 'children'),
     Output('total-executado', 'children'),
     Output('total-geral-baixas', 'children'),
     Output('eficiencia-atual', 'children'),
     Output('kpi-quantidade', 'children'),
     Output('pedidos-atraso', 'children'),
     Output('tabela-categorias', 'children'),
     Output('grafico-atrasos-semana', 'figure'),
     Output('grafico-nao-feito-semana', 'figure'),
     Output('lista-nao-feito', 'children')],
    [Input('usar-semana-anterior', 'value'), Input('nf-cat-filter', 'value')]
)
def atualizar_dashboard(usar_semana_anterior, nf_cat):
    
    
    # Calcular dados de aderência
    df_aderencia = calcular_aderencia_programacao()
    
    if df_aderencia.empty:
        # Criar gráfico vazio
        fig = go.Figure()
        fig.add_annotation(
            text="Não há dados disponíveis",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(height=400)
        return fig, "0", "0", "Total geral: 0", "0%", "0%", html.Div("Sem dados disponíveis"), html.Div([]), go.Figure(), html.Div()
    
    # Calcular semana atual usando isocalendar
    agora = datetime.now()
    if usar_semana_anterior:
        # Se checkbox marcado, subtrai 7 dias
        agora = agora - timedelta(days=7)
        
    else:
        pass
    
    semana_atual = f"{agora.isocalendar().year}-S{str(agora.isocalendar().week).zfill(2)}"
    
    
    # Buscar dados da semana selecionada
    dados_semana = df_aderencia[df_aderencia['ano_semana'] == semana_atual]
    
    # Criar gráfico de linha
    fig = go.Figure()
    
    # Linha principal de aderência
    fig.add_trace(go.Scatter(
        x=df_aderencia['ano_semana'],
        y=df_aderencia['aderencia'],
        mode='lines+markers',
        name='Aderência (%)',
        line=dict(color='#3498db', width=3),
        marker=dict(size=10, color='#3498db', line=dict(width=2, color='white')),
        customdata=list(zip(
            [f"{int(val):,}".replace(",", ".") for val in df_aderencia['qtd_planejada']],
            [f"{int(val):,}".replace(",", ".") for val in df_aderencia['qtd_baixada']],
            [f"{int(val):,}".replace(",", ".") for val in df_aderencia['total_geral_baixas']]
        )),
        hovertemplate='<b>%{x}</b><br>' +
                      'Aderência: %{y:.2f}%<br>' +
                      'Total Planejado: %{customdata[0]}<br>' +
                      'Total Executado: %{customdata[1]}<br>' +
                      'Total Geral Baixas: %{customdata[2]}<br>' +
                      '<extra></extra>'
    ))
    
    # Linha meta (100%)
    fig.add_hline(y=100, line_dash="dash", line_color="green", 
                  annotation_text="Meta (100%)", annotation_position="top right")
    
    # Linha de 80% como referência
    fig.add_hline(y=80, line_dash="dot", line_color="orange", 
                  annotation_text="Referência (80%)", annotation_position="bottom right")
    
    # Adicionar marcadores visuais para níveis de aderência
    for i, row in df_aderencia.iterrows():
        color = 'green' if row['aderencia'] >= 100 else 'orange' if row['aderencia'] >= 80 else 'red'
        fig.add_scatter(
            x=[row['ano_semana']], 
            y=[row['aderencia']], 
            mode='markers',
            marker=dict(size=12, color=color, symbol='circle', line=dict(width=2, color='white')),
            showlegend=False,
            hoverinfo='skip'
        )
    
    # Adicionar texto com a porcentagem de aderência nos pontos
    fig.add_trace(go.Scatter(
        x=df_aderencia['ano_semana'],
        y=df_aderencia['aderencia'],
        mode='text',
        text=[f"{val:.1f}%" for val in df_aderencia['aderencia']],
        textposition='top center',
        textfont=dict(
            size=16,
            color='#2c3e50',
            family='Arial Black'
        ),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig.update_layout(
        xaxis_title="Semana",
        yaxis_title="Aderência (%)",
        height=450,
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(t=20, b=20),
        yaxis=dict(
            range=[0, max(120, df_aderencia['aderencia'].max() + 10)],
            gridcolor='#e0e0e0',
            zerolinecolor='#e0e0e0'
        ),
        xaxis=dict(
            gridcolor='#e0e0e0',
            zerolinecolor='#e0e0e0'
        )
    )
    
    if not dados_semana.empty:
        total_planejado = int(dados_semana['qtd_planejada'].iloc[0])
        total_executado = int(dados_semana['qtd_baixada'].iloc[0])
        total_geral_baixas = int(dados_semana['total_geral_baixas'].iloc[0])
        eficiencia_atual = dados_semana['aderencia'].iloc[0]
    else:
        # Se não há dados da semana, usar a última semana disponível
        ultima_semana = df_aderencia.iloc[-1] if not df_aderencia.empty else None
        total_planejado = int(ultima_semana['qtd_planejada']) if ultima_semana is not None else 0
        total_executado = int(ultima_semana['qtd_baixada']) if ultima_semana is not None else 0
        total_geral_baixas = int(ultima_semana['total_geral_baixas']) if ultima_semana is not None else 0
        eficiencia_atual = ultima_semana['aderencia'] if ultima_semana is not None else 0
    
    # Calcular KPI de quantidade
    if not dados_semana.empty:
        total_executado = int(dados_semana['qtd_baixada'].iloc[0])
        total_geral = int(dados_semana['total_geral_baixas'].iloc[0])
        producao_sem_pcp = total_geral - total_executado
        kpi_quantidade = (producao_sem_pcp / total_geral * 100) if total_geral > 0 else 0
    else:
        kpi_quantidade = 0
    
    # Adicionar classes de cor baseadas na meta
    eficiencia_cor = 'text-success' if eficiencia_atual >= 100 else 'text-danger'
    kpi_cor = 'text-success' if kpi_quantidade <= 0 else 'text-danger'

    # Gerar tabela de categorias
    df_categorias = calcular_dados_categoria_por_semana()
    if not df_categorias.empty:
        # Ordenar por semana e pegar apenas as últimas 3 semanas
        df_categorias = df_categorias.sort_values(['ano_semana', 'pcp_categoria'])
        ultimas_semanas = sorted(df_categorias['ano_semana'].unique())[-3:]
        df_categorias = df_categorias[df_categorias['ano_semana'].isin(ultimas_semanas)]
        
        # Criar o cabeçalho da tabela
        header = html.Thead([
            html.Tr([
                html.Th("Categoria", style={
                    'width': '150px',
                    'text-align': 'left',
                    'padding': '8px',
                    'background-color': '#f8f9fa',
                    'border-right': '2px solid #666'  # Borda mais grossa entre semanas
                })
            ] + [
                html.Th([
                    html.Div(f"Semana {sem.split('-S')[1]}", style={
                        'text-align': 'center',
                        'margin-bottom': '5px',
                        'font-weight': 'bold'
                    }),
                    html.Div([
                        html.Span("PLAN", style={
                            'width': '80px',
                            'display': 'inline-block',
                            'text-align': 'right',
                            'border-right': '1px solid #dee2e6',
                            'padding-right': '8px'
                        }),
                        html.Span("PLAN FEITO", style={
                            'width': '120px',
                            'display': 'inline-block',
                            'text-align': 'right',
                            'border-right': '1px solid #dee2e6',
                            'padding-right': '8px',
                            'padding-left': '8px'
                        }),
                        html.Span("TOTAL FEITO", style={
                            'width': '120px',
                            'display': 'inline-block',
                            'text-align': 'right',
                            'padding-left': '8px'
                        })
                    ], style={'display': 'flex', 'justify-content': 'space-between'})
                ], style={
                    'text-align': 'center',
                    'background-color': '#f8f9fa',
                    'padding': '8px',
                    'border-right': '2px solid #666'  # Borda mais grossa entre semanas
                })
                for sem in ultimas_semanas
            ])
        ], style={'border-bottom': '2px solid #666'})  # Borda mais grossa abaixo do cabeçalho

        # Criar as linhas da tabela
        rows = []
        categorias = sorted(df_categorias['pcp_categoria'].unique())
        #print(categorias)
        for cat in categorias:
            row_data = [html.Td(cat, style={
                'font-weight': 'bold',
                'padding': '8px',
                'border-right': '2px solid #666'  # Borda mais grossa entre semanas
            })]
            
            for semana in ultimas_semanas:
                dados = df_categorias[
                    (df_categorias['pcp_categoria'] == cat) & 
                    (df_categorias['ano_semana'] == semana)
                ]
                
                if not dados.empty:
                    planejado = int(dados['planejado'].iloc[0])
                    feito = int(dados['feito'].iloc[0])
                    total = int(dados['total'].iloc[0])
                    
                    # Calcular percentagens
                    perc_feito = (feito / planejado * 100) if planejado > 0 else 0
                    perc_total_sem_pcp = ((total - feito) / total * 100) if total > 0 else 0
                    
                    # Definir cores baseadas nas regras
                    cor_feito = '#dc3545' if perc_feito <= 70 else '#ffc107' if perc_feito <= 90 else '#28a745'
                    cor_total = '#dc3545' if perc_total_sem_pcp > 20 else '#ffc107' if perc_total_sem_pcp >= 10 else '#28a745'
                    
                    row_data.append(
                        html.Td([
                            html.Div([
                                # PLAN
                                html.Div(
                                    f"{planejado:,}".replace(",", "."),
                                    style={
                                        'width': '80px',
                                        'text-align': 'right',
                                        'display': 'inline-block',
                                        'white-space': 'nowrap',
                                        'padding-right': '8px',
                                        'border-right': '1px solid #dee2e6'
                                    }
                                ),
                                # FEITO com percentagem
                                html.Div(
                                    [
                                        f"{feito:,}".replace(",", "."),
                                        html.Span(
                                            f" ({perc_feito:.1f}%)",
                                            style={
                                                'color': cor_feito,
                                                'font-weight': 'bold',
                                                'margin-left': '4px'
                                            }
                                        )
                                    ],
                                    style={
                                        'width': '120px',
                                        'text-align': 'right',
                                        'display': 'inline-block',
                                        'white-space': 'nowrap',
                                        'padding-left': '8px',
                                        'padding-right': '8px',
                                        'border-right': '1px solid #dee2e6'
                                    }
                                ),
                                # TOTAL com percentagem
                                html.Div(
                                    [
                                        f"{total:,}".replace(",", "."),
                                        html.Span(
                                            f" ({perc_total_sem_pcp:.1f}%)",
                                            style={
                                                'color': cor_total,
                                                'font-weight': 'bold',
                                                'margin-left': '4px'
                                            }
                                        )
                                    ],
                                    style={
                                        'width': '120px',
                                        'text-align': 'right',
                                        'display': 'inline-block',
                                        'white-space': 'nowrap',
                                        'padding-left': '8px'
                                    }
                                )
                            ], style={
                                'display': 'flex',
                                'justify-content': 'space-between',
                                'align-items': 'center',
                                'white-space': 'nowrap'
                            })
                        ], style={
                            'padding': '8px',
                            'border-right': '2px solid #666'  # Borda mais grossa entre semanas
                        })
                    )
                else:
                    row_data.append(
                        html.Td([
                            html.Div([
                                html.Div(
                                    "0",
                                    style={
                                        'width': '80px',
                                        'text-align': 'right',
                                        'display': 'inline-block',
                                        'padding-right': '8px',
                                        'border-right': '1px solid #dee2e6'
                                    }
                                ),
                                html.Div(
                                    [
                                        "0",
                                        html.Span(
                                            " (0.0%)",
                                            style={
                                                'color': '#dc3545',
                                                'font-weight': 'bold',
                                                'margin-left': '4px'
                                            }
                                        )
                                    ],
                                    style={
                                        'width': '120px',
                                        'text-align': 'right',
                                        'display': 'inline-block',
                                        'white-space': 'nowrap',
                                        'padding-left': '8px',
                                        'padding-right': '8px',
                                        'border-right': '1px solid #dee2e6'
                                    }
                                ),
                                html.Div(
                                    [
                                        "0",
                                        html.Span(
                                            " (0.0%)",
                                            style={
                                                'color': '#28a745',
                                                'font-weight': 'bold',
                                                'margin-left': '4px'
                                            }
                                        )
                                    ],
                                    style={
                                        'width': '120px',
                                        'text-align': 'right',
                                        'display': 'inline-block',
                                        'white-space': 'nowrap',
                                        'padding-left': '8px'
                                    }
                                )
                            ], style={
                                'display': 'flex',
                                'justify-content': 'space-between',
                                'align-items': 'center',
                                'white-space': 'nowrap'
                            })
                        ], style={
                            'padding': '8px',
                            'border-right': '2px solid #666'  # Borda mais grossa entre semanas
                        })
                    )
            
            rows.append(html.Tr(row_data, style={'border-bottom': '1px solid #dee2e6'}))
        
        tabela = dbc.Table(
            [header, html.Tbody(rows)],
            bordered=True,
            hover=True,
            responsive=True,
            style={
                'margin-top': '20px',
                'width': '100%',
                'border-collapse': 'collapse',
                'font-size': '14px',
                'border': '2px solid #666'  # Borda externa mais grossa
            }
        )
        
        # Calcular métricas mensais
        metricas_mensais = calcular_metricas_mensais()
        
        # Criar cards para cada categoria
        cards_metas = []
        for categoria, dados in metricas_mensais.items():
            # Definir cores baseadas no progresso
            cor_meta = '#28a745' if dados['perc_meta'] >= 100 else '#ffc107' if dados['perc_meta'] >= 80 else '#dc3545'
            cor_var = '#28a745' if dados['var_mes_anterior'] > 0 else '#dc3545' if dados['var_mes_anterior'] < 0 else '#6c757d'
            
            card = dbc.Card([
                dbc.CardBody([
                    html.H6(categoria, className="card-title", style={'font-weight': 'bold'}),
                    html.Div([
                        html.Div([
                            html.Span(f"{dados['perc_meta']:.1f}% da meta", 
                                    style={'color': cor_meta, 'font-weight': 'bold', 'font-size': '1.1rem'}),
                            html.Br(),
                            html.Span(
                                f"{dados['var_mes_anterior']:+.1f}% vs mês anterior",
                                style={'color': cor_var, 'font-size': '0.9rem'}
                            )
                        ], style={'margin-bottom': '8px'}),
                        html.Div([
                            dbc.Progress(
                                value=min(100, dados['perc_meta']),
                                color='success' if dados['perc_meta'] >= 100 else 'warning' if dados['perc_meta'] >= 80 else 'danger',
                                className="mb-2",
                                style={'height': '8px'}
                            ),
                            # Linha de marcação do dia atual
                            html.Div(
                                style={
                                    'position': 'absolute',
                                    'height': '12px',
                                    'width': '2px',
                                    'backgroundColor': '#000',
                                    'left': f"{(datetime.now().day / calendar.monthrange(datetime.now().year, datetime.now().month)[1]) * 100}%",
                                    'top': '-2px',
                                    'zIndex': '1'
                                }
                            )
                        ], style={'position': 'relative'}),
                        html.Small(
                            f"Meta: {dados['meta']:,.0f} | Atual: {dados['total_atual']:,.0f}",
                            className="text-muted"
                        )
                    ])
                ])
            ], className="mb-2 shadow-sm", style={'border': '1px solid #dee2e6'})
            
            cards_metas.append(card)
        
        # Calcular pedidos em atraso
        df_atraso = calcular_pedidos_atraso()
        
        # Cartão de pedidos em atraso no mesmo estilo dos cartões de métricas
        total_atraso = len(df_atraso) if not df_atraso.empty else 0
        tem_atraso = total_atraso > 0

        # Lista completa: OS (pcp_pcp) e Produto abaixo do card
        lista_resumo: list = []
        if tem_atraso:
            itens = []
            # Ordena por data de entrega mais antiga primeiro
            df_listagem = df_atraso.sort_values(by=['pcp_entrega', 'pcp_pcp'], ascending=[True, True])
            for _, row in df_listagem.iterrows():
                os_numero = row.get('pcp_pcp')
                produto_nome = row.get('produto_nome', '')
                itens.append(
                    html.Div([
                        html.Span(
                            f"OS {int(os_numero) if pd.notna(os_numero) else '-'}",
                            style={'font-weight': '600'}
                        ),
                        html.Span(f" - {produto_nome}", className="text-muted")
                    ], className="small mb-1")
                )
            lista_resumo = [
                html.Hr(),
                html.Div(itens, style={'maxHeight': '440px', 'overflowY': 'auto', 'paddingRight': '4px'})
            ]
        cartao_atraso = dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(
                        className="fas fa-exclamation-triangle me-2",
                        style={'font-size': '24px', 'color': ('#e74c3c' if tem_atraso else '#2ecc71')}
                    ),
                    html.H4("Pedidos em Atraso", className="card-title d-inline")
                ], style={'margin-bottom': '10px'}),
                html.H2(
                    f"{total_atraso:,}".replace(",", "."),
                    className=("text-danger mb-0" if tem_atraso else "text-success mb-0")
                ),
                html.P(
                    "Ordens fora do prazo" if tem_atraso else "Nenhum pedido em atraso",
                    className="card-text text-muted",
                    style={'margin-top': '5px'}
                ),
                *lista_resumo
            ])
        ], className="h-100 shadow-sm", style={'border-radius': '10px', 'border': '1px solid #e0e0e0'})
        
        # Construir gráfico de atrasos por semana (horizontal)
        # Cálculo por fotografia semanal: para cada semana, quantidade de OS cujo prazo (pcp_entrega)
        # era até o fim daquela semana e cujo total baixado acumulado até aquela semana < 90% da quantidade planejada
        with engine.connect() as conn:
            df_pcp_base = pd.read_sql(
                """
                SELECT p.pcp_id, p.pcp_qtd, p.pcp_entrega
                FROM pcp p
                LEFT JOIN produtos prod ON p.pcp_produto_id = prod.produto_id
                WHERE prod.fluxo_producao = 'Puxado' AND p.pcp_entrega IS NOT NULL AND p.pcp_correncia IS NULL
                """,
                conn
            )
            df_baixas_all = pd.read_sql(
                """
                SELECT pcp_id, qtd, data
                FROM baixa
                WHERE (ajuste != 1 OR ajuste IS NULL)
                """,
                conn
            )

        if not df_pcp_base.empty:
            df_pcp_base['pcp_entrega'] = pd.to_datetime(df_pcp_base['pcp_entrega'])
            df_baixas_all['data'] = pd.to_datetime(df_baixas_all['data'])

            hoje = datetime.now().date()
            inicio_sem_atual = hoje - timedelta(days=hoje.weekday())
            # últimas 10 semanas incluindo a atual
            semanas_fim = [(inicio_sem_atual + timedelta(days=6)) - timedelta(weeks=w) for w in range(9, -1, -1)]

            registros = []
            for fim_semana in semanas_fim:
                # acumulado de baixas até o fim da semana
                baixas_ate_sem = (df_baixas_all[df_baixas_all['data'] <= pd.to_datetime(fim_semana)]
                                  .groupby('pcp_id')['qtd']
                                  .sum()
                                  .rename('qtd_baixada'))
                df_status = df_pcp_base.copy()
                df_status = df_status[df_status['pcp_entrega'] <= pd.to_datetime(fim_semana)]
                df_status = df_status.merge(baixas_ate_sem, left_on='pcp_id', right_index=True, how='left')
                df_status['qtd_baixada'] = df_status['qtd_baixada'].fillna(0)
                df_status['em_atraso'] = df_status['qtd_baixada'] < (0.9 * df_status['pcp_qtd'])
                qtd_atraso = int(df_status['em_atraso'].sum())
                iso = pd.to_datetime(fim_semana).isocalendar()
                label_sem = f"{iso.year}-S{str(iso.week).zfill(2)}"
                registros.append({'ano_semana': label_sem, 'qtd': qtd_atraso})

            atrasos_semana = pd.DataFrame(registros)
        else:
            atrasos_semana = pd.DataFrame({'ano_semana': [], 'qtd': []})

        fig_atrasos = go.Figure()
        if not atrasos_semana.empty:
            fig_atrasos.add_trace(go.Bar(
                x=atrasos_semana['qtd'],
                y=atrasos_semana['ano_semana'],
                orientation='h',
                marker=dict(color='#e74c3c', line=dict(color='#c0392b', width=1.5)),
                text=atrasos_semana['qtd'],
                textposition='outside',
                insidetextanchor='end',
                hovertemplate='Semana: %{y}<br>Atrasos: %{x}<extra></extra>'
            ))
            fig_atrasos.update_layout(
                height=320,
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(l=60, r=10, t=10, b=20),
                xaxis=dict(
                    title='Quantidade',
                    gridcolor='#e0e0e0',
                    zerolinecolor='#e0e0e0'
                ),
                yaxis=dict(title='Semana')
            )
        else:
            fig_atrasos.update_layout(height=320, plot_bgcolor='white', paper_bgcolor='white')

        # Construir gráfico de pendências (status != FEITO): soma pcp_qtd por categoria e semana
        try:
            with engine.connect() as conn:
                df_nf = pd.read_sql(
                    """
                    SELECT p.pcp_id, p.pcp_pcp, p.pcp_categoria, p.pcp_qtd, p.pcp_entrega,
                           prod.nome AS produto_nome, cli.nome AS cliente_nome,
                           CASE WHEN (
                               SELECT COALESCE(SUM(b.qtd),0) FROM baixa b
                               WHERE b.pcp_id = p.pcp_id AND (b.ajuste != 1 OR b.ajuste IS NULL)
                           ) >= (0.9 * p.pcp_qtd) THEN 'FEITO' ELSE 'NAO_FEITO' END AS status_calc
                    FROM pcp p
                    LEFT JOIN produtos prod ON p.pcp_produto_id = prod.produto_id
                    LEFT JOIN clientes cli ON p.pcp_cliente_id = cli.cliente_id
                    WHERE p.pcp_entrega IS NOT NULL
                      AND p.pcp_correncia IS NULL
                    """,
                    conn
                )
            df_nf['pcp_entrega'] = pd.to_datetime(df_nf['pcp_entrega'])
            iso = df_nf['pcp_entrega'].dt.isocalendar()
            df_nf['ano_semana'] = iso.year.astype(str) + '-S' + iso.week.astype(str).str.zfill(2)
            df_nf_pend = df_nf[df_nf['status_calc'] != 'FEITO']
            # nf_cat é lista (multi=True); se vazio/None, não mostra nada
            if nf_cat:
                df_nf_pend = df_nf_pend[df_nf_pend['pcp_categoria'].isin(nf_cat)]
            else:
                df_nf_pend = df_nf_pend.iloc[0:0]
            df_nf_grp = df_nf_pend.groupby(['ano_semana','pcp_categoria'])['pcp_qtd'].sum().reset_index()
            # Pivot para barras agrupadas por semana
            df_pivot = df_nf_grp.pivot(index='ano_semana', columns='pcp_categoria', values='pcp_qtd').fillna(0)
            fig_nf = go.Figure()
            for cat in df_pivot.columns:
                fig_nf.add_bar(name=cat, x=df_pivot.index, y=df_pivot[cat])
            fig_nf.update_layout(
                barmode='group',
                height=360,
                plot_bgcolor='white', paper_bgcolor='white',
                margin=dict(l=30, r=10, t=10, b=30),
                xaxis_title='Semana', yaxis_title='PCP QTD (pendente)',
                xaxis=dict(gridcolor='#e0e0e0'), yaxis=dict(gridcolor='#e0e0e0')
            )
            # Construir lista detalhada por semana > categoria > item (nome) com pcp_qtd
            if not df_nf_pend.empty:
                lista_children = []
                for semana in sorted(df_nf_pend['ano_semana'].unique()):
                    lista_children.append(html.H6(f"Semana {semana}", className='mt-2'))
                    df_sem = df_nf_pend[df_nf_pend['ano_semana'] == semana]
                    for cat in sorted(df_sem['pcp_categoria'].unique()):
                        lista_children.append(html.Div(str(cat), className='fw-bold small', style={'marginTop': '4px'}))
                        df_cat = df_sem[df_sem['pcp_categoria'] == cat]
                        for _, r in df_cat.iterrows():
                            os_txt = f"OS {int(r['pcp_pcp'])}" if pd.notna(r['pcp_pcp']) else "OS -"
                            prod_txt = r.get('produto_nome') or ''
                            cli_txt = r.get('cliente_nome') or ''
                            qtd_txt = f"{int(r['pcp_qtd']):,}".replace(',', '.') if pd.notna(r['pcp_qtd']) else '0'
                            lista_children.append(html.Div(f"- {os_txt} - {prod_txt} - {cli_txt}: {qtd_txt}", className='small'))
                lista_nf = html.Div(lista_children)
            else:
                lista_nf = html.Div()
        except Exception:
            fig_nf = go.Figure()
            lista_nf = html.Div()

        return (
            fig,
            f"{total_planejado:,}".replace(",", "."),
            f"{total_executado:,}".replace(",", "."),
            f"Total geral: {total_geral_baixas:,}".replace(",", "."),
            html.Span(f"{eficiencia_atual:.1f}%", className=eficiencia_cor),
            html.Span(f"{kpi_quantidade:.1f}%", className=kpi_cor),
            cartao_atraso,
            tabela,
            fig_atrasos,
            fig_nf,
            lista_nf
        )
    
    return (
        fig,
        f"{total_planejado:,}".replace(",", "."),
        f"{total_executado:,}".replace(",", "."),
        f"Total geral: {total_geral_baixas:,}".replace(",", "."),
        html.Span(f"{eficiencia_atual:.1f}%", className=eficiencia_cor),
        html.Span(f"{kpi_quantidade:.1f}%", className=kpi_cor),
        html.Div("Sem dados disponíveis"),
        go.Figure(),
        html.Div([]),
        go.Figure(),
        html.Div()
    )
