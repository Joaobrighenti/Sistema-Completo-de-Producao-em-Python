from dash import html, dcc, callback_context, dash_table
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
from datetime import date, datetime
import pandas as pd
from app import *
import json

# BANCO DE DADOS
from banco_dados.banco import Banco

# ======== LAYOUT ======= #
layout = html.Div([
    dcc.Store(id='solicitacao-items-store', data=[]),
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle('Solicitação de Materiais/Itens')),
        dbc.ModalBody([
            # --- Seção do Solicitante e Setor ---
            dbc.Row([
                dbc.Col([
                    dbc.Label('Solicitante'),
                    dcc.Dropdown(
                        id='solicitacao_solicitante',
                        options=[
                            {"label": "Joao", "value": "Joao"},
                            {"label": "Max", "value": "Max"},
                            {"label": "Julio", "value": "Julio"},
                            {"label": "Vanderlei", "value": "Vanderlei"},
                            {"label": "Leonardo", "value": "Leonardo"},
                            {"label": "Gabriella", "value": "Gabriella"},
                            {"label": "Diva", "value": "Diva"},
                            {"label": "Valdecir", "value": "Valdecir"},
                            {"label": "Gustavo", "value": "Gustavo"},
                            {"label": "Douglas", "value": "Douglas"},
                            {"label": "Eduardo B.", "value": "Eduardo B."},
                            {"label": "Renan", "value": "Renan"}
                        ],
                        placeholder='Selecione o solicitante...',
                        className='dbc'
                    )
                ], sm=12, md=6),
                dbc.Col([
                    dbc.Label('Setor'),
                    dcc.Dropdown(
                        id='solicitacao_setor',
                        options=[
                            {'label': 'Impressão', 'value': 'producao'},
                            {'label': 'Laminação', 'value': 'laminacao'},
                            {'label': 'CorteVinco', 'value': 'cortevinco'},
                            {'label': 'Rh', 'value': 'rh'},
                            {'label': 'Arte', 'value': 'arte'},
                            {'label': 'Acopladeira', 'value': 'acopladeira'},
                            {'label': 'Comercial', 'value': 'comercial'},
                            {'label': 'Logística', 'value': 'logistica'},
                            {'label': 'Manutenção', 'value': 'manutencao'},
                            {'label': 'Qualidade', 'value': 'qualidade'},
                            {'label': 'Pcp', 'value': 'pcp'}
                        ],
                        placeholder='Selecione o setor...',
                        className='dbc'
                    )
                ], sm=12, md=6),
            ]),
            html.Hr(),
            # --- Seção para Adicionar Itens ---
            html.H5("Adicionar Item à Solicitação"),
            dbc.Row([
                dbc.Col([
                    dbc.Label('Descrição do Item'),
                    dbc.Textarea(id='solicitacao_descricao', placeholder='Descreva o item solicitado...', style={'height': '80px'})
                ], width=12, className="mb-2"),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Label('Data de Entrega'),
                    dcc.DatePickerSingle(id='solicitacao_data_entrega', className='dbc w-100', date=date.today(), initial_visible_month=date.today())
                ], lg=3, md=6, xs=12, className="mb-2"),
                dbc.Col([
                    dbc.Label('Quantidade'),
                    dbc.Input(id='solicitacao_quantidade', type='number', min=1, step=1, placeholder='Qtd')
                ], lg=3, md=6, xs=12, className="mb-2"),
                dbc.Col([
                    dbc.Label('Unidade'),
                    dcc.Dropdown(id='solicitacao_unidade', options=[{"label": lbl, "value": val} for val, lbl in [("UN", "UN"), ("KG", "KG"), ("CX", "CX"), ("PC", "PC"), ("FLS", "FLS"), ("LT", "LT"), ("BOB", "BOB"), ("RL", "RL")]], placeholder='Unid.', className='dbc')
                ], lg=3, md=6, xs=12, className="mb-2"),
                dbc.Col([
                    dbc.Label('OS Vinculada (PCP)'),
                    dcc.Dropdown(id='solicitacao_pcp_id', placeholder='Opcional', className='dbc')
                ], lg=3, md=6, xs=12, className="mb-2"),
            ], className='g-2'),
            dbc.Button("Adicionar Item", id="solicitacao-add-item-btn", color="primary", className="mt-3 w-100"),
            html.Hr(),
            # --- Tabela de Itens Adicionados ---
            html.H5("Itens na Solicitação"),
            html.Div(id='solicitacao-items-list', className='mt-3'),
            html.Div(id='solicitacao_mensagem', className='mt-3'),
        ]),
        dbc.ModalFooter([
            dbc.Button('Cancelar', id='solicitacao_cancelar', color='secondary'),
            dbc.Button('Enviar Solicitação', id='solicitacao_enviar', color='success')
        ])
    ], id='modal_solicitacao', is_open=False, size="lg")
])

