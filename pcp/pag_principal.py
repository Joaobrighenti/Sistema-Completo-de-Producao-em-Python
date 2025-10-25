from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, timedelta
import dash
from app import app
import io
from pcp.painel_chapas import *
from rascunho.tab_estoque import tabela_estoque, relatorio_estoque
from pcp.formularios import form_lembretes, form_planejamento, form_retirada
from pcp.tabela_principal import personalizar_tabela
from pcp.movimentacao_baixa import gerar_cards_movimentacao, gera_cabecalho_movimentacao
from pcp.movimentacao_retirada import gera_cabecalho_retirada, gerar_cards_retirada
from pcp.painel_chapas import painel_chapas
from pcp.gestao_facas import layout_gestao_facas
from pcp.planejamento import planejamento
from modulo_pizza.Entregas_pizza import layout_dashboard as pizza_layout
from pcp.formularios import form_solicitacao
from calculos import *
from banco_dados.banco import listar_pcp, df_clientes, listar_dados, juncao, listar_lembretes, Banco
import json
from openpyxl.styles import Alignment

banco = Banco()
df_setores = banco.ler_tabela('setor')
setor_options = [{'label': 'Todos os Setores', 'value': 'todos'}] + \
                [{'label': row['setor_nome'], 'value': row['setor_id']} for index, row in df_setores.iterrows()]

def relatorio_planejamento(semana=None, comparacao_semana='=='):
    banco = Banco()
    df_plan = banco.ler_tabela('planejamento')
    df_pcp = listar_pcp()
    
    # Merge and filter data similar to the planning page
    df_merged = pd.merge(df_plan, df_pcp, left_on='id_pcp', right_on='pcp_id', how='left')
    df_merged['data_programacao'] = pd.to_datetime(df_merged['data_programacao'], errors='coerce')
    
    if semana and comparacao_semana:
        df_merged['semana_prog'] = df_merged['data_programacao'].dt.isocalendar().week.astype('Int64')
        df_merged = Filtros.filtrar(df_merged.copy(), {'semana_prog': ('comparar_num', (comparacao_semana, semana))})
    
    # Rename columns for the report
    mapeamento_colunas = {
        'plan_id': 'ID Plan', 'id_pcp': 'ID PCP', 'pcp_pcp': 'PCP OS',
        'pcp_categoria': 'Categoria', 'cliente_nome': 'Cliente',
        'produto_nome': 'Produto', 'pcp_qtd': 'Qtd Total OP',
        'quantidade': 'Qtd Planejada', 'data_programacao': 'Data Prog.',
        'observacao': 'Obs. Plan.', 'plano_setor': 'plano_setor'
    }
    df_relatorio = df_merged.rename(columns=mapeamento_colunas)
    
    colunas_finais = list(mapeamento_colunas.values())
    return df_relatorio[colunas_finais]
 
# ========= Styles ========= #
card_style={'height': '100%',  'margin-bottom': '12px'}
 
 
 
