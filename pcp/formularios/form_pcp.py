from dash import html, dcc, callback_context, dash_table, no_update
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
from datetime import date, datetime

import json
import pandas as pd
from app import *

#BANCO DE DADOS====================================
from banco_dados.banco import listar_pcp, juncao, juncao_ret_pcp, Banco, ORDEM_COMPRA, Session, engine, CHAPA, PRODUTO, PCP, SETOR, PRODUCAO, APONTAMENTO_PRODUTO, FACA
from pcp.pag_principal import *


# ======== LAYOUT ======= #


layout = html.Div([
    dcc.Store(id='store-programacao-pcp-data'),
    dbc.Modal([
    dbc.ModalHeader(
        dbc.Row(
            [
                dbc.Col(dbc.ModalTitle("Inclusão de Produção"), className="me-auto"),
                dbc.Col(
                    [
                        dbc.Button("Programar", id="programar_pcp", color="success", className="me-2"),
                        dbc.Button('Enviar', id="Enviar_produto", color="primary", className="me-2"),
                        dbc.Button('Excluir', id="excluir_produto", color="danger", className="me-2"),
                        dbc.Button('Baixar', id="baixar_produto_pcp", color="warning", className="me-2"),
                        dbc.Button('Retirar', id="retirar_produto", color="info"),
                    ],
                    width="auto",
                ),
            ],
            align="center",
            className="w-100"
        )
    ),
    dbc.ModalBody([
        dbc.Row([
            dbc.Col([
                html.Div(
                    [
                        html.H5('IMAGEM CHAPA', className="mb-0"),
                        dbc.Button(
                            html.I(className="fas fa-search"), 
                            id="abrir_modal_chapa",
                            size="sm",
                            color="primary",
                            className="ms-2"
                        )
                    ],
                    className="d-flex align-items-center mb-2"
                ),
                html.Div(id='div_imagem_chapa', style={
                    'border': '2px dashed #ccc', 'borderRadius': '5px', 'padding': '10px',
                    'height': '250px', 'textAlign': 'center', 'display': 'flex',
                    'justifyContent': 'center', 'alignItems': 'center', 'backgroundColor': '#f9f9f9'
                }),
                html.Br(),
                html.H5('IMAGEM FACA'),
                html.Div(id='div_imagem_faca', style={
                    'border': '2px dashed #ccc', 'borderRadius': '5px', 'padding': '10px',
                    'height': '250px', 'textAlign': 'center', 'display': 'flex',
                    'justifyContent': 'center', 'alignItems': 'center', 'backgroundColor': '#f9f9f9'
                }),
            ], sm=12, md=3, lg=3),
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("ID"),
                        dbc.Input(id="id_pcp_form", placeholder="id...", type="number", disabled=True)
                    ], sm=12, md=3),
                    dbc.Col([
                        dbc.Label("O.C."),
                        dbc.Input(id="add_oc_compra", placeholder="Apenas números, Ordem de Compra...", type="number")
                    ], sm=12, md=3),
                    dbc.Col([
                        dbc.Label("PCP"),
                        dbc.Input(id="add_pcp_codigo", placeholder="Apenas números, PCP...", type="number")
                    ], sm=12, md=3),
                    dbc.Col([
                        dbc.Label("OCORRÊNCIA"),
                        dcc.Dropdown(
                            id="add_pcp_correncia",
                            options=[
                                {"label": "Cancelado", "value": 0},
                                {"label": "Prorrogado", "value": 1},
                                {"label": "Lixo", "value": 2},
                                {"label": "Variação", "value": 3},
                            ],
                            placeholder="Ocorrencia...",
                            clearable=True,
                            className='dbc'
                        )
                    ], sm=12, md=3),
                ]),
                html.Hr(),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("CATEGORIA"),
                        dcc.Dropdown(id='add_categoria', clearable=False, className='dbc',
                        options=['CAIXA 5L', 'CAIXA 10L', 'CAIXA 7L', 'TAMPA 10L', 'TAMPA 5L', 'ESPECIAL', 'CINTA', 'PIZZA',
                                                 'POTE 500ML', 'POTE 480ML', 'POTE 240ML', 'POTE 250ML',
                                                  'POTE 1L', 'POTE 360ML', 'POTE 180ML', 'POTE 150ML',
                                                  'POTE 120ML', 'POTE 80ML', 'COPO 360ML', 'COPO 200ML', 'COPO 100ML']),
                    ], sm=12, md=6),
                    
                    dbc.Col([
                        dbc.Label("CLIENTE"),
                        dcc.Dropdown(id='add_cliente', clearable=False, className='dbc'
                        ),
                    ], sm=12, md=6),
                ]),
                html.Hr(),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("PRODUTO"),
                        dcc.Dropdown(
                            id="add_produto",
                            placeholder="Selecione um Produto...",
                            style={"backgroundColor": "#c2c2c2"}  # Fundo verde claro
                        )
                    ], sm=12, md=9),
                    dbc.Col([
                        dbc.Label("CÓD PRODUTO"),
                        dbc.Input(id="add_cod_prod", placeholder="Cód...", type="text")
                    ], sm=12, md=3),
                ]),
                html.Hr(),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("QUANTIDADE"),
                        dbc.Input(id="add_quantidade", placeholder="Quantidade da Ordem...", type="number")
                    ], sm=12, md=3),
                    
                    dbc.Col([
                        dbc.Label("DATA ENTREGA"),
                        dcc.DatePickerSingle(id="add_data_entrega", className='dbc', date=date.today(), initial_visible_month=date.today())
                    ], sm=12, md=3),
                    dbc.Col([
                        dbc.Label("CÓD CHAPA"),
                        dbc.Input(id="add_cod_chapa", placeholder="Cód chapa...", type="number")
                    ], sm=12, md=3),
                    dbc.Col([
                        dbc.Label("OPÇÕES"),
                        html.Div([
                            dbc.Checkbox(
                                id="add_tercerizacao",
                                label="Terceirização",
                                value=False
                            ),
                            html.Div(style={"height": "2px"}),  # Espaçamento reduzido
                            dbc.Checkbox(
                                id="add_bopp",
                                label="BOPP",
                                value=False
                            )
                        ])
                    ], sm=12, md=3),
                ]),
                html.Br(),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("FACA"),
                        dcc.Dropdown(id='add_faca', clearable=True, className='dbc'),
                    ])
                ]),
                html.Br(),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("OBSERVAÇÃO"),
                        dbc.Textarea(id="add_observacao", placeholder="Observação geral...", style={'height': '80%'})
                    ]),
                ]),
            ], sm=12, md=4, lg=4 ),  # Coluna esquerda
            dbc.Col([
                dbc.Tabs([
                    dbc.Tab(
                        label="Finalização Produção",
                        tab_id="finalizacao",
                        children=[
                            html.H5("MOVIMENTAÇÃO FINALIZAÇÃO PRODUÇÃO"),
                            html.H5(id='div_tab_mov')
                        ]
                    ),
                    dbc.Tab(
                        label="Retirada",
                        tab_id="retirada",
                        children=[
                            html.H5("MOVIMENTAÇÃO RETIRADA"),
                            html.H5(id='div_tab_ret')
                        ]
                    ),
                    dbc.Tab(
                        label="Ordens de Compra",
                        id="tab-ordens-compra",
                        tab_id="ordem_compra",
                        children=[
                            html.H5("ORDENS DE COMPRA VINCULADAS", className="mt-3"),
                            html.Div(id='div_tab_ordem_compra')
                        ]
                    ),
                    dbc.Tab(
                        label="Apontamentos",
                        id="tab-apontamentos",
                        tab_id="apontamentos",
                        children=[
                            html.H5("APONTAMENTOS DE PRODUÇÃO", className="mt-3"),
                            html.Div(id='div_tab_apontamentos_pcp')
                        ]
                    ),
                ],
                id="tabs-movimentacao",
                active_tab="finalizacao",
                ),
            ], sm=12, md=5, lg=5 ),
            
        ]),
        html.Br(),
        html.H5(id='div_erro2'),
        
        # Modal para chapa
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Imagem da Chapa")),
                dbc.ModalBody(html.Img(id="chapa-modal-img", style={"width": "100%"})),
                dbc.ModalFooter(dbc.Button("Fechar", id="close-chapa-modal", className="ml-auto")),
            ],
            id="chapa-modal",
            size="xl",
            is_open=False,
        ),

        # Modal para faca
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Imagem da Faca")),
                dbc.ModalBody(html.Img(id="faca-modal-img", style={"width": "100%"})),
                dbc.ModalFooter(dbc.Button("Fechar", id="close-faca-modal", className="ml-auto")),
            ],
            id="faca-modal",
            size="xl",
            is_open=False,
        ),
    ]),
], id='modal_inclusao_produto', is_open=False, className='custom-modal', size="xl"),
])


