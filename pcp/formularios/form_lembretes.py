from dash import html, dcc, dash_table, no_update, callback_context
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
import pandas as pd
from datetime import datetime, date
from banco_dados.banco import Banco
from app import app

# Modal form for lembretes
layout = html.Div([
    dbc.Modal([
        dbc.ModalHeader([
            html.H3("Gerenciar Lembretes"),
        ]),
        dbc.ModalBody([
            # Form fields
            dbc.Row([
                # Hidden input for ID (used for updates)
                dbc.Input(id="lembrete-id", type="hidden"),
                
                # Lembrete text input
                dbc.Label("Lembrete:", className="mt-2"),
                dbc.Textarea(
                    id="input-lembrete",
                    placeholder="Digite o lembrete...",
                    style={"height": "100px"},
                ),
                
                # Date picker
                dbc.Label("Data:", className="mt-2"),
                dcc.DatePickerSingle(
                    id="input-data-lembrete",
                    display_format="DD/MM/YYYY",
                    date=date.today(),
                    className="w-100"
                ),
                
                # Status selection
                dbc.Label("Status:", className="mt-2"),
                dcc.Dropdown(
                    id="input-status-lembrete",
                    options=[
                        {"label": "Pendente", "value": "pendente"},
                        {"label": "Feito", "value": "feito"},
                        {"label": "Cancelado", "value": "cancelado"}
                    ],
                    value="pendente",
                    className="w-100 mb-3"
                ),
            ]),
            
            # Action buttons
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        "Salvar",
                        id="btn-save-lembrete",
                        color="success",
                        className="w-100"
                    )
                ], width=4),
                dbc.Col([
                    dbc.Button(
                        "Excluir",
                        id="btn-delete-lembrete",
                        color="danger",
                        className="w-100",
                        disabled=True
                    )
                ], width=4),
                dbc.Col([
                    dbc.Button(
                        "Cancelar",
                        id="btn-cancel-lembrete",
                        color="secondary",
                        className="w-100"
                    )
                ], width=4)
            ], className="mt-3"),
            
            # Status message
            html.Div(id="lembrete-status-message", className="mt-3"),
            
            # Table of lembretes
            html.Hr(),
            html.H5("Lembretes Cadastrados", className="mt-4"),
            dash_table.DataTable(
                id="table-lembretes",
                columns=[
                    {"name": "ID", "id": "id"},
                    {"name": "Lembrete", "id": "lembrete"},
                    {"name": "Data", "id": "data"},
                    {"name": "Status", "id": "status"}
                ],
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "left", "padding": "8px"},
                style_header={
                    "backgroundColor": "#f8f9fa",
                    "fontWeight": "bold",
                    "border": "1px solid #ddd"
                },
                style_data_conditional=[
                    {
                        "if": {"filter_query": "{status} = 'pendente'"},
                        "backgroundColor": "#fff3cd",
                        "color": "#856404"
                    },
                    {
                        "if": {"filter_query": "{status} = 'feito'"},
                        "backgroundColor": "#d4edda",
                        "color": "#155724"
                    },
                    {
                        "if": {"filter_query": "{status} = 'cancelado'"},
                        "backgroundColor": "#f8d7da",
                        "color": "#721c24"
                    }
                ],
                row_selectable="single",
                selected_rows=[],
                page_size=10
            )
        ]),
    ],
    id="modal-lembretes",
    is_open=False,
    size="lg"
    )
])

# Callback to open/close modal
@app.callback(
    Output("modal-lembretes", "is_open"),
    [Input("btn_lembretes", "n_clicks"),
     Input("btn-cancel-lembrete", "n_clicks")],
    [State("modal-lembretes", "is_open")],
    prevent_initial_call=True
)
def toggle_modal(n1, n2, is_open):
    return not is_open

# Callback to load table data
@app.callback(
    Output("table-lembretes", "data"),
    [Input("modal-lembretes", "is_open"),
     Input("btn-save-lembrete", "n_clicks"),
     Input("btn-delete-lembrete", "n_clicks")]
)
def load_table_data(is_open, n_save, n_delete):
    banco = Banco()
    df_lembretes = banco.ler_tabela('lembretes')
    
    if df_lembretes.empty:
        return []
    
    # Format the date for display
    df_lembretes['data'] = pd.to_datetime(df_lembretes['data']).dt.strftime('%d/%m/%Y')
    
    return df_lembretes.to_dict('records')

