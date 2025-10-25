import dash
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css"])

app.config['suppress_callback_exceptions'] = True
app.scripts.config.serve_locally = True
server = app.server