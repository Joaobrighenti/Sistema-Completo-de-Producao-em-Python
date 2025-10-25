from dash import html, dcc, callback_context, dash_table
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, MATCH
import pandas as pd
import base64
import io
from banco_dados.banco import Banco
from app import app
 
# Importar os formulários
from compras.formularios import form_categoria_estoque, form_estudo_estoque
 
# Instanciar o banco de dados
banco = Banco()
 
# Função utilitária para agrupar subtipos pelos 3 primeiros termos
def agrupar_subtipos(subtipos):
    agrupados = set()
    for subtipo in subtipos:
        partes = str(subtipo).split('_')
        if len(partes) >= 3:
            agrupados.add('_'.join(partes[:3]))
    return sorted(agrupados)
 
# Visualização customizada dos dados do banco
def gerar_visualizacao_banco():
    banco = Banco()
    df_cat = banco.ler_tabela("categoria_estoque")
    df_est = banco.ler_tabela("estudo_estoque")
    visual = []
    for _, row in df_cat.iterrows():
        cae_id = row['cae_id']
        linha = row['cae_linha']
        subtipos = df_est[df_est['ese_cae_id'] == cae_id]['ese_subtipo'].tolist()
        agrupados = agrupar_subtipos(subtipos)
        visual.append(
            html.Div([
                html.H5(linha, style={"marginTop": "20px", "color": "#0d6efd"}),
                html.Ul([html.Li(sub) for sub in agrupados]) if agrupados else html.Small("Nenhum subtipo vinculado.")
            ])
        )
    return html.Div(visual)
 