@app.callback(
    Output('modal_inclusao_produto', 'is_open'),
    Output('store_intermedio', 'data'),
    Output("add_produto", "options"),
    Output("add_cliente", "options"),
    Output("add_faca", "options"),
    Output("add_cod_chapa", "value"),

    Input({'type': 'editar_producao', 'index': ALL}, 'n_clicks'),
    Input('adicionar_producao', 'n_clicks'),
    Input('tabela_pcp_cal', 'selected_cells'),
    Input('tabela_pcp_cal', 'page_current'),
    
    State('modal_inclusao_produto', 'is_open'),
    State('store_pcp', 'data'),
    State('store_intermedio', 'data'),
    Input('tabela_pcp_cal', 'data'),
    prevent_initial_call=True
)
def abrir_modal_producao(n_editar, n_new, selected_cells, page_current, is_open, store_pcp, store_intermedio, tabela_data):
    # Verifique se 'selected_cells' é None
    banco = Banco()
    df_produtos = banco.ler_tabela("produtos")
    df_clientes = banco.ler_tabela("clientes")
    df_facas = banco.ler_tabela("faca")
    list_produtos = [{"label": row["nome"], "value": row["produto_id"]} for _, row in df_produtos.iterrows()]
    lista_clientes = [{"label": row["nome"], "value": row["cliente_id"]} for _, row in df_clientes.iterrows()]
    lista_facas = [{"label": f"{row['fac_cod']} - {row['fac_descricao']} - {row['fac_medida']}", "value": row["fac_id"]} for _, row in df_facas.iterrows()]

    if not selected_cells:
        selected_cells = []

    if page_current is None:
        page_current = 0 
        
    df_pcp = listar_pcp()  # Lista os dados atualizados
    store_pcp = df_pcp.to_dict('records') # Usar 'records' para uma lista de dicionários, é mais robusto
    trigg_id = callback_context.triggered[0]['prop_id'].split('.')[0]
    first_call = True if callback_context.triggered[0]['value'] is None else False

    if first_call:
        return is_open, [], list_produtos, lista_clientes, lista_facas, None

    if (trigg_id == 'adicionar_producao') or (trigg_id == 'cancel_button_novo_processo'):
        return not is_open, [], list_produtos, lista_clientes, lista_facas, None

    if n_editar:
        trigg_dict = json.loads(callback_context.triggered[0]['prop_id'].split('.')[0])
        numero_op = trigg_dict['index']

        df_pcp = pd.DataFrame(store_pcp)
     
        linha_pcp = df_pcp.loc[df_pcp['pcp_pcp'] == numero_op]
        if not linha_pcp.empty:
            chapa_id = linha_pcp.iloc[0]['pcp_chapa_id']
            store_intermedio = linha_pcp.to_dict('records')
        else:
            chapa_id = None
            store_intermedio = []

        return not is_open, store_intermedio, list_produtos, lista_clientes, lista_facas, chapa_id

    if selected_cells:
        row_index = selected_cells[0]['row']
        page_size = 40
        row_index_global = page_current * page_size + row_index
        df = pd.DataFrame(tabela_data)
        
        pcp_id = df.iloc[row_index_global]['pcp_id']

        df_pcp = pd.DataFrame(store_pcp)
        linha_pcp = df_pcp.loc[df_pcp['pcp_id'] == pcp_id]

        if not linha_pcp.empty:
            chapa_id = linha_pcp.iloc[0]['pcp_chapa_id']
            store_intermedio = linha_pcp.to_dict('records')
        else:
            chapa_id = None
            store_intermedio = []

        return not is_open, store_intermedio, list_produtos, lista_clientes, lista_facas, chapa_id
    
    return is_open, store_intermedio, list_produtos, lista_clientes, lista_facas, None
    
