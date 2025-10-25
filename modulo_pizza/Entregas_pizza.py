from dash import html, dcc, callback_context, no_update, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
from datetime import datetime, timedelta
from sqlalchemy import text, func
from sqlalchemy.orm import Session
from app import app
from banco_dados.banco import Banco, engine, BAIXA, RETIRADA, PRODUTO
import pandas as pd
import numpy as np
import json
from .formularios.form_apontamento_estoque import modal_apontamento_estoque
from calculos import Filtros
from .funcoes.excel_pizza import generate_excel_download
 
# --- Helper Functions and Data (Pizza View) ---
 
# Dias da semana para o layout (Segunda a Sábado)
WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
 
def get_daily_delivery_data(cliente_id=None, etiquetas=None, produto_nome=None):
    """Busca e processa os dados de entrega do banco de dados com uma query SQL otimizada."""
    banco = Banco()
   
    # Parâmetros e cláusulas WHERE para a query SQL
    sql_params = {}
    where_clauses = ["p.dia_entrega BETWEEN 2 AND 7"]
 
    if cliente_id:
        where_clauses.append("c.cliente_id = :cliente_id")
        sql_params['cliente_id'] = cliente_id
 
    if produto_nome:
        where_clauses.append("p.nome LIKE :produto_nome")
        sql_params['produto_nome'] = f"%{produto_nome}%"
   
    where_sql = " AND ".join(where_clauses)
 
    # Query consolidada que faz os joins e a agregação no banco de dados
    query = f"""
    WITH BaixasAgg AS (
        SELECT
            p.pcp_produto_id,
            SUM(b.qtd) AS total_baixas
        FROM baixa b
        JOIN pcp p ON b.pcp_id = p.pcp_id
        GROUP BY p.pcp_produto_id
    ),
    RetiradasAgg AS (
        SELECT
            p.pcp_produto_id,
            SUM(r.ret_qtd) AS total_retiradas
        FROM retirada r
        JOIN pcp p ON r.ret_id_pcp = p.pcp_id
        GROUP BY p.pcp_produto_id
    ),
    RetiradasExpAgg AS (
        SELECT
            ret_exp_produto_id,
            SUM(ret_exp_qtd) AS total_retiradas_exp
        FROM retirada_exp
        GROUP BY ret_exp_produto_id
    )
    SELECT
        p.produto_id,
        p.nome AS produto_nome,
        c.cliente_id,
        c.nome AS cliente_nome,
        p.dia_entrega,
        p.pedido_mensal,
        p.tipo_trabalho,
        COALESCE(ba.total_baixas, 0) AS total_baixas,
        COALESCE(re.total_retiradas, 0) AS total_retiradas,
        COALESCE(rex.total_retiradas_exp, 0) AS total_retiradas_exp
    FROM (
        SELECT DISTINCT pcp_produto_id, pcp_cliente_id
        FROM pcp
    ) AS pcp_clientes
    JOIN produtos p ON pcp_clientes.pcp_produto_id = p.produto_id
    JOIN clientes c ON pcp_clientes.pcp_cliente_id = c.cliente_id
    LEFT JOIN BaixasAgg ba ON p.produto_id = ba.pcp_produto_id
    LEFT JOIN RetiradasAgg re ON p.produto_id = re.pcp_produto_id
    LEFT JOIN RetiradasExpAgg rex ON p.produto_id = rex.ret_exp_produto_id
    WHERE {where_sql}
    """
    try:
        with banco.engine.connect() as connection:
            df_agg = pd.read_sql_query(text(query), connection, params=sql_params)
    except Exception as e:
        print(f"Erro ao executar a query SQL: {e}")
        return {}
 
    if df_agg.empty:
        return {}
 
    # Cálculos e filtro de etiqueta em Pandas (pós-SQL)
    df_agg['feito_qtd'] = df_agg['total_retiradas'] - df_agg['total_retiradas_exp']
    df_agg['imp_qtd'] = df_agg['total_baixas'] - df_agg['total_retiradas']
 
    def get_status(row):
        pedido_mensal = row['pedido_mensal']
        if pd.notna(pedido_mensal) and pedido_mensal > 0:
            soma_imp_feito = row['imp_qtd'] + row['feito_qtd']
            ratio = soma_imp_feito / pedido_mensal
            if ratio >= 2: return 'Verde'
            if ratio >= 1: return 'Laranja'
            return 'Vermelho'
        return None
   
    df_agg['status_cor'] = df_agg.apply(get_status, axis=1)
 
    if etiquetas:
        df_agg = df_agg[df_agg['status_cor'].isin(etiquetas)]
   
    if df_agg.empty: return {}
 
    # Organizar dados para exibição
    # Mapeia dia_entrega (2-7) para índices da semana (0-5)
    # 2=Segunda(0), 3=Terça(1), 4=Quarta(2), 5=Quinta(3), 6=Sexta(4), 7=Sábado(5)
    df_agg['day_index'] = df_agg['dia_entrega'].astype(int) - 2
    
    daily_data = {}
    grouped_by_day = df_agg.groupby('day_index')
 
    for day_idx, group in grouped_by_day:
        client_products = {}
        grouped_by_client = group.groupby('cliente_nome')
        for client_name, client_group in grouped_by_client:
            products_list = client_group.to_dict('records')
            client_products[client_name] = sorted(products_list, key=lambda p: p['produto_nome'])
       
        daily_data[day_idx] = dict(sorted(client_products.items()))
    
    # Garante que todos os dias da semana tenham uma entrada, mesmo que vazia
    for i in range(6):  # 0-5 (Segunda a Sábado)
        if i not in daily_data:
            daily_data[i] = {}
 
    return daily_data
 
