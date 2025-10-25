from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from app import app
from .formularios.form_laudo import layout as form_laudo_layout
from .formularios.form_cadastro_laudo import layout as form_cadastro_laudo_layout
from dash import dash_table
from banco_dados.banco import Banco, listar_pcp
from qualidade.funcao.pdf_laudo import generate_laudo_pdf_bytes

layout = dbc.Container([
    dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.Dropdown(id='flt-pcp', options=[], placeholder='PCP'), md=2, className='mb-2'),
                dbc.Col(dcc.Input(id='flt-produto', placeholder='Produto...', type='text'), md=2, className='mb-2'),
                dbc.Col(dcc.Input(id='flt-cliente', placeholder='Cliente...', type='text'), md=2, className='mb-2'),
                dbc.Col(dcc.Input(id='flt-nota', placeholder='Nota fiscal...', type='text'), md=2, className='mb-2'),
                dbc.Col(dcc.Dropdown(id='flt-prod-espec', options=[], placeholder='Produto Espec (Categoria)'), md=2, className='mb-2'),
                dbc.Col(html.Div([
                    dbc.Button('Novo Laudo', id='btn-novo-laudo', color='primary'),
                    dbc.Button('Cadastro de Laudos', id='btn-cadastro-laudos', color='secondary', className='ms-2'),
                ], className='d-flex justify-content-end'), md=2, className='mb-2')
            ])
        ])
    , className='mb-3'),

    # Lista de Laudos (CRUD)
    dbc.Card(
        dbc.CardBody([
            html.H6('Laudos Cadastrados'),
            dash_table.DataTable(
                id='laudos-lista',
                columns=[
                    {"name": "ID", "id": "id"},
                    {"name": "PCP", "id": "pcp_pcp"},
                    {"name": "Produto", "id": "produto_nome"},
                    {"name": "Cliente", "id": "cliente_nome"},
                    {"name": "Nota Fiscal", "id": "nota_fiscal"},
                    {"name": "Produto Espec", "id": "produto_espec"},
                    {"name": "PDF", "id": "_pdf"},
                    {"name": "Editar", "id": "_edit"},
                    {"name": "Excluir", "id": "_del"},
                ],
                data=[], page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'fontSize': 12},
                style_data_conditional=[
                    {'if': {'column_id': '_pdf'}, 'color': '#198754', 'textDecoration': 'underline', 'cursor': 'pointer'},
                    {'if': {'column_id': '_edit'}, 'color': '#0d6efd', 'textDecoration': 'underline', 'cursor': 'pointer'},
                    {'if': {'column_id': '_del'}, 'color': '#dc3545', 'textDecoration': 'underline', 'cursor': 'pointer'},
                ],
            ),
        ])
    , className='mb-3'),

    # Modal para exibir formulários
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id='laudos-modal-title')),
        dbc.ModalBody(id='laudos-modal-body'),
        dbc.ModalFooter(dbc.Button("Fechar", id='laudos-modal-close', className='ms-auto'))
    ], id='laudos-modal', is_open=False, size='xl'),

    # Stores
    dcc.Store(id='laudo-edit-id', data=None),
    dcc.Store(id='laudos-list-refresh', data=0),
    dcc.Download(id='laudo-pdf-download'),

    # espaço reservado (opcional)
    html.Div(id='laudos-page-content')
], fluid=True)

@app.callback(
    Output('laudos-modal', 'is_open'),
    Output('laudos-modal-title', 'children'),
    Output('laudos-modal-body', 'children'),
    Output('laudo-edit-id', 'data'),
    Output('laudos-list-refresh', 'data'),
    Input('btn-novo-laudo', 'n_clicks'),
    Input('btn-cadastro-laudos', 'n_clicks'),
    Input('laudos-modal-close', 'n_clicks'),
    Input('laudos-lista', 'active_cell'),
    State('laudos-modal', 'is_open'),
    State('laudos-lista', 'data'),
    State('laudos-list-refresh', 'data'),
    prevent_initial_call=False
)
def toggle_laudos_modal(n_novo, n_cad, n_close, active_cell, is_open, lista_data, refresh):
    ctx = callback_context
    if not ctx.triggered:
        # Inicialmente fechado e sem conteúdo
        return False, "", html.P('Use os botões acima para abrir um formulário.'), None, refresh

    btn = ctx.triggered[0]['prop_id'].split('.')[0]

    if btn == 'btn-novo-laudo':
        return True, 'Novo Laudo', form_laudo_layout, None, refresh

    if btn == 'btn-cadastro-laudos':
        return True, 'Cadastro de Laudos', form_cadastro_laudo_layout, None, refresh

    if btn == 'laudos-modal-close':
        return False, "", html.P(''), None, refresh

    if btn == 'laudos-lista' and active_cell:
        row = lista_data[active_cell['row']]
        col = active_cell.get('column_id')
        if col == '_pdf':
            # Deixar outro callback tratar o download
            return is_open, "", html.P(''), None, refresh
        if col == '_edit':
            return True, f"Editar Laudo #{row.get('id')}", form_laudo_layout, row.get('id'), refresh
        if col == '_del':
            try:
                banco = Banco()
                banco.deletar_dado('laudos', row.get('id'))
                return False, "", html.P(''), None, (refresh or 0) + 1
            except Exception:
                return is_open, "", html.P('Falha ao excluir.'), None, refresh

    return is_open, "", html.P(''), None, refresh

