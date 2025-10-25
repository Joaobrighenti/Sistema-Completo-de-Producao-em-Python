"""
Script para zerar quantidade em estoque através da tabela saida_notas
Este script permite zerar o estoque de produtos selecionados criando registros de saída automáticos
"""

from dash import html, dcc, Input, Output, State, callback_context, ALL, no_update
import dash_bootstrap_components as dbc
import pandas as pd
from banco_dados.banco import Banco, SAIDA_NOTAS, PRODUTO, PCP, BAIXA, engine
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from app import app
from dash import dash_table

def layout_zerar_estoque():
    """Layout para a funcionalidade de zerar estoque"""
    return dbc.Container([
        # Cabeçalho
        dbc.Row([
            dbc.Col([
                html.H4("🔄 Zerar Estoque de Produtos", className="text-center mb-3"),
                html.P("Selecione os produtos que deseja zerar o estoque. Será criada uma saída automática na tabela saida_notas.", 
                       className="text-muted text-center mb-4")
            ], md=12)
        ]),
        
        # Filtros
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("🔍 Filtrar por Nome do Produto:", className="form-label fw-bold"),
                        dcc.Input(
                            id="filtro-produto-zerar",
                            placeholder="Digite o nome do produto...",
                            className="form-control",
                            type="text"
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label("📊 Mostrar apenas produtos com estoque diferente de zero:", className="form-label fw-bold"),
                        dbc.Switch(
                            id="switch-apenas-estoque",
                            label="Sim (positivo ou negativo)",
                            value=True,
                            className="mt-2"
                        )
                    ], md=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("🔍 Filtrar", id="btn-filtrar-zerar", color="primary", className="me-2"),
                        dbc.Button("🔄 Atualizar", id="btn-atualizar-zerar", color="secondary", className="me-2"),
                        dbc.Button("✅ Zerar Selecionados", id="btn-zerar-selecionados", color="danger", className="me-2"),
                        dbc.Button("📋 Selecionar Todos", id="btn-selecionar-todos", color="info")
                    ], md=12, className="text-center")
                ])
            ])
        ], className="mb-3"),
        
        # Tabela de produtos
        dbc.Card([
            dbc.CardHeader("Produtos com Estoque Disponível"),
            dbc.CardBody([
                html.Div(id="tabela-produtos-zerar-container")
            ])
        ]),
        
        # Modal de confirmação
        dbc.Modal([
            dbc.ModalHeader([
                dbc.ModalTitle("⚠️ Confirmar Zeramento de Estoque"),
                dbc.Button("×", id="fechar-modal-confirmacao", className="btn-close", n_clicks=0)
            ]),
            dbc.ModalBody([
                html.Div(id="conteudo-confirmacao-zerar")
            ]),
            dbc.ModalFooter([
                dbc.Button("❌ Cancelar", id="btn-cancelar-zerar", color="secondary", className="me-2"),
                dbc.Button("✅ Confirmar Zeramento", id="btn-confirmar-zerar", color="danger")
            ])
        ], id='modal-confirmacao-zerar', size="lg", is_open=False),
        
        # Alertas
        html.Div(id="alert-zerar-estoque")
    ], fluid=True)

