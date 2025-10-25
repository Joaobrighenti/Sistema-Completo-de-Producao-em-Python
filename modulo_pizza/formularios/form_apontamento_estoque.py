from dash import html, dcc, dash_table, no_update, callback_context
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
from app import app
from banco_dados.banco import engine, PCP, PRODUTO, BAIXA, RETIRADA, RETIRADA_EXP, Banco
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
from pcp.formularios.form_retirada import layout as layout_form_retirada
from datetime import date
import json

def get_data_retirada_impresso(produto_id):
    """Busca dados para a aba 'Retirada de Impresso'."""
    if not produto_id:
        return pd.DataFrame()

    with Session(engine) as session:
        # Pega todos os PCPs para o produto
        pcps = session.query(
            PCP.pcp_id,
            PCP.pcp_pcp,
            PCP.pcp_qtd,
            PRODUTO.nome.label('nome_produto')
        ).join(PRODUTO, PCP.pcp_produto_id == PRODUTO.produto_id)\
         .filter(PCP.pcp_produto_id == produto_id).all()

        if not pcps:
            return pd.DataFrame()

        df_pcps = pd.DataFrame(pcps, columns=['pcp_id', 'pcp_pcp', 'pcp_qtd', 'nome_produto'])
        pcp_ids = df_pcps['pcp_id'].tolist()

        # Pega as baixas agregadas
        baixas = session.query(BAIXA.pcp_id, func.sum(BAIXA.qtd).label("qtd_baixa")) \
                        .filter(BAIXA.pcp_id.in_(pcp_ids)) \
                        .group_by(BAIXA.pcp_id).all()
        df_baixas = pd.DataFrame(baixas, columns=['pcp_id', 'qtd_baixa']).set_index('pcp_id')

        # Pega as retiradas agregadas
        retiradas = session.query(RETIRADA.ret_id_pcp, func.sum(RETIRADA.ret_qtd).label("qtd_retirada")) \
                          .filter(RETIRADA.ret_id_pcp.in_(pcp_ids)) \
                          .group_by(RETIRADA.ret_id_pcp).all()
        df_retiradas = pd.DataFrame(retiradas, columns=['pcp_id', 'qtd_retirada']).set_index('pcp_id')

        # Juntando os dados e calculando
        df_final = df_pcps.set_index('pcp_id')
        df_final = df_final.join(df_baixas).join(df_retiradas)
        
        # Preenche NaNs com 0 e converte para inteiros de forma segura
        df_final['qtd_baixa'] = df_final['qtd_baixa'].fillna(0).astype(int)
        df_final['qtd_retirada'] = df_final['qtd_retirada'].fillna(0).astype(int)
        
        df_final['processo'] = (df_final['pcp_qtd'] - df_final['qtd_baixa']).clip(lower=0)
        df_final['estoque'] = (df_final['qtd_baixa'] - df_final['qtd_retirada']).clip(lower=0)
        df_final.rename(columns={'pcp_qtd': 'qtd_op', 'qtd_retirada': 'retirada'}, inplace=True)

        return df_final.reset_index()[['pcp_id', 'pcp_pcp', 'nome_produto', 'qtd_op', 'processo', 'estoque', 'retirada']]

def get_retirada_exp_data(produto_id):
    """Busca o histórico de retiradas de expedição para um produto."""
    if not produto_id:
        return pd.DataFrame()
    banco = Banco()
    try:
        df = banco.ler_tabela('retirada_exp')
        df_produto = df[df['ret_exp_produto_id'] == produto_id]
        return df_produto.sort_values(by='ret_exp_data', ascending=False)
    except Exception:
        return pd.DataFrame()