# Callback para abrir o modal, carregar opções de PCP e limpar o store de itens
@app.callback(
    Output('modal_solicitacao', 'is_open'),
    Output('solicitacao_pcp_id', 'options'),
    Output('solicitacao-items-store', 'data', allow_duplicate=True),
    Input('btn-solicitacao_compras', 'n_clicks'),
    [State('modal_solicitacao', 'is_open')],
    prevent_initial_call=True
)
def toggle_modal_solicitacao(n_abrir, is_open):
    opcoes_pcp = []
    if n_abrir:
        banco = Banco()
        df_pcp = banco.ler_tabela('pcp')
        opcoes_pcp = [{'label': f'PCP {row["pcp_pcp"]}', 'value': row["pcp_id"]} 
                      for _, row in df_pcp.iterrows() if row.get("pcp_pcp")]
        # Limpa a lista de itens ao abrir o modal
        return not is_open, opcoes_pcp, []
    return is_open, dash.no_update, dash.no_update

# Callback para adicionar item ao `dcc.Store` e validar campos
@app.callback(
    Output('solicitacao-items-store', 'data', allow_duplicate=True),
    Output('solicitacao_descricao', 'value', allow_duplicate=True),
    Output('solicitacao_quantidade', 'value', allow_duplicate=True),
    Output('solicitacao_unidade', 'value', allow_duplicate=True),
    Output('solicitacao_mensagem', 'children', allow_duplicate=True),
    Input('solicitacao-add-item-btn', 'n_clicks'),
    [
        State('solicitacao-items-store', 'data'),
        State('solicitacao_descricao', 'value'),
        State('solicitacao_data_entrega', 'date'),
        State('solicitacao_pcp_id', 'value'),
        State('solicitacao_quantidade', 'value'),
        State('solicitacao_unidade', 'value'),
    ],
    prevent_initial_call=True
)
def add_item_to_store(n_clicks, items, descricao, data_entrega, pcp_id, qtd, unidade):
    if n_clicks:
        if not all([descricao, qtd, unidade]):
            # Mantém os valores e exibe alerta
            return items, descricao, qtd, unidade, dbc.Alert("Preencha Descrição, Quantidade e Unidade.", color="warning")

        new_item = {
            'descricao': descricao,
            'data_entrega': data_entrega,
            'pcp_id': pcp_id,
            'qtd': qtd,
            'unidade': unidade,
        }
        items.append(new_item)
        # Limpa campos do item e a mensagem de erro
        return items, None, None, None, ""
    # Retorno padrão para não alterar nada sem clique
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Callback para exibir a lista de itens do `dcc.Store`
@app.callback(
    Output('solicitacao-items-list', 'children'),
    Input('solicitacao-items-store', 'data')
)
def update_items_list(items):
    if not items:
        return dbc.Alert("Nenhum item adicionado à solicitação.", color="info")

    table_header = [html.Thead(html.Tr([
        html.Th("Descrição"), html.Th("Qtd"), html.Th("Unid."), 
        html.Th("Entrega"), html.Th("OS"), html.Th("Ação")
    ]))]

    table_body = [html.Tbody([
        html.Tr([
            html.Td(item['descricao']),
            html.Td(item['qtd']),
            html.Td(item['unidade']),
            datetime.strptime(item['data_entrega'].split('T')[0], '%Y-%m-%d').strftime('%d/%m/%Y'),
            html.Td(item['pcp_id'] if item.get('pcp_id') else '-'),
            html.Td(dbc.Button("Remover", id={'type': 'remove-solicitacao-item', 'index': i}, color="danger", size="sm"))
        ]) for i, item in enumerate(items)
    ])]

    return dbc.Table(table_header + table_body, bordered=True, striped=True, hover=True, responsive=True)

