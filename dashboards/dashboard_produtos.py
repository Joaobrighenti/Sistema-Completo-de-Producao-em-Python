from dash import html, dcc, Input, Output, State, callback_context, ALL, no_update
import dash_bootstrap_components as dbc
import pandas as pd
from banco_dados.banco import Banco
from app import app
from dash import dash_table
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from banco_dados.banco import PCP, PRODUTO, CLIENTE, BAIXA, engine
from dashboards.pages.integracoes import layout as integracoes_layout
from dashboards.formulario.form_crud_notas import layout as crud_saidas_layout
from dashboards.zerar_estoque import layout_zerar_estoque

# Layout do dashboard de produtos
layout = dbc.Container([
    # Cartão de filtros compacto
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                # Coluna esquerda: Filtros
                dbc.Col([
                    # Primeira linha: Produto e Cliente
                    dbc.Row([
                        dbc.Col([
                            html.Label("Produto:", className="small fw-bold"),
                            dcc.Dropdown(
                                id='filtro-produto',
                                placeholder="Selecione o produto...",
                                className="mb-2",
                                options=[{"label": "Todos", "value": "todos"}],
                                value="todos"
                            )
                        ], md=6),
                        dbc.Col([
                            html.Label("Cliente:", className="small fw-bold"),
                            dcc.Dropdown(
                                id='filtro-cliente',
                                placeholder="Selecione o cliente...",
                                className="mb-2",
                                options=[{"label": "Todos", "value": "todos"}],
                                value="todos"
                            )
                        ], md=6),
                    ], className="mb-3"),
                    
                    # Segunda linha: Fluxo, Status, Buscar
                    dbc.Row([
                        dbc.Col([
                            html.Label("Fluxo:", className="small fw-bold"),
                            dcc.Dropdown(
                                id='filtro-fluxo',
                                placeholder="Fluxo...",
                                className="mb-2",
                                options=[
                                    {"label": "Todos", "value": "todos"},
                                    {"label": "Puxado", "value": "Puxado"},
                                    {"label": "Empurrado", "value": "Empurrado"}
                                ],
                                value="todos"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Status:", className="small fw-bold"),
                            dcc.Dropdown(
                                id='filtro-status',
                                placeholder="Status...",
                                className="mb-2",
                                options=[
                                    {"label": "Todos", "value": "todos"},
                                    {"label": "Em Processo", "value": "processo"},
                                    {"label": "Em Estoque", "value": "estoque"}
                                ],
                                value="todos"
                            )
                        ], md=4),
                        dbc.Col([
                            html.Label("Buscar:", className="small fw-bold"),
                            dcc.Input(
                                id='filtro-busca',
                                placeholder="Digite para buscar...",
                                className="form-control mb-2",
                                type="text"
                            )
                        ], md=4),
                    ])
                ], md=10),
                
                # Coluna direita: Botões de Ação
                dbc.Col([
                    html.Label("Ações:", className="small fw-bold"),
                    dbc.Row([
                        dbc.Button(
                            "Aplicar",
                            id='btn-aplicar-filtros',
                            color="primary",
                            size="sm",
                            className="mb-2 w-100"
                        ),
                        dbc.Button(
                            "Integrações",
                            id='btn-abrir-integracao',
                            color="secondary",
                            size="sm",
                            className="mb-2 w-100"
                        ),
                        dbc.Button(
                            "CRUD Saídas",
                            id='btn-abrir-crud-saidas',
                            color="info",
                            size="sm",
                            className="mb-2 w-100"
                        ),
                        dbc.Button(
                            "🔄 Zerar Estoque",
                            id='btn-abrir-zerar-estoque',
                            color="warning",
                            size="sm",
                            className="w-100"
                        )
                    ])
                ], md=2),
            ])
        ])
    ], className="mb-3"),
    
    # Tabela de dados
    dbc.Card([
        dbc.CardHeader("Dados dos Produtos", className="text-center fw-bold py-2"),
        dbc.CardBody([
            html.Div([
                html.P("💡 Visualize os dados dos produtos e pedidos em aberto", 
                       className="text-muted small mb-2"),
                html.Div(id='tabela-produtos-container')
            ])
        ])
    ]),
    
    # Modal de integrações
    dbc.Modal([
        dbc.ModalHeader([
            dbc.ModalTitle("Integrações"),
            dbc.Button("×", id="fechar-modal-integracao-dashboard", className="btn-close", n_clicks=0)
        ]),
        dbc.ModalBody([
            html.Div(id="conteudo-integracao-dashboard")
        ])
    ], id='modal_integracao_dashboard', size="xl", is_open=False),
    
    # Modal de CRUD de saídas
    dbc.Modal([
        dbc.ModalHeader([
            dbc.ModalTitle("CRUD de Saídas - Tabela saida_notas"),
            dbc.Button("×", id="fechar-modal-crud-saidas", className="btn-close", n_clicks=0)
        ]),
        dbc.ModalBody([
            html.Div(id="conteudo-crud-saidas")
        ])
    ], id='modal_crud_saidas', size="xl", is_open=False),
    
    # Modal de zerar estoque
    dbc.Modal([
        dbc.ModalHeader([
            dbc.ModalTitle("🔄 Zerar Estoque de Produtos"),
            dbc.Button("×", id="fechar-modal-zerar-estoque", className="btn-close", n_clicks=0)
        ]),
        dbc.ModalBody([
            html.Div(id="conteudo-zerar-estoque")
        ])
    ], id='modal_zerar_estoque', size="xl", is_open=False)
    
], fluid=True)