@app.callback(
    Output('laudos-lista', 'data'),
    Input('laudos-list-refresh', 'data'),
    Input('flt-pcp', 'value'),
    Input('flt-produto', 'value'),
    Input('flt-cliente', 'value'),
    Input('flt-nota', 'value'),
    Input('flt-prod-espec', 'value')
)
def _load_laudos_lista(_, flt_pcp, flt_prod, flt_cli, flt_nota, flt_espec):
    banco = Banco()
    df_l = banco.ler_tabela('laudos')
    if df_l is None or df_l.empty:
        return []
    # Filtro inicial direto na tabela laudos
    df_l = df_l.fillna('')
    if flt_pcp:
        try:
            df_l = df_l[df_l['id_pcp'] == flt_pcp]
        except Exception:
            pass
    if flt_nota:
        try:
            df_l = df_l[df_l['nota_fiscal'].astype(str).str.contains(str(flt_nota), case=False, na=False)]
        except Exception:
            pass
    if flt_espec:
        try:
            df_l = df_l[df_l['produto_espec_id'] == flt_espec]
        except Exception:
            pass
    df_p = listar_pcp()
    has_pcp = df_p is not None and not getattr(df_p, 'empty', True)
    if has_pcp:
        df = df_l.merge(df_p[['pcp_id','pcp_pcp','produto_nome','cliente_nome']], left_on='id_pcp', right_on='pcp_id', how='left')
    else:
        df = df_l.copy()
        df['pcp_pcp'] = ''
        df['produto_nome'] = ''
        df['cliente_nome'] = ''
    # Filtros por produto e cliente (depois do merge com PCP)
    if flt_prod:
        df = df[df['produto_nome'].astype(str).str.contains(str(flt_prod), case=False, na=False)]
    if flt_cli:
        df = df[df['cliente_nome'].astype(str).str.contains(str(flt_cli), case=False, na=False)]
    # Mapear produto_espec_id -> categoria
    try:
        df_es = banco.ler_tabela('produto_espec')
        if df_es is not None and not df_es.empty:
            df_es = df_es[['id','categoria']].rename(columns={'id':'produto_espec_id','categoria':'produto_espec'})
            df = df.merge(df_es, on='produto_espec_id', how='left')
        else:
            df['produto_espec'] = ''
    except Exception:
        df['produto_espec'] = ''
    df['_edit'] = 'Editar'
    df['_del'] = 'Excluir'
    df['_pdf'] = 'PDF'
    return df[['id','pcp_pcp','produto_nome','cliente_nome','nota_fiscal','produto_espec','_pdf','_edit','_del']].to_dict('records')

# Download PDF callback
@app.callback(
    Output('laudo-pdf-download', 'data'),
    Input('laudos-lista', 'active_cell'),
    State('laudos-lista', 'data'),
    prevent_initial_call=True
)
def _download_laudo_pdf(active_cell, rows):
    if not active_cell or not rows:
        return None
    if active_cell.get('column_id') != '_pdf':
        return None
    row = rows[active_cell['row']]
    laudo_id = row.get('id')
    if not laudo_id:
        return None
    banco = Banco()
    df_l = banco.ler_tabela('laudos', id=laudo_id)
    if df_l is None or df_l.empty:
        return None
    laudo = df_l.iloc[0].to_dict()
    df_p = listar_pcp()
    pcp = {}
    if df_p is not None and not df_p.empty:
        r = df_p.loc[df_p['pcp_id'] == laudo.get('id_pcp')]
        if not r.empty:
            pcp = r.iloc[0].to_dict()
    prod_espec = {}
    try:
        df_es = banco.ler_tabela('produto_espec', id=laudo.get('produto_espec_id'))
        if df_es is not None and not df_es.empty:
            prod_espec = df_es.iloc[0].to_dict()
    except Exception:
        prod_espec = {}
    pdf_bytes = generate_laudo_pdf_bytes(laudo, pcp, prod_espec)
    filename = f"laudo_{laudo_id}.pdf"
    return dcc.send_bytes(lambda b: b.write(pdf_bytes), filename)

# Populate filter dropdowns
@app.callback(
    Output('flt-pcp', 'options'),
    Input('flt-pcp', 'id')
)
def _populate_flt_pcp(_):
    df = listar_pcp()
    if df is None or df.empty:
        return []
    df = df.fillna('')
    return [
        {"label": f"{row['pcp_pcp']} - {row['produto_nome']}", "value": int(row['pcp_id'])}
        for _, row in df.iterrows()
    ]

@app.callback(
    Output('flt-prod-espec', 'options'),
    Input('flt-prod-espec', 'id')
)
def _populate_flt_espec(_):
    banco = Banco()
    df = banco.ler_tabela('produto_espec')
    if df is None or df.empty:
        return []
    df = df.fillna('')
    return [
        {"label": f"{row['categoria']}", "value": int(row['id'])}
        for _, row in df.iterrows()
    ]