@app.callback(
    [
        Output('store_pcp', 'data'),
        Output('div_tab_mov', 'children'),
        Output('div_tab_ret', 'children'),
        Output('div_tab_ordem_compra', 'children'),
        Output('div_tab_apontamentos_pcp', 'children'),
        Output('div_erro2', 'children'),
        
        Output('div_erro2', 'style'),
        Output('tab-ordens-compra', 'label'),
        Output('tab-apontamentos', 'label'),
        Output('id_pcp_form', 'value'),
        Output('add_oc_compra', 'value'),
        Output('add_pcp_codigo', 'value'),
        Output('add_categoria', 'value'),
        Output('add_cliente', 'value'),
        Output('add_produto', 'value'),
        Output('add_quantidade', 'value'),
        Output('add_data_entrega', 'date'),
        Output('add_observacao', 'value'),
        Output('add_cod_prod', 'value'),
        Output('add_cod_chapa', 'value', allow_duplicate=True),
        Output('add_pcp_correncia', 'value'),
        Output('add_tercerizacao', 'value'),
        Output('add_bopp', 'value'),
        Output('add_produto', 'disabled'),
        Output('add_faca', 'value')
    ],
    [
        Input('Enviar_produto', 'n_clicks'),
        Input({'type': 'deletar_producao', 'index': ALL}, 'n_clicks'),
        Input('excluir_produto', 'n_clicks'),
        
        Input('store_intermedio', 'data')
    ],
    [
        State('store_pcp', 'data'),
        State('id_pcp_form', 'value'),
        State('add_oc_compra', 'value'),
        State('add_pcp_codigo', 'value'),
        State('add_categoria', 'value'),
        State('add_cliente', 'value'),
        State('add_produto', 'value'),
        State('add_quantidade', 'value'),
        State('add_data_entrega', 'date'),
        State('add_observacao', 'value'),
        State('add_cod_prod', 'value'),
        State('add_cod_chapa', 'value'),
        State('add_pcp_correncia', 'value'),
        State('add_tercerizacao', 'value'),
        State('add_bopp', 'value'),
        State('add_faca', 'value')
    ],
    prevent_initial_call=True
)
def nova_producao(n, delet, btn_delet, store_int, dataset,
                   id_pcp, oc, pcp, categoria, cliente, produto, qtd, data, obs, mat, chapa, ocorrencia, terceirizacao, bopp, faca_id):
    banco = Banco()
    if oc == None:
        oc = '001'
   
    # Converter valores booleanos para inteiros (0 ou 1)
    terceirizacao_valor = 1 if terceirizacao == True else 0
    bopp_valor = 1 if bopp == True else 0

    first_call = True if (callback_context.triggered[0]['value'] == None or callback_context.triggered[0]['value'] == False) else False
    trigg_id = callback_context.triggered[0]['prop_id'].split('.')[0]

    # Default labels for tabs
    label_oc = "Ordens de Compra"
    label_apontamentos = "Apontamentos"

    if first_call:
        # Retorna valores vazios ou padrão
        return dataset,[], [], [], [], [], {'margin-bottom': '15px', 'color': 'red'}, label_oc, label_apontamentos, id_pcp, oc, pcp, categoria, cliente, produto, qtd, data, obs, mat,chapa, ocorrencia, terceirizacao, bopp, False, False, False, None

    if trigg_id == 'Enviar_produto':
        df_pcp = pd.DataFrame(dataset)
        df_int = pd.DataFrame(store_int)

        if len(df_int.index) == 0:  # Novo processo
           
            if None in [categoria]:
                return dataset,[],[], [], [], [], {'margin-bottom': '15px', 'color': 'red'}, label_oc, label_apontamentos,id_pcp, oc, pcp, categoria, cliente, produto, qtd, data, obs, mat,chapa, ocorrencia, terceirizacao, bopp, False, faca_id
            if None in [cliente]:
                return dataset,[],[], [], [], [], {'margin-bottom': '15px', 'color': 'red'}, label_oc, label_apontamentos,id_pcp, oc, pcp, categoria, cliente, produto, qtd, data, obs, mat,chapa, ocorrencia, terceirizacao, bopp, False, faca_id
            if None in [produto]:
                return dataset,[],[], [], [], [], {'margin-bottom': '15px', 'color': 'red'}, label_oc, label_apontamentos,id_pcp, oc, pcp, categoria, cliente, produto, qtd, data, obs, mat, chapa, ocorrencia, terceirizacao, bopp, False, faca_id
            if None in [qtd]:
                return dataset,[],[], [], [], [], {'margin-bottom': '15px', 'color': 'red'}, label_oc, label_apontamentos,id_pcp, oc, pcp, categoria, cliente, produto, qtd, data, obs, mat, chapa, ocorrencia, terceirizacao, bopp, False, faca_id
            if None in [data]:
                return dataset,[],[], [], [], [], {'margin-bottom': '15px', 'color': 'red'}, label_oc, label_apontamentos,id_pcp, oc, pcp, categoria, cliente, produto, qtd, data, obs, mat, chapa, ocorrencia, terceirizacao, bopp, False, faca_id
            
            try:
                data = datetime.strptime(data, '%Y-%m-%d').date() if isinstance(data, str) else data
                
                banco.inserir_dados('pcp', pcp_oc=oc, pcp_pcp=pcp,pcp_categoria=categoria, pcp_cliente_id=cliente,
                               pcp_produto_id=produto, pcp_qtd=qtd, pcp_entrega=data,pcp_primiera_entrega=data,
                                 pcp_cod_prod=mat, pcp_chapa_id=chapa, pcp_emissao=date.today(), pcp_observacao=obs,
                                   pcp_correncia=ocorrencia, pcp_bopp=bopp_valor, pcp_terceirizacao=terceirizacao_valor, pcp_faca_id=faca_id)
                
                return dataset,[],[], [], [], [], {'margin-bottom': '15px', 'color': 'green'}, label_oc, label_apontamentos,None, None, None, None, None, None, None, None, None,None, None, None, False, False, False, None
        
            except ValueError as ve:

                return dataset,[],[], [], [], [], {'margin-bottom': '15px', 'color': 'red'}, label_oc, label_apontamentos,None, None, None, None, None, None, None, None, None, None,None, None, False, False, False, None
            

        else:  # Edição de processo
            
            data = datetime.strptime(data, '%Y-%m-%d').date() if isinstance(data, str) else data
    
            banco.editar_dado('pcp', id_pcp, pcp_oc=oc, pcp_pcp=pcp,pcp_categoria=categoria, pcp_cliente_id=cliente,
                               pcp_produto_id=produto, pcp_qtd=qtd, pcp_entrega=data, pcp_cod_prod=mat, pcp_chapa_id=chapa,
                               pcp_observacao=obs, pcp_correncia=ocorrencia,  pcp_bopp=bopp_valor, pcp_terceirizacao=terceirizacao_valor, pcp_faca_id=faca_id)
                        
            # Convertendo de volta para dicionário para armazenar no `store_pcp`
            store_pcp = df_pcp.to_dict()
            oc = pcp = categoria = cliente = produto = qtd = data = obs = mat = imp = aca = id_pcp = None
 
            return store_pcp,[],[], [], [],['Processo editado com sucesso!'], {'margin-bottom': '15px', 'color': 'green'}, label_oc, label_apontamentos, id_pcp, oc, pcp, categoria, cliente, produto, qtd, data, obs, mat,chapa, ocorrencia, terceirizacao, bopp, False, None

    if 'deletar_producao' in trigg_id:

        trigg_id_dict = json.loads(trigg_id)
        numero_op = trigg_id_dict['index']
        
        #deletar_pcp_por_pcp_pcp(numero_op)

        return dataset,[], [], [], [], [], {}, label_oc, label_apontamentos,None, None, None, None, None, None, None, None, None,None, None, None, False, False, False, None
  
    if trigg_id == 'excluir_produto':


        #banco.deletar_dado('pcp', id_pcp)

        return dataset,[], [], [], [], [], {}, label_oc, label_apontamentos,None, None, None, None, None, None, None, None, None,None, None, None, False, False, False, None

    if trigg_id == 'store_intermedio':
        try:

            df = pd.DataFrame(callback_context.triggered[0]['value'])
 
            valores = df.head(1).values.tolist()[0]

            id_pcp, oc, pcp, categoria, cliente, id_produto, qtd, data, odc, obs, primeira_entrega, emissao, mat, aca, imp, chapa, ocorrencia, terceirizacao, bopp,faca_id, nome_cliente, disabled = valores[:22]
            
            # Converter valores numéricos para booleanos na interface
            terceirizacao_bool = True if terceirizacao == 1 else False
            bopp_bool = True if bopp == 1 else False
            
            df_movi = juncao()
            df_movi = df_movi[df_movi['pcp_id'] == id_pcp]
            df_movi = df_movi[['data', 'qtd', 'Observação']]
            df_movi = renderizar_dataframe(df_movi)

            df_ret = juncao_ret_pcp()
            df_ret = df_ret[df_ret['pcp_id'] == id_pcp]
            df_ret = df_ret[['data_retirada', 'qtd_retirada', 'observacao']]
            df_ret = renderizar_dataframe_retirada(df_ret)

            # Buscar ordens de compra vinculadas ao PCP
            df_oc = juncao_ordem_compra_pcp()
            df_oc = df_oc[df_oc['pcp_id'] == id_pcp]
            df_oc_renderizada = renderizar_dataframe_ordem_compra(df_oc)
            
            if not df_oc.empty:
                label_oc = "✓ Ordens de Compra"

            df_apontamentos = juncao_apontamentos_pcp(id_pcp)
            df_apontamentos_renderizada = renderizar_dataframe_apontamentos(df_apontamentos)

            if not df_apontamentos.empty:
                label_apontamentos = "✓ Apontamentos"

            if faca_id == None:
                faca_id = 0
            return dataset, df_movi, df_ret, df_oc_renderizada, df_apontamentos_renderizada, [], {}, label_oc, label_apontamentos, id_pcp, oc, pcp, categoria, cliente, int(id_produto), qtd, data, obs, mat, chapa, ocorrencia,bopp_bool, terceirizacao_bool, False, int(faca_id)

        except Exception as e:

            return dataset,[], [], [], [], [], {}, label_oc, label_apontamentos, None, None, None, None, None, None, None, None, None, None,None, None, False, False, False, None
        
