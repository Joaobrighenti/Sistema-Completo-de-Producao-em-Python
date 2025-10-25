from dash import html, dcc
import dash_bootstrap_components as dbc
 
# Layout do modal/form
layout = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle(id="modal-faca-title"), close_button=True),
    dbc.ModalBody([
        dbc.Form([
            # ID oculto para controle de edição
            dcc.Store(id='fac-editing-id'),
            
            dbc.Row([
                # Coluna Esquerda: Campos do Formulário
                dbc.Col([
                    # Linha 1: Código e Medidas
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Código (Auto-gerado)", html_for="fac-codigo"),
                            dbc.Input(
                                type="text",
                                id="fac-codigo",
                                placeholder="Será gerado automaticamente",
                                required=True,
                                readonly=True
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Medidas", html_for="fac-medida"),
                            dbc.Input(
                                type="text",
                                id="fac-medida",
                                placeholder="Ex: 500x800"
                            ),
                        ], width=6),
                    ], className="mb-3"),
        
                    # Linha 2: Descrição
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Descrição", html_for="fac-descricao"),
                            dbc.Textarea(
                                id="fac-descricao",
                                placeholder="Descreva detalhes da faca",
                                style={"height": "100px"}
                            ),
                        ]),
                    ], className="mb-3"),
        
                    # Linha 3: Máquina e Status
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Máquina", html_for="fac-maquina"),
                            dcc.Dropdown(
                                id="fac-maquina",
                                options=[
                                    {"label": "CORTE E VINCO SAPO", "value": "CORTE E VINCO SAPO"},
                                    {"label": "CORTE E VINCO SBB", "value": "CORTE E VINCO SBB"},
                                    {"label": "CORTE E VINCO SBL", "value": "CORTE E VINCO SBL"},
                                ],
                                placeholder="Selecione a máquina"
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Status", html_for="fac-status"),
                            dcc.Dropdown(
                                id="fac-status",
                                options=[
                                    {"label": "ATIVA", "value": "ATIVA"},
                                    {"label": "MANUTENÇÃO", "value": "MANUTENCAO"},
                                    {"label": "INATIVA", "value": "INATIVA"},
                                ],
                                placeholder="Selecione o status"
                            ),
                        ], width=6),
                    ], className="mb-3"),
        
                    # Linha 4: Localização e Tipo de Papel
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Localização", html_for="fac-localizacao"),
                            dbc.Input(
                                type="text",
                                id="fac-localizacao",
                                placeholder="Digite a localização da faca"
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Tipo de Papel", html_for="fac-tipo-papel"),
                            dbc.Input(
                                type="text",
                                id="fac-tipo-papel",
                                placeholder="Digite o tipo de papel"
                            ),
                        ], width=6),
                    ], className="mb-3"),
                ], width=8),

                # Coluna Direita: Upload de Imagem
                dbc.Col([
                    dbc.Label("Imagem da Faca:", className="fw-bold"),
                    dcc.Upload(
                        id="upload-faca-imagem",
                        children=html.Div([
                            html.I(className="fas fa-upload me-2"),
                            html.Span("Arraste ou clique para selecionar")
                        ]),
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
                        multiple=False,
                        accept='image/*'
                    ),
                    html.Div(id='output-faca-upload'),
                    dcc.Store(id='stored-faca-path'),
                ], width=4),
            ]),
 
            # Mensagem de erro/sucesso
            html.Div(id="fac-message", className="mb-3"),
 
            # Botões de ação
            dbc.Row([
                dbc.Col([
                    # Botão de excluir (visível apenas na edição)
                    html.Div(
                        dbc.Button(
                            "Excluir",
                            id="fac-delete",
                            color="danger",
                            className="me-2",
                        ),
                        id="fac-delete-div"
                    ),
                ], width=6, className="d-flex align-items-center"),
                dbc.Col([
                    dbc.Button(
                        "Cancelar",
                        id="fac-cancel",
                        color="secondary",
                        className="me-2"
                    ),
                    dbc.Button(
                        "Salvar",
                        id="fac-submit",
                        color="primary"
                    ),
                ], width=6, className="d-flex justify-content-end"),
            ]),
        ]),
    ]),
   
    # Modal de confirmação de exclusão
    dbc.Modal([
        dbc.ModalHeader("Confirmar Exclusão"),
        dbc.ModalBody("Tem certeza que deseja excluir esta faca?"),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="fac-cancel-delete", className="me-2", color="secondary"),
            dbc.Button("Confirmar", id="fac-confirm-delete", color="danger"),
        ]),
    ], id="modal-confirm-delete", is_open=False),
   
], id="modal-form-faca", size="xl")