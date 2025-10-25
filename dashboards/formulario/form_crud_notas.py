from dash import html, dcc, Input, Output, State, callback_context, ALL, no_update
import dash_bootstrap_components as dbc
import pandas as pd
from banco_dados.banco import Banco, SAIDA_NOTAS, PRODUTO
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date
from app import app
from dash import dash_table

# Variável global para rastrear o modo de edição
EDITANDO_SAIDA_ID = None

# Layout do formulário CRUD de saídas
layout = dbc.Container([
    # Cabeçalho com botões de ação
    dbc.Row([
        dbc.Col([
            dbc.Button("➕ Nova Saída", id="btn-nova-saida", color="success", className="me-2"),
            dbc.Button("📋 Atualizar Lista", id="btn-atualizar-lista", color="primary", className="me-2"),
        ], md=6),
        dbc.Col([
            html.H5("CRUD de Saídas - Tabela saida_notas", className="text-center mb-0")
        ], md=6)
    ], className="mb-3"),
    
    # Formulário de entrada (inicialmente oculto)
    html.Div(id="formulario-saida", style={"display": "none"}, children=[
        dbc.Card([
            dbc.CardHeader("Dados da Saída"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Produto:", className="form-label"),
                        dcc.Dropdown(
                            id="input-produto-saida",
                            placeholder="Selecione o produto...",
                            options=[],
                            className="mb-3"
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label("Número NFE:", className="form-label"),
                        dbc.Input(
                            id="input-nfe-saida",
                            type="text",
                            placeholder="Número da NFE",
                            className="mb-3"
                        )
                    ], md=6)
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Label("Quantidade:", className="form-label"),
                        dbc.Input(
                            id="input-quantidade-saida",
                            type="number",
                            placeholder="Quantidade",
                            className="mb-3"
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label("Descrição:", className="form-label"),
                        dbc.Input(
                            id="input-descricao-saida",
                            type="text",
                            placeholder="Descrição do item",
                            className="mb-3"
                        )
                    ], md=6)
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Label("Observação:", className="form-label"),
                        dbc.Textarea(
                            id="input-observacao-saida",
                            placeholder="Observações adicionais",
                            className="mb-3"
                        )
                    ], md=12)
                ]),
                dbc.Row([
                    dbc.Col([
                        dbc.Button("💾 Salvar", id="btn-salvar-saida", color="success", className="me-2"),
                        dbc.Button("❌ Cancelar", id="btn-cancelar-saida", color="secondary", className="me-2"),
                        dbc.Button("🔄 Limpar", id="btn-limpar-saida", color="warning")
                    ], md=12, className="text-center")
                ])
            ])
        ], className="mb-3")
    ]),
    
    # Filtro por nome do produto
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("🔍 Filtrar por Nome do Produto:", className="form-label fw-bold"),
                    dcc.Input(
                        id="filtro-nome-produto",
                        placeholder="Digite o nome do produto para filtrar...",
                        className="form-control",
                        type="text"
                    )
                ], md=8),
                dbc.Col([
                    html.Label("📊 Limite de Itens:", className="form-label fw-bold"),
                    dcc.Dropdown(
                        id="limite-itens",
                        options=[
                            {"label": "10 itens", "value": 10},
                            {"label": "20 itens", "value": 20},
                            {"label": "50 itens", "value": 50},
                            {"label": "100 itens", "value": 100}
                        ],
                        value=20,
                        className="form-control"
                    )
                ], md=4)
            ], className="mb-3")
        ])
    ], className="mb-3"),
    
    # Tabela de dados
    dbc.Card([
        dbc.CardHeader("Registros de Saídas"),
        dbc.CardBody([
            html.Div(id="tabela-saidas-container")
        ])
    ]),
    
    # Alertas
    html.Div(id="alert-saidas")
], fluid=True)

# Callback para carregar opções de produtos
@app.callback(
    Output("input-produto-saida", "options"),
    Input("btn-nova-saida", "n_clicks"),
    prevent_initial_call=False
)
def carregar_produtos(n_clicks):
    try:
        banco = Banco()
        df_produtos = banco.ler_tabela("produtos")
        
        opcoes = []
        for _, produto in df_produtos.iterrows():
            opcoes.append({
                "label": f"{produto['produto_id']} - {produto['nome']}",
                "value": produto['produto_id']
            })
        
        return opcoes
    except Exception as e:
        return []