def create_day_column(day_name, children, card_style=None):
    """Cria uma coluna para um dia da semana."""
    return dbc.Col(
        dbc.Card([
            dbc.CardHeader(day_name),
            dbc.CardBody(children=children)
        ], style=card_style),
        lg=4, md=6, sm=12, className="mb-3" # Responsividade para diferentes tamanhos de tela
    )
 
# --- Helper Functions (Empurrado View) ---
def calcular_somas(pcp_ids):
    with Session(engine) as session:
        soma_qtd_baixa = dict(session.query(BAIXA.pcp_id, func.sum(BAIXA.qtd))
                              .filter(BAIXA.pcp_id.in_(pcp_ids))
                              .group_by(BAIXA.pcp_id).all())
       
        soma_qtd_retirada = dict(session.query(RETIRADA.ret_id_pcp, func.sum(RETIRADA.ret_qtd))
                                 .filter(RETIRADA.ret_id_pcp.in_(pcp_ids))
                                 .group_by(RETIRADA.ret_id_pcp).all())
    return soma_qtd_baixa, soma_qtd_retirada
 
def formatar_numero(val):
    return '{:,.0f}'.format(val).replace(',', '.') if val is not None else val
 
def tabela_pcp_formacao(df):
    banco = Banco()
    df_produtos = banco.ler_tabela("produtos")
    df_clientes = banco.ler_tabela("clientes")
   
    df = df.merge(df_produtos[['produto_id', 'nome']], left_on='pcp_produto_id', right_on='produto_id', how='left')
    df = df.merge(df_clientes[['cliente_id', 'nome']], left_on='pcp_cliente_id', right_on='cliente_id', how='left')
    df.rename(columns={'nome_x': 'nome', 'nome_y': 'cliente_nome'}, inplace=True)
 
    df['pcp_entrega'] = pd.to_datetime(df['pcp_entrega'], errors='coerce')
    df['pcp_emissao'] = pd.to_datetime(df['pcp_emissao'], errors='coerce')
    df['pcp_semana'] = df['pcp_entrega'].dt.isocalendar().week
   
    pcp_ids = df['pcp_id'].tolist()
    soma_qtd_baixa, soma_qtd_retirada = calcular_somas(pcp_ids)
   
    df['qtd_baixa'] = df['pcp_id'].map(soma_qtd_baixa).fillna(0)
    df['qtd_retirada'] = df['pcp_id'].map(soma_qtd_retirada).fillna(0)
    df['saldo_em_processo'] = (df['pcp_qtd'] - df['qtd_baixa']).clip(lower=0)
    df['saldo_em_estoque'] = (df['qtd_baixa'] - df['qtd_retirada']).clip(lower=0)
    df['pcp_entrega_formatada'] = df['pcp_entrega'].dt.strftime('%d/%m/%Y').fillna('')
    df.sort_values(by='pcp_entrega', ascending=True, inplace=True)
   
    return df
 
