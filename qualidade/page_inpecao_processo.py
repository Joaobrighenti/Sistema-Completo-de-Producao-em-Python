from dash import html, dcc, callback, Input, Output, State, no_update, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
from banco_dados.banco import engine, Banco
from qualidade.formularios import form_inspecao
import json
from app import app
 
banco = Banco()
 
# Função para carregar e preparar os dados da tabela de inspeção com SQL direto
def carregar_dados_inspecao(pcp_lote=None):
    try:
        query = """
        SELECT
            ip.id,
            ip.data,
            s.setor_nome,
            m.maquina_nome,
            p.pcp_pcp,
            ip.tipo_produto,
            ip.qtd_inspecionada,
            ip.observacao,
            ip.checklist
        FROM
            inspecao_processo ip
        LEFT JOIN setor s ON ip.setor_id = s.setor_id
        LEFT JOIN maquina m ON ip.maquina_id = m.maquina_id
        LEFT JOIN pcp p ON ip.pcp_id = p.pcp_id
        """
       
        params = {}
        if pcp_lote:
            # Use LIKE for a 'contains' search, and cast the numeric column to text
            query += " WHERE CAST(p.pcp_pcp AS TEXT) LIKE :pcp_lote"
            params['pcp_lote'] = f'%{pcp_lote}%'
 
        query += " ORDER BY ip.id DESC"
 
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params=params)
 
        # Renomear colunas para exibição
        df = df.rename(columns={
            "data": "Data",
            "setor_nome": "Setor",
            "maquina_nome": "Máquina",
            "pcp_pcp": "Lote (PCP)",
            "tipo_produto": "Produto",
            "qtd_inspecionada": "Qtd Inspec.",
            "observacao": "Observação"
        })
       
        # Formatar data
        if not df.empty and 'Data' in df.columns:
            df['Data'] = pd.to_datetime(df['Data']).dt.strftime('%d/%m/%Y')
       
        # Colunas a serem exibidas na tabela
        colunas_visiveis = ["Data", "Setor", "Máquina", "Lote (PCP)", "Produto", "Qtd Inspec.", "Observação"]
       
        return df, colunas_visiveis
    except Exception as e:
        print(f"Erro ao carregar dados de inspeção com SQL: {e}")
        return pd.DataFrame(), []
 
# Layout da página
layout = dbc.Container([
    dcc.Store(id="inspecao-store-success-signal"), # Sinaliza sucesso para recarregar a tabela
    dcc.Store(id='inspecao-store-selected-row-id'), # Armazena o ID da linha selecionada
   
    # Container para o alerta de sucesso
    html.Div(id="inspecao-alert-container"),
 
    # Adiciona o layout do modal chamando a função
    form_inspecao.get_layout(),
 
    # Modal para exibir o checklist
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Detalhes do Checklist")),
            dbc.ModalBody(id="checklist-details-body"),
            dbc.ModalFooter(
                dbc.Button("Fechar", id="close-checklist-modal-btn", className="ms-auto", n_clicks=0)
            ),
        ],
        id="modal-checklist-details",
        is_open=False,
    ),
   
    # Modal de confirmação para exclusão
    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Confirmar Exclusão")),
            dbc.ModalBody("Tem certeza de que deseja excluir este registro? Esta ação não pode ser desfeita."),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="cancel-delete-btn", color="secondary"),
                dbc.Button("Excluir", id="confirm-delete-btn", color="danger"),
            ]),
        ],
        id="modal-confirm-delete",
        is_open=False,
    ),
 
    html.Div([
        dbc.Row([
            dbc.Col(
                html.H1("Inspeção de Processos", style={'color': 'white', 'font-size': '22px', 'margin': 0}),
                width="auto"
            ),
            dbc.Col(
                dbc.Input(id="filtro-lote-pcp", placeholder="Filtrar Lote (PCP)...", type="text", size="sm", style={'width': '200px'}),
                width="auto"
            ),
            dbc.Col(
                [
                    dbc.Button([html.I(className="fa fa-plus me-2"), "Nova Inspeção"], id="abrir-modal-inspecao-btn", color="primary"),
                    dbc.Button([html.I(className="fa fa-list-alt me-2"), "Ver Checklist"], id="ver-checklist-btn", color="info", disabled=True, className="ms-2"),
                    dbc.Button([html.I(className="fa fa-trash me-2"), "Excluir"], id="excluir-inspecao-btn", color="danger", disabled=True, className="ms-2"),
                ],
                width="auto"
            )
        ],
        justify="between",
        align="center",
        )
    ],
    style={
        'position': 'sticky',
        'top': 0,
        'zIndex': 1020,
        'background-color': '#02083d',
        'padding': '10px 20px',
        'border-radius': '8px',
        'margin-bottom': '20px',
        'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'
    }),
 
    dbc.Row(
        dbc.Col(
            html.Div(id="tabela-inspecao-container"), # Container para a tabela
            width=12
        )
    )
], fluid=True, className="py-3")
 