def renderizar_dataframe(df):
    # Formatar a coluna 'data' para o formato 'DD/MM/YYYY'
    df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
    
    # Estilo para a tabela e cabeçalho
    table_style = {
        'width': '100%',  # Tabela ocupa todo o container
        'borderCollapse': 'collapse',
        'border': '1px solid #ddd',  # Borda leve para cada célula
    }
    
    # Estilo para o contêiner com scroll
    container_style = {
        'maxHeight': '500px',  # Altura máxima
        'overflowY': 'auto',   # Scroll vertical
        'overflowX': 'hidden', # Sem scroll horizontal
        'border': '1px solid #ddd',
        'borderRadius': '5px'
    }
    
    header_style = {
        'backgroundColor': '#4CAF50',  # Cor de fundo do cabeçalho
        'color': 'white',  # Cor do texto no cabeçalho
        'fontWeight': 'bold',
        'textAlign': 'center',  # Centralizar o texto
        'padding': '8px',  # Espaçamento nas células do cabeçalho
        'position': 'sticky',  # Cabeçalho fixo
        'top': '0',            # Fixa no topo
        'zIndex': '10'         # Fica por cima do conteúdo
    }

    row_style = {
        'textAlign': 'center',
        'padding': '8px',
    }

    # Estilo para a linha de total
    total_row_style = {
        'backgroundColor': '#FFEB3B',  # Cor de fundo amarela
        'fontWeight': 'bold',  # Deixa o texto em negrito
        'textAlign': 'center',
        'padding': '8px',
        'position': 'sticky',  # Total fixo no final
        'bottom': '0',         # Fixa na parte inferior
        'zIndex': '10'         # Fica por cima do conteúdo
    }

    # Calcula a soma da coluna 'qtd'
    total_qtd = df['qtd'].sum()

    # Cria a tabela com as linhas dos dados e a linha com a soma
    return html.Div([
        html.Table([
            html.Thead(
                html.Tr([html.Th(col, style=header_style) for col in df.columns])
            ),
            html.Tbody([
                html.Tr([  # Linhas de dados
                    html.Td(df.iloc[i][col], style=row_style) for col in df.columns
                ]) for i in range(len(df))
            ] + [
                html.Tr([  # Linha de soma com fundo amarelo
                    html.Td("Total", style=total_row_style),  # Coluna "Total"
                    html.Td(f"{int(total_qtd)}", style=total_row_style),  # Soma da coluna 'qtd'
                    html.Td("", style=total_row_style),  # Deixa as outras células vazias
                ])
            ]),
        ], style=table_style)
    ], style=container_style)