def get_data_retirada_expedicao(produto_id):
    """Busca dados para a aba 'Retirada Expedição'."""
    if not produto_id:
        return None, None, None

    with Session(engine) as session:
        produto = session.query(PRODUTO.nome).filter(PRODUTO.produto_id == produto_id).scalar()

        total_baixas = session.query(func.sum(BAIXA.qtd))\
            .join(PCP, BAIXA.pcp_id == PCP.pcp_id)\
            .filter(PCP.pcp_produto_id == produto_id).scalar() or 0

        total_retiradas = session.query(func.sum(RETIRADA.ret_qtd))\
            .join(PCP, RETIRADA.ret_id_pcp == PCP.pcp_id)\
            .filter(PCP.pcp_produto_id == produto_id).scalar() or 0
        
        impresso = total_baixas - total_retiradas
        
        return produto_id, produto, impresso

def modal_apontamento_estoque():
    """Retorna o layout do modal de apontamento."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Apontamento de Estoque")),
            dbc.ModalBody([
                dcc.Store(id='store-selected-product-id'),
                dcc.Store(id='store-retirada-exp-trigger', data=0),
                dbc.Tabs(
                    [
                        dbc.Tab(label="Retirada de Impresso", tab_id="tab-impresso", children=[
                            html.Div(id="tab-content-impresso"),
                            layout_form_retirada,
                        ]),
                        dbc.Tab(label="Retirada Expedição", tab_id="tab-expedicao", children=[
                            html.Div(id="content-retirada-exp-form"),
                            html.Div(id="content-retirada-exp-feedback"),
                            html.Div(id="content-retirada-exp-history"),
                        ]),
                    ],
                    id="tabs-apontamento-estoque",
                    active_tab="tab-impresso",
                ),
            ]),
        ],
        id="modal-apontamento-estoque",
        size="xl",
        is_open=False,
    )

@app.callback(
    Output("tab-content-impresso", "children"),
    Input("tabs-apontamento-estoque", "active_tab"),
    Input('store-selected-product-id', 'data')
)
def render_tab_impresso(active_tab, produto_id):
    if active_tab != "tab-impresso" or not produto_id:
        return html.Div()

    df = get_data_retirada_impresso(produto_id)
    return dash_table.DataTable(
        id='table-retirada-impresso',
        columns=[{"name": i, "id": i} for i in df.columns if i != 'pcp_id'],
        data=df.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
        cell_selectable=True,
    )

@app.callback(
    Output("modal_retirada_producao", "is_open", allow_duplicate=True),
    Output("retirada_pcp", "value", allow_duplicate=True),
    Input("table-retirada-impresso", "active_cell"),
    State("table-retirada-impresso", "data"),
    prevent_initial_call=True
)
def open_retirada_modal(active_cell, data):
    if not active_cell:
        return no_update, no_update

    row_idx = active_cell['row']
    pcp_id = data[row_idx]['pcp_id']
    
    return True, pcp_id

@app.callback(
    Output('content-retirada-exp-form', 'children'),
    Input("tabs-apontamento-estoque", "active_tab"),
    Input('store-selected-product-id', 'data'),
)
def render_expedicao_form(active_tab, produto_id):
    if active_tab != "tab-expedicao" or not produto_id:
        return html.Div()

    prod_id, prod_nome, impresso_sum = get_data_retirada_expedicao(produto_id)

    return html.Div([
        dbc.Row([
            dbc.Col(html.Strong("ID do Produto:"), width=3),
            dbc.Col(prod_id, width=9)
        ]),
        dbc.Row([
            dbc.Col(html.Strong("Nome do Produto:"), width=3),
            dbc.Col(prod_nome, width=9)
        ]),
        dbc.Row([
            dbc.Col(html.Strong("Soma de Impresso (Estoque):"), width=3),
            dbc.Col(f"{impresso_sum:,.0f}", width=9)
        ]),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                dbc.Label("Quantidade"),
                dbc.Input(id="ret-exp-qtd", type="number", placeholder="Informe a quantidade...")
            ], width=6),
            dbc.Col([
                dbc.Label("Ajuste de Saldo"),
                dbc.Checklist(
                    options=[{"label": "Ajuste de Estoque", "value": "ajuste"}],
                    value=[],
                    id="ret-exp-ajuste",
                    inline=True,
                )
            ], width=6, className="align-self-center"),
        ]),
        dbc.Button("Registrar Retirada", id="btn-registrar-retirada-exp", color="primary", className="mt-3"),
    ], className="mt-3")

@app.callback(
    Output('content-retirada-exp-history', 'children'),
    [Input('store-retirada-exp-trigger', 'data'),
     Input("tabs-apontamento-estoque", "active_tab"),
     Input('store-selected-product-id', 'data')],
    prevent_initial_call=True
)
def render_expedicao_history(trigger, active_tab, produto_id):
    if active_tab != "tab-expedicao" or not produto_id:
        return html.Div()

    df_history = get_retirada_exp_data(produto_id)
    if not df_history.empty:
        history_table_header = [
            html.Thead(html.Tr([html.Th("Data"), html.Th("Qtd"), html.Th("Usuário"), html.Th("Ajuste"), html.Th("Ação")]))
        ]
        history_table_body = [
            html.Tbody([
                html.Tr([
                    html.Td(row['ret_exp_data']),
                    html.Td(row['ret_exp_qtd']),
                    html.Td(row['ret_exp_usuario']),
                    html.Td(row['ret_exp_ajuste']),
                    html.Td(dbc.Button("Excluir", id={'type': 'delete-ret-exp', 'index': row['ret_exp_id']}, color="danger", size="sm"))
                ]) for index, row in df_history.iterrows()
            ])
        ]
        return html.Div([
            html.Hr(),
            html.H5("Histórico de Lançamentos"),
            dbc.Table(history_table_header + history_table_body, bordered=True, striped=True, hover=True, responsive=True, className="mt-3")
        ])
    return html.P("Nenhum lançamento encontrado.", className="mt-3")

@app.callback(
    Output('content-retirada-exp-feedback', 'children'),
    Output('store-retirada-exp-trigger', 'data'),
    Input("btn-registrar-retirada-exp", "n_clicks"),
    Input({'type': 'delete-ret-exp', 'index': ALL}, 'n_clicks'),
    State("ret-exp-qtd", "value"),
    State("ret-exp-ajuste", "value"),
    State("store-selected-product-id", "data"),
    State('store-login-state', 'data'),
    State('store-retirada-exp-trigger', 'data'),
    prevent_initial_call=True
)
def handle_expedicao_actions(n_add, n_delete, qtd, ajuste, produto_id, login_state, trigger):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update
        
    triggered_id = ctx.triggered_id
    banco = Banco()
    
    if triggered_id == 'btn-registrar-retirada-exp':
        if not qtd or qtd <= 0:
            return dbc.Alert("A quantidade deve ser um número positivo.", color="danger"), no_update
        
        username = login_state.get('username') if login_state and login_state.get('username') else "N/A"
        try:
            banco.inserir_dados(
                'retirada_exp',
                ret_exp_produto_id=produto_id,
                ret_exp_qtd=qtd,
                ret_exp_data=date.today(),
                ret_exp_usuario=username,
                ret_exp_ajuste="Sim" if ajuste and "ajuste" in ajuste else "Não"
            )
            return dbc.Alert("Retirada registrada com sucesso!", color="success"), trigger + 1
        except Exception as e:
            return dbc.Alert(f"Erro ao registrar: {e}", color="danger"), no_update

    if isinstance(triggered_id, dict) and triggered_id.get('type') == 'delete-ret-exp':
        # Ensure a delete button was actually clicked
        if not any(n_delete):
            return no_update, no_update
        ret_exp_id_to_delete = triggered_id['index']
        try:
            banco.deletar_dado('retirada_exp', id=ret_exp_id_to_delete)
            return dbc.Alert("Lançamento excluído com sucesso!", color="warning"), trigger + 1
        except Exception as e:
            return dbc.Alert(f"Erro ao excluir: {e}", color="danger"), no_update

    return no_update, no_update
