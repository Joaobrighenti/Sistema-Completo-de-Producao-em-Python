from dash import html, dcc, dash, callback_context
# Import PreventUpdate from dash.exceptions
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
from app import app
# Ensure Banco and helper functions are accessible
# Adjust the import path if banco.py is not in the root directory
# e.g., from ..banco import Banco, listar_dados, listar_pcp
from banco_dados.banco import Banco, listar_dados, listar_pcp
from datetime import datetime
import pandas as pd

layout = html.Div([
    dcc.Store(id='store-planejamento', data={'timestamp': datetime.now().isoformat()}), # Store to trigger updates
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Gerenciar Planejamento de Produção")),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Selecionar Planejamento (para Editar/Excluir):"),
                    dcc.Dropdown(
                        id='dropdown-editar-planejamento',
                        placeholder='Selecione para editar ou excluir...',
                        clearable=True
                    )
                ], width=12)
            ], className="mb-3"),
            html.Hr(),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ordem de Produção (PCP):", html_for="dropdown-id-pcp"),
                    dcc.Dropdown(
                        id='dropdown-id-pcp',
                        placeholder='Selecione o PCP...',
                        options=[], # Populated by callback
                        clearable=False
                    )
                ], md=6),
                 dbc.Col([
                    dbc.Label("Data Programada:", html_for="input-data-programacao"),
                    dbc.Input(id='input-data-programacao', type='date', required=True)
                ], md=6),
            ], className="mb-3"),
             dbc.Row([
                 dbc.Col([
                    dbc.Label("Quantidade:", html_for="input-quantidade"),
                    dbc.Input(id='input-quantidade', type='number', min=0, required=True)
                ], md=6),
                dbc.Col([
                    dbc.Label("Etiqueta:", html_for="input-etiqueta"),
                    dbc.Input(id='input-etiqueta', type='text', placeholder='Ex: MAQ-01, TURNO-A')
                ], md=6),
            ], className="mb-3"),
             dbc.Row([
                 dbc.Col([
                    dbc.Label("Observação:", html_for="input-observacao"),
                    dbc.Textarea(id='input-observacao', placeholder='Detalhes adicionais...')
                ], width=12),
            ], className="mb-3"),

            # Hidden input to store the ID of the item being edited
            dcc.Input(id='input-planejamento-id', type='hidden'),

            # Feedback area
            html.Div(id='feedback-planejamento', className="mt-3")
        ]),
        dbc.ModalFooter([
            dbc.Button("Excluir", id="btn-excluir-planejamento", color="danger", className="me-auto", style={'display': 'none'}), # Hidden by default
            dbc.Button("Fechar", id="btn-fechar-planejamento", color="secondary"),
            dbc.Button("Salvar", id="btn-salvar-planejamento", color="primary"),
        ])
    ], id='modal-planejamento', size='lg', is_open=False, backdrop='static') # Static backdrop prevents closing on click outside
])

# --- Callbacks --- #