layout = dbc.Container([
form_planejamento.layout,
form_retirada.layout,
form_lembretes.layout,
form_solicitacao.layout,
 
# Store para controlar a página atual do painel de chapas
dcc.Store(id='store-pagina-chapas', data=1),
 
    dbc.Row(
    [
        dbc.Col(
            children=[
                dbc.Button(
                    html.I(className="fa fa-bars"),
                    id="btn-toggle-sidebar",
                    color="light",
                    style={'marginRight': '15px'}
                ),
                html.H3(
                    "GRUPO NICOPEL",
                    style={
                        'text-align': 'left',
                        'color': '#FFFFFF',
                        'margin': '0'
                    }
                ),
            ],
            width=10,
            style={'display': 'flex', 'align-items': 'center'}
        ),
        dbc.Col(
            [  
                dbc.Button(
                    html.I(className="fa fa-shopping-cart"),
                    id="btn-solicitacao_compras",
                    color="danger",
                    style={'margin-left': '8px'}
                ),
                dbc.Button(
                    html.I(className="fa fa-desktop"),
                    id="btn-planejamento",
                    color="success",
                    style={'margin-left': '8px'}
                ),
                dbc.Button(
                    html.I(className="fa fa-th-large"),
                    id="abrir_modal_chapa",
                    color="primary",
                    style={'margin-left': '8px'}
                ),
                dbc.Button(
                    html.I(className="fa fa-sticky-note"),
                    id="btn_lembretes",
                    color="dark",
                    style={'margin-left': '8px'}
                ),
                dbc.Button(
                    html.I(className="fa fa-spinner"),
                    id="btn_refresh_clientes",
                    color="warning",
                    style={'margin-left': '8px'}
                )
            ],
            width=2,
            style={
                'text-align': 'right',
                'display': 'flex',
                'align-items': 'center',
                'justify-content': 'flex-end'
            }
        ),
    ],
    id='header-row',
    style={
    'background-color': '#02083d',
    'padding': '10px 20px',
    'border-radius': '0 0 8px 8px',
    'box-shadow': '2px 2px 5px rgba(0, 0, 0, 0.3)',
    'position': 'fixed',
    'top': '0',
    'left': '18vw',  # 👈 RESOLVE sem quebrar o grid
    'right': '0',
    'zIndex': '9999',
    'width': 'calc(100vw - 19vw)',  # 👈 ajusta o tamanho real para compensar o left
    'margin': '0',
    'transition': 'left 0.3s, width 0.3s'
}
),
html.Div(style={'height': '70px'}),
    dbc.Row([
        #filtros =========================================
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                #COLUNA 1 =========================
                                dbc.Col([
                                   
                                    dbc.Row([
                                        dbc.Col([
                                            dcc.Dropdown(
                                                id='visualizacao_select',
                                                options=[
                                                    {'label': 'Tabela Completa', 'value': 'tabela'},
                                                    {'label': 'Planejamento Semanal', 'value': 'planejamento_semanal'},  
                                                    {'label': 'Movimentação Tabela', 'value': 'movimentacao_tabela'},
                                                    {'label': 'Movimentação Retirada', 'value': 'movimentacao_retirada'},
                                                    #{'label': 'Controle de P.A em Estoque', 'value': 'estoque_pa'},
                                                    {'label': 'Painel Chapas', 'value': 'painel_chapas'},
                                                    {'label': 'Gestão de Facas', 'value': 'gestao_facas'},    
                                                ],
                                                value='tabela',  # Valor inicial
                                                placeholder='Escolha a visualização',
                                                className='dbc'
                                            )
                                        ]),
                                        html.Div(style={"margin-top": "2px"}),
                                        dbc.Col([
                                            # New dropdown for indicators filter
                                            dcc.Dropdown(
                                                id='indicadores_filter',
                                                options=[
                                                    {'label': '🚚 Terceirização', 'value': '🚚'},
                                                    {'label': '🔪 BOPP', 'value': '🔪'},
                                                    {'label': '🚫 Retrabalho', 'value': '🚫'},
                                                    {'label': '🔑 Aprovado', 'value': '🔑'},
                                                ],
                                                multi=True,
                                                placeholder='Filtrar por indicadores',
                                                className='dbc'
                                            )
                                        ]),
                                        html.Div(style={"margin-top": "2px"}),
                                        dbc.Col([
                                            html.Div([
                                                html.Label("Mostrar quebra por partes?", style={'fontWeight': 'bold', 'marginRight': '10px'}),
                                                dbc.RadioItems(
                                                    id='toggle-partes-planejamento',
                                                    options=[
                                                        {'label': 'Sim', 'value': 'sim'},
                                                        {'label': 'Não', 'value': 'nao'}
                                                    ],
                                                    value='sim',
                                                    inline=True,
                                                    labelStyle={'marginRight': '10px'},
                                                    inputStyle={'marginRight': '5px'}
                                                )
                                            ], style={'display': 'flex', 'alignItems': 'center', 'padding': '5px'})
                                        ], id='filtro-setor-container', style={'display': 'none'}),
                                    ]),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Button(
                                                    "Exportação",
                                                    id='btn_exp_excel',
                                                    style={
                                                        'color': 'white',
                                                        'backgroundColor': '#28a745',  # Verde moderno
                                                        'padding': '6px 0',  # Reduz altura do botão
                                                        'borderRadius': '8px',  # Cantos levemente arredondados
                                                        'border': 'none',
                                                        'boxShadow': '0px 4px 6px rgba(0, 0, 0, 0.1)',
                                                        'transition': 'all 0.3s ease-in-out',
                                                        'width': '100%',  # Ocupa toda a largura disponível
                                                        'textAlign': 'center',
                                                        'fontSize': '16px'  # Ajuste do tamanho da fonte para manter a proporção
                                                    },
                                                    size='md',  # Tamanho médio para evitar que fique muito alto
                                                    outline=False
                                                ),
                                                width=12  # Garante que a coluna ocupa toda a largura
                                            ),
                                            dcc.Download(id="download_excel")
                                        ],
                                        justify="center",
                                        align="center",
                                        className="mt-3"
                                    )
                                ]),
                                #COLUNA 4 =========================
                                dbc.Col([
                         
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Input(id='procurar_ordem',
                                                placeholder="O.S.",
                                                type="text",
                                                style={'height': '37px',
                                                        'border': '2px solid #D3D3D3',
                                                        'border-radius': '4px'})
                                        ], width=6, style={'padding': '0', 'margin': '0', 'padding-right': '4px'}),
                                        dbc.Col([
                                            dcc.Dropdown(
                                                id='ocorrencia_ordem_producao',
                                                options=[
                                                    {'label': 'Cancelados', 'value': 0},
                                                    {'label': 'Prorrogados', 'value': 1},
                                                    {'label': 'Lixo', 'value': 2},
                                                    {'label': 'Variação', 'value': 3}
                                                ],
                                               
                                                className='dbc',
                                                style={
                                                    'height': '37px',
                                                    'minHeight': '37px',
                                                    'width': '100%'
                                                },
                                               
                                                clearable=True
                                            )
                                        ], width=6, style={'padding': '0', 'margin': '0'})
                                    ], style={'padding': '0', 'margin': '0', 'width': '100%'}),  # Remover padding e margin da linha
 
                                    dbc.Row([
                                        dbc.Input(id='procurar_ordem_compra',
                                                placeholder="Ordem de Compra...",
                                                type="text",
                                                style={'height': '37px',
                                                        'margin-top': '4px',
                                                        'border': '2px solid #D3D3D3',
                                                        'border-radius': '4px'})
                                    ], style={'padding': '0', 'margin': '0'}),  # Remover padding e margin da linha
 
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Input(id='procurar_produto',
                                                    placeholder="Produto...",
                                                    type="text",
                                                    style={'height': '37px',
                                                            'margin-top': '4px',
                                                            'border': '2px solid #D3D3D3',
                                                            'border-radius': '4px'})
                                        ], style={'padding': '0', 'margin': '0', 'margin-right': '4px'}),  # Espaço entre os campos
 
                                        dbc.Col([
                                            dbc.Input(id='codigo_produto',
                                                    placeholder="Código...",
                                                    type="text",
                                                    style={'height': '37px',
                                                            'margin-top': '4px',
                                                            'border': '2px solid #D3D3D3',
                                                            'border-radius': '4px'})
                                        ],  style={'padding': '0', 'margin': '0'})
                                    ], justify="start", style={'padding': '0', 'margin': '0'})  # Alinhar tudo à esquerda e remover padding/margin
                                ], style={'padding': '0', 'margin': '0'}),  # Remover padding e margin da coluna principal
                                #COLUNA 3 =========================
                                dbc.Col([
                           
                                    dbc.Row([
                                        dbc.Col([
                                            dcc.Checklist(
                                                id='check_pote',
                                                options=[{'label': ' Pote', 'value': 'POTE'}],
                                                value=[],  # Nenhum Pote selecionado inicialmente
                                                inline=True,  # Para manter o checkbox na mesma linha
                                            ),
                                        ], sm=3, md=3),
                                        dbc.Col([
                                            dcc.Dropdown(
                                                id='categoria_filter',
                                                options=['CAIXA 5L', 'CAIXA 10L', 'CAIXA 7L', 'TAMPA 10L', 'TAMPA 5L', 'ESPECIAL', 'CINTA', 'PIZZA',
                                                        'POTE 500ML', 'POTE 480ML', 'POTE 240ML', 'POTE 250ML',
                                                        'POTE 1L', 'POTE 360ML', 'POTE 180ML', 'POTE 150ML',
                                                        'POTE 120ML', 'POTE 80ML', 'COPO 360ML', 'COPO 200ML', 'COPO 100ML'],
                                                placeholder='Categoria',
                                                multi=True,
                                                className='dbc'
                                            ),
                                        ], sm=9, md=9),
                                       
                                    ]),
                                    dbc.Row([
                                        dbc.Col([
                                            dcc.Checklist(
                                                id='check_cliente',
                                                options=[{'label': ' Fora', 'value': '=!'}],
                                                value=[],  # Nenhum Pote selecionado inicialmente
                                                inline=True,  # Para manter o checkbox na mesma linha
                                            ),
                                        ], sm=3, md=3),
                                        dbc.Col([
                                        dcc.Dropdown(
                                        id='cliente_filter',
                                        options=[{'label': i, 'value': i} for i in df_clientes['nome']],
                                        placeholder='Cliente',
                                        className='dbc'
                                    ),
                                    ], sm=9, md=9),
                                    ], style={'margin-top': '4px'}),
                                    dbc.Row([
                                        dcc.Dropdown(
                                        id='status_produto',
                                        options=['FEITO', 'PARCIAL', 'PENDENTE'],
                                        value=['PARCIAL', 'PENDENTE'],  # Valores padrão
                                        placeholder='Status',
                                        multi=True,
                                        className='dbc'
                                    ),
                                    ], style={'margin-top': '4px'}),
                                    ]),
                                #COLUNA 4 =========================
                                dbc.Col([
                               
 
                                    dbc.Row([  # Linha do ano (desabilitado)
                                        dbc.Col([  # Coluna do ano
                                            dcc.Dropdown(
                                                id='select_ano',
                                                options=[{'label': '2025', 'value': '2025'}],
                                                value='2025',
                                                placeholder="Ano",
                                                className='dbc',
                                                disabled=True,
                                                style={'width': '100%'}  # Garante que o Dropdown ocupe toda a largura da coluna
                                            ),
                                        ])
                                    ]),
 
                                    dbc.Row([  # Linha de comparação e semana
                                        dbc.Col([  # Coluna de comparação
                                            dcc.Dropdown(
                                                id='select_comparacao_semana',
                                                options=[
                                                    {'label': '=', 'value': '=='},
                                                    {'label': '>=', 'value': '>='},
                                                    {'label': '<=', 'value': '<='},
                                                    {'label': '>', 'value': '>'},
                                                    {'label': '<', 'value': '<'},
                                                ],
                                                value='==',
                                                placeholder="",
                                                className='dbc',
                                                style={'width': '100%'}
                                            ),
                                        ], width=4),  # Controla a largura da coluna da comparação
 
                                        dbc.Col([  # Coluna da semana
                                            dcc.Dropdown(
                                                id='select_semana',
                                                options=[{"label": f"{i}", "value": i} for i in range(1, 53)],
                                                placeholder="Semana",
                                                className='dbc',
                                                style={'width': '100%'}
                                            ),
                                        ], width=8)  # Controla a largura da coluna para a "Semana"
                                    ], style={'margin-top': '4px'}),  # Alinhamento da linha de comparação
 
                                    dbc.Row([  # Linha da data exata
                                        dbc.Col([  # Coluna de entrada de data
                                            dbc.Input(
                                                id='data_exata',
                                                placeholder="dd/mm/aaaa",
                                                type="text",
                                                style={
                                                    'height': '37px',
                                                    'border': '2px solid #D3D3D3',
                                                    'border-radius': '4px',
                                                    'width': '100%'  # Garante que o campo de entrada ocupe toda a largura
                                                }
                                            ),
                                        ])
                                    ], style={'padding': '0', 'margin-top': '4px'}),  # Alinhamento da linha de data
                                ]),                                                                  
                                #COLUNA 5 =========================
                                dbc.Col([
                             
                                    # Linha dos primeiros botões
                                    dbc.Row(
                                        [
                                            dcc.Dropdown(
                                                id='select_tipo_produto',
                                                options=[
                                                    {'label': 'ESTOQUE', 'value': 'Empurrado'},
                                                    {'label': 'PEDIDO', 'value': 'Puxado'},
                                   
                                                ],
                                                value='Puxado',  # Valor padrão
                                                placeholder="Estoque/Pedido",
                                                className='dbc',
                                                style={'width': '100%'}
                                            ),
                                   
                                        ],
                                        style={'display': 'flex', 'justify-content': 'center'}  # Garante que os botões fiquem mais próximos
                                    ),
 
                                    # Linha dos segundos botões - Dropdown Chapa e Checklist Vazias
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dcc.Dropdown(
                                                    id='select_chapa',
                                                    placeholder="Chapa",
                                                    className='dbc',
                                                    style={'width': '100%'}
                                                ),
                                                width=8  # Dropdown ocupa 8 colunas
                                            ),
                                            dbc.Col(
                                                dcc.Checklist(
                                                    id='check_chapas_vazias',
                                                    options=[{'label': '  Vazias', 'value': 'VAZIAS'}],
                                                    value=[],
                                                    inline=True,
                                                    labelStyle={'display': 'flex', 'align-items': 'center', 'height': '37px'} # Alinha verticalmente com o dropdown
                                                ),
                                                width=4  # Checklist ocupa 4 colunas
                                            )
                                        ],
                                        align="center", # Alinha itens verticalmente no centro da linha
                                        style={'margin-top': '4px'} # Mantém a margem superior
                                    )
                                ,
 
                                    # Linha dos filtros de Status da Chapa (OS e Arte)
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dcc.Dropdown(
                                                    id='filter_chapa_os',
                                                    options=[
                                                        {'label': 'OS: Todas', 'value': 'Todas'},
                                                        {'label': 'OS: Feitas', 'value': 'Feitas'},
                                                        {'label': 'OS: Pendentes', 'value': 'Pendentes'}
                                                    ],
                                                    value='Todas',
                                                    placeholder="Status OS",
                                                    className='dbc',
                                                    clearable=False,
                                                    style={'width': '100%'}
                                                ),
                                                width=6
                                            ),
                                            dbc.Col(
                                                dcc.Dropdown(
                                                    id='filter_chapa_arte',
                                                    options=[
                                                        {'label': 'Arte: Todas', 'value': 'Todas'},
                                                        {'label': 'Arte: Feitas', 'value': 'Feitas'},
                                                        {'label': 'Arte: Pendentes', 'value': 'Pendentes'}
                                                    ],
                                                    value='Todas',
                                                    placeholder="Status Arte",
                                                    className='dbc',
                                                    clearable=False,
                                                    style={'width': '100%'}
                                                ),
                                                width=6
                                            )
                                        ],
                                        style={'margin-top': '4px'} # Espaçamento acima desta linha
                                    )
 
                                ])
 
                            #FIM =========================
 
                            ])
                            ], style={'margin-top': '1px'})
                        ], style={'margin': '10px'},className='card-borda-preta')
                    ])
                ])
            ])      
    ]),
    #KANBAN DE DIAS PARA PRODUCAO
    dbc.Row([
    dbc.Col([
        dbc.Container(id='card_generator_dia1', fluid=True, style={'width': '100%', 'padding': '0px', 'margin': '0px'})
    ], sm=12, md=2, lg=2),
   
    dbc.Col([
        dbc.Container(id='card_generator_dia2', fluid=True, style={'width': '100%', 'padding': '0px', 'margin': '0px'})
    ], sm=12, md=2, lg=2),
   
    dbc.Col([
        dbc.Container(id='card_generator_dia3', fluid=True, style={'width': '100%', 'padding': '0px', 'margin': '0px'})
    ], sm=12, md=2, lg=2),
   
    dbc.Col([
        dbc.Container(id='card_generator_dia4', fluid=True, style={'width': '100%', 'padding': '0px', 'margin': '0px'})
    ], sm=12, md=2, lg=2),
   
    dbc.Col([
        dbc.Container(id='card_generator_dia5', fluid=True, style={'width': '100%', 'padding': '0px', 'margin': '0px'})
    ], sm=12, md=2, lg=2),
   
    dbc.Col([
        dbc.Container(id='card_generator_dia6', fluid=True, style={'width': '100%', 'padding': '0px', 'margin': '0px'})
    ], sm=12, md=2, lg=2),
   
   
    dbc.Col([
        dbc.Container(id='tabela_pcp', fluid=True, children=[]),  # Este já está no seu layout
        # Certifique-se de adicionar 'tabela_pcp_cal' também
        dash_table.DataTable(id='tabela_pcp_cal', columns=[], data=[], cell_selectable=True, style_table={})
    ])
])
   
], fluid=True)

