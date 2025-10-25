from banco_dados.banco import *
import dash
from datetime import datetime, timedelta
import pandas as pd

from calculos import Filtros
import dash_bootstrap_components as dbc

from dash import Input, Output, ctx, ALL, html, dcc, callback, MATCH, State
from datetime import datetime
from app import app



def painel_chapas(filtro_os='Todas', filtro_arte='Todas', semana=None, comparacao_semana='=', categoria='Todas', chapa_selecionada=None, pagina_atual=1):
    banco = Banco()
    
    # Fazer join otimizado direto no banco para pegar todos os dados necessários de uma vez
    with Session(engine) as session:
        # Query otimizada que faz join entre chapa, pcp e produtos
        query = session.query(
            CHAPA.ch_codigo,
            CHAPA.ch_semana,
            CHAPA.ch_tamanho,
            CHAPA.ch_folhas,
            CHAPA.ch_obs,
            CHAPA.ch_st_op,
            CHAPA.ch_st_ar,
            CHAPA.ch_imagem,
            PCP.pcp_produto_id,
            PCP.pcp_qtd,
            PCP.pcp_entrega,
            PRODUTO.nome.label("produto_nome")
        ).outerjoin(PCP, CHAPA.ch_codigo == PCP.pcp_chapa_id) \
         .outerjoin(PRODUTO, PCP.pcp_produto_id == PRODUTO.produto_id)
        
        # Converter para DataFrame
        results = query.all()
        if results:
            df_completo = pd.DataFrame([{
                'ch_codigo': r.ch_codigo,
                'ch_semana': r.ch_semana,
                'ch_tamanho': r.ch_tamanho,
                'ch_folhas': r.ch_folhas,
                'ch_obs': r.ch_obs,
                'ch_st_op': r.ch_st_op,
                'ch_st_ar': r.ch_st_ar,
                'ch_imagem': r.ch_imagem,
                'pcp_produto_id': r.pcp_produto_id,
                'pcp_qtd': r.pcp_qtd,
                'pcp_entrega': r.pcp_entrega,
                'produto_nome': r.produto_nome
            } for r in results])
        else:
            df_completo = pd.DataFrame()

    if df_completo.empty:
        return html.Div("Nenhuma chapa encontrada", className="text-center mt-4")

    # Agrupar produtos por chapa para otimizar
    produtos_por_chapa = {}
    if not df_completo.empty:
        df_produtos = df_completo[df_completo['pcp_produto_id'].notna()]
        for _, row in df_produtos.iterrows():
            ch_codigo = row['ch_codigo']
            if ch_codigo not in produtos_por_chapa:
                produtos_por_chapa[ch_codigo] = []
            produtos_por_chapa[ch_codigo].append({
                'nome': row['produto_nome'],
                'qtd': row['pcp_qtd'],
                'entrega': row['pcp_entrega']
            })

    # Obter chapas únicas para filtros
    df_chapas = df_completo[['ch_codigo', 'ch_semana', 'ch_tamanho', 'ch_folhas', 'ch_obs', 'ch_st_op', 'ch_st_ar', 'ch_imagem']].drop_duplicates('ch_codigo')

    cards = []
    modals = []

    # Aplicar filtros
    df_chapas_filtrado = df_chapas.copy()
    
    if filtro_os == 'Feitas':
        df_chapas_filtrado = df_chapas_filtrado[pd.notna(df_chapas_filtrado['ch_st_op']) & (df_chapas_filtrado['ch_st_op'] != '')]
    elif filtro_os == 'Pendentes':
        df_chapas_filtrado = df_chapas_filtrado[pd.isna(df_chapas_filtrado['ch_st_op']) | (df_chapas_filtrado['ch_st_op'] == '')]
    
    if filtro_arte == 'Feitas':
        df_chapas_filtrado = df_chapas_filtrado[pd.notna(df_chapas_filtrado['ch_st_ar']) & (df_chapas_filtrado['ch_st_ar'] != '')]
    elif filtro_arte == 'Pendentes':
        df_chapas_filtrado = df_chapas_filtrado[pd.isna(df_chapas_filtrado['ch_st_ar']) | (df_chapas_filtrado['ch_st_ar'] == '')]
    
    # Filtro por chapa específica selecionada
    if chapa_selecionada:
        df_chapas_filtrado = df_chapas_filtrado[df_chapas_filtrado['ch_codigo'] == int(chapa_selecionada)]
   
    if categoria != 'Todas':
        if categoria is not None:
            if isinstance(categoria, list):
                df_chapas_filtrado = df_chapas_filtrado[df_chapas_filtrado['ch_tamanho'].isin(categoria)]
            else:
                df_chapas_filtrado = df_chapas_filtrado[df_chapas_filtrado['ch_tamanho'] == categoria]

    # Aplicar filtro de Semana
    if semana is not None and comparacao_semana:
        try:
            df_chapas_filtrado['ch_semana_num'] = pd.to_numeric(df_chapas_filtrado['ch_semana'], errors='coerce')
            df_chapas_filtrado = df_chapas_filtrado.dropna(subset=['ch_semana_num'])
            df_chapas_filtrado['ch_semana_num'] = df_chapas_filtrado['ch_semana_num'].astype(int)
            
            semana_int = int(semana)

            if comparacao_semana == '=':
                df_chapas_filtrado = df_chapas_filtrado[df_chapas_filtrado['ch_semana_num'] == semana_int]
            elif comparacao_semana == '>=':
                df_chapas_filtrado = df_chapas_filtrado[df_chapas_filtrado['ch_semana_num'] >= semana_int]
            elif comparacao_semana == '<=':
                df_chapas_filtrado = df_chapas_filtrado[df_chapas_filtrado['ch_semana_num'] <= semana_int]
            elif comparacao_semana == '>':
                df_chapas_filtrado = df_chapas_filtrado[df_chapas_filtrado['ch_semana_num'] > semana_int]
            elif comparacao_semana == '<':
                df_chapas_filtrado = df_chapas_filtrado[df_chapas_filtrado['ch_semana_num'] < semana_int]
        except (ValueError, TypeError) as e:
            print(f"Erro ao converter semana para filtro: {e}")

    # Calcular informações de paginação
    total_chapas = len(df_chapas_filtrado)
    chapas_por_pagina = 20
    total_paginas = max(1, (total_chapas + chapas_por_pagina - 1) // chapas_por_pagina)
    
    # Validar página atual
    if pagina_atual < 1:
        pagina_atual = 1
    elif pagina_atual > total_paginas:
        pagina_atual = total_paginas
    
    # Calcular índices para paginação
    inicio = (pagina_atual - 1) * chapas_por_pagina
    fim = inicio + chapas_por_pagina
    
    # Aplicar paginação
    df_chapas_paginado = df_chapas_filtrado.iloc[inicio:fim]

    # Criar cards apenas para as chapas da página atual
    for _, chapa in df_chapas_paginado.iterrows():
        ch_id = int(chapa["ch_codigo"])
        
        # Obter produtos relacionados do dicionário pré-processado
        produtos_relacionados = produtos_por_chapa.get(ch_id, [])

        # Lista de produtos otimizada
        itens_produto = []
        for produto in produtos_relacionados:
            if produto['nome']:
                itens_produto.append(
                    html.Tr([
                        html.Td(produto['nome']),
                        html.Td(f"{produto['qtd']}"),
                        html.Td(str(produto['entrega']) if produto['entrega'] else '')
                    ])
                )
                
        # Verificar se há imagem para esta chapa
        imagem_tooltip = None
        imagem_modal = None
        if pd.notna(chapa.get('ch_imagem')) and chapa['ch_imagem']:
            # Criar o tooltip com a imagem
            imagem_tooltip = dbc.Tooltip(
                html.Img(
                    src=chapa['ch_imagem'],
                    style={"maxWidth": "400px", "maxHeight": "400px"}
                ),
                target={"type": "img-icon", "index": ch_id},
                placement="top",
                delay={"show": 0, "hide": 0}
            )
            
            # Criar modal para exibir a imagem em tamanho completo
            imagem_modal = dbc.Modal(
                [
                    dbc.ModalHeader(f"Chapa {ch_id}"),
                    dbc.ModalBody(
                        html.Img(
                            src=chapa['ch_imagem'],
                            style={"width": "100%"}
                        )
                    ),
                    dbc.ModalFooter(
                        dbc.Button("Fechar", id={"type": "close-modal", "index": ch_id}, className="ml-auto")
                    ),
                ],
                id={"type": "modal-chapa", "index": ch_id},
                size="x",
                centered=True,
            )
            modals.append(imagem_modal)

        card = dbc.Card(
    dbc.CardBody([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H5(f"Chapa: {chapa['ch_codigo']}", className="card-title mb-0 me-2"),
                    dbc.Badge(
                        "OS", 
                        color="success" if pd.notna(chapa['ch_st_op']) and chapa['ch_st_op'] else "danger", 
                        className="me-1"
                    ),
                    dbc.Badge(
                        "ARTE", 
                        color="success" if pd.notna(chapa['ch_st_ar']) and chapa['ch_st_ar'] else "danger",
                        className="me-1"
                    )
                ], style={'display': 'flex', 'alignItems': 'center'})
            ], width=12),
        ], className="mb-2"),

        dbc.Row([
            dbc.Col([html.Small("Semana", className="text-muted"), html.Div(chapa["ch_semana"])], width=4),
            dbc.Col([html.Small("Tamanho", className="text-muted"), html.Div(chapa["ch_tamanho"])], width=4),
            dbc.Col([html.Small("Folhas", className="text-muted"), html.Div(chapa["ch_folhas"])], width=4),
        ], className="mb-1", style={"rowGap": "0.25rem"}),

        html.Div([
            html.Table(
                [html.Thead(html.Tr([
                    html.Th("Produto", style={"fontSize": "0.8rem"}),
                    html.Th("Qtd", style={"fontSize": "0.8rem"}),
                    html.Th("Entrega", style={"fontSize": "0.8rem"})
                ]))] + 
                [html.Tbody(itens_produto if itens_produto else html.Tr(html.Td(html.I("Nenhum produto", className="text-muted"), colSpan=3)))],
                className="table table-sm",
                style={"fontSize": "0.85rem", "marginBottom": "0"}
            )
        ], className="mb-2"),

        html.Div([
            html.Small("Observações", className="text-muted d-block"),
            html.Div(chapa["ch_obs"] if chapa["ch_obs"] else "—", style={"fontSize": "0.85rem"})
        ]),

        # Botões fixados no final
        html.Div([
            dbc.Button(
                html.I(className="fas fa-file", title='OP'),
                id={"type": "btn-status-op", "index": ch_id},
                color="success",
                className="me-2 btn-sm",
                n_clicks=0
            ),
            
            dbc.Button(
                html.I([html.I(className="far fa-image")]),
                id={"type": "btn-status-ar", "index": ch_id},
                color="danger",
                className="btn-sm me-2",
                n_clicks=0
            ),
            
            # Ícone para visualizar a imagem (apenas se houver imagem)
            html.Span(
                html.I(className="fas fa-eye", style={"cursor": "pointer", "color": "#007bff" if pd.notna(chapa.get('ch_imagem')) and chapa['ch_imagem'] else "#ccc"}),
                id={"type": "img-icon", "index": ch_id},
                style={"display": "inline-block", "marginLeft": "0px", "visibility": "visible" if pd.notna(chapa.get('ch_imagem')) and chapa['ch_imagem'] else "hidden"},
                n_clicks=0
            ),
            
            # Tooltip para mostrar a imagem
            imagem_tooltip if imagem_tooltip else html.Div(),
        ], className="mt-auto d-flex justify-content-end pt-2")

    ], className="d-flex flex-column"),  # <- ESSENCIAL: flex column
    className="shadow-sm p-2 h-100",
    style={"fontSize": "0.9rem"}
)

        cards.append(dbc.Col(card, width=3))

    # Controles de paginação
    controles_paginacao = dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button(
                    "◀ Anterior", 
                    id="btn-pagina-anterior", 
                    color="secondary", 
                    disabled=(pagina_atual <= 1),
                    size="sm"
                ),
                dbc.Button(
                    f"Página {pagina_atual} de {total_paginas}",
                    color="info",
                    disabled=True,
                    size="sm"
                ),
                dbc.Button(
                    "Próximo ▶", 
                    id="btn-pagina-proximo", 
                    color="secondary", 
                    disabled=(pagina_atual >= total_paginas),
                    size="sm"
                ),
            ], style={"display": "flex", "justify-content": "center"})
        ], width=12)
    ], className="mb-3", justify="center")

    # Informações adicionais
    info_resultados = dbc.Row([
        dbc.Col([
            html.P(
                f"Mostrando {len(df_chapas_paginado)} de {total_chapas} chapas",
                className="text-muted text-center mb-2"
            )
        ], width=12)
    ])

    layout = dbc.Container([
        info_resultados,
        controles_paginacao,
    ] + [dbc.Row(cards[i:i+4], className="gy-3 mb-3") for i in range(0, len(cards), 4)] + modals, fluid=True)

    return layout