# Toggle Modal
@app.callback(
    Output('modal-planejamento', 'is_open'),
    [Input('btn-planejamento', 'n_clicks'), # Button from pag_principal.py
     Input('btn-fechar-planejamento', 'n_clicks'),
     Input('btn-salvar-planejamento', 'n_clicks'), # Listen to save button clicks
     Input('feedback-planejamento', 'children') # Check feedback for success message
     ],
    State('modal-planejamento', 'is_open'),
    prevent_initial_call=True,
)
def toggle_planejamento_modal(n_open, n_close, n_save, feedback, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    trigger_prop = ctx.triggered[0]['prop_id'].split('.')[1]

    # Open modal
    if trigger_id == 'btn-planejamento':
        return True

    # Close modal via "Fechar" button
    if trigger_id == 'btn-fechar-planejamento':
        return False

    # Close modal after successful save
    if trigger_id == 'btn-salvar-planejamento' and feedback:
        # Check if feedback is a dbc.Alert and has color=success
        is_success = False
        if isinstance(feedback, dict) and feedback.get('type') == 'Alert':
            is_success = feedback.get('props', {}).get('color') == 'success'
        elif hasattr(feedback, 'color') and getattr(feedback, 'color') == 'success': # If it's already a component object
             is_success = True

        if is_success:
            return False # Close only on success

    return is_open # Keep modal open otherwise, e.g., during save errors or non-success feedback

# Populate Dropdowns when Modal Opens or Store Updates
@app.callback(
    [Output('dropdown-id-pcp', 'options'),
     Output('dropdown-editar-planejamento', 'options')],
    [Input('modal-planejamento', 'is_open'),
     Input('store-planejamento', 'data')], # Triggered by modal opening or store update
)
def populate_dropdowns(is_open, store_data):
    if not is_open:
        raise PreventUpdate # Don't update if modal is closed

    pcp_options = []
    plan_options = []

    try:
        # Populate PCP Dropdown
        # Fetch PCP data including product name - ensure listar_pcp provides necessary columns
        df_pcp = listar_pcp()
        if df_pcp is not None and not df_pcp.empty:
            # Check if required columns exist
            required_cols = ['pcp_id', 'pcp_pcp', 'produto_nome']
            if all(col in df_pcp.columns for col in required_cols):
                 pcp_options = [{'label': f"{row['pcp_pcp']} - {row['produto_nome']}", 'value': row['pcp_id']}
                               for index, row in df_pcp.sort_values(by='pcp_pcp').iterrows()]
            else:
                print("Warning: Missing required columns in df_pcp for planning dropdown.")

        # Populate Edit Dropdown
        banco = Banco()
        df_plan = banco.ler_tabela('planejamento')
        if not df_plan.empty:
            df_plan['data_programacao_dt'] = pd.to_datetime(df_plan['data_programacao'], errors='coerce')
            df_plan = df_plan.dropna(subset=['data_programacao_dt']) # Drop rows where date conversion failed
            df_plan['data_programacao_str'] = df_plan['data_programacao_dt'].dt.strftime('%d/%m/%y')

            # Fetch associated PCP numbers for better labels
            pcp_ids_plan = df_plan['id_pcp'].unique().tolist()
            if pcp_ids_plan and df_pcp is not None and not df_pcp.empty and 'pcp_id' in df_pcp.columns and 'pcp_pcp' in df_pcp.columns:
                 pcp_map = df_pcp[df_pcp['pcp_id'].isin(pcp_ids_plan)].set_index('pcp_id')['pcp_pcp'].to_dict()
                 df_plan['pcp_pcp_label'] = df_plan['id_pcp'].map(pcp_map).fillna('N/A')
            else:
                df_plan['pcp_pcp_label'] = 'N/A'

            plan_options = [{'label': f"ID:{row['plan_id']} | PCP:{row['pcp_pcp_label']} | Qtd:{row['quantidade']} | Data:{row['data_programacao_str']}", 'value': row['plan_id']}
                            for index, row in df_plan.sort_values(by='data_programacao_dt', ascending=False).iterrows()]

    except Exception as e:
        print(f"Erro ao popular dropdowns de planejamento: {e}")
        # Return empty lists or raise PreventUpdate if necessary

    return pcp_options, plan_options


@app.callback(
    [
        Output('modal-planejamento', 'is_open', allow_duplicate=True),
        Output('dropdown-id-pcp', 'value', allow_duplicate=True),
        Output('input-quantidade', 'value', allow_duplicate=True),
        Output('input-data-programacao', 'value', allow_duplicate=True),
        Output('input-observacao', 'value', allow_duplicate=True),
        Output('input-etiqueta', 'value', allow_duplicate=True),
        Output('input-planejamento-id', 'value', allow_duplicate=True),
        Output('btn-excluir-planejamento', 'style', allow_duplicate=True),
        Output('feedback-planejamento', 'children', allow_duplicate=True),
        Output('dropdown-editar-planejamento', 'value', allow_duplicate=True),
        Output('dropdown-id-pcp', 'options', allow_duplicate=True),
        Output('dropdown-editar-planejamento', 'options', allow_duplicate=True)
    ],
    [
        Input('store-programacao-pcp-data', 'data'),
        Input('dropdown-editar-planejamento', 'value')
    ],
    [State('modal-planejamento', 'is_open')],
    prevent_initial_call=True
)
def gerenciar_form_planejamento(dados_programacao, id_planejamento_edicao, modal_aberto):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Gatilho 1: Dados do formulário PCP para programar
    if triggered_id == 'store-programacao-pcp-data':
        if not dados_programacao:
            raise PreventUpdate
        
        pcp_id = dados_programacao.get('pcp_id')
        pcp_qtd = dados_programacao.get('pcp_qtd')

        if pcp_id is None or pcp_qtd is None:
            raise PreventUpdate
        
        # --- Lógica para buscar opções ---
        pcp_options = []
        plan_options = []
        try:
            df_pcp = listar_pcp()
            if df_pcp is not None and not df_pcp.empty:
                required_cols = ['pcp_id', 'pcp_pcp', 'produto_nome']
                if all(col in df_pcp.columns for col in required_cols):
                    pcp_options = [{'label': f"{row['pcp_pcp']} - {row['produto_nome']}", 'value': row['pcp_id']}
                                   for index, row in df_pcp.sort_values(by='pcp_pcp').iterrows()]

            banco = Banco()
            df_plan = banco.ler_tabela('planejamento')
            if not df_plan.empty:
                df_plan['data_programacao_dt'] = pd.to_datetime(df_plan['data_programacao'], errors='coerce')
                df_plan = df_plan.dropna(subset=['data_programacao_dt'])
                df_plan['data_programacao_str'] = df_plan['data_programacao_dt'].dt.strftime('%d/%m/%y')
                
                pcp_ids_plan = df_plan['id_pcp'].unique().tolist()
                if pcp_ids_plan and df_pcp is not None and not df_pcp.empty and 'pcp_id' in df_pcp.columns and 'pcp_pcp' in df_pcp.columns:
                    pcp_map = df_pcp[df_pcp['pcp_id'].isin(pcp_ids_plan)].set_index('pcp_id')['pcp_pcp'].to_dict()
                    df_plan['pcp_pcp_label'] = df_plan['id_pcp'].map(pcp_map).fillna('N/A')
                else:
                    df_plan['pcp_pcp_label'] = 'N/A'
                
                plan_options = [{'label': f"ID:{row['plan_id']} | PCP:{row['pcp_pcp_label']} | Qtd:{row['quantidade']} | Data:{row['data_programacao_str']}", 'value': row['plan_id']}
                                for index, row in df_plan.sort_values(by='data_programacao_dt', ascending=False).iterrows()]
        except Exception as e:
            print(f"Erro ao popular dropdowns em gerenciar_form_planejamento: {e}")
        # --- Fim da lógica ---

        return (
            True, pcp_id, pcp_qtd, None, None, None, None, 
            {'display': 'none'}, "", None,
            pcp_options, plan_options
        )

    # Gatilho 2: Seleção no dropdown de edição
    if triggered_id == 'dropdown-editar-planejamento':
        if not id_planejamento_edicao:
            return (
                dash.no_update, None, None, None, None, None, None, 
                {'display': 'none'}, "", dash.no_update, dash.no_update, dash.no_update
            )
        
        try:
            banco = Banco()
            df_plan = banco.ler_tabela('planejamento')
            plan_data = df_plan[df_plan['plan_id'] == id_planejamento_edicao]

            if plan_data.empty:
                feedback = dbc.Alert("Item não encontrado.", color="warning")
                return (
                    dash.no_update, None, None, None, None, id_planejamento_edicao, 
                    {'display': 'inline-block'}, feedback, dash.no_update, dash.no_update, dash.no_update
                )

            plan_data = plan_data.iloc[0]
            data_programacao_dt = pd.to_datetime(plan_data['data_programacao'], errors='coerce')
            data_str = "" if pd.isna(data_programacao_dt) else data_programacao_dt.strftime('%Y-%m-%d')
            
            return (
                dash.no_update, plan_data['id_pcp'], plan_data['quantidade'], data_str,
                plan_data['observacao'], plan_data['etiqueta'], id_planejamento_edicao, 
                {'display': 'inline-block'}, "", dash.no_update, dash.no_update, dash.no_update
            )
        except Exception as e:
            feedback = dbc.Alert(f"Erro ao carregar dados: {e}", color="danger")
            return (
                dash.no_update, None, None, None, None, None, 
                {'display': 'none'}, feedback, dash.no_update, dash.no_update, dash.no_update
            )

    raise PreventUpdate


# Save or Update Planejamento
@app.callback(
    [Output('feedback-planejamento', 'children', allow_duplicate=True),
     Output('store-planejamento', 'data', allow_duplicate=True)],
    Input('btn-salvar-planejamento', 'n_clicks'),
    [State('dropdown-id-pcp', 'value'),
     State('input-quantidade', 'value'),
     State('input-data-programacao', 'value'),
     State('input-observacao', 'value'),
     State('input-etiqueta', 'value'),
     State('input-planejamento-id', 'value')], # Get the ID for update
    prevent_initial_call=True
)
def salvar_planejamento(n_clicks, id_pcp, quantidade, data_programacao, observacao, etiqueta, plan_id):
    if not n_clicks:
        raise PreventUpdate

    if not id_pcp or quantidade is None or not data_programacao: # Check for None quantity
        return dbc.Alert("PCP, Quantidade e Data Programada são obrigatórios.", color="warning", duration=4000), dash.no_update

    try:
        # Validate quantity
        try:
            quantidade_int = int(quantidade)
            if quantidade_int < 0:
                 return dbc.Alert("Quantidade não pode ser negativa.", color="warning", duration=4000), dash.no_update
        except (ValueError, TypeError):
            return dbc.Alert("Quantidade inválida.", color="warning", duration=4000), dash.no_update

        # Validate date
        try:
            data_programacao_date = datetime.strptime(data_programacao, '%Y-%m-%d').date()
        except ValueError:
             return dbc.Alert("Formato de Data Programada inválido (use AAAA-MM-DD).", color="warning", duration=4000), dash.no_update


        # Prepare data
        data_dict = {
            'id_pcp': id_pcp,
            'quantidade': quantidade_int,
            'data_programacao': data_programacao_date,
            'observacao': observacao,
            'etiqueta': etiqueta
        }

        banco = Banco()
        alert_msg = ""
        alert_color = "success"
        store_update = dash.no_update

        if plan_id: # If ID exists, it's an update
            print(f"Tentando editar plan_id: {plan_id} com dados: {data_dict}")
            success = banco.editar_dado('planejamento', plan_id, **data_dict)
            if success:
                alert_msg = f"Planejamento ID {plan_id} atualizado com sucesso!"
                store_update = {'timestamp': datetime.now().isoformat()} # Trigger refresh
            else:
                 alert_msg = f"Erro ao atualizar planejamento ID {plan_id}."
                 alert_color="danger"
        else: # No ID, it's an insertion
            print(f"Tentando inserir dados: {data_dict}")
            banco.inserir_dados('planejamento', **data_dict)
            alert_msg = "Novo planejamento inserido com sucesso!"
            store_update = {'timestamp': datetime.now().isoformat()} # Trigger refresh
            # Optionally clear form fields after successful insert? (Handled by dropdown selection logic now)

        return dbc.Alert(alert_msg, color=alert_color, duration=4000), store_update

    except ValueError as ve:
         print(f"Erro de valor ao salvar planejamento: {ve}")
         return dbc.Alert(f"Erro de valor: {ve}", color="danger", duration=4000), dash.no_update
    except Exception as e:
        print(f"Erro geral ao salvar planejamento: {e}")
        return dbc.Alert(f"Erro interno ao salvar: {e}", color="danger", duration=4000), dash.no_update


# Delete Planejamento
@app.callback(
    [Output('feedback-planejamento', 'children', allow_duplicate=True),
     Output('store-planejamento', 'data', allow_duplicate=True),
     # Outputs to reset form after delete
     Output('dropdown-id-pcp', 'value', allow_duplicate=True),
     Output('input-quantidade', 'value', allow_duplicate=True),
     Output('input-data-programacao', 'value', allow_duplicate=True),
     Output('input-observacao', 'value', allow_duplicate=True),
     Output('input-etiqueta', 'value', allow_duplicate=True),
     Output('input-planejamento-id', 'value', allow_duplicate=True),
     Output('dropdown-editar-planejamento', 'value', allow_duplicate=True), # Clear edit dropdown
     Output('btn-excluir-planejamento', 'style', allow_duplicate=True)], # Hide delete button
    Input('btn-excluir-planejamento', 'n_clicks'),
    State('input-planejamento-id', 'value'),
    prevent_initial_call=True
)
def excluir_planejamento(n_clicks, plan_id):
    if not n_clicks or not plan_id:
         raise PreventUpdate

    print(f"Tentando excluir plan_id: {plan_id}")

    try:
        banco = Banco()
        success = banco.deletar_dado('planejamento', plan_id)
        alert_msg = ""
        alert_color = "success"
        store_update = dash.no_update
        # Values to reset the form fields
        reset_values = (None, None, None, None, None, None, None, {'display': 'none'})


        if success:
            alert_msg = f"Planejamento ID {plan_id} excluído com sucesso!"
            store_update = {'timestamp': datetime.now().isoformat()} # Trigger refresh
            return dbc.Alert(alert_msg, color=alert_color, duration=4000), store_update, *reset_values
        else:
            alert_msg = f"Erro ao excluir planejamento ID {plan_id}. Verifique se o ID existe."
            alert_color="danger"
            # Don't reset form on error
            return dbc.Alert(alert_msg, color=alert_color, duration=4000), store_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    except Exception as e:
        print(f"Erro ao excluir planejamento: {e}")
        # Don't reset form on error
        return dbc.Alert(f"Erro interno ao excluir: {e}", color="danger", duration=4000), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