# Callback para mostrar a mensagem de sucesso
@app.callback(
    Output("inspecao-alert-container", "children"),
    Input("inspecao-store-success-signal", "data"),
    prevent_initial_call=True
)
def show_success_alert(signal):
    if not signal:
        return no_update
       
    if signal.get('type') == 'save':
        message = "Inspeção salva com sucesso!"
        color = "success"
    elif signal.get('type') == 'delete':
        message = "Registro de inspeção excluído com sucesso!"
        color = "warning"
    else:
        return no_update
 
    return dbc.Alert(
        [
            html.I(className=f"fa fa-check-circle me-2"),
            message
        ],
        is_open=True,
        duration=4000,
        color=color,
        className="m-3"
    )
 
# Callback para abrir o modal do formulário
@app.callback(
    Output("modal-form-inspecao", "is_open", allow_duplicate=True),
    Input("abrir-modal-inspecao-btn", "n_clicks"),
    State("modal-form-inspecao", "is_open"),
    prevent_initial_call=True
)
def toggle_modal(n, is_open):
    if n:
        return not is_open
    return no_update
 
# Callback para carregar/atualizar a tabela de inspeções
@app.callback(
    Output("tabela-inspecao-container", "children"),
    Input("inspecao-store-success-signal", "data"),
    Input("filtro-lote-pcp", "value")
)
def atualizar_tabela_inspecao(signal, pcp_lote):
    df, colunas_visiveis = carregar_dados_inspecao(pcp_lote)
   
    if df.empty:
        return dbc.Alert("Nenhum registro de inspeção encontrado.", color="info", className="text-center")
 
    data = df.to_dict('records')
    tooltip_data = []
   
    TRUNCATE_LIMIT = 50
    for row in data:
        tooltip_row = {}
        if 'Observação' in row and row['Observação'] and len(row['Observação']) > TRUNCATE_LIMIT:
            tooltip_row['Observação'] = row['Observação']
            row['Observação'] = row['Observação'][:TRUNCATE_LIMIT] + '...'
        tooltip_data.append(tooltip_row)
 
    tabela = dash_table.DataTable(
        id='tabela-inspecao',
        columns=[{"name": i, "id": i} for i in colunas_visiveis],
        data=data,
        row_selectable='single',
        selected_rows=[],
        style_table={'overflowY': 'auto', 'border': '1px solid #ccc'},
        page_size=25,
        style_header={
            'backgroundColor': '#02083d',
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'center',
            'padding': '10px'
        },
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'fontSize': '14px',
            'border': '1px solid #ddd',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ],
        style_cell_conditional=[
            {
                'if': {'column_id': 'Observação'},
                'maxWidth': '200px',
                'textAlign': 'left'
            }
        ],
        tooltip_data=tooltip_data,
        tooltip_duration=None,
    )
   
    return tabela
 
# Habilitar/desabilitar botões com base na seleção da tabela
@app.callback(
    Output("ver-checklist-btn", "disabled"),
    Output("excluir-inspecao-btn", "disabled"),
    Output("inspecao-store-selected-row-id", "data"),
    Input("tabela-inspecao", "selected_rows"),
    State("tabela-inspecao", "data"),
)
def toggle_action_buttons(selected_rows, table_data):
    if selected_rows:
        selected_id = table_data[selected_rows[0]]['id']
        return False, False, selected_id
    return True, True, None
 