# Callback para atualizar tabela com filtros
@app.callback(
    Output("tabela-saidas-container", "children"),
    [Input("filtro-nome-produto", "value"),
     Input("limite-itens", "value"),
     Input("btn-atualizar-lista", "n_clicks"),
     Input("btn-salvar-saida", "n_clicks"),
     Input({"type": "btn-excluir", "index": ALL}, "n_clicks")],
    prevent_initial_call=False
)
def atualizar_tabela_com_filtros(filtro_nome, limite_itens, n_atualizar, n_salvar, n_excluir):
    try:
        # Usar limite padrão se não fornecido
        if limite_itens is None:
            limite_itens = 20
        
        tabela_atualizada = criar_tabela_saidas(filtro_nome, limite_itens)
        return tabela_atualizada
    except Exception as e:
        return html.P(f"Erro ao atualizar tabela: {str(e)}", className="text-danger")

# Callback unificado para controlar formulário, edição, exclusão
@app.callback(
    [Output("formulario-saida", "style"),
     Output("input-produto-saida", "value"),
     Output("input-nfe-saida", "value"),
     Output("input-quantidade-saida", "value"),
     Output("input-descricao-saida", "value"),
     Output("input-observacao-saida", "value"),
     Output("alert-saidas", "children")],
    [Input("btn-nova-saida", "n_clicks"),
     Input("btn-cancelar-saida", "n_clicks"),
     Input("btn-limpar-saida", "n_clicks"),
     Input("btn-salvar-saida", "n_clicks"),
     Input({"type": "btn-editar", "index": ALL}, "n_clicks"),
     Input({"type": "btn-excluir", "index": ALL}, "n_clicks")],
    [State("input-produto-saida", "value"),
     State("input-nfe-saida", "value"),
     State("input-quantidade-saida", "value"),
     State("input-descricao-saida", "value"),
     State("input-observacao-saida", "value"),
     State({"type": "btn-editar", "index": ALL}, "id"),
     State({"type": "btn-excluir", "index": ALL}, "id")],
    prevent_initial_call=False
)
def controlar_saidas_unificado(n_nova, n_cancelar, n_limpar, n_salvar, 
                               n_editar, n_excluir, produto_id, nfe, quantidade, 
                               descricao, observacao, ids_editar, ids_excluir):
    global EDITANDO_SAIDA_ID
    
    ctx = callback_context
    if not ctx.triggered:
        # Carregar dados iniciais
        return {"display": "none"}, None, None, None, None, None, no_update
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Controle do formulário
    if trigger_id == "btn-nova-saida":
        EDITANDO_SAIDA_ID = None  # Resetar modo de edição
        return {"display": "block"}, None, None, None, None, None, no_update
    
    elif trigger_id in ["btn-cancelar-saida", "btn-limpar-saida"]:
        EDITANDO_SAIDA_ID = None  # Resetar modo de edição
        return {"display": "none"}, None, None, None, None, None, no_update
    
    # Editar saída
    elif "btn-editar" in trigger_id:
        # Encontrar qual botão foi clicado
        for i, n_click in enumerate(n_editar):
            if n_click and n_click > 0:
                # Extrair o ID da saída do ID do botão
                saida_id = ids_editar[i]["index"]
                EDITANDO_SAIDA_ID = saida_id  # Definir modo de edição
                
                try:
                    banco = Banco()
                    df_saida = banco.ler_tabela("saida_notas", id=saida_id)
                    
                    if not df_saida.empty:
                        saida = df_saida.iloc[0]
                        return (
                            {"display": "block"},
                            saida.get('produto_id'),
                            saida.get('numero_nfe'),
                            saida.get('quantidade'),
                            saida.get('descricao'),
                            saida.get('observacao'),
                            no_update
                        )
                except Exception as e:
                    print(f"Erro ao carregar dados para edição: {e}")
        
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update
    
    # Excluir saída
    elif "btn-excluir" in trigger_id:
        # Encontrar qual botão foi clicado
        for i, n_click in enumerate(n_excluir):
            if n_click and n_click > 0:
                # Extrair o ID da saída do ID do botão
                saida_id = ids_excluir[i]["index"]
                
                try:
                    banco = Banco()
                    banco.deletar_dado("saida_notas", saida_id)
                    
                    alerta = dbc.Alert("✅ Saída excluída com sucesso!", color="success", dismissable=True)
                    
                    return no_update, no_update, no_update, no_update, no_update, no_update, alerta
                except Exception as e:
                    alerta = dbc.Alert(f"❌ Erro ao excluir: {str(e)}", color="danger", dismissable=True)
                    return no_update, no_update, no_update, no_update, no_update, no_update, alerta
        
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update
    
    # Salvar saída
    elif trigger_id == "btn-salvar-saida":
        if not produto_id:
            alerta = dbc.Alert("❌ Produto é obrigatório!", color="danger", dismissable=True)
            return no_update, no_update, no_update, no_update, no_update, no_update, alerta
        
        try:
            banco = Banco()
            
            # Preparar dados
            dados = {
                'produto_id': produto_id,
                'numero_nfe': nfe,
                'quantidade': quantidade,
                'descricao': descricao,
                'observacao': observacao
            }
            
            # Verificar se estamos editando ou criando
            if EDITANDO_SAIDA_ID is not None:
                # Estamos editando - atualizar registro existente
                saida_id = EDITANDO_SAIDA_ID
                
                # Verificar se NFE já existe em outro registro
                if nfe:
                    df_existente = banco.ler_tabela("saida_notas")
                    if not df_existente.empty:
                        registros_com_nfe = df_existente[df_existente['numero_nfe'] == nfe]
                        # Filtrar registros diferentes do que estamos editando
                        outros_registros = registros_com_nfe[registros_com_nfe['id'] != saida_id]
                        if len(outros_registros) > 0:
                            alerta = dbc.Alert("❌ NFE já existe em outro registro!", color="warning", dismissable=True)
                            return no_update, no_update, no_update, no_update, no_update, no_update, alerta
                
                # Atualizar registro existente
                banco.editar_dado("saida_notas", saida_id, **dados)
                alerta = dbc.Alert("✅ Saída atualizada com sucesso!", color="success", dismissable=True)
                EDITANDO_SAIDA_ID = None  # Resetar modo de edição
                
            else:
                # Estamos criando - verificar se NFE já existe
                if nfe:
                    df_existente = banco.ler_tabela("saida_notas")
                    if not df_existente.empty and nfe in df_existente['numero_nfe'].values:
                        alerta = dbc.Alert("❌ NFE já existe no sistema!", color="warning", dismissable=True)
                        return no_update, no_update, no_update, no_update, no_update, no_update, alerta
                
                # Inserir nova saída
                banco.inserir_dados("saida_notas", **dados)
                alerta = dbc.Alert("✅ Saída registrada com sucesso!", color="success", dismissable=True)
            
            return {"display": "none"}, None, None, None, None, None, alerta
            
        except Exception as e:
            alerta = dbc.Alert(f"❌ Erro ao salvar: {str(e)}", color="danger", dismissable=True)
            return no_update, no_update, no_update, no_update, no_update, no_update, alerta
    

    
    return no_update, no_update, no_update, no_update, no_update, no_update, no_update