def formatar_numero(val):
    if pd.isna(val) or val is None:
        return "0"
    try:
        return '{:,.0f}'.format(float(val)).replace(',', '.')
    except (ValueError, TypeError):
        return "0"

def obter_dados_produtos_em_lote(produto_ids):
    """
    Obtém dados de baixas, pedidos em aberto e saídas para uma lista de produtos
    """
    with Session(engine) as session:
        # Baixas por produto (considerar todos, independente de pcp_correncia)
        baixas = session.query(
            PCP.pcp_produto_id,
            func.sum(BAIXA.qtd).label("qtd_baixa")
        ).join(
            BAIXA, PCP.pcp_id == BAIXA.pcp_id
        ).filter(
            PCP.pcp_produto_id.in_(produto_ids)
        ).group_by(PCP.pcp_produto_id).all()
        
        # Quantidade total planejada por produto (considerar todos, independente de pcp_correncia)
        qtd_planejada = session.query(
            PCP.pcp_produto_id,
            func.sum(PCP.pcp_qtd).label("qtd_planejada")
        ).filter(
            PCP.pcp_produto_id.in_(produto_ids)
        ).group_by(PCP.pcp_produto_id).all()
        
        # Quantidade em processo por produto (DESCONSIDERAR quando pcp_correncia != NULL)
        # Obter PCPs com pcp_correncia NULL e calcular quantidade em processo
        pcp_processo = session.query(
            PCP.pcp_produto_id,
            PCP.pcp_qtd,
            func.coalesce(func.sum(BAIXA.qtd), 0).label("qtd_baixada")
        ).outerjoin(
            BAIXA, PCP.pcp_id == BAIXA.pcp_id
        ).filter(
            PCP.pcp_produto_id.in_(produto_ids),
            PCP.pcp_correncia.is_(None)  # Apenas PCPs onde pcp_correncia é NULL
        ).group_by(PCP.pcp_produto_id, PCP.pcp_qtd, PCP.pcp_id).all()
        
        # Calcular quantidade em processo por produto
        qtd_processo_dict = {}
        for produto_id, pcp_qtd, qtd_baixada in pcp_processo:
            if produto_id not in qtd_processo_dict:
                qtd_processo_dict[produto_id] = 0
            qtd_processo_dict[produto_id] += max(0, pcp_qtd - qtd_baixada)
        
        qtd_processo = [(produto_id, qtd) for produto_id, qtd in qtd_processo_dict.items()]
        
        # Pedidos em aberto por produto e status
        from banco_dados.banco import PEDIDOS_EM_ABERTO
        
        # Pedidos com status "Aberto"
        pedidos_aberto = session.query(
            PEDIDOS_EM_ABERTO.produto_id,
            func.sum(PEDIDOS_EM_ABERTO.quantidade).label("qtd_aberto")
        ).filter(
            PEDIDOS_EM_ABERTO.produto_id.in_(produto_ids),
            PEDIDOS_EM_ABERTO.situacao == "Aberto"
        ).group_by(PEDIDOS_EM_ABERTO.produto_id).all()
        
        # Pedidos com status "Fechado"
        pedidos_fechado = session.query(
            PEDIDOS_EM_ABERTO.produto_id,
            func.sum(PEDIDOS_EM_ABERTO.quantidade).label("qtd_fechado")
        ).filter(
            PEDIDOS_EM_ABERTO.produto_id.in_(produto_ids),
            PEDIDOS_EM_ABERTO.situacao == "Fechado"
        ).group_by(PEDIDOS_EM_ABERTO.produto_id).all()
        
        # Pedidos com status "Pronto para faturar"
        pedidos_pronto = session.query(
            PEDIDOS_EM_ABERTO.produto_id,
            func.sum(PEDIDOS_EM_ABERTO.quantidade).label("qtd_pronto")
        ).filter(
            PEDIDOS_EM_ABERTO.produto_id.in_(produto_ids),
            PEDIDOS_EM_ABERTO.situacao == "Pronto para faturar"
        ).group_by(PEDIDOS_EM_ABERTO.produto_id).all()
        
        # Saídas por produto (para calcular estoque real)
        from banco_dados.banco import SAIDA_NOTAS
        saidas = session.query(
            SAIDA_NOTAS.produto_id,
            func.sum(SAIDA_NOTAS.quantidade).label("qtd_saida")
        ).filter(
            SAIDA_NOTAS.produto_id.in_(produto_ids)
        ).group_by(SAIDA_NOTAS.produto_id).all()
        

        
        return {
            'baixas': dict(baixas),
            'qtd_planejada': dict(qtd_planejada),
            'qtd_processo': dict(qtd_processo),
            'pedidos_aberto': dict(pedidos_aberto),
            'pedidos_fechado': dict(pedidos_fechado),
            'pedidos_pronto': dict(pedidos_pronto),
            'saidas': dict(saidas)
        }



