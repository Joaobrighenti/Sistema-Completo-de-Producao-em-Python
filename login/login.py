from dash import html
import dash_bootstrap_components as dbc

layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card(
                    dbc.CardBody([
                        html.H2("Login", className="text-center mb-4 text-white fw-bold"),
                        html.P("Bem-vindo! Faça login para acessar sua conta.", className="text-center text-white mb-4"),
                        dbc.Input(id="input-username", type="text", placeholder="Usuário", className="mb-3"),
                        dbc.Input(id="input-password", type="password", placeholder="Senha", className="mb-3"),
                        dbc.Button("Login", id="btn-login", color="success", className="w-100 text-white fw-bold", n_clicks=0),
                        html.Div(id="login-feedback", className="text-danger text-center mt-2")
                    ]),
                    className="shadow-lg border-0", 
                    style={
                        "width": "100%", 
                        "max-width": "400px",
                        "padding": "30px",
                        "border-radius": "15px",
                        "background": "rgba(169, 169, 169, 0.6)",  # Ajuste a transparência aqui
                        "height": "400px",  # Ajusta altura do card
                        "backdrop-filter": "blur(10px)"  # Efeito de desfoque no fundo
                    }
                )  
            ], width=12, className="d-flex justify-content-center")
        ], className="vh-100 align-items-center justify-content-center")
    ], fluid=True, className="d-flex justify-content-center align-items-center vh-100", 
       style={
           "background": "linear-gradient(to bottom, #8e9eab, ##eef2f3)",  # Apply the new test gradient
           # "background-size": "400% 400%", 
           "height": "100vh",
           "position": "relative", # Keep position if needed for other elements
           "overflow": "hidden" # Keep overflow hidden
       })
])