@app.callback(
    Output({"type": "btn-status-ar", "index": ALL}, "n_clicks"),
    Input({"type": "btn-status-ar", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def atualizar_fim_chapa(n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered:
        raise dash.exceptions.PreventUpdate

    chapa_id = triggered["index"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    banco = Banco()
    banco.editar_dado("chapa", id=chapa_id, ch_st_ar=now)

    
    return [0 for _ in n_clicks_list]  # reseta cliques (opcional)


@app.callback(
    Output({"type": "btn-status-op", "index": ALL}, "n_clicks"),
    Input({"type": "btn-status-op", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def atualizar_fim_chapa(n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered:
        raise dash.exceptions.PreventUpdate

    chapa_id = triggered["index"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    banco = Banco()
    banco.editar_dado("chapa", id=chapa_id, ch_st_op=now)

    
    return [0 for _ in n_clicks_list]  # reseta cliques (opcional)

# Callback para abrir o modal quando o ícone é clicado
@app.callback(
    Output({"type": "modal-chapa", "index": MATCH}, "is_open"),
    [Input({"type": "img-icon", "index": MATCH}, "n_clicks"),
     Input({"type": "close-modal", "index": MATCH}, "n_clicks")],
    [State({"type": "modal-chapa", "index": MATCH}, "is_open")],
    prevent_initial_call=True
)
def toggle_modal(n_open, n_close, is_open):
    if n_open or n_close:
        return not is_open
    return is_open

# Callback para controlar paginação
@app.callback(
    Output('store-pagina-chapas', 'data'),
    [Input('btn-pagina-anterior', 'n_clicks'),
     Input('btn-pagina-proximo', 'n_clicks')],
    [State('store-pagina-chapas', 'data')],
    prevent_initial_call=True
)
def controlar_paginacao(n_anterior, n_proximo, pagina_data):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return pagina_data or 1
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    pagina_atual = pagina_data or 1
    
    if trigger_id == 'btn-pagina-anterior' and n_anterior:
        return max(1, pagina_atual - 1)
    elif trigger_id == 'btn-pagina-proximo' and n_proximo:
        return pagina_atual + 1
    
    return pagina_atual

# Callback para resetar página quando os filtros mudarem
@app.callback(
    Output('store-pagina-chapas', 'data', allow_duplicate=True),
    [Input('filter_chapa_os', 'value'),
     Input('filter_chapa_arte', 'value'), 
     Input('select_semana', 'value'),
     Input('categoria_filter', 'value'),
     Input('select_chapa', 'value'),
     Input('visualizacao_select', 'value')],
    prevent_initial_call=True
)
def resetar_pagina_ao_filtrar(filtro_os, filtro_arte, semana, categoria, chapa, visualizacao):
    """
    Reseta a página para 1 quando qualquer filtro for alterado
    """
    if visualizacao == 'painel_chapas':
        return 1
    return dash.no_update