@app.callback(
    [
        Output('card_generator_dia1', 'children'),
        Output('card_generator_dia2', 'children'),
        Output('card_generator_dia3', 'children'),
        Output('card_generator_dia4', 'children'),
        Output('card_generator_dia5', 'children'),
        Output('card_generator_dia6', 'children'),
        Output('tabela_pcp', 'children'),
        Output("download_excel", "data"),
        Output('informacoes-personalizadas', 'children'),
        Output('informacoes-personalizadas-2', 'children')
    ],
    [
        Input('btn_refresh_clientes', 'n_clicks'),
        Input("btn_exp_excel", "n_clicks"),
        Input('select_tipo_produto', 'value'),
        Input('procurar_produto', 'value'),
        Input('status_produto', 'value'),
        Input('categoria_filter', 'value'),
        Input('select_ano', 'value'),
        Input('select_semana', 'value'),
        Input('cliente_filter', 'value'),
        Input('visualizacao_select', 'value'),
        Input('procurar_ordem', 'value'),
        Input('procurar_ordem_compra', 'value'),
        Input('codigo_produto', 'value'),
        Input('check_pote', 'value'),
        Input('check_chapas_vazias', 'value'),
        Input('filter_chapa_os', 'value'),
        Input('filter_chapa_arte', 'value'),
        Input('select_comparacao_semana', 'value'),
        Input('ocorrencia_ordem_producao', 'value'),
        Input('select_chapa', 'value'),
        Input('store-pagina-chapas', 'data'),
        Input('indicadores_filter', 'value'),  # New input for indicators filter
        Input('toggle-partes-planejamento', 'value'),
    ]
)
def atualizar_cards(n, click_excel, tipo_produto, produto, status,
    categoria, ano, semana, cliente, visualizacao, ordem_filtro, oc, cod_prod, opcao_pote, chapas_vazias_check,
    filtro_os, filtro_arte, comparacao_semana, ocorrencia, chapa_selecionada, pagina_chapas, indicadores_selecionados, mostrar_partes):
 
    #FILTROS =========================================
    df_pcp = listar_pcp()
 
    df_filtrado = df_pcp.copy()
    trigg_id = callback_context.triggered[0]['prop_id'].split('.')[0]
 
    try:
        df_filtrado['pcp_entrega'] = pd.to_datetime(df_filtrado['pcp_entrega'], errors='coerce')
        df_filtrado['pcp_emissao'] = pd.to_datetime(df_filtrado['pcp_emissao'], errors='coerce')
       
        linhas_invalidas = df_filtrado[df_filtrado['pcp_entrega'].isna()]
        if not linhas_invalidas.empty:
            print("Linhas com 'pcp_entrega' inválidas:")
            print(linhas_invalidas)
 
        df_filtrado = df_filtrado.dropna(subset=['pcp_entrega'])
 
        df_filtrado['pcp_ano'] = df_filtrado['pcp_entrega'].dt.year.astype(int)
        df_filtrado['pcp_sem'] = df_filtrado['pcp_entrega'].dt.isocalendar().week.astype(int)
 
        # Apply indicators filter
        if indicadores_selecionados:
            # Create a mask for each selected indicator
            mask = pd.Series([False] * len(df_filtrado))
            for indicador in indicadores_selecionados:
                if indicador == '🚚':
                    # Filter for terceirização
                    terceirizacao_mask = df_filtrado.apply(
                        lambda row: any(row[col] == 1 or row[col] is True
                                    for col in ['pcp_tercereizacao', 'pcp_tercerizacao', 'pcp_terceirizacao']
                                    if col in row),
                        axis=1
                    )
                    mask = mask | terceirizacao_mask
                elif indicador == '🔪':
                    # Filter for BOPP
                    bopp_mask = df_filtrado['pcp_bopp'] == 1
                    mask = mask | bopp_mask
                elif indicador == '🚫':
                    # Filter for Retrabalho
                    retrabalho_mask = df_filtrado['pcp_retrabalho'] == 1
                    mask = mask | retrabalho_mask
                elif indicador == '🔑':
                    # Filter for Aprovado
                    aprovado_mask = df_filtrado['pcp_retrabalho'] == 2
                    mask = mask | aprovado_mask
           
            df_filtrado = df_filtrado[mask]
 
    except Exception as e:
        print(f"Erro ao processar o DataFrame: {e}")
 
    opcao_pote = opcao_pote[0] if opcao_pote else None
   
    df_filtrado_final = Filtros.filtrar(df_filtrado,
    {
    'cliente_nome': ('exato', cliente),
   
    'pcp_pcp': ('contem', ordem_filtro),
    'produto_nome': ('contem', produto),
    'pcp_categoria': ('multi', categoria),
    'pcp_oc': ('contem', oc),
    'pcp_cod_prod': ('contem', cod_prod),
    })
 
    df_filtrado_final = Filtros.filtrar(df_filtrado_final,
    {
    'pcp_categoria': ('contem', opcao_pote),
    })
 
    # Filtro para chapas vazias
    chapas_vazias = chapas_vazias_check[0] if chapas_vazias_check else None
    if chapas_vazias == 'VAZIAS':
        # Filtrar registros onde pcp_chapa_id é nulo, vazio ou NaN
        df_filtrado_final = df_filtrado_final[
            df_filtrado_final['pcp_chapa_id'].isna() |
            (df_filtrado_final['pcp_chapa_id'] == '') |
            (df_filtrado_final['pcp_chapa_id'] == 'None')
        ]
   
    # Filtro para chapa específica selecionada
    if chapa_selecionada:
        # Converter para string para comparação
        df_filtrado_final = df_filtrado_final[
            df_filtrado_final['pcp_chapa_id'].astype(str) == str(chapa_selecionada)
        ]
 
    # Função para ler lembretes pendentes e criar cards para a sidebar
    def gerar_lembretes_sidebar():
        try:
            # Obter lembretes pendentes
            df_lembretes = listar_lembretes('pendente')
           
            if df_lembretes.empty:
                return []
           
            # Formatar data para exibição
            df_lembretes['data'] = pd.to_datetime(df_lembretes['data']).dt.strftime('%d/%m/%Y')
           
            # Criar um card para cada lembrete pendente
            cards = []
            for _, row in df_lembretes.iterrows():
                card = dbc.Card(
                    dbc.CardBody([
                        html.H6(f"Lembrete: {row['data']}", className="card-subtitle mb-2 text-muted"),
                        html.P(row['lembrete'], className="card-text"),
                    ]),
                    className="mb-3 border-warning",  # Borda amarela para lembretes pendentes
                    style={"background-color": "#fff3cd"}  # Fundo amarelo claro
                )
                cards.append(card)
           
            return html.Div([
                html.H5("Lembretes Pendentes", className="mb-3"),
                html.Div(cards)
            ], id="informacoes-personalizadas-2", style={'margin-top': '15px'})
        except Exception as e:
            print(f"Erro ao gerar lembretes: {e}")
            return []
   
    #====================================================================
    if trigg_id == 'btn_exp_excel':
        if visualizacao == 'planejamento_semanal':
            df = relatorio_planejamento(semana=semana, comparacao_semana=comparacao_semana)
            excel_data = to_excel_with_sectors(df)
            file_name = f"Relatorio_Planejamento_Semana_{semana}.xlsx"
        elif visualizacao == 'estoque_pa':
            df = relatorio_estoque(df_filtrado, cliente, produto, categoria, tipo_produto)
            excel_data = to_excel(df)
            file_name = "Relatorio_Estoque_PA.xlsx"
        else:
            df = relatorio_tabela(df_filtrado_final, status, semana)
            excel_data = to_excel(df)
            file_name = "Relatorio_PCP.xlsx"
           
        return [
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dcc.send_bytes(excel_data.getvalue(), file_name),
            dash.no_update,    # Retorna um componente vazio para garantir que a tabela desapareça
            dash.no_update
        ]
 
    #====================================================================
    if visualizacao == 'movimentacao_tabela':
        tabela_movi = juncao()
        cabecalho = gera_cabecalho_movimentacao()
        tabela_card_movimentacao = gerar_cards_movimentacao(tabela_movi, cliente, ordem_filtro, produto, ano, semana, categoria)
 
        # Retornar lembretes pendentes para mostrar na sidebar
        lembretes_sidebar = gerar_lembretes_sidebar()
        return [[], [], [], [], [], [], [cabecalho] + tabela_card_movimentacao, None,None, lembretes_sidebar]
 
    elif visualizacao == 'movimentacao_retirada':
        tabela_reti = juncao_ret_pcp()
        cabecalho = gera_cabecalho_retirada()
        tabela_card_retirada = gerar_cards_retirada(tabela_reti, cliente, ordem_filtro, produto, ano, semana, categoria)
 
        # Retornar lembretes pendentes para mostrar na sidebar
        lembretes_sidebar = gerar_lembretes_sidebar()
        return [[], [], [], [], [], [], [cabecalho] + tabela_card_retirada, None, None, lembretes_sidebar]
   
    elif visualizacao == 'estoque_pa':
       
        tabela_de_estoque = tabela_estoque(df_filtrado, cliente, produto, categoria, tipo_produto)
 
        # Retornar lembretes pendentes para mostrar na sidebar
        lembretes_sidebar = gerar_lembretes_sidebar()
        return [[], [], [], [], [], [], tabela_de_estoque, None, None, lembretes_sidebar]
   
    elif visualizacao == 'dashboard':
       
        #layout = layout_dashboard()
       
        # Retornar lembretes pendentes para mostrar na sidebar
        lembretes_sidebar = gerar_lembretes_sidebar()
        return [[], [], [], [], [], [], layout, None, None, lembretes_sidebar]
   
    elif visualizacao == 'painel_chapas':
       
        # Passar os filtros OS, Arte, Semana (com comparação), chapa selecionada e página atual para a função painel_chapas
        painel = painel_chapas(filtro_os=filtro_os, filtro_arte=filtro_arte, semana=semana, comparacao_semana=comparacao_semana, categoria=categoria, chapa_selecionada=chapa_selecionada, pagina_atual=pagina_chapas or 1)
       
        # Retornar lembretes pendentes para mostrar na sidebar
        lembretes_sidebar = gerar_lembretes_sidebar()
        return [[], [], [], [], [], [], painel, None, None, lembretes_sidebar]
   
    elif visualizacao == 'gestao_facas':
        layout = layout_gestao_facas()
       
        # Retornar lembretes pendentes para mostrar na sidebar
        lembretes_sidebar = gerar_lembretes_sidebar()
        return [[], [], [], [], [], [], layout, None, None, lembretes_sidebar]
   
    elif visualizacao == 'pizza':
        layout = pizza_layout()
        lembretes_sidebar = gerar_lembretes_sidebar()
        return [[], [], [], [], [], [], layout, None, None, lembretes_sidebar]
   
    elif visualizacao == 'tabela':
     
        # Pass semana and comparacao_semana to personalizar_tabela
        visual, infos = personalizar_tabela(df_filtrado_final,tipo_produto, status, semana, comparacao_semana=comparacao_semana, ocorrencia=ocorrencia)
       
        # Obter lembretes pendentes para mostrar na sidebar junto com as informações da tabela
        lembretes_sidebar = None
        lembretes_sidebar = gerar_lembretes_sidebar()
       
        # Retornar ambos (informações da tabela e lembretes) em uma lista para serem exibidos um abaixo do outro
        return [[], [], [], [], [], [], visual, None, infos, lembretes_sidebar]
   
    elif visualizacao == 'planejamento_semanal':
        # Pass week filters to the planejamento function
        planejamento_layout = planejamento(semana=semana, comparacao_semana=comparacao_semana, mostrar_partes=mostrar_partes)
       
        # Retornar lembretes pendentes para mostrar na sidebar
        lembretes_sidebar = gerar_lembretes_sidebar()
        return [[], [], [], [], [], [], planejamento_layout, None,None, lembretes_sidebar]
 
 
    else:  # Caso de "produção" ou qualquer outro estado inesperado
        # Retornar lembretes pendentes para mostrar na sidebar
        lembretes_sidebar = gerar_lembretes_sidebar()
        return [
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            lembretes_sidebar
        ]
   
