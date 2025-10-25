import dash_bootstrap_components as dbc
from dash import html, dcc
from app import app
from dash.dependencies import Input, Output, State


def get_form_cotacao():
    return html.Div([
        dbc.Modal(
            [
                dbc.ModalHeader("Cadastro de Cotação"),
                dbc.ModalBody([
                    dbc.Form([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Valor Unitário - Com ICMS e Sem IPI"),
                                dbc.Input(id="cot-valor-unit", type="number", placeholder="Valor R$", size="sm"),
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Valor Entrada"),
                                dbc.Input(id="cot-valor-entrada", type="number", placeholder="Valor de Entrada R$", size="sm"),
                            ], width=6),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Fornecedor"),
                                dcc.Dropdown(id="cot-fornecedor-id", placeholder="Selecione um fornecedor", clearable=True),
                            ], width=12),
                        ], className="mt-2"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("IPI (%)"),
                                dbc.Input(id="cot-ipi", type="number", placeholder="%", size="sm"),
                            ], width=6),
                            dbc.Col([
                                dbc.Label("ICMS (%)"),
                                dbc.Input(id="cot-icms", type="number", placeholder="%", size="sm"),
                            ], width=6),
                        ], className="mt-2"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Condição de Pagamento"),
                                dbc.Input(id="cot-condicao-pagamento", type="text", placeholder="Ex: 30/60/90", size="sm"),
                            ], width=6),
                            dbc.Col([
                                dbc.Label("Forma de Pagamento"),
                                dbc.Input(id="cot-forma-pagamento", type="text", placeholder="Ex: Boleto", size="sm"),
                            ], width=6),
                        ], className="mt-2"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Observação"),
                                dbc.Textarea(id="cot-observacao", placeholder="Observações sobre a cotação", style={"height": "100px"}),
                            ], className="mt-2"),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Imagem da Cotação"),
                                dcc.Upload(
                                    id='upload-cotacao-imagem',
                                    children=html.Div(['Arraste e solte ou ', html.A('selecione um arquivo')]),
                                    style={
                                        'width': '100%',
                                        'height': '60px',
                                        'lineHeight': '60px',
                                        'borderWidth': '1px',
                                        'borderStyle': 'dashed',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'margin': '10px 0'
                                    },
                                    multiple=False
                                ),
                                html.Div(id='output-cotacao-imagem-upload'),
                            ])
                        ]),
                        # Campos ocultos
                        dcc.Input(id="cot-id", type="hidden"),
                        dcc.Input(id="cot-oc-id", type="hidden"),
                    ]),
                    html.Div(id="feedback-form-cotacao", className="mt-2"),
                ]),
                dbc.ModalFooter([
                    dbc.Button("Fechar", id="btn-fechar-cotacao", color="secondary", size="sm"),
                    dbc.Button("Salvar", id="btn-salvar-cotacao", color="primary", size="sm", className="ms-auto"),
                ]),
            ],
            id="modal-form-cotacao",
            size="lg",
        )
    ])

