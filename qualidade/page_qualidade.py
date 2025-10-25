from dash import html, dcc, callback_context, ctx
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime, timedelta
import dash
from app import app
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import Session
from banco_dados.banco import engine, BAIXA, RETIRADA, Banco
from dash import dash_table
import numpy as np
from .formularios import form_retrabalho
 
# ========= Styles ========= #
card_style = {'height': '100%', 'margin-bottom': '12px'}
 
layout = dbc.Container([
    dcc.Store(id='store-retrabalho-update-trigger'),
    form_retrabalho.layout,
    dbc.Row([
        dbc.Col(
            html.H3(
                "QUALIDADE - CONTROLE DE LOTE",
                style={
                    'text-align': 'left',
                    'color': '#FFFFFF',
                    'margin': '0'
                }
            ),
            width=10,
            style={'display': 'flex', 'align-items': 'center'}
        ),
        dbc.Col([
            dbc.Button(
                html.I(className="fa fa-refresh"),
                id="btn_refresh_qualidade",
                color="warning",
                style={'margin-left': '8px'}
            ),
        ], width=2,
        style={
            'text-align': 'right',
            'display': 'flex',
            'align-items': 'center',
            'justify-content': 'flex-end'}
        ),
    ], style={
        'background-color': '#02083d',
        'padding': '10px 20px',
        'border-radius': '0 0 8px 8px',
        'box-shadow': '2px 2px 5px rgba(0, 0, 0, 0.3)',
        'position': 'fixed',
        'top': '0',
        'left': '18vw',
        'right': '0',
        'zIndex': '9999',
        'width': 'calc(100vw - 19vw)',
        'margin': '0'}
    ),
    html.Div(style={'height': '70px'}),
 
    # Seção de Filtros
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        # Coluna de Pesquisa
                        dbc.Col([
                            dbc.Row([html.H4("PESQUISA")]),
                            dbc.Row([dbc.Input(id='filtro_lot', placeholder="LoT...", type="number", style={'height': '37px', 'border': '2px solid #D3D3D3', 'border-radius': '4px'})]),
                            dbc.Row([dbc.Input(id='filtro_produto', placeholder="Produto...", type="text", style={'height': '37px','margin-top': '4px','border': '2px solid #D3D3D3','border-radius': '4px'})]),
                            dbc.Row([dbc.Input(id='filtro_cliente', placeholder="Cliente...", type="text", style={'height': '37px','margin-top': '4px','border': '2px solid #D3D3D3','border-radius': '4px'})]),
                        ], lg=4, md=12, className="mb-3 mb-lg-0"),
 
                        # Coluna de Filtros
                        dbc.Col([
                            dbc.Row([html.H4("FILTROS")]),
                            dbc.Row([dbc.Col([dcc.Input(id='filtro_categoria', placeholder="Categoria...", type="text", style={'height': '37px', 'border': '2px solid #D3D3D3', 'border-radius': '4px', 'width': '100%'})])]),
                            dbc.Row([dbc.Col([dcc.Dropdown(id='filtro_status', options=[{'label': 'Pendente', 'value': 'PENDENTE'}, {'label': 'Parcial', 'value': 'PARCIAL'}, {'label': 'Feito', 'value': 'FEITO'}], placeholder='Status', multi=True, className='dbc', style={'margin-top': '4px'}, value=['FEITO'])])]),
                            dbc.Row([dbc.Col([dcc.Dropdown(id='filtro_status_retrabalho',
                             options=[{'label': 'Aguardando Aprovação', 'value': 'AGUARDANDO APROVACAO'},
                              {'label': 'Retrabalho', 'value': 'RETRABALHO'},
                               {'label': 'Aprovado', 'value': 'APROVADO'},
                               {'label': 'Reprovado', 'value': 'REPROVADO'},
                               {'label': 'Aprovado Sob Concessão', 'value': 'APROVADO SOB CONCESSAO'}],
                               placeholder='Status Retrabalho', multi=True, className='dbc', style={'margin-top': '4px'}, value=['RETRABALHO','AGUARDANDO APROVACAO'])])]),
                        ], lg=4, md=12, className="mb-3 mb-lg-0"),
 
                        # Coluna de Ações
                        dbc.Col([
                            dbc.Row([html.H4("AÇÕES")]),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button("Filtrar", id='btn_filtrar_qualidade', color='primary', className="d-grid gap-2 col-12 mx-auto", style={'margin-bottom': '8px','fontSize': '16px'}),
                                    dbc.Button("Exportar", id='btn_exp_excel_qualidade', className="d-grid gap-2 col-12 mx-auto", style={'color': 'white','backgroundColor': '#28a745','padding': '6px 0','borderRadius': '8px','border': 'none','boxShadow': '0px 4px 6px rgba(0, 0, 0, 0.1)','transition': 'all 0.3s ease-in-out','textAlign': 'center','fontSize': '16px','margin-top': '6px'}, size='md'),
                                    dcc.Download(id="download_excel_qualidade")
                                ]),
                            ]),
                        ], lg=4, md=12),
                    ]),
                ])
            ])
        ])
    ], style={'margin-bottom': '20px'}),
 
    dbc.Row([
        dbc.Col([
            html.Div(id='tabela_qualidade_container')
        ])
    ])
 
], fluid=True)
 
