import dash
from dash import html, dcc, callback
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from sqlalchemy import func, text
from io import StringIO

from app import app
from banco_dados.banco import Session, engine, APONTAMENTO_PRODUTO, PRODUCAO, SETOR, PCP, PRODUTO, CLIENTE, Banco, PLANEJAMENTO

def create_apontamento_report(categorias=None, semanas_entrega=None, cliente_ids=None, semanas_planejamento=None):
    with Session(engine) as session:
        # CTE to get the latest planning date for each PCP
        ultimo_planejamento_subq = session.query(
            PLANEJAMENTO.id_pcp,
            func.max(PLANEJAMENTO.data_programacao).label('ultima_data_programacao')
        ).group_by(PLANEJAMENTO.id_pcp).subquery()

        # Main query
        query = session.query(
            PCP.pcp_pcp,
            PRODUTO.nome.label('produto_nome'),
            PCP.pcp_qtd,
            APONTAMENTO_PRODUTO.atp_plano,
            SETOR.setor_nome,
            func.sum(APONTAMENTO_PRODUTO.atp_qtd * func.coalesce(APONTAMENTO_PRODUTO.atp_repeticoes, 1)).label('total_qtd'),
            func.sum(func.coalesce(APONTAMENTO_PRODUTO.atp_refugos, 0) * func.coalesce(APONTAMENTO_PRODUTO.atp_repeticoes, 1)).label('total_refugos')
        ).join(APONTAMENTO_PRODUTO, PCP.pcp_id == APONTAMENTO_PRODUTO.atp_pcp)\
         .join(PRODUCAO, APONTAMENTO_PRODUTO.atp_producao == PRODUCAO.pr_id)\
         .join(SETOR, PRODUCAO.pr_setor_id == SETOR.setor_id)\
         .join(PRODUTO, PCP.pcp_produto_id == PRODUTO.produto_id)\
         .outerjoin(ultimo_planejamento_subq, PCP.pcp_id == ultimo_planejamento_subq.c.id_pcp)

        # Apply filters
        if categorias:
            query = query.filter(PCP.pcp_categoria.in_(categorias))
        if semanas_entrega:
            query = query.filter(func.strftime('%W', PCP.pcp_entrega).in_(semanas_entrega))
        if cliente_ids:
            query = query.join(CLIENTE, PCP.pcp_cliente_id == CLIENTE.cliente_id).filter(CLIENTE.cliente_id.in_(cliente_ids))
        if semanas_planejamento:
            query = query.filter(func.strftime('%W', ultimo_planejamento_subq.c.ultima_data_programacao).in_(semanas_planejamento))

        query = query.group_by(PCP.pcp_pcp, PRODUTO.nome, PCP.pcp_qtd, APONTAMENTO_PRODUTO.atp_plano, SETOR.setor_nome).statement

        df = pd.read_sql(query, session.bind)

        if df.empty:
            return pd.DataFrame()

        plano_map = {0: 'Tampa', 1: 'Fundo', 2: 'Berço/Envelope', 3: 'Lâmina'}
        df['atp_plano'] = df['atp_plano'].map(plano_map).fillna('Não Especificado')

        pivoted_df = df.pivot_table(
            index=['pcp_pcp', 'produto_nome', 'pcp_qtd', 'atp_plano'],
            columns='setor_nome',
            values=['total_qtd', 'total_refugos'],
            fill_value=0
        )
        pivoted_df = pivoted_df.astype(int)

        pivoted_df.columns = ['_'.join(map(str, col)).strip() for col in pivoted_df.columns.values]
        pivoted_df = pivoted_df.reset_index()

        pivoted_df = pivoted_df.rename(columns={
            'pcp_pcp': 'PCP',
            'produto_nome': 'Produto',
            'pcp_qtd': 'Qtd Planejada',
            'atp_plano': 'Plano',
        })
        
        return pivoted_df

title_div = html.Div(
    html.H1("Relatório de Apontamentos de Produção",
            className="text-center mb-0",
            style={
                'color': '#2c3e50',
                'font-weight': '600',
                'letter-spacing': '0.5px',
                'text-shadow': '1px 1px 2px rgba(0,0,0,0.1)'
            }),
    style={
        'background': 'linear-gradient(to right, #f8f9fa, #e9ecef, #f8f9fa)',
        'padding': '20px',
        'border-radius': '10px',
        'box-shadow': '0 4px 6px rgba(0,0,0,0.1)',
        'margin-bottom': '25px'
    }
)