@app.callback(
    Output('filtro-setor-container', 'style'),
    [Input('visualizacao_select', 'value')]
)
def toggle_sector_filter(visualizacao):
    if visualizacao == 'planejamento_semanal':
        return {'display': 'block', 'margin-top': '2px'}
    return {'display': 'none'}

@app.callback(
    Output('modal_inclusao_cliente', "is_open"),
    Input('btn_add_cliente', 'n_clicks'),
    State('modal_inclusao_cliente', "is_open")
)
def toggle_modal_cliente(n,  is_open):
    if n:  
        return not is_open  
    return is_open
 
@app.callback(
    Output('cliente_filter', 'options'),
    #Atualizar as opções do Dropdown
    Input('btn_refresh_clientes', 'n_clicks')  # Gatilho: clique no botão
)
def atualizar_clientes(n_clicks):
    # Recarregar os dados do banco de dados
    df_clientes_atualizado = listar_dados('clientes')  # Sua função para obter os dados atualizados
   
    # Retornar as opções formatadas
    return [{'label': i, 'value': i} for i in df_clientes_atualizado['nome']]
 
@app.callback(
    Output('select_chapa', 'options'),
    Input('btn_refresh_clientes', 'n_clicks')  # Usar o mesmo botão de refresh para atualizar as chapas
)
def atualizar_chapas(n_clicks):
    """
    Atualiza as opções do dropdown de chapas com os IDs disponíveis no banco
    """
    try:
        df_chapas = listar_dados('chapa')  # Buscar dados das chapas
       
        # Criar lista de opções com os códigos das chapas
        opcoes_chapas = [{'label': f"Chapa {codigo}", 'value': codigo}
                        for codigo in sorted(df_chapas['ch_codigo'].dropna().unique())]
       
        return opcoes_chapas
    except Exception as e:
        print(f"Erro ao carregar chapas: {e}")
        return []
 
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
        writer.close()
    output.seek(0)
    return output