# Callback to handle row selection
@app.callback(
    [Output("input-lembrete", "value"),
     Output("input-data-lembrete", "date"),
     Output("input-status-lembrete", "value"),
     Output("lembrete-id", "value"),
     Output("btn-delete-lembrete", "disabled")],
    [Input("table-lembretes", "selected_rows")],
    [State("table-lembretes", "data")]
)
def select_row(selected_rows, data):
    if selected_rows and data:
        row = data[selected_rows[0]]
        
        # Convert date from string to date object
        date_obj = datetime.strptime(row['data'], '%d/%m/%Y').date()
        
        return row['lembrete'], date_obj, row['status'], row['id'], False
    
    # Clear form if no row selected
    today = date.today()
    return "", today, "pendente", None, True

# Callback to save lembrete
@app.callback(
    [Output("lembrete-status-message", "children"),
     Output("input-lembrete", "value", allow_duplicate=True),
     Output("lembrete-id", "value", allow_duplicate=True),
     Output("btn-delete-lembrete", "disabled", allow_duplicate=True),
     Output("table-lembretes", "selected_rows")],
    [Input("btn-save-lembrete", "n_clicks")],
    [State("lembrete-id", "value"),
     State("input-lembrete", "value"),
     State("input-data-lembrete", "date"),
     State("input-status-lembrete", "value")],
    prevent_initial_call=True
)
def save_lembrete(n_clicks, lembrete_id, lembrete_texto, data_lembrete, status):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    
    if not lembrete_texto:
        return dbc.Alert("O texto do lembrete é obrigatório!", color="danger"), no_update, no_update, no_update, []
    
    # Process date string to date object if needed
    if isinstance(data_lembrete, str):
        try:
            data_obj = datetime.strptime(data_lembrete, '%Y-%m-%d').date()
        except ValueError:
            return dbc.Alert("Formato de data inválido!", color="danger"), no_update, no_update, no_update, []
    else:
        data_obj = data_lembrete
    
    banco = Banco()
    
    try:
        if lembrete_id:  # Update existing lembrete
            banco.editar_dado('lembretes', lembrete_id, 
                             lembrete=lembrete_texto,
                             data=data_obj,
                             status=status)
            message = dbc.Alert("Lembrete atualizado com sucesso!", color="success")
        else:  # Create new lembrete
            banco.inserir_dados('lembretes',
                              lembrete=lembrete_texto,
                              data=data_obj,
                              status=status)
            message = dbc.Alert("Lembrete criado com sucesso!", color="success")
        
        # Clear form
        return message, "", None, True, []
        
    except Exception as e:
        return dbc.Alert(f"Erro ao salvar lembrete: {str(e)}", color="danger"), no_update, no_update, no_update, []

# Callback to delete lembrete
@app.callback(
    [Output("lembrete-status-message", "children", allow_duplicate=True),
     Output("input-lembrete", "value", allow_duplicate=True),
     Output("lembrete-id", "value", allow_duplicate=True),
     Output("btn-delete-lembrete", "disabled", allow_duplicate=True),
     Output("table-lembretes", "selected_rows", allow_duplicate=True)],
    [Input("btn-delete-lembrete", "n_clicks")],
    [State("lembrete-id", "value")],
    prevent_initial_call=True
)
def delete_lembrete(n_clicks, lembrete_id):
    if not n_clicks or not lembrete_id:
        return no_update, no_update, no_update, no_update, no_update
    
    banco = Banco()
    
    try:
        banco.deletar_dado('lembretes', lembrete_id)
        message = dbc.Alert("Lembrete excluído com sucesso!", color="success")
        
        # Clear form
        return message, "", None, True, []
        
    except Exception as e:
        return dbc.Alert(f"Erro ao excluir lembrete: {str(e)}", color="danger"), no_update, no_update, no_update, []