# Abrir/fechar modal de detalhes do checklist
@app.callback(
    Output("modal-checklist-details", "is_open"),
    Output("checklist-details-body", "children"),
    Input("ver-checklist-btn", "n_clicks"),
    Input("close-checklist-modal-btn", "n_clicks"),
    State("inspecao-store-selected-row-id", "data"),
    State("modal-checklist-details", "is_open"),
    prevent_initial_call=True
)
def toggle_checklist_modal(n_ver, n_close, row_id, is_open):
    if not n_ver and not n_close:
        return no_update, no_update
 
    if not row_id:
        return False, "Nenhuma linha selecionada."
 
    df, _ = carregar_dados_inspecao()
    checklist_data_json = df.loc[df['id'] == row_id, 'checklist'].iloc[0]
   
    try:
        checklist_data = json.loads(checklist_data_json) if isinstance(checklist_data_json, str) else checklist_data_json

        if isinstance(checklist_data, str):
            checklist_data = json.loads(checklist_data)

    except (json.JSONDecodeError, TypeError):
        return is_open, "Erro ao ler os dados do checklist."
 
    # Mapeamento de valores para texto e cor
    status_map = {
        "conforme": ("Conforme", "success"),
        "nao_conforme": ("Não Conforme", "danger"),
        "nao_aplica": ("Não se aplica", "secondary"),
    }
   
    # Nomes dos itens do checklist
    all_checklist_items = {}
    for items in form_inspecao.checklist_items_por_produto.values():
        all_checklist_items.update(items)
 
    details_header = dbc.Row([
        dbc.Col(html.B("Item do Checklist"), width=6),
        dbc.Col(html.B("Status"), width=3, className="text-center"),
        dbc.Col(html.B("Quantidade"), width=3, className="text-center"),
    ], className="mb-2 border-bottom pb-2")
 
    details_rows = []
    if not checklist_data:
        return not is_open, "Nenhum dado de checklist disponível."
 
    for key, value in checklist_data.items():
        item_name = all_checklist_items.get(key, key.replace('_', ' ').title())
       
        # Lida com o formato novo (dicionário) e o antigo (string)
        if isinstance(value, dict):
            status = value.get("status", "N/A")
            quantidade = value.get("quantidade", "-")
        else:
            status = value
            quantidade = "-" # Dado antigo não tem quantidade
 
        status_text, status_color = status_map.get(status, (status, "dark"))
       
        details_rows.append(
            dbc.Row([
                dbc.Col(item_name, width=6),
                dbc.Col(dbc.Badge(status_text, color=status_color, className="w-100"), width=3),
                dbc.Col(quantidade, width=3, className="text-center")
            ], className="mb-2 align-items-center")
        )
   
    final_layout = [details_header] + details_rows
       
    return not is_open, final_layout
 
# Abrir/fechar modal de confirmação de exclusão E REALIZAR EXCLUSÃO
@app.callback(
    Output("modal-confirm-delete", "is_open", allow_duplicate=True),
    Output("inspecao-store-success-signal", "data", allow_duplicate=True),
    Input("excluir-inspecao-btn", "n_clicks"),
    Input("cancel-delete-btn", "n_clicks"),
    Input("confirm-delete-btn", "n_clicks"),
    State("modal-confirm-delete", "is_open"),
    State("inspecao-store-selected-row-id", "data"),
    prevent_initial_call=True,
)
def handle_delete_modal_and_action(n_open, n_cancel, n_confirm, is_open, row_id):
    from dash import callback_context
    ctx = callback_context
 
    if not ctx.triggered:
        return no_update, no_update
 
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
 
    if trigger_id == 'confirm-delete-btn':
        if row_id:
            try:
                banco.deletar_dado("inspecao_processo", row_id)
                return False, {'type': 'delete'}
            except Exception as e:
                print(f"Erro ao excluir registro: {e}")
                return True, no_update # Mantém o modal aberto em caso de erro
        return False, no_update # Fecha o modal se não houver ID
 
    elif trigger_id in ['excluir-inspecao-btn', 'cancel-delete-btn']:
        return not is_open, no_update
 
    return no_update, no_update
 