def to_excel_with_sectors(df_planejamento):
    """
    Exports a DataFrame to an Excel file with a main sheet and separate sheets for each sector
    found in the 'plano_setor' column.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 1. Main Sheet
        df_planejamento_export = df_planejamento.drop(columns=['plano_setor'], errors='ignore')
        df_planejamento_export.to_excel(writer, index=False, sheet_name='Planejamento Geral')

        # 2. Sector Sheets
        banco = Banco()
        df_setores = banco.ler_tabela('setor')
        setor_map = df_setores.set_index('setor_id')['setor_nome'].to_dict()

        # Get all unique sector IDs from the JSON data
        all_sector_ids = set()
        if 'plano_setor' in df_planejamento.columns:
            for item in df_planejamento['plano_setor'].dropna():
                try:
                    data = json.loads(item) if isinstance(item, str) else item
                    if isinstance(data, dict):
                        all_sector_ids.update(data.keys())
                except (json.JSONDecodeError, TypeError):
                    continue
        
        # Create a sheet for each sector
        for sector_id_str in all_sector_ids:
            try:
                sector_id = int(sector_id_str)
                sector_name = setor_map.get(sector_id, f"Setor_{sector_id}")

                sector_data = []
                for _, row in df_planejamento.iterrows():
                    plano_setor = row.get('plano_setor')
                    if plano_setor and pd.notna(plano_setor):
                        data = json.loads(plano_setor) if isinstance(plano_setor, str) else plano_setor
                        if isinstance(data, dict) and str(sector_id) in data:
                            new_row = row.to_dict()
                            new_row['Qtd Planejada'] = data[str(sector_id)]
                            sector_data.append(new_row)
                
                if sector_data:
                    df_sector = pd.DataFrame(sector_data)
                    df_sector_export = df_sector.drop(columns=['plano_setor'], errors='ignore')
                    # Ensure sheet name is valid
                    safe_sheet_name = sector_name.replace('/', '_').replace('\\', '_')[:31]
                    df_sector_export.to_excel(writer, index=False, sheet_name=safe_sheet_name)

            except (ValueError, TypeError):
                continue

    output.seek(0)
    return output

@app.callback(
    Output('header-row', 'style'),
    Input('sidebar-state', 'data')
)
def adjust_header_on_sidebar_toggle(sidebar_state):
    base_style = {
        'background-color': '#02083d',
        'padding': '10px 20px',
        'border-radius': '0 0 8px 8px',
        'box-shadow': '2px 2px 5px rgba(0, 0, 0, 0.3)',
        'position': 'fixed',
        'top': '0',
        'right': '0',
        'zIndex': '9999',
        'margin': '0',
        'transition': 'left 0.3s, width 0.3s'
    }
    if sidebar_state == 'closed':
        base_style['left'] = '0'
        base_style['width'] = '100vw'
    else:
        base_style['left'] = '18vw'
        base_style['width'] = 'calc(100vw - 19vw)'
    return base_style