def renderizar_dataframe_retirada(df):
    # Formatar a coluna 'data' para o formato 'DD/MM/YYYY'
    df['data_retirada'] = pd.to_datetime(df['data_retirada']).dt.strftime('%d/%m/%Y')
    
    # Estilo para a tabela e cabeçalho
    table_style = {
        'width': '100%',  # Tabela ocupa todo o container
        'borderCollapse': 'collapse',
        'border': '1px solid #ddd',  # Borda leve para cada célula
    }
    
    # Estilo para o contêiner com scroll
    container_style = {
        'maxHeight': '500px',  # Altura máxima
        'overflowY': 'auto',   # Scroll vertical
        'overflowX': 'hidden', # Sem scroll horizontal
        'border': '1px solid #ddd',
        'borderRadius': '5px'
    }
    
    header_style = {
        'backgroundColor': '#4CAF50',  # Cor de fundo do cabeçalho
        'color': 'white',  # Cor do texto no cabeçalho
        'fontWeight': 'bold',
        'textAlign': 'center',  # Centralizar o texto
        'padding': '8px',  # Espaçamento nas células do cabeçalho
        'position': 'sticky',  # Cabeçalho fixo
        'top': '0',            # Fixa no topo
        'zIndex': '10'         # Fica por cima do conteúdo
    }

    row_style = {
        'textAlign': 'center',
        'padding': '8px',
    }

    # Estilo para a linha de total
    total_row_style = {
        'backgroundColor': '#FFEB3B',  # Cor de fundo amarela
        'fontWeight': 'bold',  # Deixa o texto em negrito
        'textAlign': 'center',
        'padding': '8px',
        'position': 'sticky',  # Total fixo no final
        'bottom': '0',         # Fixa na parte inferior
        'zIndex': '10'         # Fica por cima do conteúdo
    }

    # Calcula a soma da coluna 'qtd'
    total_qtd = df['qtd_retirada'].sum()

    # Cria a tabela com as linhas dos dados e a linha com a soma
    return html.Div([
        html.Table([
            html.Thead(
                html.Tr([html.Th(col, style=header_style) for col in df.columns])
            ),
            html.Tbody([
                html.Tr([  # Linhas de dados
                    html.Td(df.iloc[i][col], style=row_style) for col in df.columns
                ]) for i in range(len(df))
            ] + [
                html.Tr([  # Linha de soma com fundo amarelo
                    html.Td("Total", style=total_row_style),  # Coluna "Total"
                    html.Td(f"{int(total_qtd)}", style=total_row_style),  # Soma da coluna 'qtd'
                    html.Td("", style=total_row_style),  # Deixa as outras células vazias
                ])
            ]),
        ], style=table_style)
    ], style=container_style)