def obter_produtos_com_estoque(filtro_nome=None, apenas_com_estoque=True):
    """Obtém produtos com suas quantidades de estoque"""
    try:
        banco = Banco()
        
        # Carregar dados básicos
        df_produtos = banco.ler_tabela("produtos")
        df_pcp = banco.ler_tabela("pcp")
        df_clientes = banco.ler_tabela("clientes")
        
        if df_produtos.empty or df_pcp.empty:
            return pd.DataFrame()
        
        # Fazer merge dos dados (usando a mesma lógica do dashboard principal)
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
        
        # Agrupar por produto
        df_agrupado = df_completo.groupby([
            'produto_id', 'nome_x', 'fluxo_producao'
        ]).agg({
            'pcp_qtd': 'sum',
            'nome_y': lambda x: ', '.join(x.unique())  # Clientes únicos
        }).reset_index()
        
        # Obter dados de baixas e saídas
        produto_ids = df_agrupado['produto_id'].unique().tolist()
        
        with Session(engine) as session:
            # Baixas por produto
            baixas = session.query(
                PCP.pcp_produto_id,
                func.sum(BAIXA.qtd).label("qtd_baixa")
            ).join(
                BAIXA, PCP.pcp_id == BAIXA.pcp_id
            ).filter(
                PCP.pcp_produto_id.in_(produto_ids)
            ).group_by(PCP.pcp_produto_id).all()
            
            # Saídas por produto
            saidas = session.query(
                SAIDA_NOTAS.produto_id,
                func.sum(SAIDA_NOTAS.quantidade).label("qtd_saida")
            ).filter(
                SAIDA_NOTAS.produto_id.in_(produto_ids)
            ).group_by(SAIDA_NOTAS.produto_id).all()
        
        # Aplicar dados em lote
        df_agrupado['qtd_baixa'] = df_agrupado['produto_id'].map(dict(baixas)).fillna(0)
        df_agrupado['qtd_saida'] = df_agrupado['produto_id'].map(dict(saidas)).fillna(0)
        
        # Calcular saldo em estoque
        df_agrupado['qtd_estoque'] = df_agrupado['qtd_baixa'] - df_agrupado['qtd_saida']
        
        # Aplicar filtro de nome se fornecido
        if filtro_nome and filtro_nome.strip():
            filtro_lower = filtro_nome.lower().strip()
            df_agrupado = df_agrupado[
                df_agrupado['nome_x'].str.lower().str.contains(filtro_lower, na=False)
            ]
        
        # Aplicar filtro de estoque se solicitado
        if apenas_com_estoque:
            # Mostrar produtos com estoque diferente de zero (positivo ou negativo)
            df_agrupado = df_agrupado[df_agrupado['qtd_estoque'] != 0]
        
        # Ordenar por quantidade de estoque (negativos primeiro, depois positivos)
        df_agrupado = df_agrupado.sort_values('qtd_estoque', ascending=True)
        
        return df_agrupado
        
    except Exception as e:
        print(f"Erro ao obter produtos com estoque: {e}")
        return pd.DataFrame()

def criar_tabela_produtos_zerar(df_produtos):
    """Cria a tabela de produtos para zerar estoque"""
    if df_produtos.empty:
        return html.P("Nenhum produto encontrado com os filtros aplicados.", className="text-muted text-center")
    
    # Criar dados da tabela
    dados_tabela = []
    for _, row in df_produtos.iterrows():
        qtd_estoque = int(row['qtd_estoque'])
        # Formatar com sinal negativo se necessário
        if qtd_estoque < 0:
            qtd_formatada = f"-{abs(qtd_estoque):,}".replace(',', '.')
        else:
            qtd_formatada = f"{qtd_estoque:,}".replace(',', '.')
        
        dados_tabela.append({
            'ID Produto': row['produto_id'],
            'Nome do Produto': row['nome_x'],  # Usar nome_x (nome do produto)
            'Fluxo': row['fluxo_producao'],
            'Qtd em Estoque': qtd_formatada,
            'Selecionado': False
        })
    
    # Colunas da tabela
    colunas_tabela = [
        {"name": "Selecionar", "id": "Selecionado", "type": "text", "presentation": "markdown"},
        {"name": "ID", "id": "ID Produto"},
        {"name": "Nome do Produto", "id": "Nome do Produto"},
        {"name": "Fluxo", "id": "Fluxo"},
        {"name": "Qtd em Estoque", "id": "Qtd em Estoque"}
    ]
    
    tabela = dash_table.DataTable(
        id='tabela-produtos-zerar',
        columns=colunas_tabela,
        data=dados_tabela,
        style_table={'height': '500px', 'overflowY': 'auto', 'border': '1px solid #ccc'},
        row_selectable='multi',
        page_size=20,
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
            {'if': {'column_id': 'Qtd em Estoque', 'filter_query': '{Qtd em Estoque} > "0"'},
             'backgroundColor': 'rgba(34, 139, 34, 0.2)', 'color': 'black'},
            {'if': {'column_id': 'Qtd em Estoque', 'filter_query': '{Qtd em Estoque} < "0"'},
             'backgroundColor': 'rgba(220, 53, 69, 0.2)', 'color': 'white', 'fontWeight': 'bold'},
            {'if': {'column_id': 'Qtd em Estoque', 'filter_query': '{Qtd em Estoque} = "0"'},
             'backgroundColor': 'rgba(108, 117, 125, 0.2)', 'color': 'black'},
            {'if': {'state': 'selected'},
             'backgroundColor': 'rgba(0, 123, 255, 0.3)', 'color': 'black'}
        ]
    )
    
    return tabela

