from dash import html, dcc, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
from dash import dash_table
from app import app
from banco_dados.banco import Banco, listar_pcp

layout = dbc.Card([
    dbc.CardHeader(html.H5("Novo Laudo")),
    dbc.CardBody([
        # Linha 1: Selecionar PCP e exibir infos
        dbc.Row([
            dbc.Col([
                dbc.Label("PCP (label = pcp_pcp | value = pcp_id)"),
                dcc.Dropdown(id='laudo-pcp', options=[], placeholder='Selecione o PCP...')
            ], md=6),
            dbc.Col([
                dbc.Label("Produto"),
                html.Div(id='laudo-info-produto', className='form-control', style={'background': '#f8f9fa'})
            ], md=3),
            dbc.Col([
                dbc.Label("Qtd Planejada"),
                html.Div(id='laudo-info-qtd', className='form-control', style={'background': '#f8f9fa'})
            ], md=3),
        ], className='mb-2'),
        dbc.Row([
            dbc.Col([
                dbc.Label("Cliente"),
                html.Div(id='laudo-info-cliente', className='form-control', style={'background': '#f8f9fa'})
            ], md=6),
        ], className='mb-3'),

        # Linha 2: Nota fiscal e qtd_por_plano (tabela editável)
        dbc.Row([
            dbc.Col([
                dbc.Label("Nota Fiscal"),
                dcc.Input(id='laudo-nota', type='number', placeholder='Número da nota...', className='form-control')
            ], md=3),
            dbc.Col([
                dbc.Label("Qtd por Plano"),
                dash_table.DataTable(
                    id='laudo-qpp-table',
                    columns=[
                        {"name": "Parte", "id": "parte", "presentation": "input"},
                        {"name": "Total", "id": "total", "type": "numeric"},
                        {"name": "Volumes", "id": "volumes", "type": "numeric"},
                        {"name": "Por Volume", "id": "por_volume", "type": "numeric"},
                    ],
                    data=[{"parte": "Tampa", "total": None, "volumes": None, "por_volume": None},
                          {"parte": "Fundo", "total": None, "volumes": None, "por_volume": None}],
                    editable=True,
                    row_deletable=True,
                    style_table={"overflowX": "auto"},
                    style_cell={"fontSize": 12},
                ),
                dbc.Button("Adicionar Linha", id='laudo-qpp-add', size='sm', className='mt-2')
            ], md=9),
        ], className='mb-3'),

        # Linha 3: produto_espec_id
        dbc.Row([
            dbc.Col([
                dbc.Label("Produto Espec (produto_espec_id)"),
                dcc.Dropdown(id='laudo-prod-espec', options=[], placeholder='Selecione o Produto Especificação...')
            ], md=6),
        ], className='mb-3'),

        # Mensagem de resultado
        dbc.Alert(id='laudo-save-msg', is_open=False, color='success', className='mb-0'),

        # Ações
        dbc.Button("Salvar", id='btn-salvar-laudo', color='success', className='mt-3')
    ])
])


# Callbacks
@app.callback(
    Output('laudo-pcp', 'options'),
    Input('laudo-pcp', 'id')
)
def _populate_pcp_options(_):
    df = listar_pcp()
    if df is None or df.empty:
        return []
    # Cria opções com label pcp_pcp e value pcp_id
    df = df.fillna('')
    opts = [
        {"label": f"{row['pcp_pcp']} - {row['produto_nome']}", "value": int(row['pcp_id'])}
        for _, row in df.iterrows()
    ]
    return opts


@app.callback(
    Output('laudo-info-produto', 'children'),
    Output('laudo-info-qtd', 'children'),
    Output('laudo-info-cliente', 'children'),
    Input('laudo-pcp', 'value')
)
def _update_pcp_info(pcp_id):
    if not pcp_id:
        return '', '', ''
    df = listar_pcp()
    if df is None or df.empty:
        return '', '', ''
    row = df.loc[df['pcp_id'] == pcp_id]
    if row.empty:
        return '', '', ''
    r = row.iloc[0]
    return r.get('produto_nome', ''), str(r.get('pcp_qtd', '')), r.get('cliente_nome', '')


@app.callback(
    Output('laudo-qpp-table', 'data'),
    Input('laudo-qpp-table', 'data_timestamp'),
    State('laudo-qpp-table', 'data')
)
def _recalc_por_volume(_, data):
    if not data:
        return data
    new_data = []
    for row in data:
        total = row.get('total')
        volumes = row.get('volumes')
        por_volume = None
        try:
            if total is not None and volumes not in (None, 0):
                por_volume = int(round(float(total) / float(volumes)))
        except Exception:
            por_volume = None
        new_row = {**row, 'por_volume': por_volume}
        new_data.append(new_row)
    return new_data


@app.callback(
    Output('laudo-qpp-table', 'data', allow_duplicate=True),
    Input('laudo-qpp-add', 'n_clicks'),
    State('laudo-qpp-table', 'data'),
    prevent_initial_call=True
)
def _add_qpp_row(n, data):
    data = data or []
    data.append({"parte": "", "total": None, "volumes": None, "por_volume": None})
    return data


@app.callback(
    Output('laudo-prod-espec', 'options'),
    Input('laudo-prod-espec', 'id'),
    Input('laudos-modal', 'is_open')
)
def _populate_prod_espec(_, is_open):
    banco = Banco()
    df = banco.ler_tabela('produto_espec')
    if df is None or df.empty:
        return []
    df = df.fillna('')
    return [
        {"label": f"{row['id']} - {row['categoria']} {('- ' + row['grupo']) if row['grupo'] else ''}", "value": int(row['id'])}
        for _, row in df.iterrows()
    ]