def criar_tabela_saidas(filtro_nome=None, limite_itens=20):
    """Cria a tabela de saídas com dados do banco"""
    try:
        banco = Banco()
        df_saidas = banco.ler_tabela("saida_notas")
        df_produtos = banco.ler_tabela("produtos")
        
        if df_saidas.empty:
            return html.P("Nenhuma saída registrada.", className="text-muted text-center")
        
        # Fazer merge com produtos para mostrar nome
        df_completo = df_saidas.merge(
            df_produtos[['produto_id', 'nome']], 
            left_on='produto_id', 
            right_on='produto_id', 
            how='left'
        )
        
        # Aplicar filtro por nome do produto se fornecido
        if filtro_nome and filtro_nome.strip():
            filtro_lower = filtro_nome.lower().strip()
            df_completo = df_completo[
                df_completo['nome'].str.lower().str.contains(filtro_lower, na=False)
            ]
        
        # Ordenar por ID decrescente (mais recentes primeiro)
        df_completo = df_completo.sort_values('id', ascending=False)
        
        # Aplicar limite de itens
        df_completo = df_completo.head(limite_itens)
        
        if df_completo.empty:
            if filtro_nome and filtro_nome.strip():
                return html.P(f"Nenhuma saída encontrada para produtos contendo '{filtro_nome}'.", className="text-muted text-center")
            else:
                return html.P("Nenhuma saída registrada.", className="text-muted text-center")
        
        # Criar linhas da tabela
        linhas_tabela = []
        
        # Cabeçalho
        cabecalho = html.Thead([
            html.Tr([
                html.Th("ID", style={'backgroundColor': '#02083d', 'color': 'white', 'textAlign': 'center', 'padding': '8px'}),
                html.Th("Produto", style={'backgroundColor': '#02083d', 'color': 'white', 'textAlign': 'center', 'padding': '8px'}),
                html.Th("NFE", style={'backgroundColor': '#02083d', 'color': 'white', 'textAlign': 'center', 'padding': '8px'}),
                html.Th("Quantidade", style={'backgroundColor': '#02083d', 'color': 'white', 'textAlign': 'center', 'padding': '8px'}),
                html.Th("Descrição", style={'backgroundColor': '#02083d', 'color': 'white', 'textAlign': 'center', 'padding': '8px'}),
                html.Th("Observação", style={'backgroundColor': '#02083d', 'color': 'white', 'textAlign': 'center', 'padding': '8px'}),
                html.Th("Ações", style={'backgroundColor': '#02083d', 'color': 'white', 'textAlign': 'center', 'padding': '8px'}),
            ])
        ])
        
        # Corpo da tabela
        for _, row in df_completo.iterrows():
            saida_id = int(row['id']) if pd.notna(row['id']) else 0
            
            linhas_tabela.append(
                html.Tr([
                    html.Td(str(saida_id), style={'textAlign': 'center', 'padding': '6px', 'border': '1px solid #ddd'}),
                    html.Td(
                        str(f"{row['produto_id']} - {row['nome']}") if pd.notna(row['produto_id']) and pd.notna(row['nome']) else 'N/A',
                        style={'textAlign': 'center', 'padding': '6px', 'border': '1px solid #ddd'}
                    ),
                    html.Td(
                        str(row['numero_nfe']) if pd.notna(row['numero_nfe']) else 'N/A',
                        style={'textAlign': 'center', 'padding': '6px', 'border': '1px solid #ddd'}
                    ),
                    html.Td(
                        str(int(row['quantidade'])) if pd.notna(row['quantidade']) else '0',
                        style={'textAlign': 'center', 'padding': '6px', 'border': '1px solid #ddd'}
                    ),
                    html.Td(
                        str(row['descricao']) if pd.notna(row['descricao']) else 'N/A',
                        style={'textAlign': 'center', 'padding': '6px', 'border': '1px solid #ddd'}
                    ),
                    html.Td(
                        str(row['observacao']) if pd.notna(row['observacao']) else 'N/A',
                        style={'textAlign': 'center', 'padding': '6px', 'border': '1px solid #ddd'}
                    ),
                    html.Td([
                        dbc.Button(
                            "✏️",
                            id={"type": "btn-editar", "index": saida_id},
                            color="warning",
                            size="sm",
                            className="me-1"
                        ),
                        dbc.Button(
                            "🗑️",
                            id={"type": "btn-excluir", "index": saida_id},
                            color="danger",
                            size="sm"
                        )
                    ], style={'textAlign': 'center', 'padding': '6px', 'border': '1px solid #ddd'})
                ])
            )
        
        corpo_tabela = html.Tbody(linhas_tabela)
        
        # Tabela completa
        tabela_html = html.Div([
            html.Table([
                cabecalho,
                corpo_tabela
            ], className="table table-striped", style={'width': '100%'})
        ], style={'height': '400px', 'overflowY': 'auto'})
        
        return tabela_html
        
    except Exception as e:
        return html.Div([
            html.P(f"Erro ao carregar dados: {str(e)}", className="text-danger")
        ])