# Visualização customizada dos dados do Excel importado, linkando com subtipos do banco
def gerar_visualizacao_linkada(df_excel):
    banco = Banco()
    df_cat = banco.ler_tabela("categoria_estoque")
    df_est = banco.ler_tabela("estudo_estoque")
    def extrair_agrupados_excel(desc):
        if pd.isna(desc):
            return set()
        desc = str(desc).strip('[]').replace(' ', '')
        subtipos = desc.split(',')
        return set(agrupar_subtipos(subtipos))
    df_excel['Subtipos Agrupados'] = df_excel['Descrição Detalhada'].apply(extrair_agrupados_excel)
 
    # Soma por subtipo completo
    soma_qtde = {}
    for _, row in df_excel.iterrows():
        desc = row.get('Descrição Detalhada', '')
        if pd.isna(desc):
            continue
        desc = str(desc).strip('[]').replace(' ', '')
        subtipos = desc.split(',')
        qtde = row.get('Qtde Armazenamento', 0)
        try:
            qtde = float(qtde)
        except Exception:
            qtde = 0
        for subtipo in subtipos:
            if subtipo:
                soma_qtde[subtipo] = soma_qtde.get(subtipo, 0) + qtde
 
    peso_medio_map = {row['ese_subtipo']: row['ese_peso_medio'] for _, row in df_est.iterrows()}
 
    visual = []
    for _, row_cat in df_cat.iterrows():
        cae_id = row_cat['cae_id']
        linha = row_cat['cae_linha']
        cae_consumo = row_cat.get('cae_consumo_mensal', 0)
        subtipos_banco = df_est[df_est['ese_cae_id'] == cae_id]['ese_subtipo'].tolist()

        # Pré-cálculo dos dias de estoque e unidades para encontrar o mínimo da categoria
        grupos_para_calculo = {}
        for subtipo in subtipos_banco:
            partes = str(subtipo).split('_')
            if len(partes) >= 3:
                chave = '_'.join(partes[:3])
                grupos_para_calculo.setdefault(chave, []).append(subtipo)

        dados_estoque_grupos = []
        if cae_consumo and cae_consumo > 0:
            for grupo, subtipos_completos in grupos_para_calculo.items():
                soma_unid_grupo = 0
                dias_estoque_subitens = []
                for sub in subtipos_completos:
                    qtde_kg = soma_qtde.get(sub, 0)
                    peso_medio = peso_medio_map.get(sub, 1)
                    unid = qtde_kg / peso_medio if peso_medio else 0
                    soma_unid_grupo += unid
                    dias_estoque = unid / (cae_consumo / 21)
                    dias_estoque_subitens.append(dias_estoque)
                
                dias_estoque_grupo = sum(dias_estoque_subitens)
                dados_estoque_grupos.append({'dias': dias_estoque_grupo, 'unid': soma_unid_grupo})

        min_dias_estoque_categoria = 0
        unid_totais_min_estoque = 0
        if dados_estoque_grupos:
            grupos_com_estoque = [g for g in dados_estoque_grupos if g['dias'] > 0]
            if grupos_com_estoque:
                grupo_min_estoque = min(grupos_com_estoque, key=lambda x: x['dias'])
                min_dias_estoque_categoria = grupo_min_estoque['dias']
                unid_totais_min_estoque = grupo_min_estoque['unid']
       
        # Barra de progresso para a categoria
        barra_width_categoria = 0
        barra_color_categoria = "#198754"  # Verde por padrão
        if cae_consumo and cae_consumo > 0:
            barra_width_categoria = min(100, int((unid_totais_min_estoque / cae_consumo) * 100))
        
        if min_dias_estoque_categoria < 7:
            barra_color_categoria = "#dc3545"  # Vermelho
        elif min_dias_estoque_categoria < 15:
            barra_color_categoria = "#fd7e14"  # Laranja

        grupos = {}
        for subtipo in subtipos_banco:
            partes = str(subtipo).split('_')
            if len(partes) >= 3:
                chave = '_'.join(partes[:3])
                grupos.setdefault(chave, []).append(subtipo)
 
        itens = []
        for grupo, subtipos_completos in grupos.items():
            soma_peso = 0
            soma_unid = 0
            subitens = []
            lista_dias_estoque_subitens = []
            for sub in subtipos_completos:
                qtde_kg = soma_qtde.get(sub, 0)
                peso_medio = peso_medio_map.get(sub, 1)
                unid = qtde_kg / peso_medio if peso_medio else 0
                soma_peso += qtde_kg
                soma_unid += unid
                dias_estoque = unid / (cae_consumo/21) if cae_consumo else 0
                lista_dias_estoque_subitens.append(dias_estoque)
                # Barra de progresso para subitem
                barra_width = min(100, int((dias_estoque/60)*100)) if unid else 0
                if dias_estoque < 60:
                    barra_color = "#198754"  # verde
                elif dias_estoque == 60:
                    barra_color = "#fd7e14"  # laranja
                else:
                    barra_color = "#dc3545"  # vermelho
                # Buscar todas as linhas do Excel cuja Descrição Detalhada contenha exatamente o subtipo na lista
                descricoes_qtde = []
                for _, excel_row in df_excel.iterrows():
                    desc_det = str(excel_row.get('Descrição Detalhada', '')).strip('[]').replace(' ', '')
                    subtipos_excel = desc_det.split(',') if desc_det else []
                    if str(sub) in subtipos_excel:
                        descricao = str(excel_row['Descrição']) if 'Descrição' in excel_row else ''
                        qtde_arm = excel_row['Qtde Armazenamento'] if 'Qtde Armazenamento' in excel_row else ''
                        qtde_arm_fmt = f"{qtde_arm:,.3f}".replace(",", ".") if qtde_arm != '' else ''
                        descricoes_qtde.append(
                            html.Div([
                                html.Span(f"Descrição: {descricao}", style={"fontSize": "12px", "color": "#555", "marginRight": "16px"}),
                                html.Span(f"Qtde Armazenamento: {qtde_arm_fmt}", style={"fontSize": "12px", "color": "#555"})
                            ], style={"marginLeft": "60px", "marginBottom": "2px"})
                        )
                subitens.append(
                    html.Div([
                        html.Div([
                            html.Div("└─", style={"width": "32px", "color": "#888", "flex": "0 0 32px"}),
                            html.Div(sub, style={"fontWeight": "500", "width": "240px", "minWidth": "120px", "padding": "16px 0"}),
                            html.Div(f"{qtde_kg:,.2f}".replace(",", "."), style={"width": "130px", "textAlign": "right", "padding": "16px 0"}),
                            html.Div(f"{unid:,.0f}".replace(",", "."), style={"width": "110px", "textAlign": "right", "padding": "16px 0"}),
                            html.Div([
                                html.Span(f"{int(round(dias_estoque))}" if unid else "-", style={"marginRight": "8px"}),
                                html.Div(style={
                                    "display": "inline-block",
                                    "verticalAlign": "middle",
                                    "height": "10px",
                                    "width": "180px",
                                    "backgroundColor": "#bebebd",
                                    "borderRadius": "5px",
                                    "overflow": "hidden"
                                }, children=[
                                    html.Div(style={
                                        "height": "100%",
                                        "width": f"{barra_width}%",
                                        "backgroundColor": barra_color,
                                        "transition": "width 0.3s"
                                    })
                                ])
                            ], style={"width": "140px", "display": "flex", "alignItems": "center", "justifyContent": "flex-end", "padding": "16px 0", "marginLeft": "24px"})
                        ], style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "12px",
                            "backgroundColor": "#fff",
                            "borderRadius": "4px",
                            "marginBottom": "1px",
                            "border": "1px solid #eee",
                            "padding": "2px 8px 2px 8px"
                        }),
                        *descricoes_qtde
                    ])
                )
            # Cálculo do grupo (pai) usando soma dos dias de estoque dos subitens
            dias_estoque_grupo = sum(lista_dias_estoque_subitens) if lista_dias_estoque_subitens else 0
            barra_width_grupo = min(100, int((dias_estoque_grupo/60)*100)) if soma_unid else 0
            if dias_estoque_grupo < 60:
                barra_color_grupo = "#198754"
            elif dias_estoque_grupo == 60:
                barra_color_grupo = "#fd7e14"
            else:
                barra_color_grupo = "#dc3545"
            aparece_no_excel = any(grupo in grupo_excel for grupo_excel in df_excel['Subtipos Agrupados'])
            icone = "✔️" if aparece_no_excel else "❌"
            cor = "green" if aparece_no_excel else "red"
            itens.append(
                html.Div([
                    html.Div([
                        html.Div("", style={"width": "32px", "flex": "0 0 32px"}),
                        html.Div([
                            html.Span(grupo, style={
                                "fontWeight": "bold",
                                "fontSize": "16px",
                                "color": "#333"
                            }),
                            html.Span(f" {icone}", style={
                                "color": cor,
                                "marginLeft": "8px",
                                "fontSize": "16px"
                            })
                        ], style={"width": "240px", "minWidth": "120px", "padding": "16px 0"}),
                        html.Div(f"{soma_peso:,.2f}".replace(",", "."), style={"width": "130px", "textAlign": "right", "fontWeight": "bold", "padding": "16px 0"}),
                        html.Div(f"{soma_unid:,.0f}".replace(",", "."), style={"width": "110px", "textAlign": "right", "fontWeight": "bold", "padding": "16px 0"}),
                        html.Div([
                            html.Span(f"{int(round(dias_estoque_grupo))}" if soma_unid else "-", style={"marginRight": "8px"}),
                            html.Div(style={
                                "display": "inline-block",
                                "verticalAlign": "middle",
                                "height": "10px",
                                "width": "180px",
                                "backgroundColor": "#AAAFAF",
                                "borderRadius": "5px",
                                "overflow": "hidden"
                            }, children=[
                                html.Div(style={
                                    "height": "100%",
                                    "width": f"{barra_width_grupo}%",
                                    "backgroundColor": barra_color_grupo,
                                    "transition": "width 0.3s"
                                })
                            ])
                        ], style={"width": "140px", "display": "flex", "alignItems": "center", "justifyContent": "flex-end", "padding": "16px 0", "marginLeft": "24px"})
                    ], style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "12px",
                        "padding": "10px 8px 2px 8px",
                        "backgroundColor": "#c4cad1",
                        "borderRadius": "5px",
                        "marginBottom": "0px",
                        "border": "1px solid #dee2e6"
                    }),
                    html.Div(subitens, style={"marginLeft": "0px", "marginTop": "0px"})
                ], style={"marginBottom": "2px"})
            )
 
        # Crie o conteúdo que será recolhível
        collapsible_content = html.Div([
            html.Div([
                html.Div([
                    html.Div("", style={"width": "32px", "flex": "0 0 32px"}),
                    html.Div("Subtipo", style={"fontWeight": "bold", "width": "240px", "minWidth": "120px"}),
                    html.Div("Peso (Kg)", style={"fontWeight": "bold", "width": "130px", "textAlign": "right"}),
                    html.Div("Unid. Totais", style={"fontWeight": "bold", "width": "110px", "textAlign": "right"}),
                    html.Div("Dias de Estoque", style={"fontWeight": "bold", "width": "140px", "textAlign": "right", "marginLeft": "24px"})
                ], style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                    "backgroundColor": "#8a9aaa",
                    "borderRadius": "4px",
                    "marginBottom": "10px",
                    "padding": "16px 8px 16px 8px"
                })
            ]),
            html.Div(itens) if itens else html.Small("Nenhum subtipo vinculado.")
        ])

        visual.append(
            html.Div([
                html.Div([
                    dbc.Button(
                        html.I(className="fas fa-chevron-down"), 
                        id={'type': 'collapse-btn-relatorio', 'index': cae_id},
                        color="link",
                        n_clicks=0,
                        style={'fontSize': '20px', 'marginRight': '10px', 'padding': '0'}
                    ),
                    html.H4([
                        # Título da Categoria e Unidades Totais
                        html.Div([
                            linha,
                            html.Span(f" (Unid. Totais: {unid_totais_min_estoque:,.0f})".replace(",", "."), style={
                                'fontSize': '18px',
                                'color': '#6c757d',
                                'marginLeft': '10px',
                                'fontWeight': 'normal'
                            })
                        ], style={'fontSize': '24px'}),

                        # Barra de Progresso e informações de estoque/demanda
                        html.Div([
                            html.Span(f"Menor Estoque: {int(round(min_dias_estoque_categoria))} dias", style={'fontSize': '16px', 'color': '#343a40'}),
                            html.Div(style={ # Container da Barra
                                "height": "14px",
                                "width": "200px",
                                "backgroundColor": "#e9ecef",
                                "borderRadius": "7px",
                                "overflow": "hidden",
                            }, children=[
                                html.Div(style={ # Barra
                                    "height": "100%",
                                    "width": f"{barra_width_categoria}%",
                                    "backgroundColor": barra_color_categoria,
                                })
                            ]),
                            html.Span(f"Demanda Mensal: {cae_consumo:,.0f}".replace(",", "."), style={'fontSize': '16px', 'color': '#343a40'})
                        ], style={
                            'display': 'flex',
                            'alignItems': 'center',
                            'gap': '15px'
                        })
                    ], style={
                        "display": "flex",
                        "justifyContent": "flex-start",
                        "gap": "50px",
                        "alignItems": "center",
                        "color": "#0d6efd",
                        "borderBottom": "2px solid #0d6efd",
                        "paddingBottom": "10px",
                        "margin": "0",
                        "flexGrow": "1"
                    })
                ], style={
                    "display": "flex",
                    "alignItems": "center",
                    "marginTop": "30px",
                    "marginBottom": "10px",
                }),
                dbc.Collapse(
                    collapsible_content,
                    id={'type': 'collapse-content-relatorio', 'index': cae_id},
                    is_open=False
                )
            ], style={"marginBottom": "20px"})
        )
 
    return html.Div(visual)
 
