from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import pandas as pd
import io
from sqlalchemy import inspect
import json

from cadastros.formularios import form_add_cliente, form_add_produto, form_plano_prod
from login.formularios import form_member
from login.formularios import form_controle_usuario
from app import app
from oee.formularios.form_setor import layout as form_setor_layout
from oee.formularios.form_maq import layout as form_maq_layout
from oee.formularios.form_razao import layout as form_razao_layout
from oee.formularios.form_horario import layout as form_horario_layout
from oee.formularios.form_categoria import layout as form_categoria_layout
from banco_dados.banco import Banco
from banco_dados.banco import User
from sqlalchemy.orm import sessionmaker

from pcp.formularios import form_baixa_producao, form_chapa, form_pcp, form_retirada


# Helper function for excel export
def to_excel(df, sheet_name='Dados'):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


# ========= Layout ========= #
layout = dbc.Container([
    # Modals first
    form_baixa_producao.layout,
    form_add_cliente.layout,
    form_add_produto.layout,
    form_retirada.layout,
    form_chapa.layout,

    form_setor_layout,
    form_maq_layout,
    form_razao_layout,
    form_horario_layout,
    form_categoria_layout,
    form_plano_prod.layout,
    form_controle_usuario.layout,

    form_pcp.layout,
  
    form_member.layout,
    html.Div([
        html.Img(src=app.get_asset_url('logo.png'),
                 style={'width': '250px', 'height': 'auto', 'margin': '20px'})
    ]),

    # Nome do usuário + ações
    html.Div([
        html.Div(
            id="sidebar-username",
            style={
                "color": "#521e1e",
                "fontSize": "16px",
                "padding": "12px 0",
                "textAlign": "center",
                "backgroundColor": "#f8f9fa",
                "borderRadius": "8px"
            }
        ),
        html.Div(
            dbc.Button(
                "Alterar Senha",
                id="btn-abrir-modal-senha",
                #color="primary",
                className="w-100 fw-bold",
                style={
                    "margin-top": "8px",
                    "border-radius": "5px",
                    "font-size": "10px",
                    "padding": "4px 8px",
                    "color": "#ffffff",
                    "background": "#3498db",
                    "border": "none",
                    "box-shadow": "0px 4px 6px rgba(0,0,0,0.1)",
                    "transition": "0.3s"
                    
                }
            ),
            className="d-flex justify-content-center"
        ),
    ]),

    html.Div(
        dbc.Button(
            "Logout",
            id="btn-logout",
            color="danger",
            className="w-100 fw-bold",
            style={
             
                "border-radius": "5px",
                "font-size": "10px",
                "padding": "4px 8px",
                "background": "#e74c3c",
                "border": "none",
                "box-shadow": "0px 4px 6px rgba(0,0,0,0.1)",
                "transition": "0.3s",
                "margin-top": "8px"
            }
        ),
        className="d-flex justify-content-center"
    ),

    html.Hr(),
    dbc.Row([
        dbc.Col([
            dbc.Nav([

    
            ], vertical=True, pills=True, fill=True, className="d-block"),

            
        ], width=12)
    ], className="g-0"),
    html.Div([
        dbc.Button(
            "CADASTROS ⮟",
            id="btn-toggle-cadastros",
            color="light",
            className="w-100 mb-2 text-start shadow-sm",
            style={"fontWeight": "bold"}
        ),
        dbc.Collapse(
            html.Div([
                dbc.Button(
                    [html.I(className="fa fa-users me-2"), "Cadastrar Cliente"],
                    id='btn_add_cliente',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-pencil me-2"), "Cadastrar produto"],
                    id='btn_abrir_produto',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-cogs me-2"), "Configurar Partes"],
                    id='btn_configurar_partes',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-id-card me-2"), "Cadastros de Pessoas"],
                    id='btn_cadastro_pessoas',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
            ], style={"padding": "8px"}),
            id="collapse-cadastros",
            is_open=False
        )
    ], id='cadastros-buttons'),
    html.Div([
        dbc.Button(
            "PCP ⮟",
            id="btn-toggle-admin",
            color="light",
            className="w-100 mb-2 text-start shadow-sm",
            style={"fontWeight": "bold"}
        ),
        dbc.Collapse(
            html.Div([
                dbc.Button(
                    [html.I(className="fa fa-home me-2"), "Sistema de PCP"],
                    id='btn_sistema_pcp',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-sistema-pcp",
                    href="/pcp",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-industry me-2"), "Adicionar Produção"],
                    id='adicionar_producao',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
            ], style={"padding": "8px"}),
            id="collapse-admin",
            is_open=False
        )
    ], id='admin-buttons'),

    html.Div([
        dbc.Button(
            "OEE ⮟",
            id="btn-toggle-oee",
            color="light",
            className="w-100 mb-2 text-start shadow-sm",
            style={"fontWeight": "bold"}
        ),
        dbc.Collapse(
            html.Div([
                dbc.Button(
                    [html.I(className="fa fa-tachometer me-2"), "Sistema OEE"],
                    id='btn_sistema_oee',
                    className="w-100 mb-1 shadow-sm btn-sistema-oee",
                    href="/oee",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-building me-2"), "Adicionar Setores"],
                    id='btn_add_setores',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px", "backgroundColor": "#ffffff"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-cogs me-2"), "Adicionar Máquinas"],
                    id='btn_add_maquinas',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px", "backgroundColor": "#ffffff"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-sitemap me-2"), "Árvore de Razões"],
                    id='btn_arvore_razoes',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px", "backgroundColor": "#ffffff"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-clock me-2"), "Adicionar Horários"],
                    id='btn_add_horarios',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px", "backgroundColor": "#ffffff"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-tags me-2"), "Gerenciar Categoria"],
                    id='btn_gerenciar_categoria',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    style={"textAlign": "left", "marginTop": "2px", "backgroundColor": "#ffffff"}
                ),
                
            ], style={"padding": "8px"}),
            id="collapse-oee",
            is_open=False
        )
    ], id='oee-buttons'),

    html.Div([
        dbc.Button(
            "COMPRAS ⮟",
            id="btn-toggle-compras",
            color="light",
            className="w-100 mb-2 text-start shadow-sm",
            style={"fontWeight": "bold"}
        ),
        dbc.Collapse(
            html.Div([
                dbc.Button(
                    [html.I(className="fa fa-shopping-cart me-2"), "Sistema de Compras"],
                    id='btn_sistema_compras',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-sistema-compras",
                    href="/compras",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-boxes me-2"), "Relatório de Estoque"],
                    id='btn_relatorio_estoque',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-relatorio-estoque",
                    href="/relatorioestoque",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-truck me-2"), "Entrega de Mercadoria"],
                    id='btn_entrega_mercadoria',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    href="/entregamercadoria",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
            ], style={"padding": "8px"}),
            id="collapse-compras",
            is_open=False
        )
    ], id='compras-buttons'),

    html.Div([
        dbc.Button(
            "QUALIDADE ⮟",
            id="btn-toggle-qualidade",
            color="light",
            className="w-100 mb-2 text-start shadow-sm",
            style={"fontWeight": "bold"}
        ),
        dbc.Collapse(
            html.Div([
                dbc.Button(
                    [html.I(className="fa fa-clipboard-check me-2"), "Inspeção Final"],
                    id='btn_qualidade_lotes',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    href="/qualidade",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-tasks me-2"), "Inspeção de Processos"],
                    id='btn_inspecao_processo',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    href="/inspecaoprocessos",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-file-alt me-2"), "Laudos"],
                    id='btn_laudos_qualidade',
                    color="light",
                    className="w-100 mb-1 shadow-sm",
                    href="/laudosqualidade",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
            ], style={"padding": "8px"}),
            id="collapse-qualidade",
            is_open=False
        )
    ], id='qualidade-buttons'),

    html.Div([
        dbc.Button(
            "DASHBOARDS ⮟",
            id="btn-toggle-dash",
            color="light",
            className="w-100 mb-2 text-start shadow-sm",
            style={"fontWeight": "bold"}
        ),
        dbc.Collapse(
            html.Div([
                dbc.Button(
                    [html.I(className="fa fa-chart-bar me-2"), "Dashboard de Planejamento Setor"],
                    id='btn_dashboard_compras',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-compras",
                    href="/compras/relatorio",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-truck me-2"), "Agendamento Logística"],
                    id='btn_agendamento_logistica',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-oee",
                    href="/agendamentologistica",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-tachometer-alt me-2"), "Dashboard PCP Geral"],
                    id='btn_dashboard_pcp',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-pcp",
                    href="/dashpcp",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-boxes me-2"), "Dashboard Produtos"],
                    id='btn_dashboard_produtos',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-pcp",
                    href="/dashprodutosnicopel",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-chart-line me-2"), "Dashboard OEE Máquina"],
                    id='btn_dashboard_oee',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-oee",
                    href="/dashboard-oee",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-chart-area me-2"), "Dashboard OEE Geral"],
                    id='btn_dashboard_oee_geral',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-oee",
                    href="/dashoeegeral",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-chart-area me-2"), "Dashboard OEE Setor"],
                    id='btn_dashboard_oee_setor',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-oee",
                    href="/dashoeesetor",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-users me-2"), "Painel Clientes Estoque"],
                    id='btn_painel_clientes_estoque',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-oee",
                    href="/painelclientesestoque",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-clipboard-list me-2"), "Dashboard Apontamento"],
                    id='btn_dashboard_apontamento',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-oee",
                    href="/relatorioapontamento",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-check-double me-2"), "Dashboard Qualidade"],
                    id='btn_dashboard_qualidade',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-oee",
                    href="/dashboardqualidade",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
                dbc.Button(
                    [html.I(className="fa fa-file-invoice-dollar me-2"), "Demonstrativo"],
                    id='btn_dashboard_dre',
                    color="light",
                    className="w-100 mb-1 shadow-sm btn-dashboard-oee",
                    href="/demonstrativo",
                    style={"textAlign": "left", "marginTop": "2px"}
                ),
            ], style={"padding": "8px"}),
            id="collapse-dash",
            is_open=False
        )
    ], id='dash-buttons'),

    html.Div([
        dbc.Button(
            "EXPORTAR DADOS ⮟",
            id="btn-toggle-export",
            color="secondary",
            className="w-100 mb-2 text-start shadow-sm",
            style={"fontWeight": "bold"}
        ),
        dbc.Collapse(
            html.Div([
                dcc.Dropdown(
                    id='export-table-dropdown',
                    placeholder="Selecione uma tabela...",
                    className="mb-2"
                ),
                dbc.Button(
                    [html.I(className="fa fa-file-excel me-2"), "Exportar Tabela para Excel"],
                    id='btn-export-table',
                    color="success",
                    className="w-100"
                ),
                dcc.Download(id="download-table-excel")
            ], style={"padding": "8px"}),
            id="collapse-export",
            is_open=False
        )
    ], id='export-buttons'),

    html.Div(id="informacoes-personalizadas", style={'margin-top': '15px'}),
    html.Div(id="informacoes-personalizadas-2", style={'margin-top': '15px'}),
    dcc.Store(id='store-sidebar-perms'),

], id="app-sidebar")


@app.callback(
    Output("collapse-admin", "is_open"),
    Input("btn-toggle-admin", "n_clicks"),
    State("collapse-admin", "is_open"),
    prevent_initial_call=True
    )
def toggle_collapse(n_clicks, is_open):
    return not is_open

@app.callback(
    Output("collapse-cadastros", "is_open"),
    Input("btn-toggle-cadastros", "n_clicks"),
    State("collapse-cadastros", "is_open"),
    prevent_initial_call=True
)
def toggle_collapse_cadastros(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open

@app.callback(
    Output("collapse-dash", "is_open"),
    Input("btn-toggle-dash", "n_clicks"),
    State("collapse-dash", "is_open"),
    prevent_initial_call=True
)
def toggle_collapse_dash(n_clicks, is_open):
    return not is_open

@app.callback(
    Output("collapse-compras", "is_open"),
    Input("btn-toggle-compras", "n_clicks"),
    State("collapse-compras", "is_open"),
    prevent_initial_call=True
)
def toggle_collapse_compras(n_clicks, is_open):
    return not is_open

@app.callback(
    Output("collapse-oee", "is_open"),
    Input("btn-toggle-oee", "n_clicks"),
    State("collapse-oee", "is_open"),
    prevent_initial_call=True
)
def toggle_collapse_oee(n_clicks, is_open):
    return not is_open

@app.callback(
    Output("collapse-qualidade", "is_open"),
    Input("btn-toggle-qualidade", "n_clicks"),
    State("collapse-qualidade", "is_open"),
    prevent_initial_call=True
)
def toggle_collapse_qualidade(n_clicks, is_open):
    return not is_open

@app.callback(
    Output("collapse-export", "is_open"),
    Input("btn-toggle-export", "n_clicks"),
    State("collapse-export", "is_open"),
    prevent_initial_call=True
)
def toggle_collapse_export(n_clicks, is_open):
    return not is_open

# This callback will run once when the sidebar is loaded to populate the dropdown
@app.callback(
    Output('export-table-dropdown', 'options'),
    Input('app-sidebar', 'id') # Dummy input to trigger on load
)
def populate_table_dropdown(_):
    try:
        banco = Banco()
        inspector = inspect(banco.engine)
        table_names = sorted(inspector.get_table_names())
        options = [{'label': name, 'value': name} for name in table_names]
        return options
    except Exception as e:
        print(f"Erro ao carregar nomes das tabelas: {e}")
        return []


@app.callback(
    Output('store-sidebar-perms', 'data'),
    Input('sidebar-username', 'children'),
    prevent_initial_call=False
)
def load_sidebar_permissions(username_text):
    # Espera-se texto do tipo "Bem-vindo, NOME!" ou vazio
    try:
        username = (username_text or '').replace('Bem-vindo,', '').replace('!', '').strip()
        if not username:
            return {}
        banco = Banco()
        SessionFactory = sessionmaker(bind=banco.engine)
        session = SessionFactory()
        try:
            user = session.query(User).filter_by(username=username).first()
            if not user or not user.user_level:
                return {}
            # user_level pode ser dict (JSON do SQLAlchemy) ou string JSON
            import json as _json
            return user.user_level if isinstance(user.user_level, dict) else _json.loads(user.user_level)
        finally:
            session.close()
    except Exception:
        return {}


@app.callback(
    [
        Output('cadastros-buttons', 'style'),
        Output('admin-buttons', 'style'),
        Output('oee-buttons', 'style'),
        Output('compras-buttons', 'style'),
        Output('qualidade-buttons', 'style'),
        Output('dash-buttons', 'style'),
        Output('export-buttons', 'style'),
    ],
    Input('store-sidebar-perms', 'data')
)
def apply_sidebar_permissions(perms):
    def visible(flag):
        return {} if flag else {'display': 'none'}

    collapses = (perms or {}).get('collapses', {}) if isinstance(perms, dict) else {}
    return (
        visible(collapses.get('cadastros', False)),
        visible(collapses.get('pcp', False)),
        visible(collapses.get('oee', False)),
        visible(collapses.get('compras', False)),
        visible(collapses.get('qualidade', False)),
        visible(collapses.get('dashboards', False)),
        visible(collapses.get('export', False)),
    )

@app.callback(
    Output('download-table-excel', 'data'),
    Input('btn-export-table', 'n_clicks'),
    State('export-table-dropdown', 'value'),
    prevent_initial_call=True
)
def export_selected_table(n_clicks, table_name):
    if not n_clicks or not table_name:
        raise PreventUpdate

    try:
        banco = Banco()
        with banco.engine.connect() as conn:
            df = pd.read_sql_table(table_name, conn)
        
        return dcc.send_bytes(to_excel(df, sheet_name=table_name).getvalue(), f"{table_name}.xlsx")

    except Exception as e:
        print(f"Erro ao exportar tabela {table_name}: {e}")
        raise PreventUpdate