# Callback para remover item do `dcc.Store`
@app.callback(
    Output('solicitacao-items-store', 'data', allow_duplicate=True),
    Input({'type': 'remove-solicitacao-item', 'index': ALL}, 'n_clicks'),
    State('solicitacao-items-store', 'data'),
    prevent_initial_call=True
)
def remove_item_from_store(n_clicks, items):
    if not any(n_clicks):
        return dash.no_update

    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update

    button_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        button_id = json.loads(button_id_str)
        index_to_remove = button_id.get('index')
        if index_to_remove is not None:
            items.pop(index_to_remove)
    except (json.JSONDecodeError, IndexError):
        pass
        
    return items

# Callback para enviar a solicitação (e fechar o modal)
@app.callback(
    Output('solicitacao_mensagem', 'children', allow_duplicate=True),
    Output('modal_solicitacao', 'is_open', allow_duplicate=True),
    Output('solicitacao-items-store', 'data', allow_duplicate=True),
    Output('solicitacao_solicitante', 'value', allow_duplicate=True),
    Output('solicitacao_setor', 'value', allow_duplicate=True),
    Input('solicitacao_enviar', 'n_clicks'),
    [
        State('solicitacao-items-store', 'data'),
        State('solicitacao_solicitante', 'value'),
        State('solicitacao_setor', 'value'),
    ],
    prevent_initial_call=True
)
def processar_solicitacao(n_clicks, items, solicitante, setor):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if not solicitante or not setor:
        return dbc.Alert("Por favor, preencha o Solicitante e o Setor.", color='danger'), True, items, solicitante, setor
    
    if not items:
        return dbc.Alert("Adicione pelo menos um item à solicitação.", color='danger'), True, items, solicitante, setor

    try:
        banco = Banco()
        df_ordem_compra = banco.ler_tabela('ordem_compra')
        
        if df_ordem_compra.empty or 'oc_solicitacao' not in df_ordem_compra.columns or df_ordem_compra['oc_solicitacao'].isnull().all():
            next_solicitacao_id = 1
        else:
            next_solicitacao_id = int(df_ordem_compra['oc_solicitacao'].max()) + 1

        for item in items:
            data_entrega = datetime.strptime(item['data_entrega'].split('T')[0], '%Y-%m-%d').date()
            banco.inserir_dados('ordem_compra',
                oc_nome_solicitacao=item['descricao'],
                oc_data_necessaria=data_entrega,
                oc_pcp_id=item['pcp_id'],
                oc_solicitante=solicitante,
                oc_setor=setor,
                oc_qtd_solicitada=item['qtd'],
                oc_unid_compra=item['unidade'],
                oc_status="Solicitar ao Fornecedor",
                oc_solicitacao=next_solicitacao_id
            )
        
        msg = dbc.Alert(f'Solicitação N° {next_solicitacao_id} enviada com sucesso!', color='success')
        # Limpa o formulário após o sucesso
        return msg, False, [], None, None

    except Exception as e:
        return dbc.Alert(f'Erro ao salvar solicitação: {str(e)}', color='danger'), True, items, solicitante, setor

# Callback para o botão de cancelar (limpa tudo e fecha)
@app.callback(
    Output('modal_solicitacao', 'is_open', allow_duplicate=True),
    Output('solicitacao-items-store', 'data', allow_duplicate=True),
    Output('solicitacao_solicitante', 'value', allow_duplicate=True),
    Output('solicitacao_setor', 'value', allow_duplicate=True),
    Output('solicitacao_descricao', 'value', allow_duplicate=True),
    Output('solicitacao_quantidade', 'value', allow_duplicate=True),
    Output('solicitacao_unidade', 'value', allow_duplicate=True),
    Input('solicitacao_cancelar', 'n_clicks'),
    prevent_initial_call=True
)
def fechar_e_limpar_modal(n_clicks):
    if n_clicks:
        return False, [], None, None, None, None, None
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