@app.callback(
    [Output('tabela-produtos-container', 'children')],
    [Input('btn-aplicar-filtros', 'n_clicks')],
    [State('filtro-produto', 'value'),
     State('filtro-cliente', 'value'),
     State('filtro-fluxo', 'value'),
     State('filtro-status', 'value'),
     State('filtro-busca', 'value')],
    prevent_initial_call=True
)
def atualizar_tabela_produtos(n_clicks, produto, cliente, fluxo, status, busca):
    if not n_clicks:
        return [html.P("Clique em 'Aplicar' para carregar os dados.")]
    
    try:
        banco = Banco()
        
        # Carregar dados básicos
        df_produtos = banco.ler_tabela("produtos")
        df_pcp = banco.ler_tabela("pcp")
        df_clientes = banco.ler_tabela("clientes")
        
        # Fazer merge dos dados
        df_completo = df_pcp.merge(
            df_produtos[['produto_id', 'nome', 'fluxo_producao']], 
            left_on='pcp_produto_id', 
            right_on='produto_id', 
            how='left'
        ).merge(
            df_clientes[['cliente_id', 'nome']], 
            left_on='pcp_cliente_id', 
            right_on='cliente_id', 
            how='left'
        )
        
        # Aplicar filtros
        if produto and produto != "todos":
            df_completo = df_completo[df_completo['produto_id'] == produto]
        
        if cliente and cliente != "todos":
            df_completo = df_completo[df_completo['nome_y'] == cliente]
        
        if fluxo and fluxo != "todos":
            df_completo = df_completo[df_completo['fluxo_producao'] == fluxo]
        
        # Filtro de busca
        if busca:
            busca_lower = busca.lower()
            df_completo = df_completo[
                df_completo['nome_x'].str.lower().str.contains(busca_lower, na=False) |
                df_completo['nome_y'].str.lower().str.contains(busca_lower, na=False)
            ]
        
        # Verificar se há dados para processar
        if df_completo.empty:
            return [html.P("Nenhum dado encontrado com os filtros aplicados.")]
        
        # Agrupar por produto
        df_agrupado = df_completo.groupby([
            'produto_id', 'nome_x', 'fluxo_producao'
        ]).agg({
            'pcp_qtd': 'sum',
            'nome_y': lambda x: ', '.join(x.unique())  # Clientes únicos
        }).reset_index()
        
        # Verificar se o agrupamento resultou em dados
        if df_agrupado.empty:
            return [html.P("Nenhum produto encontrado com os filtros aplicados.")]
        
        # Obter dados de baixas e pedidos em aberto
        produto_ids = df_agrupado['produto_id'].unique().tolist()
        
        # Verificar se há IDs de produtos válidos
        if not produto_ids:
            return [html.P("Nenhum produto válido encontrado.")]
        
        dados_lote = obter_dados_produtos_em_lote(produto_ids)
        
        # Verificar se os dados do lote são válidos
        if not dados_lote or not isinstance(dados_lote, dict):
            return [html.P("Erro ao carregar dados do banco. Tente novamente.")]
        
        # Aplicar dados em lote
        df_agrupado['qtd_baixa'] = df_agrupado['produto_id'].map(dados_lote.get('baixas', {})).fillna(0)
        df_agrupado['qtd_planejada'] = df_agrupado['produto_id'].map(dados_lote.get('qtd_planejada', {})).fillna(0)
        df_agrupado['qtd_processo'] = df_agrupado['produto_id'].map(dados_lote.get('qtd_processo', {})).fillna(0)
        
        # Aplicar dados dos pedidos em aberto
        df_agrupado['qtd_pedidos_aberto'] = df_agrupado['produto_id'].map(dados_lote.get('pedidos_aberto', {})).fillna(0)
        df_agrupado['qtd_pedidos_fechado'] = df_agrupado['produto_id'].map(dados_lote.get('pedidos_fechado', {})).fillna(0)
        df_agrupado['qtd_pedidos_pronto'] = df_agrupado['produto_id'].map(dados_lote.get('pedidos_pronto', {})).fillna(0)
        
        # Aplicar dados de saídas
        df_agrupado['qtd_saida'] = df_agrupado['produto_id'].map(dados_lote.get('saidas', {})).fillna(0)
        
        # Calcular saldos
        # Qtd em Estoque: apenas entradas (baixas) - saídas
        df_agrupado['qtd_estoque'] = df_agrupado['qtd_baixa'] - df_agrupado['qtd_saida'].fillna(0)
        
        # Aplicar filtro de status
        if status and status != "todos":
            if status == "processo":
                df_agrupado = df_agrupado[df_agrupado['qtd_processo'] > 0]
            elif status == "estoque":
                df_agrupado = df_agrupado[df_agrupado['qtd_estoque'] > 0]  # Estoque (entradas - saídas)
        
        # Verificar se ainda há dados após aplicar filtros
        if df_agrupado.empty:
            return [html.P("Nenhum produto encontrado com os filtros aplicados.")]
        
        # Formatar números
        colunas_numericas = ['qtd_planejada', 'qtd_processo', 'qtd_estoque', 'qtd_pedidos_aberto', 'qtd_pedidos_fechado', 'qtd_pedidos_pronto']
        for col in colunas_numericas:
            df_agrupado[col] = df_agrupado[col].apply(formatar_numero)
        
        # Remover coluna Ações se existir
        if 'Ações' in df_agrupado.columns:
            df_agrupado = df_agrupado.drop('Ações', axis=1)
        
        # Renomear colunas
        df_agrupado = df_agrupado.rename(columns={
            'produto_id': 'ID Produto',
            'nome_x': 'Nome do Produto',
            'fluxo_producao': 'Fluxo de Produção',
            'nome_y': 'Clientes',
            'qtd_planejada': 'Qtd Planejada',
            'qtd_processo': 'Produção',
            'qtd_estoque': 'Qtd em Estoque',
            'qtd_pedidos_aberto': 'Pedidos Aberto',
            'qtd_pedidos_fechado': 'Pedidos Fechado',
            'qtd_pedidos_pronto': 'Pedidos Pronto'
        })
        
        # Criar dados da tabela
        dados_tabela = []
        for _, row in df_agrupado.iterrows():
            try:
                row_dict = row.to_dict()
                # Garantir que não há valores None ou NaN
                for key, value in row_dict.items():
                    if pd.isna(value) or value is None:
                        row_dict[key] = ""
                dados_tabela.append(row_dict)
            except Exception as e:
                print(f"Erro ao processar linha: {e}")
                continue
        
        # Verificar se há dados válidos
        if not dados_tabela:
            return [html.P("Nenhum dado encontrado com os filtros aplicados.")]
        
        # Criar tabela
        colunas_tabela = [
            {"name": "ID", "id": "ID Produto"},
            {"name": "Nome do Produto", "id": "Nome do Produto"},
            {"name": "Clientes", "id": "Clientes"},
            #{"name": "Fluxo de Produção", "id": "Fluxo de Produção"},
            #{"name": "Qtd Planejada", "id": "Qtd Planejada"},
            {"name": "Produção", "id": "Produção"},
            {"name": "Qtd em Estoque", "id": "Qtd em Estoque"},
            {"name": "Pedidos Aberto", "id": "Pedidos Aberto"},
            {"name": "Pedidos Fechado", "id": "Pedidos Fechado"},
            {"name": "Pedidos Pronto", "id": "Pedidos Pronto"}
        ]
        
        # Verificar se todos os dados são válidos
        dados_validos = []
        for item in dados_tabela:
            try:
                # Verificar se todos os campos necessários existem e são válidos
                item_valido = {}
                for col in colunas_tabela:
                    col_id = col['id']
                    if col_id in item:
                        value = item[col_id]
                        if pd.isna(value) or value is None:
                            item_valido[col_id] = ""
                        else:
                            item_valido[col_id] = str(value)
                    else:
                        item_valido[col_id] = ""
                

                
                dados_validos.append(item_valido)
            except Exception as e:
                print(f"Erro ao validar item: {e}")
                continue
        
        if not dados_validos:
            return [html.P("Erro ao processar dados. Tente novamente.")]
        
        tabela = dash_table.DataTable(
            id='tabela-produtos-datatable',
            columns=colunas_tabela,
            data=dados_validos,
            style_table={'height': '600px', 'overflowY': 'auto', 'border': '1px solid #ccc'},
            row_selectable='single',
            page_size=40,
            sort_action="native",
            sort_mode="multi",
            style_header={
                'backgroundColor': '#02083d', 
                'fontWeight': 'bold', 
                'textAlign': 'center', 
                'padding': '8px',
                'color': 'white',
                'fontSize': '12px'
            },
            style_cell={
                'textAlign': 'center', 
                'padding': '6px', 
                'fontSize': '12px', 
                'border': '1px solid #ddd',
                'cursor': 'pointer'
            },
            style_data_conditional=[
                {'if': {'column_id': 'Produção', 'filter_query': '{Produção} > "0"'},
                 'backgroundColor': 'rgba(255, 165, 0, 0.2)', 'color': 'black'},
                {'if': {'column_id': 'Qtd em Estoque', 'filter_query': '{Qtd em Estoque} > "0"'},
                 'backgroundColor': 'rgba(34, 139, 34, 0.2)', 'color': 'black'},
                {'if': {'column_id': 'Qtd em Estoque', 'filter_query': '{Qtd em Estoque} <= "0"'},
                 'backgroundColor': 'rgba(220, 53, 69, 0.2)', 'color': 'white', 'fontWeight': 'bold'},
                {'if': {'column_id': 'Pedidos Aberto', 'filter_query': '{Pedidos Aberto} > "0"'},
                 'backgroundColor': 'rgba(0, 123, 255, 0.2)', 'color': 'black'},
                {'if': {'column_id': 'Pedidos Fechado', 'filter_query': '{Pedidos Fechado} > "0"'},
                 'backgroundColor': 'rgba(108, 117, 125, 0.2)', 'color': 'black'},
                {'if': {'column_id': 'Pedidos Pronto', 'filter_query': '{Pedidos Pronto} > "0"'},
                 'backgroundColor': 'rgba(52, 58, 64, 0.2)', 'color': 'black'},
                {'if': {'state': 'selected'},
                 'backgroundColor': 'rgba(0, 123, 255, 0.3)', 'color': 'black'}
            ]
        )
        
        return [tabela]
        
    except Exception as e:
        return [html.Div([
            html.P(f"Erro ao carregar dados: {str(e)}", className="text-danger")
        ])]