def renderizar_dataframe_ordem_compra(df):
    """
    Renderiza a tabela de ordens de compra vinculadas ao PCP
    """
    if df.empty:
        return html.Div("Nenhuma ordem de compra vinculada a este PCP", 
                       style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})
    
    # Formatar a coluna 'data_entrega' para o formato 'DD/MM/YYYY'
    if 'data_entrega' in df.columns:
        df['data_entrega'] = pd.to_datetime(df['data_entrega'], errors='coerce').dt.strftime('%d/%m/%Y')
        df['data_entrega'] = df['data_entrega'].fillna('')  # Substituir NaT por string vazia
    
    # Renomear colunas para exibição
    df_display = df.copy()
    df_display = df_display.rename(columns={
        'nome_solicitacao': 'Produto',
        'qtd_solicitada': 'Qtd',
        'unid_compra': 'Unidade',  # Nova coluna adicionada
        'data_entrega': 'Data Entrega',
        'status': 'Status',
        'nota': 'Nota Fiscal'
    })
    
    # Estilo para a tabela e cabeçalho
    table_style = {
        'width': '100%',
        'borderCollapse': 'collapse',
        'border': '1px solid #ddd',
    }
    
    # Estilo para o contêiner com scroll
    container_style = {
        'maxHeight': '500px',  # Altura máxima
        'overflowY': 'auto',   # Scroll vertical
        'overflowX': 'hidden', # Sem scroll horizontal
        'border': '1px solid #ddd',
        'borderRadius': '5px'
    }
    
    header_style = {
        'backgroundColor': '#2E86C1',  # Azul para diferenciar das outras tabelas
        'color': 'white',
        'fontWeight': 'bold',
        'textAlign': 'center',
        'padding': '8px',
        'position': 'sticky',  # Cabeçalho fixo
        'top': '0',            # Fixa no topo
        'zIndex': '10'         # Fica por cima do conteúdo
    }

    row_style = {
        'textAlign': 'center',
        'padding': '8px',
        'border': '1px solid #ddd',
    }

    # Estilo para linhas com status diferentes
    def get_row_style(status):
        base_style = row_style.copy()
        if status == 'Entregue Total':
            base_style['backgroundColor'] = 'rgba(0, 255, 0, 0.1)'  # Verde claro
        elif status in ['Pendente', 'Em Andamento']:
            base_style['backgroundColor'] = 'rgba(255, 255, 0, 0.1)'  # Amarelo claro
        return base_style

    # Colunas para exibição (excluindo pcp_id)
    columns_to_show = [col for col in df_display.columns if col != 'pcp_id']

    return html.Div([
        html.Table([
            html.Thead(
                html.Tr([html.Th(col, style=header_style) for col in columns_to_show])
            ),
            html.Tbody([
                html.Tr([
                    html.Td(df_display.iloc[i][col], 
                           style=get_row_style(df_display.iloc[i].get('Status', ''))) 
                    for col in columns_to_show
                ]) for i in range(len(df_display))
            ]),
        ], style=table_style)
    ], style=container_style)