def create_layout():
    return dbc.Container([
        # Incluir os layouts dos formulários
        form_categoria_estoque.layout,
        form_estudo_estoque.layout,
       
        # Card de importação e cadastros
        dbc.Card([
            dbc.CardHeader("Importação e Cadastros", className="h4"),
            dbc.CardBody([
                # Linha única com upload e botões
                dbc.Row([
                    # Coluna para upload
                    dbc.Col([
                        dcc.Upload(
                            id='upload-excel',
                            children=html.Div([
                                html.I(className="fas fa-file-excel me-2"),
                                'Importar arquivo Excel'
                            ]),
                            style={
                                'width': '100%',
                                'height': '38px',
                                'lineHeight': '38px',
                                'borderWidth': '1px',
                                'borderStyle': 'dashed',
                                'borderRadius': '5px',
                                'textAlign': 'center',
                                'backgroundColor': '#f8f9fa'
                            },
                            multiple=False
                        ),
                    ], width=6),
                   
                    # Coluna para botões
                    dbc.Col([
                        dbc.ButtonGroup([
                            dbc.Button(
                                [html.I(className="fas fa-list me-2"), "Cadastro de Categorias"],
                                id="btn-cadastro-categorias",
                                color="primary",
                                outline=True,
                                size="md",
                                className="me-2"
                            ),
                            dbc.Button(
                                [html.I(className="fas fa-clipboard-list me-2"), "Cadastro de Estudos"],
                                id="btn-cadastro-estudos",
                                color="primary",
                                outline=True,
                                size="md"
                            ),
                        ], className="float-end")
                    ], width=6, className="text-end"),
                ], className="align-items-center"),
               
                # Área para feedback
                dbc.Row([
                    dbc.Col([
                        html.Div(id="output-importacao")
                    ], width=12)
                ], className="mt-3")
            ])
        ], className="mb-3"),
       
        # Botão para alternar visualização (mantido para navegação, mas só mostra agrupada)
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    # dbc.Button("Visualização Tabela", id="btn-tabela", color="secondary", outline=True, className="me-2"),
                    dbc.Button("Visualização Agrupada", id="btn-agrupada", color="primary", outline=False)
                ])
            ], width=12)
        ], className="mb-3 mt-2"),
        # Área para exibir os dados agrupados
        dbc.Card([
            dbc.CardHeader("Visualização Agrupada", className="h4"),
            dbc.CardBody([
                html.Div(id="visualizacao-agrupada", style={"display": "block"})
            ])
        ])
    ], fluid=True)
 
