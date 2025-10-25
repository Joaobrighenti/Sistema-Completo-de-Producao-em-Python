from dash import html, dcc, callback_context, exceptions
import dash_bootstrap_components as dbc
from app import app
from dash.dependencies import Input, Output, State, ALL
from banco_dados.banco import Banco
from banco_dados.banco import engine
from datetime import datetime
import dash
import pandas as pd
from sqlalchemy import text
import json

layout = dbc.Modal([
    dbc.ModalHeader("Apontamento de Retrabalho"),
    dbc.ModalBody(
        dbc.Row([
            dbc.Col([
                dcc.Store(id='store_pcp_id_retrabalho'),
                dcc.Store(id='store_local_retrabalho_update'),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("PCP ID:"),
                        dbc.Input(id='pcp_id_retrabalho_input', disabled=True),
                    ], width=2),
                    dbc.Col([
                        dbc.Label("LoT:"),
                        dbc.Input(id='pcp_pcp_retrabalho_input', disabled=True),
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Qtd OP:"),
                        dbc.Input(id='pcp_qtd_retrabalho_input', disabled=True),
                    ], width=2),
                    dbc.Col([
                        dbc.Label("Produto:"),
                        dbc.Input(id='produto_nome_retrabalho_input', disabled=True),
                    ], width=6),
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Quantidade Inspecionada:"),
                        dbc.Input(id='qtd_inspecionada_input', type='number'),
                    ]),
                    dbc.Col([
                        dbc.Label("Qtd Não Conforme", id="label-nao-conforme"),
                        dbc.Input(id='qtd_nao_conforme_input', type='number'),
                    ]),
                ], className="mt-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Observação:"),
                        dbc.Textarea(id='obs_retrabalho_input', style={'height': '100px'}),
                    ]),
                ], className="mt-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Decisão Final:"),
                        dbc.RadioItems(
                            id='radio_retrabalho_status',
                            options=[
                                {'label': 'Retrabalho', 'value': 1},
                                {'label': 'Aprovado', 'value': 2},
                                {'label': 'Reprovado', 'value': 3},
                                {'label': 'Aprovado Sob Concessão', 'value': 4},
                            ],
                            inline=True
                        ),
                    ])
                ], className="mt-3"),
                html.Div(id='feedback_retrabalho', className='mt-3'),
                html.Hr(),
                html.H5("Apontamentos Anteriores"),
                html.Div(id="container_tabela_retrabalho")
            ], md=7),
            dbc.Col([
                html.H5("Inspeções de Processo"),
                html.Div(id="container_inspecoes_processo")
            ], md=5, style={'maxHeight': '70vh', 'overflowY': 'auto'})
        ])
    ),
    dbc.ModalFooter([
        dbc.Button("Enviar", id="btn_enviar_retrabalho", color="primary"),
        dbc.Button("Cancelar", id="btn_cancelar_retrabalho", color="secondary")
    ]),
], id="modal_retrabalho", is_open=False, centered=True)


@app.callback(
    Output("modal_retrabalho", "is_open", allow_duplicate=True),
    Input("btn_cancelar_retrabalho", "n_clicks"),
    prevent_initial_call=True,
)
def close_modal_on_cancel(n_clicks):
    if n_clicks:
        return False
    return dash.no_update
 
@app.callback(
    Output("feedback_retrabalho", "children"),
    Output("modal_retrabalho", "is_open", allow_duplicate=True),
    Output('store-retrabalho-update-trigger', 'data'),
    Input("btn_enviar_retrabalho", "n_clicks"),
    [
        State("store_pcp_id_retrabalho", "data"),
        State("qtd_inspecionada_input", "value"),
        State("qtd_nao_conforme_input", "value"),
        State("obs_retrabalho_input", "value"),
        State("radio_retrabalho_status", "value"),
    ],
    prevent_initial_call=True
)
def submit_retrabalho(n_clicks, pcp_id, qtd_verificada, qtd_nao_conforme, obs, status_final):
    if not n_clicks:
        return "", dash.no_update, dash.no_update

    if not status_final:
        return dbc.Alert("O campo 'Decisão Final' é obrigatório.", color="danger"), True, dash.no_update

    banco = Banco()
    
    if status_final == 1 and (not qtd_verificada or not qtd_nao_conforme):
        return dbc.Alert("Para 'Retrabalho', preencha 'Quantidade Inspecionada' e 'Quantidade Não Conforme'.", color="danger"), True, dash.no_update

    apontamento_data = {
        'pcp_id': pcp_id,
        'quantidade_verificada': qtd_verificada,
        'quantidade_nao_conforme': qtd_nao_conforme,
        'observacao': obs,
        'data_hora': datetime.now(),
        'status': status_final
    }
    banco.inserir_dados('apontamento_retrabalho', **apontamento_data)

    pcp_update_data = {
        'pcp_retrabalho': status_final
    }
    banco.editar_dado('pcp', id=pcp_id, **pcp_update_data)

    return dbc.Alert("Operação realizada com sucesso!", color="success"), False, datetime.now().timestamp()
 