def juncao_ordem_compra_pcp():
    """
    Busca ordens de compra vinculadas aos PCPs
    """
    with Session(engine) as session:
        try:
            # Consulta que busca as ordens de compra vinculadas ao PCP
            query = session.query(
                ORDEM_COMPRA.oc_pcp_id.label("pcp_id"),
                ORDEM_COMPRA.oc_nome_solicitacao.label("nome_solicitacao"),
                ORDEM_COMPRA.oc_qtd_solicitada.label("qtd_solicitada"),
                ORDEM_COMPRA.oc_unid_compra.label("unid_compra"),
                ORDEM_COMPRA.oc_data_entrega.label("data_entrega"),
                ORDEM_COMPRA.oc_status.label("status"),
                ORDEM_COMPRA.oc_nota.label("nota")
            ).filter(ORDEM_COMPRA.oc_pcp_id.isnot(None))

            # Converter os resultados em uma lista de dicionários
            results = query.all()
            data = [row._asdict() for row in results]

            # Criar um DataFrame do pandas
            df = pd.DataFrame(data)
            return df
        
        except Exception as e:
            print(f'Erro na consulta de ordens de compra: {e}')
            return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro

def juncao_apontamentos_pcp(pcp_id):
    """
    Busca apontamentos de produção vinculados a um PCP específico.
    """
    with Session(engine) as session:
        try:
            # Query básica com todas as colunas que podem existir
            query = session.query(
                SETOR.setor_nome,
                APONTAMENTO_PRODUTO.atp_qtd,
                PRODUCAO.pr_data,
                PRODUCAO.pr_inicio,
                APONTAMENTO_PRODUTO.atp_plano
            ).join(PRODUCAO, APONTAMENTO_PRODUTO.atp_producao == PRODUCAO.pr_id)\
             .join(SETOR, PRODUCAO.pr_setor_id == SETOR.setor_id)\
             .filter(APONTAMENTO_PRODUTO.atp_pcp == pcp_id)
            
            # Tentar adicionar colunas opcionais usando try/except
            from sqlalchemy import literal
            
            try:
                query = query.add_columns(APONTAMENTO_PRODUTO.atp_refugos)
            except:
                query = query.add_columns(literal(0).label('atp_refugos'))
                
            try:
                query = query.add_columns(APONTAMENTO_PRODUTO.atp_obs)
            except:
                query = query.add_columns(literal('').label('atp_obs'))
                
            try:
                query = query.add_columns(APONTAMENTO_PRODUTO.atp_custo)
            except:
                query = query.add_columns(literal(0.0).label('atp_custo'))
            
            results = query.all()
            if not results:
                return pd.DataFrame(columns=['setor_nome', 'atp_qtd', 'pr_data', 'pr_inicio', 'atp_plano', 'atp_refugos', 'atp_obs', 'atp_custo'])
                
            # Converter para DataFrame
            df = pd.DataFrame(results)
            
            # Renomear colunas para manter consistência
            column_names = ['setor_nome', 'atp_qtd', 'pr_data', 'pr_inicio', 'atp_plano', 'atp_refugos', 'atp_obs', 'atp_custo']
            df.columns = column_names
            
            return df
            
        except Exception as e:
            print(f'Erro na consulta de apontamentos de produção: {e}')
            return pd.DataFrame()