@app.callback(
    Output('laudo-save-msg', 'children'),
    Output('laudo-save-msg', 'is_open'),
    Output('laudo-save-msg', 'color'),
    Output('laudos-list-refresh', 'data', allow_duplicate=True),
    Output('laudos-modal', 'is_open', allow_duplicate=True),
    Output('laudo-edit-id', 'data', allow_duplicate=True),
    Input('btn-salvar-laudo', 'n_clicks'),
    State('laudo-pcp', 'value'),
    State('laudo-nota', 'value'),
    State('laudo-qpp-table', 'data'),
    State('laudo-prod-espec', 'value'),
    State('laudo-edit-id', 'data'),
    State('laudos-list-refresh', 'data'),
    prevent_initial_call=True
)
def _save_laudo(n, pcp_id, nota_fiscal, qpp_rows, produto_espec_id, edit_id, refresh):
    ctx = callback_context
    if not ctx.triggered or ctx.triggered[0]['prop_id'].split('.')[0] != 'btn-salvar-laudo':
        return no_update, no_update, no_update, no_update, no_update, no_update
    if not n:
        return '', False, 'success', refresh, no_update, no_update
    if not pcp_id:
        return 'Selecione um PCP.', True, 'warning', refresh, True, edit_id
    # Montar JSON numérico
    qpp = {}
    for row in qpp_rows or []:
        parte = (row.get('parte') or '').strip()
        if not parte:
            continue
        total = row.get('total')
        volumes = row.get('volumes')
        por_volume = row.get('por_volume')
        # Garante numéricos ou None
        try:
            total = int(total) if total is not None else None
        except Exception:
            total = None
        try:
            volumes = int(volumes) if volumes is not None else None
        except Exception:
            volumes = None
        try:
            por_volume = int(por_volume) if por_volume is not None else (int(round(float(total) / float(volumes))) if (total and volumes) else None)
        except Exception:
            por_volume = None
        qpp[parte] = {"total": total, "volumes": volumes, "por_volume": por_volume}

    try:
        banco = Banco()
        if edit_id:
            banco.editar_dado('laudos', edit_id, id_pcp=pcp_id, nota_fiscal=nota_fiscal, qtd_por_plano=qpp, produto_espec_id=produto_espec_id)
        else:
            banco.inserir_dados('laudos', id_pcp=pcp_id, nota_fiscal=nota_fiscal, qtd_por_plano=qpp, produto_espec_id=produto_espec_id)
        # Sucesso: fecha o modal e limpa o edit-id
        return '', False, 'success', (refresh or 0) + 1, False, None
    except Exception as e:
        return f'Erro ao salvar: {e}', True, 'danger', refresh, True, edit_id


# Prefill ao editar (define apenas valores essenciais e deixa as infos serem preenchidas pelo callback de PCP)
@app.callback(
    Output('laudo-pcp', 'value'),
    Output('laudo-nota', 'value'),
    Output('laudo-qpp-table', 'data', allow_duplicate=True),
    Output('laudo-prod-espec', 'value', allow_duplicate=True),
    Input('laudos-modal', 'is_open'),
    State('laudo-edit-id', 'data'),
    State('laudo-prod-espec', 'options'),
    prevent_initial_call=True
)
def _prefill_from_edit(is_open, edit_id, prod_espec_options):
    if not is_open:
        return no_update, no_update, no_update, no_update
    if not edit_id:
        return None, None, [
            {"parte": "Tampa", "total": None, "volumes": None, "por_volume": None},
            {"parte": "Fundo", "total": None, "volumes": None, "por_volume": None}
        ], None
    banco = Banco()
    df = banco.ler_tabela('laudos', id=edit_id)
    if df is None or df.empty:
        return None, None, [], None
    row = df.iloc[0]
    id_pcp = row.get('id_pcp')
    nota = row.get('nota_fiscal')
    prod_espec = row.get('produto_espec_id')
    qpp = row.get('qtd_por_plano') or {}
    data_rows = []
    try:
        # qpp pode vir como dict (json)
        if isinstance(qpp, dict):
            items_iter = qpp.items()
        else:
            items_iter = []
        for parte, vals in items_iter:
            total = vals.get('total') if isinstance(vals, dict) else None
            volumes = vals.get('volumes') if isinstance(vals, dict) else None
            por_volume = vals.get('por_volume') if isinstance(vals, dict) else None
            try:
                if por_volume is None and total is not None and volumes:
                    por_volume = int(round(float(total) / float(volumes)))
                else:
                    por_volume = int(por_volume) if por_volume is not None else None
            except Exception:
                por_volume = None
            data_rows.append({
                'parte': parte,
                'total': total,
                'volumes': volumes,
                'por_volume': por_volume
            })
    except Exception:
        data_rows = []
    # Só seta value se opção existir para evitar falha de sincronização
    target_value = prod_espec if prod_espec is not None else None
    try:
        values = set([opt.get('value') for opt in (prod_espec_options or [])])
        if target_value not in values:
            target_value = no_update
    except Exception:
        target_value = prod_espec
    return id_pcp, nota, (data_rows or []), target_value

# Quando as opções do dropdown são carregadas/recarregadas, garante selecionar o valor do registro em edição
@app.callback(
    Output('laudo-prod-espec', 'value', allow_duplicate=True),
    Input('laudo-prod-espec', 'options'),
    State('laudo-edit-id', 'data'),
    prevent_initial_call=True
)
def _sync_prod_espec_value(options, edit_id):
    if not options or not edit_id:
        return no_update
    try:
        banco = Banco()
        df = banco.ler_tabela('laudos', id=edit_id)
        if df is None or df.empty:
            return no_update
        prod_espec = df.iloc[0].get('produto_espec_id')
        opt_values = set([opt.get('value') for opt in options])
        if prod_espec in opt_values:
            return prod_espec
        return no_update
    except Exception:
        return no_update