# Callbacks para a funcionalidade de zerar estoque
@app.callback(
    Output("tabela-produtos-zerar-container", "children"),
    [Input("btn-filtrar-zerar", "n_clicks"),
     Input("btn-atualizar-zerar", "n_clicks"),
     Input("modal_zerar_estoque", "is_open")],
    [State("filtro-produto-zerar", "value"),
     State("switch-apenas-estoque", "value")],
    prevent_initial_call=False
)
def atualizar_tabela_produtos_zerar(n_filtrar, n_atualizar, modal_aberto, filtro_nome, apenas_estoque):
    """Atualiza a tabela de produtos para zerar estoque"""
    # Carregar dados quando o modal abrir ou quando os botões forem clicados
    if modal_aberto or n_filtrar or n_atualizar:
        df_produtos = obter_produtos_com_estoque(filtro_nome, apenas_estoque)
        return criar_tabela_produtos_zerar(df_produtos)
    
    return html.P("Clique em 'Filtrar' ou 'Atualizar' para carregar os dados.", className="text-muted text-center")

@app.callback(
    [Output("modal-confirmacao-zerar", "is_open"),
     Output("conteudo-confirmacao-zerar", "children")],
    [Input("btn-zerar-selecionados", "n_clicks"),
     Input("fechar-modal-confirmacao", "n_clicks"),
     Input("btn-cancelar-zerar", "n_clicks")],
    [State("tabela-produtos-zerar", "selected_rows"),
     State("tabela-produtos-zerar", "data")],
    prevent_initial_call=True
)
def controlar_modal_confirmacao(n_zerar, n_fechar, n_cancelar, selected_rows, data):
    """Controla o modal de confirmação para zerar estoque"""
    ctx = callback_context
    if not ctx.triggered:
        return False, []
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id in ["fechar-modal-confirmacao", "btn-cancelar-zerar"]:
        return False, []
    
    elif trigger_id == "btn-zerar-selecionados":
        if not selected_rows:
            return False, dbc.Alert("❌ Selecione pelo menos um produto para zerar o estoque!", color="warning")
        
        # Preparar dados dos produtos selecionados
        produtos_selecionados = []
        total_quantidade_positiva = 0
        total_quantidade_negativa = 0
        
        for row_index in selected_rows:
            produto = data[row_index]
            qtd_estoque_str = produto['Qtd em Estoque']
            
            # Converter quantidade (remover pontos e tratar sinal negativo)
            if qtd_estoque_str.startswith('-'):
                quantidade = -int(qtd_estoque_str[1:].replace('.', ''))
            else:
                quantidade = int(qtd_estoque_str.replace('.', ''))
            
            produtos_selecionados.append({
                'id': produto['ID Produto'],
                'nome': produto['Nome do Produto'],
                'quantidade': quantidade
            })
            
            if quantidade > 0:
                total_quantidade_positiva += quantidade
            elif quantidade < 0:
                total_quantidade_negativa += abs(quantidade)
        
        # Criar conteúdo do modal
        conteudo = [
            html.H5("⚠️ Confirmação de Zeramento de Estoque", className="text-center mb-4"),
            html.P(f"Você está prestes a zerar o estoque de {len(produtos_selecionados)} produto(s).", 
                   className="text-center mb-3"),
        ]
        
        # Adicionar informações sobre ações que serão realizadas
        if total_quantidade_positiva > 0:
            conteudo.append(html.P(f"📤 Produtos com estoque positivo: {total_quantidade_positiva:,} unidades serão dadas como saída".replace(',', '.'), 
                                   className="text-center mb-2 fw-bold text-success"))
        
        if total_quantidade_negativa > 0:
            conteudo.append(html.P(f"📥 Produtos com estoque negativo: {total_quantidade_negativa:,} unidades serão removidas das saídas".replace(',', '.'), 
                                   className="text-center mb-2 fw-bold text-warning"))
        
        conteudo.extend([
            html.H6("Produtos selecionados:", className="mb-3"),
            html.Ul([
                html.Li([
                    f"ID {prod['id']} - {prod['nome']} (",
                    html.Span(f"{prod['quantidade']:,} unidades".replace(',', '.'), 
                             className="fw-bold text-success" if prod['quantidade'] > 0 else "fw-bold text-warning" if prod['quantidade'] < 0 else "fw-bold text-muted"),
                    ")"
                ])
                for prod in produtos_selecionados
            ], className="mb-4"),
            
            dbc.Alert([
                html.Strong("⚠️ ATENÇÃO: "),
                "Esta ação modificará registros na tabela saida_notas: ",
                html.Br(),
                "• Produtos com estoque positivo: serão criadas saídas automáticas",
                html.Br(),
                "• Produtos com estoque negativo: serão removidas/reduzidas saídas existentes",
                html.Br(),
                "Esta ação não pode ser desfeita facilmente. Certifique-se de que esta é a ação desejada."
            ], color="warning", className="mb-3"),
            
            html.P("Deseja continuar com o zeramento?", className="text-center fw-bold")
        ])
        
        return True, conteudo
    
    return False, []