def renderizar_dataframe_apontamentos(df):
    """
    Renderiza a tabela de apontamentos de produção, com quebra por plano.
    """
    if df.empty:
        return html.Div("Nenhum apontamento de produção para este PCP.", 
                       style={'textAlign': 'center', 'padding': '20px', 'color': '#666'})
    
    # Preencher valores nulos para evitar erros
    df['atp_refugos'] = df['atp_refugos'].fillna(0)
    df['atp_custo'] = df['atp_custo'].fillna(0.0)
    df['atp_obs'] = df['atp_obs'].fillna('')
    df['atp_plano'] = df['atp_plano'].fillna('Não Especificado')
    
    # Inferir os tipos de dados para evitar FutureWarnings de downcasting
    if not df.empty:
        df = df.infer_objects(copy=False)
    
    # Mapear valores de plano para texto
    plano_map = {0: 'Tampa', 1: 'Fundo', 2: 'Berço/Envelope', 3: 'Lâmina'}
    df['Plano'] = df['atp_plano'].map(plano_map).fillna('Não Especificado')

    # Agrupar por setor e plano
    df_grouped = df.groupby(['setor_nome', 'Plano']).agg({
        'atp_qtd': 'sum',
        'atp_refugos': 'sum',
        'atp_custo': 'sum',
        'atp_obs': lambda x: ' | '.join(filter(None, x.unique())),
        'pr_data': 'last',
        'pr_inicio': 'last'
    }).reset_index()

    # Formatar data/hora
    df_grouped['Data/Hora'] = df_grouped.apply(
        lambda row: f"{pd.to_datetime(row['pr_data']).strftime('%d/%m/%Y')} {row['pr_inicio'].strftime('%H:%M')}" 
        if pd.notna(row['pr_inicio']) else pd.to_datetime(row['pr_data']).strftime('%d/%m/%Y'), 
        axis=1
    )

    df_display = df_grouped.rename(columns={
        'setor_nome': 'Setor',
        'atp_qtd': 'Qtd Total',
        'atp_refugos': 'Refugos Total',
        'atp_custo': 'Custo Total',
        'atp_obs': 'Observações',
    })
    
    # Formatar valores numéricos
    df_display['Qtd Total'] = df_display['Qtd Total'].astype(int)
    df_display['Refugos Total'] = df_display['Refugos Total'].astype(int)
    df_display['Custo Total'] = df_display['Custo Total'].round(2)
    
    # Estilos
    table_style = {'width': '100%', 'borderCollapse': 'collapse', 'border': '1px solid #ddd', 'marginBottom': '20px'}
    container_style = {'maxHeight': '500px', 'overflowY': 'auto'}
    header_style = {'backgroundColor': '#6c757d', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center', 'padding': '8px', 'position': 'sticky', 'top': '0', 'zIndex': '10'}
    row_style = {'textAlign': 'center', 'padding': '8px', 'border': '1px solid #ddd', 'verticalAlign': 'middle'}
    
    # Criar uma tabela para cada plano
    planos_unicos = df_display['Plano'].unique()
    tables = []
    
    for plano in planos_unicos:
        df_plano = df_display[df_display['Plano'] == plano]
        
        # Colunas para exibir (excluindo 'Plano' já que está no título)
        columns_to_show = ['Setor', 'Qtd Total', 'Refugos Total', 'Custo Total', 'Observações', 'Data/Hora']
        
        tables.append(html.H5(f"Plano: {plano}", style={'marginTop': '20px', 'marginBottom': '10px'}))
        tables.append(html.Table([
            html.Thead(html.Tr([html.Th(col, style=header_style) for col in columns_to_show])),
            html.Tbody([
                html.Tr([
                    html.Td(df_plano.iloc[i][col], style=row_style) for col in columns_to_show
                ]) for i in range(len(df_plano))
            ])
        ], style=table_style))

    return html.Div(tables, style=container_style)

@app.callback(
    Output('div_imagem_chapa', 'children'),
    [Input('add_cod_chapa', 'value')],
    prevent_initial_call=True
)
def gerar_imagem_chapa(chapa_id):
    placeholder_style = {'color': '#888', 'fontStyle': 'italic'}
    
    if not chapa_id:
        return html.Span("Selecione uma chapa para ver a imagem.", style=placeholder_style)

    with Session(engine) as session:
        chapa = session.query(CHAPA).filter(CHAPA.ch_codigo == chapa_id).first()
        
        if not chapa:
            return html.Span("Chapa não encontrada.", style=placeholder_style)

        if chapa.ch_imagem:
            return html.Img(
                id='chapa-img-thumbnail', 
                src=chapa.ch_imagem, 
                style={'maxWidth': '100%', 'maxHeight': '100%', 'objectFit': 'contain', 'cursor': 'pointer'}
            )
        else:
            return html.Span("Sem imagem para esta chapa.", style=placeholder_style)

@app.callback(
    Output('div_imagem_faca', 'children'),
    [Input('add_faca', 'value')],
    prevent_initial_call=True
)
def gerar_imagem_faca(faca_id):
    placeholder_style = {'color': '#888', 'fontStyle': 'italic'}

    if not faca_id:
        return html.Span("Selecione uma faca para ver a imagem.", style=placeholder_style)

    with Session(engine) as session:
        faca = session.query(FACA).filter(FACA.fac_id == faca_id).first()
        
        if not faca:
            return html.Span("Faca não encontrada.", style=placeholder_style)

        if faca.fac_imagem:
            return html.Img(
                id='faca-img-thumbnail', 
                src=faca.fac_imagem, 
                style={'maxWidth': '100%', 'maxHeight': '100%', 'objectFit': 'contain', 'cursor': 'pointer'}
            )
        else:
            return html.Span("Sem imagem para esta faca.", style=placeholder_style)

@app.callback(
    [Output("chapa-modal", "is_open"), Output("chapa-modal-img", "src")],
    [Input("chapa-img-thumbnail", "n_clicks"), Input("close-chapa-modal", "n_clicks")],
    [State("chapa-modal", "is_open"), State("chapa-img-thumbnail", "src")],
    prevent_initial_call=True,
)
def toggle_chapa_modal(n_img, n_close, is_open, src):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "chapa-img-thumbnail" and n_img:
        return True, src
    
    if trigger_id == "close-chapa-modal":
        return False, no_update
    
    return is_open, no_update

@app.callback(
    [Output("faca-modal", "is_open"), Output("faca-modal-img", "src")],
    [Input("faca-img-thumbnail", "n_clicks"), Input("close-faca-modal", "n_clicks")],
    [State("faca-modal", "is_open"), State("faca-img-thumbnail", "src")],
    prevent_initial_call=True,
)
def toggle_faca_modal(n_img, n_close, is_open, src):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "faca-img-thumbnail" and n_img:
        return True, src
    
    if trigger_id == "close-faca-modal":
        return False, no_update

    return is_open, no_update

@app.callback(
    Output('store-programacao-pcp-data', 'data', allow_duplicate=True),
    Output('div_erro2', 'children', allow_duplicate=True),
    Output('div_erro2', 'style', allow_duplicate=True),
    Input('programar_pcp', 'n_clicks'),
    [State('id_pcp_form', 'value'),
     State('add_quantidade', 'value')],
    prevent_initial_call=True
)
def programar_pcp(n_clicks, pcp_id, pcp_qtd):
    if not n_clicks:
        raise PreventUpdate

    style = {'margin-bottom': '15px', 'color': 'red'}
    
    if not pcp_id:
        msg = "Para programar, a Ordem de Produção precisa ser salva primeiro. Clique em 'Enviar'."
        return no_update, msg, style
        
    if pcp_qtd is None:
        msg = "O campo 'Quantidade' precisa ser preenchido para programar."
        return no_update, msg, style

    if pcp_id and pcp_qtd is not None:
        return {'pcp_id': pcp_id, 'pcp_qtd': pcp_qtd}, "", {}

    raise PreventUpdate