@app.callback(
    Output("container_tabela_retrabalho", "children"),
    [Input("store_pcp_id_retrabalho", "data"),
     Input("store_local_retrabalho_update", "data")]
)
def update_retrabalho_table(pcp_id, _):
    if not pcp_id:
        return html.P("Nenhum PCP selecionado.")
 
    banco = Banco()
    df_filtrado = banco.ler_tabela('apontamento_retrabalho', pcp_id=pcp_id)
 
    if df_filtrado.empty:
        return html.P("Nenhum apontamento de retrabalho para este PCP.")

    status_map = {
        1: 'Retrabalho',
        2: 'Aprovado',
        3: 'Reprovado',
        4: 'Aprovado Sob Concessão'
    }
    df_filtrado['status_texto'] = df_filtrado['status'].map(status_map).fillna('Não definido')
    
    if 'data_hora' in df_filtrado.columns and not df_filtrado['data_hora'].isnull().all():
        df_filtrado['data_hora'] = pd.to_datetime(df_filtrado['data_hora']).dt.strftime('%d/%m/%Y %H:%M')
    else:
        df_filtrado['data_hora'] = 'N/A'


    tabela = dbc.Table([
        html.Thead(html.Tr([
            html.Th("Data/Hora"),
            html.Th("Status"),
            html.Th("Qtd Verificada"),
            html.Th("Qtd Não Conforme"),
            html.Th("Observação"),
            html.Th("Ação"),
        ])),
        html.Tbody([
            html.Tr([
                html.Td(row['data_hora']),
                html.Td(row['status_texto']),
                html.Td(row['quantidade_verificada']),
                html.Td(row['quantidade_nao_conforme']),
                html.Td(row['observacao']),
                html.Td(dbc.Button("Excluir", id={'type': 'delete-retrabalho', 'index': row['id']}, color="danger", size="sm")),
            ]) for i, row in df_filtrado.iterrows()
        ])
    ], bordered=True, striped=True, hover=True, responsive=True)
    return tabela
 
@app.callback(
    Output("container_inspecoes_processo", "children"),
    [Input("store_pcp_id_retrabalho", "data"),
     Input("store_local_retrabalho_update", "data")]
)
def update_inspecoes_processo(pcp_id, _):
    if not pcp_id:
        return html.P("Nenhuma inspeção para este PCP.")

    try:
        query = text("""
            SELECT ip.id, ip.data, ip.tipo_produto, ip.qtd_inspecionada, ip.observacao, ip.checklist
            FROM inspecao_processo ip
            WHERE ip.pcp_id = :pcp_id
            ORDER BY ip.id DESC
        """)
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"pcp_id": pcp_id})

        if df.empty:
            return html.P("Nenhuma inspeção registrada para este PCP.")

        def render_checklist_cell(val):
            try:
                data = val
                if isinstance(val, str):
                    data = json.loads(val)
                if not isinstance(data, dict):
                    return "-"
                items = []
                for k, v in data.items():
                    if isinstance(v, dict):
                        status = v.get("status", "-")
                        qtd = v.get("quantidade", "-")
                    else:
                        status = v
                        qtd = "-"
                    items.append(html.Li(f"{k}: {status} (Qtd: {qtd})"))
                return html.Ul(items)
            except Exception:
                return "-"

        rows = []
        for _, r in df.iterrows():
            data_fmt = pd.to_datetime(r['data']).strftime('%d/%m/%Y') if pd.notna(r['data']) else '-'
            rows.append(
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Strong("Data: "), data_fmt, html.Br(),
                            html.Strong("Produto: "), r.get('tipo_produto', '-'), html.Br(),
                            html.Strong("Qtd Inspecionada: "), r.get('qtd_inspecionada', '-'), html.Br(),
                            html.Strong("Observação: "), r.get('observacao', '-') or '-', html.Br(),
                            html.Strong("Checklist:"),
                            render_checklist_cell(r.get('checklist'))
                        ])
                    ])
                ], className="mb-2")
            )

        return html.Div(rows)
    except Exception as e:
        return html.P(f"Erro ao carregar inspeções: {e}")

@app.callback(
    Output('store_local_retrabalho_update', 'data'),
    Input({'type': 'delete-retrabalho', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True
)
def delete_retrabalho(n_clicks):
    triggered_id = callback_context.triggered_id
    if not triggered_id or not any(n_clicks):
        raise exceptions.PreventUpdate
 
    apontamento_id = int(triggered_id['index'])
    banco = Banco()
   
    apontamento = banco.ler_tabela('apontamento_retrabalho', id=apontamento_id)
    if not apontamento.empty:
        pcp_id = int(apontamento.iloc[0]['pcp_id'])
       
        banco.deletar_dado('apontamento_retrabalho', id=apontamento_id)
       
        banco.editar_dado('pcp', id=pcp_id, pcp_retrabalho=None)
 
    return datetime.now().timestamp()

@app.callback(
    Output("label-nao-conforme", "children"),
    Input("radio_retrabalho_status", "value")
)
def update_label_nao_conforme(status_value):
    if status_value == 1:
        return "Qtd. para Retrabalho:"
    elif status_value == 3:
        return "Qtd. Reprovada:"
    else:
        return "Qtd. Não Conforme:"