@app.callback(
    Output("alert-zerar-estoque", "children"),
    [Input("btn-confirmar-zerar", "n_clicks")],
    [State("tabela-produtos-zerar", "selected_rows"),
     State("tabela-produtos-zerar", "data")],
    prevent_initial_call=True
)
def executar_zeramento_estoque(n_confirmar, selected_rows, data):
    """Executa o zeramento do estoque dos produtos selecionados"""
    if not n_confirmar or not selected_rows:
        return no_update
    
    try:
        banco = Banco()
        produtos_processados = 0
        erros = []
        acoes_realizadas = []
        
        for row_index in selected_rows:
            produto = data[row_index]
            produto_id = produto['ID Produto']
            qtd_estoque_str = produto['Qtd em Estoque']
            
            # Converter quantidade (remover pontos e tratar sinal negativo)
            if qtd_estoque_str.startswith('-'):
                quantidade = -int(qtd_estoque_str[1:].replace('.', ''))
            else:
                quantidade = int(qtd_estoque_str.replace('.', ''))
            
            try:
                if quantidade > 0:
                    # Estoque positivo: criar saída para zerar
                    dados_saida = {
                        'produto_id': produto_id,
                        'quantidade': quantidade,
                        'descricao': f'Zeramento automático de estoque - {datetime.now().strftime("%d/%m/%Y %H:%M")}',
                        'numero_nfe': f'AUTO-ZERO-{datetime.now().strftime("%Y%m%d%H%M%S")}-{produto_id}',
                        'observacao': f'Zeramento automático do estoque do produto ID {produto_id} executado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}'
                    }
                    
                    banco.inserir_dados("saida_notas", **dados_saida)
                    acoes_realizadas.append(f"ID {produto_id}: Adicionada saída de {quantidade:,} unidades".replace(',', '.'))
                    
                elif quantidade < 0:
                    # Estoque negativo: remover saídas existentes para equilibrar
                    qtd_para_remover = abs(quantidade)
                    
                    # Buscar saídas existentes do produto
                    df_saidas = banco.ler_tabela("saida_notas")
                    saidas_produto = df_saidas[df_saidas['produto_id'] == produto_id].sort_values('id', ascending=False)
                    
                    if saidas_produto.empty:
                        erros.append(f"Produto ID {produto_id}: Nenhuma saída encontrada para remover")
                        continue
                    
                    # Remover saídas até equilibrar
                    qtd_removida = 0
                    saidas_removidas = 0
                    
                    for _, saida in saidas_produto.iterrows():
                        if qtd_removida >= qtd_para_remover:
                            break
                            
                        saida_id = saida['id']
                        qtd_saida = saida['quantidade']
                        
                        if qtd_removida + qtd_saida <= qtd_para_remover:
                            # Remover saída completa
                            banco.deletar_dado("saida_notas", saida_id)
                            qtd_removida += qtd_saida
                            saidas_removidas += 1
                        else:
                            # Reduzir quantidade da saída
                            qtd_restante = qtd_para_remover - qtd_removida
                            nova_quantidade = qtd_saida - qtd_restante
                            
                            banco.editar_dado("saida_notas", saida_id, quantidade=nova_quantidade)
                            qtd_removida += qtd_restante
                    
                    if qtd_removida > 0:
                        acoes_realizadas.append(f"ID {produto_id}: Removidas {qtd_removida:,} unidades de {saidas_removidas} saída(s)".replace(',', '.'))
                    else:
                        erros.append(f"Produto ID {produto_id}: Não foi possível remover saídas suficientes")
                        continue
                
                else:
                    # Estoque zero: não fazer nada
                    acoes_realizadas.append(f"ID {produto_id}: Estoque já está zerado")
                
                produtos_processados += 1
                
            except Exception as e:
                erros.append(f"Produto ID {produto_id}: {str(e)}")
        
        # Criar mensagem de resultado
        if produtos_processados == len(selected_rows):
            mensagem = f"✅ Zeramento concluído com sucesso! {produtos_processados} produto(s) processado(s)."
            cor = "success"
        elif produtos_processados > 0:
            mensagem = f"⚠️ Zeramento parcial: {produtos_processados} de {len(selected_rows)} produto(s) processado(s)."
            cor = "warning"
        else:
            mensagem = f"❌ Erro no zeramento: nenhum produto foi processado."
            cor = "danger"
        
        # Criar conteúdo do alerta
        conteudo_alerta = [
            html.Strong(mensagem),
            html.Br(),
            html.Small(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y às %H:%M')}")
        ]
        
        if acoes_realizadas:
            conteudo_alerta.append(html.Br())
            conteudo_alerta.append(html.Strong("Ações realizadas:"))
            for acao in acoes_realizadas:
                conteudo_alerta.append(html.Br())
                conteudo_alerta.append(html.Small(acao, className="text-muted"))
        
        if erros:
            conteudo_alerta.append(html.Br())
            conteudo_alerta.append(html.Strong("Erros encontrados:"))
            for erro in erros:
                conteudo_alerta.append(html.Br())
                conteudo_alerta.append(html.Small(erro, className="text-danger"))
        
        alerta = dbc.Alert(conteudo_alerta, color=cor, dismissable=True)
        return alerta
        
    except Exception as e:
        return dbc.Alert(f"❌ Erro geral no zeramento: {str(e)}", color="danger", dismissable=True)

@app.callback(
    Output("tabela-produtos-zerar", "selected_rows"),
    [Input("btn-selecionar-todos", "n_clicks")],
    [State("tabela-produtos-zerar", "data")],
    prevent_initial_call=True
)
def selecionar_todos_produtos(n_clicks, data):
    """Seleciona todos os produtos da tabela"""
    if n_clicks and data:
        return list(range(len(data)))
    return no_update