filter_card = dbc.Card(
    dbc.CardBody([
        dbc.Row([
            dbc.Col(
                [
                    dbc.Label("Categoria", html_for="categoria-filter-apontamento"),
                    dcc.Dropdown(
                        id='categoria-filter-apontamento',
                        placeholder="Filtrar...",
                        options=[
                            {'label': 'CAIXA 5L', 'value': 'CAIXA 5L'}, {'label': 'CAIXA 10L', 'value': 'CAIXA 10L'},
                            {'label': 'CAIXA 7L', 'value': 'CAIXA 7L'}, {'label': 'TAMPA 10L', 'value': 'TAMPA 10L'},
                            {'label': 'TAMPA 5L', 'value': 'TAMPA 5L'}, {'label': 'ESPECIAL', 'value': 'ESPECIAL'},
                            {'label': 'CINTA', 'value': 'CINTA'}, {'label': 'PIZZA', 'value': 'PIZZA'},
                            {'label': 'POTE 500ML', 'value': 'POTE 500ML'}, {'label': 'POTE 480ML', 'value': 'POTE 480ML'},
                            {'label': 'POTE 240ML', 'value': 'POTE 240ML'}, {'label': 'POTE 250ML', 'value': 'POTE 250ML'},
                            {'label': 'POTE 1L', 'value': 'POTE 1L'}, {'label': 'POTE 360ML', 'value': 'POTE 360ML'},
                            {'label': 'POTE 180ML', 'value': 'POTE 180ML'}, {'label': 'POTE 150ML', 'value': 'POTE 150ML'},
                            {'label': 'POTE 120ML', 'value': 'POTE 120ML'}, {'label': 'POTE 80ML', 'value': 'POTE 80ML'},
                            {'label': 'COPO 360ML', 'value': 'COPO 360ML'}, {'label': 'COPO 200ML', 'value': 'COPO 200ML'},
                            {'label': 'COPO 100ML', 'value': 'COPO 100ML'}
                        ],
                        multi=True
                    ),
                ],
                width=3
            ),
            dbc.Col(
                [
                    dbc.Label("Semana Entrega", html_for="semana-filter-apontamento"),
                    dcc.Dropdown(id='semana-filter-apontamento', placeholder="Filtrar...", multi=True),
                ],
                width=3
            ),
            dbc.Col(
                [
                    dbc.Label("Cliente", html_for="cliente-filter-apontamento"),
                    dcc.Dropdown(id='cliente-filter-apontamento', placeholder="Filtrar...", multi=True),
                ],
                width=3
            ),
            dbc.Col(
                [
                    dbc.Label("Semana Último Planejamento", html_for="semana-planejamento-filter-apontamento"),
                    dcc.Dropdown(id='semana-planejamento-filter-apontamento', placeholder="Filtrar...", multi=True),
                ],
                width=3
            )
        ])
    ]),
    className="mb-4"
)

layout = dbc.Container([
    title_div,
    filter_card,
    dcc.Store(id='report-data-store'),
    dcc.Loading(
        id="loading-apontamento-report",
        type="circle",
        children=html.Div(id="apontamento-report-table-container")
    ),
    dbc.Row(
        dbc.Col(
            dbc.Pagination(id="pagination", max_value=0, fully_expanded=False, active_page=1),
            width={"size": "auto", "offset": 5},
        )
    )
], fluid=True)

@app.callback(
    [Output('report-data-store', 'data'),
     Output('pagination', 'max_value'),
     Output('pagination', 'active_page')],
    [Input('url', 'pathname'),
     Input('categoria-filter-apontamento', 'value'),
     Input('semana-filter-apontamento', 'value'),
     Input('cliente-filter-apontamento', 'value'),
     Input('semana-planejamento-filter-apontamento', 'value')]
)
def update_report_data(pathname, categorias, semanas_entrega, cliente_ids, semanas_planejamento):
    if pathname != '/relatorioapontamento':
        raise PreventUpdate
    
    report_df_pivoted = create_apontamento_report(categorias, semanas_entrega, cliente_ids, semanas_planejamento)

    if report_df_pivoted.empty:
        return pd.DataFrame().to_json(date_format='iso', orient='split'), 0, 1

    report_df_pivoted = report_df_pivoted.sort_values(by='PCP', ascending=True)

    page_markers = []
    current_page = 1
    row_count = 0
    PAGE_ROW_LIMIT = 30
    
    merge_cols = ['PCP', 'Produto', 'Qtd Planejada']
    grouped = report_df_pivoted.groupby(merge_cols, sort=False)

    for _, group in grouped:
        if row_count > 0 and row_count + len(group) > PAGE_ROW_LIMIT:
            current_page += 1
            row_count = 0
        
        page_markers.extend([current_page] * len(group))
        row_count += len(group)

    report_df_pivoted['page'] = page_markers
    max_pages = report_df_pivoted['page'].max() if not report_df_pivoted.empty else 1
    
    return report_df_pivoted.to_json(date_format='iso', orient='split'), max_pages, 1