@app.callback(
    [Output('filtro-cliente', 'options'),
     Output('filtro-produto', 'options')],
    Input('btn-aplicar-filtros', 'n_clicks'),
    prevent_initial_call=False
)
def carregar_opcoes_filtros(n_clicks):
    try:
        banco = Banco()
        df_clientes = banco.ler_tabela("clientes")
        df_produtos = banco.ler_tabela("produtos")
        
        # Opções de clientes
        opcoes_clientes = [{"label": "Todos", "value": "todos"}]
        for _, cliente in df_clientes.iterrows():
            opcoes_clientes.append({
                "label": cliente['nome'],
                "value": cliente['nome']
            })
        
        # Opções de produtos
        opcoes_produtos = [{"label": "Todos", "value": "todos"}]
        for _, produto in df_produtos.iterrows():
            opcoes_produtos.append({
                "label": f"{produto['produto_id']} - {produto['nome']}",
                "value": produto['produto_id']
            })
        
        return opcoes_clientes, opcoes_produtos
    except Exception as e:
        return [{"label": "Todos", "value": "todos"}], [{"label": "Todos", "value": "todos"}]







# Callback para abrir/fechar modal de integrações
@app.callback(
    [Output('modal_integracao_dashboard', 'is_open'),
     Output('conteudo-integracao-dashboard', 'children')],
    [Input('btn-abrir-integracao', 'n_clicks'),
     Input('fechar-modal-integracao-dashboard', 'n_clicks')],
    [State('modal_integracao_dashboard', 'is_open')],
    prevent_initial_call=True
)
def controlar_modal_integracao(n_abrir, n_fechar, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open, []
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'btn-abrir-integracao':
        return True, integracoes_layout
    elif trigger_id == 'fechar-modal-integracao-dashboard':
        return False, []
    
    return is_open, []

# Callback para abrir/fechar modal de CRUD de saídas
@app.callback(
    [Output('modal_crud_saidas', 'is_open'),
     Output('conteudo-crud-saidas', 'children')],
    [Input('btn-abrir-crud-saidas', 'n_clicks'),
     Input('fechar-modal-crud-saidas', 'n_clicks')],
    [State('modal_crud_saidas', 'is_open')],
    prevent_initial_call=True
)
def controlar_modal_crud_saidas(n_abrir, n_fechar, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open, []
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'btn-abrir-crud-saidas':
        return True, crud_saidas_layout
    elif trigger_id == 'fechar-modal-crud-saidas':
        return False, []
    
    return is_open, []

# Callback para abrir/fechar modal de zerar estoque
@app.callback(
    [Output('modal_zerar_estoque', 'is_open'),
     Output('conteudo-zerar-estoque', 'children')],
    [Input('btn-abrir-zerar-estoque', 'n_clicks'),
     Input('fechar-modal-zerar-estoque', 'n_clicks')],
    [State('modal_zerar_estoque', 'is_open')],
    prevent_initial_call=True
)
def controlar_modal_zerar_estoque(n_abrir, n_fechar, is_open):
    ctx = callback_context
    if not ctx.triggered:
        return is_open, []
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'btn-abrir-zerar-estoque':
        return True, layout_zerar_estoque()
    elif trigger_id == 'fechar-modal-zerar-estoque':
        return False, []
    
    return is_open, []


