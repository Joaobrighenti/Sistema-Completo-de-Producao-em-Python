from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from app import app
from sqlalchemy.orm import sessionmaker
from banco_dados.banco import engine, User
import json


def build_permissions_editor(current_permissions: dict | None = None) -> html.Div:
    perms = current_permissions or {}
    # Collapses available
    collapses = [
        ("cadastros", "Cadastros"),
        ("pcp", "PCP"),
        ("oee", "OEE"),
        ("compras", "Compras"),
        ("qualidade", "Qualidade"),
        ("dashboards", "Dashboards"),
        ("export", "Exportar Dados"),
    ]
    return html.Div([
        html.H6("Permissões de Sidebar"),
        html.Div([
            dbc.Checklist(
                id="chk-collapses",
                options=[{"label": label, "value": key} for key, label in collapses],
                value=[k for k, _ in collapses if perms.get("collapses", {}).get(k, False)],
                inline=False,
            )
        ]),
        html.Small("Você poderá detalhar por botões depois; por ora controlamos os grupos (collapses)."),
    ])


layout = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Controle de Usuários")),
    dbc.ModalBody([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Criar / Editar Usuário"),
                    dbc.CardBody([
                        dbc.Input(id="inp-username", placeholder="Username"),
                        html.Br(),
                        dbc.Input(id="inp-password", placeholder="Senha inicial / Nova senha", type="password"),
                        html.Br(),
                        build_permissions_editor(),
                        html.Br(),
                        dbc.Button("Salvar", id="btn-save-user", color="primary"),
                        html.Span(id="user-save-feedback", className="ms-2"),
                    ])
                ])
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Usuários Existentes"),
                    dbc.CardBody([
                        dcc.Dropdown(id="ddl-users", placeholder="Selecione um usuário"),
                        html.Br(),
                        dbc.Button("Carregar", id="btn-load-user", color="secondary"),
                    ])
                ])
            ], md=6)
        ])
    ]),
    dbc.ModalFooter([
        dbc.Button("Fechar", id="btn-close-controle-usuarios", className="ms-auto")
    ])
], id="modal-controle-usuarios", is_open=False, size="lg")


@app.callback(
    Output("ddl-users", "options"),
    Input("modal-controle-usuarios", "is_open")
)
def load_users_options(is_open):
    if not is_open:
        return []
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    try:
        users = session.query(User).order_by(User.username.asc()).all()
        return [{"label": u.username, "value": u.id} for u in users]
    finally:
        session.close()


@app.callback(
    Output("modal-controle-usuarios", "is_open"),
    [Input("btn_cadastro_pessoas", "n_clicks"), Input("btn-close-controle-usuarios", "n_clicks")],
    State("modal-controle-usuarios", "is_open"),
    prevent_initial_call=True,
)
def toggle_modal(open_clicks, close_clicks, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    if trigger == 'btn_cadastro_pessoas':
        return True
    if trigger == 'btn-close-controle-usuarios':
        return False
    return is_open


@app.callback(
    [Output("inp-username", "value"), Output("inp-password", "value"), Output("chk-collapses", "value")],
    Input("btn-load-user", "n_clicks"),
    State("ddl-users", "value"),
    prevent_initial_call=True,
)
def load_user(n_clicks, user_id):
    if not user_id:
        return "", "", []
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    try:
        u = session.query(User).get(user_id)
        if not u:
            return "", "", []
        perms = {}
        try:
            perms = u.user_level if isinstance(u.user_level, dict) else json.loads(u.user_level)
        except Exception:
            perms = {}
        enabled = [k for k in (perms.get("collapses") or {}).keys() if perms.get("collapses", {}).get(k)]
        return u.username, "", enabled
    finally:
        session.close()


@app.callback(
    Output("user-save-feedback", "children"),
    Input("btn-save-user", "n_clicks"),
    State("inp-username", "value"),
    State("inp-password", "value"),
    State("chk-collapses", "value"),
    State("ddl-users", "value"),
    prevent_initial_call=True,
)
def save_user(n_clicks, username, password, enabled_collapses, selected_user_id):
    if not username:
        return "Informe o username"

    perms = {"collapses": {k: True for k in (enabled_collapses or [])}}

    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    try:
        if selected_user_id:
            user = session.query(User).get(selected_user_id)
            if not user:
                return "Usuário não encontrado"
            user.username = username
            if password:
                user.password = password
            user.user_level = perms
        else:
            user = User(username=username, password=password or "", user_level=perms)
            session.add(user)
        session.commit()
        return "Salvo com sucesso"
    except Exception as e:
        session.rollback()
        return f"Erro ao salvar: {e}"
    finally:
        session.close()

