import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

from banco_dados.banco import authenticate_user, edit_password
from app import app

# ======== Layout ======= #
layout = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle(id="titulo_usuario")),  # Exibe o usuário logado
    dbc.ModalBody([
        dbc.Row([
            dbc.Col([
                dbc.Label("Senha Atual"),
                dbc.Input(id="senha_atual", type="password", placeholder="Digite sua senha atual...", required=True),
            ], sm=10),
            dbc.Col([
                html.I(className="fa fa-eye", id="toggle_senha_atual", style={"cursor": "pointer", "fontSize": "20px"})
            ], sm=2, style={"display": "flex", "alignItems": "center", "justifyContent": "center"}),
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col([
                dbc.Label("Nova Senha"),
                dbc.Input(id="nova_senha", type="password", placeholder="Digite a nova senha...", required=True),
            ], sm=10),
            dbc.Col([
                html.I(className="fa fa-eye", id="toggle_nova_senha", style={"cursor": "pointer", "fontSize": "20px"})
            ], sm=2, style={"display": "flex", "alignItems": "center", "justifyContent": "center"}),
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col([
                dbc.Label("Confirme a Nova Senha"),
                dbc.Input(id="confirmar_senha", type="password", placeholder="Confirme a nova senha...", required=True),
            ], sm=10),
            dbc.Col([
                html.I(className="fa fa-eye", id="toggle_confirmar_senha", style={"cursor": "pointer", "fontSize": "20px"})
            ], sm=2, style={"display": "flex", "alignItems": "center", "justifyContent": "center"}),
        ]),
        html.Br(),
        html.Div(id="mensagem_erro", style={"textAlign": "center"})
    ]),
    dbc.ModalFooter([
        dbc.Button("Alterar Senha", id="botao_alterar_senha", color="success"),
        dbc.Button("Cancelar", id="fechar_modal_senha", color="secondary", className="ml-auto")
    ])
], id="modal_alterar_senha", size="md", is_open=False)

# ======== CALLBACK PARA EXIBIR A SENHA ======= #
@app.callback(
    [Output("senha_atual", "type"), Output("toggle_senha_atual", "className")],
    [Input("toggle_senha_atual", "n_clicks")],
    [State("senha_atual", "type")]
)
def toggle_senha_atual(n, tipo):
    if n and tipo == "password":
        return "text", "fa fa-eye-slash"
    return "password", "fa fa-eye"

@app.callback(
    [Output("nova_senha", "type"), Output("toggle_nova_senha", "className")],
    [Input("toggle_nova_senha", "n_clicks")],
    [State("nova_senha", "type")]
)
def toggle_nova_senha(n, tipo):
    if n and tipo == "password":
        return "text", "fa fa-eye-slash"
    return "password", "fa fa-eye"

@app.callback(
    [Output("confirmar_senha", "type"), Output("toggle_confirmar_senha", "className")],
    [Input("toggle_confirmar_senha", "n_clicks")],
    [State("confirmar_senha", "type")]
)
def toggle_confirmar_senha(n, tipo):
    if n and tipo == "password":
        return "text", "fa fa-eye-slash"
    return "password", "fa fa-eye"


# ======== CALLBACK ======= #
@app.callback(
    [Output("modal_alterar_senha", "is_open"),
     Output("titulo_usuario", "children"),
     Output("mensagem_erro", "children"),
     Output("mensagem_erro", "style")],  # Adicionando um Output para o estilo
    [Input("btn-abrir-modal-senha", "n_clicks"),
     Input("fechar_modal_senha", "n_clicks"),
     Input("botao_alterar_senha", "n_clicks")],
    [State("store-login-state", "data"),
     State("senha_atual", "value"),
     State("nova_senha", "value"),
     State("confirmar_senha", "value"),
     State("modal_alterar_senha", "is_open")]
)
def gerenciar_modal_e_senha(n_open, n_close, n_alterar, login_state, senha_atual, nova_senha, confirmar_senha, is_open):
    ctx = dash.callback_context

    if not ctx.triggered:
        return is_open, "", "", {}

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Obtém o nome do usuário logado
    usuario_logado = login_state.get("username", "Usuário Desconhecido") if login_state else "Usuário Desconhecido"

    # ABRIR MODAL
    if triggered_id == "btn-abrir-modal-senha":
        return True, f"ALTERAR SENHA DE {usuario_logado}", "", {}

    # FECHAR MODAL
    if triggered_id == "fechar_modal_senha":
        return False, "", "", {}

    # ALTERAR SENHA
    if triggered_id == "botao_alterar_senha":
        if not login_state:
            return is_open, f"ALTERAR SENHA DE {usuario_logado}", "Erro: Usuário não autenticado.", {"color": "red"}

        username = login_state.get("username")

        # Verifica se a senha antiga é correta
        user_level = authenticate_user(username, senha_atual)
        if not user_level:
            return is_open, f"ALTERAR SENHA DE {usuario_logado}", "Erro: Senha atual incorreta.", {"color": "red"}

        # Verifica se a nova senha e a confirmação coincidem
        if nova_senha != confirmar_senha:
            return is_open, f"ALTERAR SENHA DE {usuario_logado}", "Erro: As senhas novas não coincidem.", {"color": "red"}

        # Atualiza a senha no banco de dados
        edit_password(username, nova_senha)

        return is_open, "", "Senha alterada com sucesso!", {"color": "green"}  # Verde para sucesso

    return is_open, "", "", {}