@app.callback(
    [Output('cliente-filter-apontamento', 'options'),
     Output('semana-filter-apontamento', 'options'),
     Output('semana-planejamento-filter-apontamento', 'options')],
    [Input('url', 'pathname')]
)
def populate_filters(pathname):
    if pathname != '/relatorioapontamento':
        raise PreventUpdate

    # Client filter
    banco = Banco()
    df_clientes = banco.ler_tabela('clientes')
    cliente_options = []
    if not df_clientes.empty:
        cliente_options = [{'label': row['nome'], 'value': row['cliente_id']} for _, row in df_clientes.sort_values('nome').iterrows()]

    semana_entrega_options = []
    semana_planejamento_options = []

    with Session(engine) as session:
        # Delivery week filter
        query_entrega = session.query(func.strftime('%W', PCP.pcp_entrega).label('semana')).filter(PCP.pcp_entrega.isnot(None)).distinct().order_by('semana')
        semanas_entrega = [row.semana for row in query_entrega.all()]
        semana_entrega_options = [{'label': f'Semana Entrega {s}', 'value': s} for s in semanas_entrega]

        # Latest planning week filter
        ultimo_planejamento_subq = session.query(
            func.max(PLANEJAMENTO.data_programacao).label('ultima_data_programacao')
        ).group_by(PLANEJAMENTO.id_pcp).subquery()

        semanas_planejamento_query = session.query(
            func.strftime('%W', ultimo_planejamento_subq.c.ultima_data_programacao).label('semana')
        ).distinct().order_by(text('semana'))
        
        semanas_planejamento = [row.semana for row in semanas_planejamento_query.all() if row.semana is not None]
        semana_planejamento_options = [{'label': f'Semana Planejamento {s}', 'value': s} for s in semanas_planejamento]

    return cliente_options, semana_entrega_options, semana_planejamento_options

@app.callback(
    Output("apontamento-report-table-container", "children"),
    [Input('report-data-store', 'data'),
     Input("pagination", "active_page")]
)
def update_table_display(data, active_page):
    if not data or not active_page:
        raise PreventUpdate

    report_df_pivoted = pd.read_json(StringIO(data), orient='split')
    
    if report_df_pivoted.empty:
        return html.Div("Nenhum dado de apontamento encontrado.", style={'textAlign': 'center', 'padding': '20px'})

    report_df = report_df_pivoted[report_df_pivoted['page'] == active_page].copy()
    
    available_sectors = set([c.split('_')[-1] for c in report_df.columns if c.startswith('total_qtd')])
    
    desired_order = [
        "FORMATAÇÃO", "IMPRESSÃO", "PLASTIFICAÇÃO", "ACOPLAGEM", 
        "CORTE VINCO", "COLADEIRA/DOBRADEIRA", "POTE/COPO", "PRISCELL"
    ]

    all_sectors = [sector for sector in desired_order if sector in available_sectors]
    remaining_sectors = sorted([sector for sector in available_sectors if sector not in all_sectors])
    all_sectors.extend(remaining_sectors)

    header_cols = ['PCP', 'Produto', 'Qtd Planejada', 'Plano'] + all_sectors
    table_header = [
        html.Thead(html.Tr([html.Th(col, style={'textAlign': 'center', 'verticalAlign': 'middle', 'backgroundColor': '#343a40', 'color': 'white'}) for col in header_cols]))
    ]
    
    merge_cols = ['PCP', 'Produto', 'Qtd Planejada']
    
    all_groups_list = list(report_df_pivoted.groupby(merge_cols, sort=False).groups.keys())

    report_df['rowspan'] = report_df.groupby(merge_cols)['PCP'].transform('count')
    report_df['is_first'] = ~report_df.duplicated(subset=merge_cols, keep='first')
    report_df['is_last'] = ~report_df.duplicated(subset=merge_cols, keep='last')
    
    body_rows = []
    group_colors = ['#FFFFFF', '#f8f9fa']

    for _, row in report_df.iterrows():
        cells = []
        row_style = {}
        
        group_key = tuple(row[col] for col in merge_cols)
        try:
            group_idx = all_groups_list.index(group_key)
        except ValueError:
            group_idx = 0
        
        current_color = group_colors[group_idx % 2]
        td_style = {'textAlign': 'center', 'verticalAlign': 'middle', 'backgroundColor': current_color}

        if row['is_first']:
            row_style['border-top'] = '2px solid #333'
            for col in merge_cols:
                cells.append(html.Td(f"{int(row[col]):,}".replace(',', '.') if isinstance(row[col], (int, float)) else row[col], rowSpan=row['rowspan'], style=td_style))
        
        cells.append(html.Td(row['Plano'], style=td_style))

        if row['is_last']:
            row_style['border-bottom'] = '2px solid #333'

        for sector in all_sectors:
            qtd_col = f'total_qtd_{sector}'
            refugo_col = f'total_refugos_{sector}'
            qtd_val = row.get(qtd_col, 0)
            refugo_val = row.get(refugo_col, 0)
            pcp_qtd = row.get('Qtd Planejada', 0)

            if pcp_qtd > 0:
                yield_percentage = ((qtd_val - refugo_val) / pcp_qtd) * 100
            else:
                yield_percentage = 0

            cell_content = [
                html.Span(f"{int(qtd_val):,}".replace(',', '.'), style={'color': 'green', 'fontWeight': 'bold'}),
                html.Br(),
                html.Span(f"{int(refugo_val):,}".replace(',', '.'), style={'color': 'red', 'fontWeight': 'bold'}),
                html.Br(),
                html.Span(f"{yield_percentage:.2f}%", style={'fontWeight': 'bold'})
            ]
            
            cells.append(html.Td(cell_content, style=td_style))

        body_rows.append(html.Tr(cells, style=row_style))

    table_body = [html.Tbody(body_rows)]
    
    table = dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True, id='tabela_apontamento_report')
    return table