# Define the layout
layout = create_layout()
 
# Callback para processar upload de arquivo
@app.callback(
    [Output("output-importacao", "children"),
     Output("visualizacao-agrupada", "children"),
     Output("visualizacao-agrupada", "style")],
    [Input("upload-excel", "contents"),
     Input("btn-agrupada", "n_clicks")],
    [State("upload-excel", "filename"),
     State("visualizacao-agrupada", "children"),
     State("visualizacao-agrupada", "style")]
)
def process_upload_and_toggle(contents, n_agrupada, filename, agrupada_atual, agrupada_style):
    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    # Estado inicial: nada carregado
    if contents is None:
        if trigger == "btn-agrupada":
            # Mostrar agrupada do banco
            return "", gerar_visualizacao_banco(), {"display": "block"}
        else:
            return "", "", {"display": "block"}
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        df = pd.read_excel(io.BytesIO(decoded))
        visual_excel = gerar_visualizacao_linkada(df)
        # Sempre mostra agrupada
        return dbc.Alert("Arquivo importado com sucesso!", color="success"), visual_excel, {"display": "block"}
    except Exception as e:
        return dbc.Alert(f"Erro ao processar arquivo: {str(e)}", color="danger"), "", {"display": "block"}
 
# Callback para controlar a abertura dos modais
@app.callback(
    [Output("modal-categoria", "is_open"),
     Output("modal-estudo", "is_open")],
    [Input("btn-cadastro-categorias", "n_clicks"),
     Input("btn-cadastro-estudos", "n_clicks"),
     Input("categoria-btn-fechar", "n_clicks"),
     Input("estudo-btn-fechar", "n_clicks")],
    [State("modal-categoria", "is_open"),
     State("modal-estudo", "is_open")]
)
def toggle_modals(n1, n2, n3, n4, is_open1, is_open2):
    ctx = callback_context
    if not ctx.triggered:
        return False, False
   
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
   
    if button_id == "btn-cadastro-categorias":
        return not is_open1, False
    elif button_id == "btn-cadastro-estudos":
        return False, not is_open2
    elif button_id == "categoria-btn-fechar":
        return False, is_open2
    elif button_id == "estudo-btn-fechar":
        return is_open1, False
   
    return is_open1, is_open2

# Callback para controlar o colapso das categorias
@app.callback(
    Output({'type': 'collapse-content-relatorio', 'index': MATCH}, 'is_open'),
    [Input({'type': 'collapse-btn-relatorio', 'index': MATCH}, 'n_clicks')],
    [State({'type': 'collapse-content-relatorio', 'index': MATCH}, 'is_open')],
    prevent_initial_call=True
)
def toggle_category_collapse(n_clicks, is_open):
    return not is_open

def format_brasileiro(valor, casas=2):
        partes = f"{valor:,.{casas}f}".split(".")
        inteiro = partes[0].replace(",", ".")
        decimal = partes[1] if len(partes) > 1 else "00"
        return f"{inteiro},{decimal}"