def tabela_estoque_empurrado(df, cliente, produto, categoria):
    df_geral = tabela_pcp_formacao(df)
   
    data_atual = pd.to_datetime("today")
    mes_atual = data_atual.month
    ano_atual = data_atual.year
   
    banco = Banco()
    df_retiradas = banco.ler_tabela("retirada")
    df_pcp = banco.ler_tabela("pcp")
   
    df_retiradas = df_retiradas.merge(
        df_pcp[['pcp_id', 'pcp_produto_id']],
        left_on='ret_id_pcp',
        right_on='pcp_id',
        how='left'
    )
   
    df_retiradas['ret_data'] = pd.to_datetime(df_retiradas['ret_data'], errors='coerce')
    df_retiradas = df_retiradas[
        (df_retiradas['ret_data'].dt.month == mes_atual) &
        (df_retiradas['ret_data'].dt.year == ano_atual)
    ]
   
    df_retiradas_sum = df_retiradas.groupby('pcp_produto_id')['ret_qtd'].sum().reset_index()
    df_retiradas_sum.rename(columns={'pcp_produto_id': 'produto_id', 'ret_qtd': 'qtd_retirada_mes_atual'}, inplace=True)
   
    numeric_cols = ["saldo_em_processo", "saldo_em_estoque", "qtd_retirada"]
    df_geral[numeric_cols] = df_geral[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    df_somas = df_geral.groupby("pcp_produto_id", as_index=False).agg({
        "saldo_em_processo": "sum",
        "saldo_em_estoque": "sum",
        "qtd_retirada": "sum",
        "pcp_categoria": "first",
        "pcp_cliente_id": "first",
        "cliente_nome": "first"
    }).rename(columns={"pcp_produto_id": "produto_id"})
   
    df_somas = pd.merge(df_somas, df_retiradas_sum, on='produto_id', how='left')
    df_somas['qtd_retirada'] = df_somas['qtd_retirada_mes_atual'].fillna(0)
    df_somas.drop('qtd_retirada_mes_atual', axis=1, inplace=True)
   
    df_produtos = banco.ler_tabela("produtos")
   
    df_produtos = df_produtos[
        (df_produtos['fluxo_producao'] == 'Empurrado') &
        (pd.isna(df_produtos['dia_entrega']))
    ]
   
    df_final = df_produtos.merge(df_somas, on="produto_id", how="left").fillna(0)
   
    fim_do_mes = data_atual + pd.offsets.MonthEnd()
    dias_uteis = np.busday_count(data_atual.strftime('%Y-%m-%d'), fim_do_mes.strftime('%Y-%m-%d')) if np.busday_count(data_atual.strftime('%Y-%m-%d'), fim_do_mes.strftime('%Y-%m-%d')) > 0 else 1
    dias_uteis_passados = np.busday_count(f"{data_atual.year}-{data_atual.month:02d}-01", data_atual.strftime('%Y-%m-%d')) if np.busday_count(f"{data_atual.year}-{data_atual.month:02d}-01", data_atual.strftime('%Y-%m-%d')) > 0 else 1
    #print(dias_uteis)
    df_final['saldo_em_estoque_por_pedido'] = round(df_final['saldo_em_estoque'] / (df_final['pedido_mensal'] / dias_uteis), 2)
    df_final['saldo_em_estoque_por_venda'] = round(df_final['saldo_em_estoque'] / (df_final['qtd_retirada'] / dias_uteis_passados), 2)
   
    def calcular_seta(valor):
        if pd.isna(valor) or valor == float('inf') or valor == -float('inf'): return "0", "gray"
        elif valor > 8: return f"{int(valor)} ↑", "green"
        elif valor > 3: return f"{int(valor)} !", "orange"
        else: return f"{int(valor)} ↓", "red"
   
    df_final['seta_por_pedido'], df_final['cor_seta_por_pedido'] = zip(*df_final['saldo_em_estoque_por_pedido'].apply(calcular_seta))
    df_final['seta_por_venda'], df_final['cor_seta_por_venda'] = zip(*df_final['saldo_em_estoque_por_venda'].apply(calcular_seta))
   
    df_final.sort_values(by='saldo_em_estoque_por_pedido', ascending=True, inplace=True)
   
    for col in numeric_cols: df_final[col] = df_final[col].map(formatar_numero)
       
    df_final = Filtros.filtrar(df_final, {
        'cliente_nome': ('exato', cliente),
        'nome': ('contem', produto),
        'pcp_categoria': ('multi', categoria),
    })
   
    table = dash_table.DataTable(
        columns=[
            {"name": "ID PRODUTO", "id": "produto_id"},
            {"name": "PRODUTO", "id": "nome"},
            {"name": "PREVISÃO MENSAL", "id": "pedido_mensal"},
            {"name": "ESTOQUE", "id": "saldo_em_estoque"},
            {"name": "COBERTURA PROJEÇÃO", "id": "seta_por_pedido"},
        ],
        data=df_final.to_dict("records"),
        page_size=30,
        style_data_conditional=[
            {'if': {'column_id': 'seta_por_pedido', 'filter_query': '{seta_por_pedido} contains "↑"'}, 'color': 'green'},
            {'if': {'column_id': 'seta_por_pedido', 'filter_query': '{seta_por_pedido} contains "!"'}, 'color': 'orange'},
            {'if': {'column_id': 'seta_por_pedido', 'filter_query': '{seta_por_pedido} contains "↓"'}, 'color': 'red'},
        ],
        style_table={'height': '800px', 'overflowY': 'auto', 'border': '1px solid #ccc'},
        style_header={'fontWeight': 'bold', 'textAlign': 'center'},
        style_cell={'textAlign': 'center', 'padding': '5px'},
    )
    
    # Adiciona os dados ao objeto table para uso na exportação
    table.df_data = df_final
    return table
 
# Lógica para determinar o dia central inicial
today_index = datetime.now().weekday()
initial_center_day_index = 0 if today_index == 6 else today_index
 
# --- Layout ---
 
def layout_dashboard():
    banco = Banco()
    df_pcp_initial = banco.ler_tabela('pcp')
   
    return dbc.Container([
        dcc.Store(id='pizza-center-day-store', data=initial_center_day_index),
        dcc.Store(id='store-pcp-empurrado', data=df_pcp_initial.to_dict()),
        dcc.Store(id='store-daily-data', data={}),
        dcc.Store(id='store-empurrado-data', data={}),
        modal_apontamento_estoque(),
 
        dcc.Dropdown(
            id='panel-selector',
            options=[
                {'label': 'Entregas Programadas', 'value': 'programadas'},
                {'label': 'Estoque Empurrado', 'value': 'empurrado'},
            ],
            value='programadas',
            clearable=False,
            className="mb-3"
        ),
 
        html.Div(id='panel-programadas', children=[
            dbc.Card(dbc.CardBody(dbc.Row([
                dbc.Col(dbc.Button("<<", id="pizza-prev-btn", n_clicks=0, style={'background-color': '#02083d', 'color': 'white'}), sm=2, md=1, className="d-grid"),
                dbc.Col(dbc.Row([
                    dbc.Col(dcc.Dropdown(id='pizza-cliente-filter', placeholder="Cliente..."), sm=12, lg=3, className="mb-1 mb-lg-0"),
                    dbc.Col(dcc.Dropdown(
                        id='pizza-etiqueta-filter',
                        placeholder="Etiqueta...",
                        options=[
                            {'label': 'Verde', 'value': 'Verde'},
                            {'label': 'Laranja', 'value': 'Laranja'},
                            {'label': 'Vermelho', 'value': 'Vermelho'},
                        ],
                        multi=True
                    ), sm=12, lg=3, className="mb-1 mb-lg-0"),
                    dbc.Col(dbc.Input(id='pizza-produto-filter', placeholder="Produto...", type='text', debounce=True), sm=12, lg=3, className="mb-1 mb-lg-0"),
                    dbc.Col(dbc.Button("📊 Excel", id="pizza-export-excel", n_clicks=0, style={'background-color': '#28a745', 'color': 'white'}), sm=12, lg=3, className="d-grid"),
                ]), sm=8, md=10),
                dbc.Col(dbc.Button(">>", id="pizza-next-btn", n_clicks=0, style={'background-color': '#02083d', 'color': 'white'}), sm=2, md=1, className="d-grid"),
            ], align="center", justify="between")), className="mb-4", style={'background-color': 'white'}),
            dbc.Row(id="pizza-week-view", className="mb-3"),
            # Download link para Excel (invisível inicialmente)
            dcc.Download(id="pizza-excel-download"),
        ]),
 
        html.Div(id='panel-empurrado', children=[
            dbc.Card(dbc.CardBody(dbc.Row([
                dbc.Col(dcc.Dropdown(id='empurrado-cliente-filter', placeholder="Filtrar por Cliente..."), md=3),
                dbc.Col(dcc.Input(id='empurrado-produto-filter', placeholder="Buscar Produto...", type='text', debounce=True), md=3),
                dbc.Col(dcc.Dropdown(id='empurrado-categoria-filter', placeholder="Filtrar por Categoria...", multi=True), md=3),
                dbc.Col(dbc.Button("📊 Excel", id="empurrado-export-excel", n_clicks=0, style={'background-color': '#28a745', 'color': 'white'}), md=3),
            ]))),
            html.Div(id='empurrado-table-container'),
            # Download link para Excel (invisível inicialmente)
            dcc.Download(id="empurrado-excel-download")
        ], style={'display': 'none'})
 
    ], fluid=True)
 
# --- Callbacks ---
 
@app.callback(
    Output('panel-programadas', 'style'),
    Output('panel-empurrado', 'style'),
    Input('panel-selector', 'value')
)
def toggle_panels(selected_view):
    if selected_view == 'programadas':
        return {'display': 'block'}, {'display': 'none'}
    else:
        return {'display': 'none'}, {'display': 'block'}
 
@app.callback(
    Output('pizza-cliente-filter', 'options'),
    Output('empurrado-cliente-filter', 'options'),
    Input('pizza-center-day-store', 'data') # Dummy input
)
def populate_cliente_filters(_):
    banco = Banco()
    try:
        df_clientes = banco.ler_tabela('clientes').sort_values('nome')
        options = [{'label': row['nome'], 'value': row['nome']} for index, row in df_clientes.iterrows()]
        pizza_options = [{'label': row['nome'], 'value': row['cliente_id']} for index, row in df_clientes.iterrows()]
        return pizza_options, options
    except Exception as e:
        print(f"Erro ao popular filtro de clientes: {e}")
        return [], []
 
@app.callback(
    Output('empurrado-categoria-filter', 'options'),
    Input('pizza-center-day-store', 'data') # Dummy input
)
def populate_categoria_filter(_):
    banco = Banco()
    try:
        df_pcp = banco.ler_tabela('pcp')
        categorias = df_pcp['pcp_categoria'].dropna().unique()
        options = [{'label': cat, 'value': cat} for cat in sorted(categorias)]
        return options
    except Exception as e:
        print(f"Erro ao popular filtro de categorias: {e}")
        return []
 
@app.callback(
    Output('empurrado-table-container', 'children'),
    Input('empurrado-cliente-filter', 'value'),
    Input('empurrado-produto-filter', 'value'),
    Input('empurrado-categoria-filter', 'value'),
    State('store-pcp-empurrado', 'data')
)
def update_empurrado_table(cliente, produto, categoria, pcp_data):
    df_pcp = pd.DataFrame(pcp_data)
    return tabela_estoque_empurrado(df_pcp, cliente, produto, categoria)
 
@app.callback(
    Output('pizza-center-day-store', 'data'),
    [Input('pizza-prev-btn', 'n_clicks'),
     Input('pizza-next-btn', 'n_clicks')],
    [State('pizza-center-day-store', 'data')],
    prevent_initial_call=True
)
def update_pizza_center_day(prev_clicks, next_clicks, center_day_index):
    ctx = callback_context
    if not ctx.triggered:
        return center_day_index
       
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
   
    num_days = len(WEEKDAYS)
    if button_id == 'pizza-next-btn':
        return (center_day_index + 1) % num_days
    elif button_id == 'pizza-prev-btn':
        return (center_day_index - 1 + num_days) % num_days
   
    return center_day_index
 
@app.callback(
    Output('modal-apontamento-estoque', 'is_open'),
    Output('store-selected-product-id', 'data'),
    Input({'type': 'btn-pizza-edit', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def open_edit_modal(n_clicks):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks):
        return no_update, no_update
 
    triggered_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
    product_id = json.loads(triggered_id_str)['index']
   
    return True, product_id
 
@app.callback(
    Output('pizza-week-view', 'children'),
    [Input('pizza-center-day-store', 'data'),
     Input('pizza-cliente-filter', 'value'),
     Input('pizza-etiqueta-filter', 'value'),
     Input('pizza-produto-filter', 'value')]
)
def update_pizza_column_visibility(center_day_index, cliente_id, etiquetas, produto_nome):
    """Atualiza as colunas visíveis com base nos filtros e na navegação."""
    daily_data = get_daily_delivery_data(cliente_id, etiquetas, produto_nome)
    num_days = len(WEEKDAYS)
    visible_columns = []
 
    indicator_colors = {
        'Semanal': 'success',
        'Quinzenal': 'warning',
        'Mensal': 'danger'
    }
 
    indices_to_show = [
        (center_day_index - 1 + num_days) % num_days,
        center_day_index,
        (center_day_index + 1) % num_days
    ]
 
    for index in indices_to_show:
        day_name = WEEKDAYS[index]
        day_data = daily_data.get(index, {})
 
        if not day_data:
            card_content = html.P("Nenhuma entrega programada.", className="text-muted small")
        else:
            card_content = []
            for client_name, products in day_data.items():
                client_header = dbc.Row([
                    dbc.Col(html.H6(client_name, className="mb-0"), width=5, className="text-start"),
                    dbc.Col("Ped.", width=2, className="text-center fw-bold"),
                    dbc.Col("Imp", width=2, className="text-center fw-bold"),
                    dbc.Col("Feito", width=2, className="text-center fw-bold"),
                    dbc.Col("", width=1), # Spacer for the button column
                ], style={'background-color': '#818a89', 'color': 'white', 'padding': '8px 10px', 'border-radius': '5px', 'margin-top': '10px', 'min-width': '500px'},
                className="g-0 align-items-center")
               
                list_items = []
                for product_info in products:
                    product_id = product_info.get('produto_id')
                    tipo_trabalho = product_info.get('tipo_trabalho')
                    pedido_mensal = product_info.get('pedido_mensal', 0)
                    imp_qtd = product_info.get('imp_qtd', 0)
                    feito_qtd = product_info.get('feito_qtd', 0)
                   
                    soma_imp_feito = imp_qtd + feito_qtd
                    if pedido_mensal > 0:
                        ratio = soma_imp_feito / pedido_mensal
                        if ratio >= 2: bg_color = '#d4edda'
                        elif ratio >= 1: bg_color = '#fff3cd'
                        else: bg_color = '#f8d7da'
                    else:
                        bg_color = '#f0f0f0'
 
                    indicator_span = html.Span()
                    if tipo_trabalho and tipo_trabalho in indicator_colors:
                        indicator_span = html.Span(
                            tipo_trabalho[0],
                            className=f"badge bg-{indicator_colors[tipo_trabalho]} me-2"
                        )
                   
                    product_row = dbc.Row([
                        dbc.Col([
                            indicator_span,
                            html.Span(f"{product_info['produto_nome']}")
                        ], width=5, className="text-start"),
                       
                        dbc.Col(
                            html.Span(
                                f"{pedido_mensal:,.0f}",
                                style={'background-color': bg_color, 'padding': '2px 5px', 'border-radius': '5px'}
                            ),
                            width=2, className="text-center"
                        ),
                        dbc.Col(html.Span(f"{imp_qtd:,.0f}"), width=2, className="text-center"),
                        dbc.Col(html.Span(f"{feito_qtd:,.0f}"), width=2, className="text-center"),
                        dbc.Col(
                            dbc.Button(
                                html.I(className="fa fa-pencil-alt"),
                                id={'type': 'btn-pizza-edit', 'index': product_id},
                                color="light",
                                size="sm",
                                className="p-1 border-0"
                            ),
                            width=1, className="text-end"
                        )
                    ], align="center", className="g-0 w-100", style={'min-width': '500px'})
                   
                    list_items.append(dbc.ListGroupItem(product_row, className="py-1 px-2 small"))
               
                client_section = html.Div([
                    client_header,
                    dbc.ListGroup(list_items, flush=True)
                ], style={'overflowX': 'auto'})
 
                card_content.append(client_section)
       
        card_style = {'border': '5px solid #1500ff'} if index == today_index else None
        visible_columns.append(create_day_column(day_name, card_content, card_style=card_style))
   
    return visible_columns

# Callbacks para exportar Excel

@app.callback(
    Output('store-daily-data', 'data'),
    [Input('pizza-center-day-store', 'data'),
     Input('pizza-cliente-filter', 'value'),
     Input('pizza-etiqueta-filter', 'value'),
     Input('pizza-produto-filter', 'value')]
)
def store_daily_data(center_day_index, cliente_id, etiquetas, produto_nome):
    """Armazena os dados diários para uso na exportação Excel"""
    daily_data = get_daily_delivery_data(cliente_id, etiquetas, produto_nome)
    return daily_data

@app.callback(
    Output('pizza-excel-download', 'data'),
    Input('pizza-export-excel', 'n_clicks'),
    State('store-daily-data', 'data'),
    State('pizza-center-day-store', 'data'),
    prevent_initial_call=True
)
def export_pizza_excel(n_clicks, daily_data, center_day_index):
    """Exporta dados das entregas programadas para Excel"""
    if n_clicks and daily_data is not None:
        try:
            excel_data = generate_excel_download(daily_data, center_day_index, 'programadas')
            return dict(
                content=excel_data,
                filename=f"entregas_programadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                base64=True
            )
        except Exception as e:
            print(f"Erro ao exportar Excel: {e}")
            return None
    return None

@app.callback(
    Output('store-empurrado-data', 'data'),
    Input('empurrado-cliente-filter', 'value'),
    Input('empurrado-produto-filter', 'value'),
    Input('empurrado-categoria-filter', 'value'),
    State('store-pcp-empurrado', 'data')
)
def store_empurrado_data(cliente, produto, categoria, pcp_data):
    """Armazena os dados do estoque empurrado para uso na exportação Excel"""
    if pcp_data:
        df_pcp = pd.DataFrame(pcp_data)
        table_result = tabela_estoque_empurrado(df_pcp, cliente, produto, categoria)
        # Extrai os dados do DataFrame
        if hasattr(table_result, 'df_data'):
            return table_result.df_data.to_dict("records")
    return []

@app.callback(
    Output('empurrado-excel-download', 'data'),
    Input('empurrado-export-excel', 'n_clicks'),
    State('store-empurrado-data', 'data'),
    prevent_initial_call=True
)
def export_empurrado_excel(n_clicks, empurrado_data):
    """Exporta dados do estoque empurrado para Excel"""
    if n_clicks and empurrado_data:
        try:
            # Converte os dados de volta para DataFrame
            df_final = pd.DataFrame(empurrado_data)
            excel_data = generate_excel_download({}, 0, 'empurrado', df_final)
            return dict(
                content=excel_data,
                filename=f"estoque_empurrado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                base64=True
            )
        except Exception as e:
            print(f"Erro ao exportar Excel: {e}")
            return None
    return None