def obter_dados_em_lote(pcp_ids):
    """
    Combina todas as consultas ao banco em uma única função para reduzir o número de conexões
    """
    if not pcp_ids:
        return {'baixas': {}, 'retiradas': {}}
 
    with Session(engine) as session:
        # Baixas
        baixas = session.query(BAIXA.pcp_id, func.sum(BAIXA.qtd).label("qtd_baixa")) \
                        .filter(BAIXA.pcp_id.in_(pcp_ids)) \
                        .group_by(BAIXA.pcp_id).all()
       
        # Retiradas
        retiradas = session.query(RETIRADA.ret_id_pcp, func.sum(RETIRADA.ret_qtd).label("qtd_retirada")) \
                          .filter(RETIRADA.ret_id_pcp.in_(pcp_ids)) \
                          .group_by(RETIRADA.ret_id_pcp).all()
       
        return {
            'baixas': dict(baixas),
            'retiradas': dict(retiradas),
        }
 
def formatar_numero(val):
    if pd.isna(val) or val == '':
        return ''
    try:
        return '{:,.0f}'.format(float(val)).replace(',', '.')
    except (ValueError, TypeError):
        return val
 
def gerar_tabela_qualidade(lot, produto, cliente, categoria, status_baixa_filtro, status_retrabalho_filtro):
   
    query = text("""
        SELECT
            pcp.*,
            c.nome AS nome_cliente,
            p.nome AS nome_produto
        FROM pcp
        LEFT JOIN clientes AS c ON pcp.pcp_cliente_id = c.cliente_id
        LEFT JOIN produtos AS p ON pcp.pcp_produto_id = p.produto_id
    """)
   
    with engine.connect() as connection:
        df_filtrado = pd.read_sql(query, connection)
    # Filtro padrão: mostrar apenas pcp_correncia = NULL ou 3
    df_filtrado = df_filtrado[(df_filtrado['pcp_correncia'].isnull()) | (df_filtrado['pcp_correncia'] == 3)]
 
    pcp_ids = df_filtrado['pcp_id'].unique().tolist()
    if not pcp_ids:
        return html.Div("Nenhum dado encontrado.")
 
    dados_lote = obter_dados_em_lote(pcp_ids)
 
    df_filtrado['qtd_baixa'] = df_filtrado['pcp_id'].map(dados_lote['baixas']).fillna(0)
    df_filtrado['qtd_retirada'] = df_filtrado['pcp_id'].map(dados_lote['retiradas']).fillna(0)
 
    condicoes = [
        df_filtrado['pcp_correncia'] == 3,
        df_filtrado['qtd_baixa'] == 0,
        (df_filtrado['qtd_baixa'] > 0) & (df_filtrado['qtd_baixa'] < 0.9 * df_filtrado['pcp_qtd']),
        df_filtrado['qtd_baixa'] >= 0.9 * df_filtrado['pcp_qtd']
    ]
    valores = ['FEITO', 'PENDENTE', 'PARCIAL', 'FEITO']
    df_filtrado['status_baixa'] = np.select(condicoes, valores, default='PENDENTE')
   
    banco = Banco()
    df_apontamentos = banco.ler_tabela('apontamento_retrabalho')

    if not df_apontamentos.empty:
        df_apontamentos['data_hora'] = pd.to_datetime(df_apontamentos['data_hora'])
        # Pega o status do apontamento mais recente para cada pcp_id
        latest_status = df_apontamentos.sort_values('data_hora', ascending=True).groupby('pcp_id')['status'].last()
        df_filtrado['pcp_retrabalho'] = df_filtrado['pcp_id'].map(latest_status)
    else:
        # Se não houver apontamentos, todos ficam sem status definido por enquanto
        df_filtrado['pcp_retrabalho'] = np.nan

    status_map = {
        1: 'RETRABALHO',
        2: 'APROVADO',
        3: 'REPROVADO',
        4: 'APROVADO SOB CONCESSAO'
    }
    df_filtrado['status_retrabalho'] = df_filtrado['pcp_retrabalho'].map(status_map).fillna('AGUARDANDO APROVACAO')
 
    # Apply all filters after calculations
    if lot:
        df_filtrado = df_filtrado[df_filtrado['pcp_pcp'] == lot]
    if produto:
        df_filtrado = df_filtrado[df_filtrado['nome_produto'].str.contains(produto, case=False, na=False)]
    if cliente:
        df_filtrado = df_filtrado[df_filtrado['nome_cliente'].str.contains(cliente, case=False, na=False)]
    if categoria:
        df_filtrado = df_filtrado[df_filtrado['pcp_categoria'].str.contains(categoria, case=False, na=False)]
    if status_baixa_filtro:
        df_filtrado = df_filtrado[df_filtrado['status_baixa'].isin(status_baixa_filtro)]
    if status_retrabalho_filtro:
        df_filtrado = df_filtrado[df_filtrado['status_retrabalho'].isin(status_retrabalho_filtro)]
 
    df_filtrado = df_filtrado.sort_values(by='pcp_id', ascending=False)
 
    df_filtrado['saldo_em_processo'] = (df_filtrado['pcp_qtd'] - df_filtrado['qtd_baixa']).clip(lower=0)
    df_filtrado['saldo_em_estoque'] = (df_filtrado['qtd_baixa'] - df_filtrado['qtd_retirada']).clip(lower=0)
    df_filtrado['qtd_retrabalho'] = df_filtrado['pcp_perdida_retrabalho']
 
    colunas_formatar = ['pcp_qtd', 'saldo_em_processo', 'saldo_em_estoque', 'qtd_retirada', 'qtd_retrabalho']
    for col in colunas_formatar:
        df_filtrado[col] = df_filtrado[col].apply(formatar_numero)
 
    colunas_tabela = [
        {"name": "OC", "id": "pcp_oc"},
        {"name": "LoT", "id": "pcp_pcp"},
        {"name": "CATEGORIA", "id": "pcp_categoria"},
        {"name": "CÓD", "id": "pcp_cod_prod"},
        {"name": "CLIENTE", "id": "nome_cliente"},
        {"name": "Produto", "id": "nome_produto"},
        {"name": "QTD OP", "id": "pcp_qtd"},
        {"name": "PROCESSO", "id": "saldo_em_processo"},
        {"name": "ESTOQUE", "id": "saldo_em_estoque"},
        {"name": "RETIRADA", "id": "qtd_retirada"},
        {"name": "Status", "id": "status_baixa"},
        {"name": "status retrabalho", "id": "status_retrabalho"},
        {"name": "qtd retrabalho", "id": "qtd_retrabalho"},
    ]
 
    tabela = dash_table.DataTable(
        id='tabela_qualidade',
        columns=colunas_tabela,
        data=df_filtrado.to_dict('records'),
        style_table={'overflowX': 'auto'},
        page_size=20,
        row_selectable='single',
        selected_rows=[],
        style_cell={'textAlign': 'left'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        style_data_conditional=[
            {
                'if': {'filter_query': '{status_retrabalho} = "RETRABALHO"', 'column_id': 'status_retrabalho'},
                'backgroundColor': 'red',
                'color': 'white'
            },
            {
                'if': {'filter_query': '{status_retrabalho} = "APROVADO"', 'column_id': 'status_retrabalho'},
                'backgroundColor': 'green',
                'color': 'white'
            },
            {
                'if': {'filter_query': '{status_retrabalho} = "REPROVADO"', 'column_id': 'status_retrabalho'},
                'backgroundColor': '#b22222', # Dark Red
                'color': 'white'
            },
            {
                'if': {'filter_query': '{status_retrabalho} = "APROVADO SOB CONCESSAO"', 'column_id': 'status_retrabalho'},
                'backgroundColor': '#ff8c00', # Dark Orange
                'color': 'white'
            }
        ]
    )
    return tabela
 
@app.callback(
    Output('tabela_qualidade_container', 'children'),
    [Input('btn_filtrar_qualidade', 'n_clicks'),
     Input('store-retrabalho-update-trigger', 'data')],
    [State("filtro_lot", "value"),
     State('filtro_produto', 'value'),
     State('filtro_cliente', 'value'),
     State('filtro_categoria', 'value'),
     State('filtro_status', 'value'),
     State('filtro_status_retrabalho', 'value')]
)
def update_table(n_clicks, trigger_data, lot, produto, cliente, categoria, status, status_retrabalho):
    return gerar_tabela_qualidade(lot, produto, cliente, categoria, status, status_retrabalho)
 
@app.callback(
    Output("modal_retrabalho", "is_open"),
    Output("store_pcp_id_retrabalho", "data"),
    Output("pcp_id_retrabalho_input", "value"),
    Output("pcp_pcp_retrabalho_input", "value"),
    Output("pcp_qtd_retrabalho_input", "value"),
    Output("produto_nome_retrabalho_input", "value"),
    Input("tabela_qualidade", "active_cell"),
    [State("tabela_qualidade", "data"),
     State("tabela_qualidade", "page_current")],
    prevent_initial_call=True
)
def open_retrabalho_modal(active_cell, table_data, page_current):
    if not active_cell:
        return False, None, None, None, None, None

    page_current = page_current if page_current is not None else 0
    page_size = 20  # As set in the table properties

    row_index = (page_current * page_size) + active_cell['row']

    if row_index >= len(table_data):
        return False, None, None, None, None, None

    row_data = table_data[row_index]
    pcp_id = row_data.get('pcp_id')
    lot = row_data.get('pcp_pcp')
    qtd = row_data.get('pcp_qtd')
    produto = row_data.get('nome_produto')
   
    return True, pcp_id, pcp_id, lot, qtd, produto