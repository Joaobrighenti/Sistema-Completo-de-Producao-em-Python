import dash_bootstrap_components as dbc
import dash
from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State
from datetime import datetime, date
from app import app
from banco_dados.banco import ORDEM_COMPRA, PRODUTO_COMPRAS, FORNECEDORES, Banco
from compras.formularios.form_cotacao import get_form_cotacao
import pandas as pd
import base64
import os
import uuid
from pathlib import Path
from PIL import Image
import io

# Instanciando a classe Banco
banco = Banco()


# Layout do formulário de Ordem de Compra
def get_form():
    current_date = date.today()
    
    return html.Div([
        dcc.Store(id='store-cotacao-update', data=0),
        # Modal principal da Ordem de Compra
        dbc.Modal(
            [
                dbc.ModalHeader("Cadastro de Ordem de Compra"),
                dbc.ModalBody([
                    dbc.Row([
                        # Coluna da Esquerda: Formulário Principal
                        dbc.Col([
                            dbc.Form([
                                # Primeira linha
                                html.Div([
                                    html.H6("Informações Básicas", className="p-2 mb-2")
                                ], style={"background-color": "#e9ecef", "width": "100%", "text-align": "left", "border-radius": "5px", "border": "1px solid #ced4da"}),
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Nº Solicitação"),
                                        dbc.Input(id="oc-solicitacao", type="text", disabled=True, size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Solicitante"),
                                        dbc.Input(id="oc-solicitante", type="text", disabled=True, size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Setor"),
                                        dbc.Input(id="oc-setor", type="text", disabled=True, size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Número da OC"),
                                        dbc.Input(id="oc-numero", type="text", placeholder="Número OC", size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Status*"),
                                        dbc.Select(
                                            id="oc-status",
                                            options=[
                                                {"label": "Solicitar ao Fornecedor", "value": "Solicitar ao Fornecedor"},
                                                {"label": "Aguardando Aprovação", "value": "Aguardando Aprovação"},
                                                {"label": "Aguardando Recebimento", "value": "Aguardando Recebimento"},
                                                {"label": "Entregue Parcial", "value": "Entregue Parcial"},
                                                {"label": "Entregue Total", "value": "Entregue Total"},
                                                {"label": "Cancelado", "value": "Cancelado"}
                                            ],
                                            value="solicitar_fornecedor",
                                            size="sm"
                                        ),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Data Necessária"),
                                        dcc.DatePickerSingle(
                                            id="oc-data-necessaria",
                                            placeholder="Data",
                                            display_format="DD/MM/YYYY",
                                            style={"width": "100%"},
                                        ),
                                    ], width=2),
                                ], className="mb-2"),
                                
                                # Segunda linha - Produtos e quantidades
                                html.Div([
                                    html.H6("Produto e Quantidades", className="p-2 mb-2")
                                ], style={"background-color": "#e9ecef", "width": "100%", "text-align": "left", "border-radius": "5px", "margin-top": "15px", "border": "1px solid #ced4da"}),
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Nome da Solicitação"),
                                        dbc.Input(id="oc-nome-solicitacao", type="text", placeholder="Nome da solicitação", size="sm"),
                                    ], width=12),
                                ], className="mb-2"),
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Produto"),
                                        dbc.InputGroup([
                                            dcc.Dropdown(
                                                id="oc-produto-id",
                                                options=[],
                                                searchable=True,
                                                clearable=True,
                                                placeholder="Digite para pesquisar...",
                                                style={"width": "90%"}
                                            ),
                                            dbc.Button("+", id="btn-add-produto", color="success", size="sm", className="ms-1", style={"width": "30px"})
                                        ]),
                                    ], width=12),
                                ], className="mb-2"),
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Fornecedor"),
                                        dbc.Select(
                                            id="oc-fornecedor-id",
                                            options=[],
                                            size="sm"
                                        ),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Un. Compra*"),
                                        dbc.Select(
                                            id="oc-unid-compra",
                                            options=[
                                                {"label": "UN", "value": "UN"}, {"label": "KG", "value": "KG"},
                                                {"label": "CX", "value": "CX"}, {"label": "PC", "value": "PC"},
                                                {"label": "FLS", "value": "FLS"}, {"label": "BOB", "value": "BOB"},
                                                {"label": "LT", "value": "LT"}, {"label": "RL", "value": "RL"}
                                            ],
                                            placeholder="Selecione",
                                            size="sm"
                                        ),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Qtd. Solicitada*"),
                                        dbc.Input(id="oc-qtd-solicitada", type="number", placeholder="Qtd.", size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("SKU"),
                                        dbc.Input(id="oc-sku", type="text", placeholder="SKU", size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("PCP ID"),
                                        dbc.Input(id="oc-pcp-id", type="text", placeholder="PCP ID", size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Qtd. Recebida"),
                                        dbc.Input(id="oc-qtd-recebida", type="number", placeholder="Qtd. recebida", size="sm"),
                                    ], width=2),
                                ], className="mb-2"),
                                
                                # Terceira linha - Valores e conversão
                                html.Div([
                                    html.H6("Valores e Conversão", className="p-2 mb-2")
                                ], style={"background-color": "#e9ecef", "width": "100%", "text-align": "left", "border-radius": "5px", "margin-top": "15px", "border": "1px solid #ced4da"}),
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Un. Conversão"),
                                        dbc.Select(
                                            id="oc-unidade-conversao",
                                            options=[
                                                {"label": "UN", "value": "UN"},
                                                {"label": "KG", "value": "KG"},
                                                {"label": "CX", "value": "CX"},
                                                {"label": "PC", "value": "PC"},
                                                {"label": "FLS", "value": "FLS"},
                                                {"label": "BOB", "value": "BOB"},
                                                {"label": "LT", "value": "LT"},
                                                {"label": "RL", "value": "RL"}
                                            ],
                                            placeholder="Selecione",
                                            size="sm"
                                        ),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Conversão"),
                                        dbc.Input(id="oc-conversao", type="number", placeholder="Fator", size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Valor Unit.*"),
                                        dbc.Input(id="oc-valor-unit", type="number", placeholder="Valor", size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("IPI (%)*"),
                                        dbc.Input(id="oc-ipi", type="number", placeholder="IPI", size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("ICMS (%)*"),
                                        dbc.Input(id="oc-icms", type="number", placeholder="ICMS", size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Frete (R$)"),
                                        dbc.Input(id="oc-frete", type="number", placeholder="Frete", size="sm"),
                                    ], width=2),
                                ], className="mb-2"),
                                
                                # Quarta linha - Datas e Observações
                                html.Div([
                                    html.H6("Datas e Observações", className="p-2 mb-2")
                                ], style={"background-color": "#e9ecef", "width": "100%", "text-align": "left", "border-radius": "5px", "margin-top": "15px", "border": "1px solid #ced4da"}),
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Data Emissão"),
                                        dcc.DatePickerSingle(
                                            id="oc-data-emissao",
                                            placeholder="Data",
                                            display_format="DD/MM/YYYY",
                                            date=current_date,
                                            style={"width": "100%"},
                                        ),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Data Entrega*"),
                                        dcc.DatePickerSingle(
                                            id="oc-data-entrega",
                                            placeholder="Data",
                                            display_format="DD/MM/YYYY",
                                            style={"width": "100%"},
                                        ),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Categoria"),
                                        dbc.Select(id="oc-categoria-id", options=[], placeholder="Selecione", size="sm"),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Informações do Fornecedor"),
                                        html.Div(
                                            id="fornecedor-info-display",
                                            style={
                                                "border": "1px solid #dee2e6",
                                                "border-radius": "5px",
                                                "padding": "8px",
                                                "background-color": "#f8f9fa",
                                                "min-height": "60px",
                                                "font-size": "12px"
                                            },
                                            children="Selecione um fornecedor para ver suas informações"
                                        ),
                                    ], width=4),
                                    dbc.Col([
                                        dbc.Label("Custo x Orçamento (%)"),
                                        html.Div(id='valor-alvo-display', style={
                                                "border": "1px solid #dee2e6",
                                                "border-radius": "5px",
                                                "padding": "8px",
                                                "background-color": "#f8f9fa",
                                                "min-height": "60px",
                                                "font-size": "12px"
                                            })
                                    ], width=2),
                                ], className="mb-2"),
                                
                                # Quinta linha - Observação
                                dbc.Row([
                                    dbc.Col([
                                        dbc.Label("Nota Fiscal"),
                                        dbc.Input(
                                            id="oc-nota",
                                            type="text",
                                            placeholder="Número da NF",
                                            size="sm"
                                        ),
                                    ], width=2),
                                    dbc.Col([
                                        dbc.Label("Observação"),
                                        dbc.Textarea(
                                            id="oc-observacao",
                                            placeholder="Observações",
                                            style={"height": "38px"},
                                            size="sm"
                                        ),
                                    ], width=10),
                                ], className="mb-2"),
                                
                                # Campos ocultos
                                dbc.Input(id="oc-id", type="hidden"),
                                
                                # Mensagem de feedback
                                html.Div(id="feedback-form-oc", className="mt-2"),
                            ]),
                        ], width=8),

                        # Coluna da Direita: Cotações
                        dbc.Col([
                            html.Div([
                                dbc.Row([
                                    dbc.Col(html.H5("Cotações"), width="auto"),
                                    dbc.Col(dbc.Button("Adicionar Cotação", id="btn-abrir-modal-cotacao", color="success", size="sm"), width="auto")
                                ], justify="between", align="center"),
                                html.Hr(),
                                dbc.Alert(
                                    id="feedback-lista-cotacoes",
                                    color="light",
                                    is_open=False,
                                    duration=4000,  # A mensagem desaparecerá após 4 segundos
                                    dismissable=True,
                                ),
                                html.Div(id="lista-cotacoes", className="mt-3", style={"max-height": "70vh", "overflow-y": "auto"})
                            ])
                        ], width=4, style={"border-left": "1px solid #dee2e6", "padding-left": "15px"})
                    ])
                ]),
                dbc.ModalFooter([
                    dbc.Button("Fechar", id="btn-fechar-oc", className="me-2", color="secondary", size="sm"),
                    dbc.Button("Excluir", id="btn-excluir-oc", className="me-2", color="danger", size="sm"),
                    dbc.Button("Salvar", id="btn-salvar-oc", className="ms-auto", color="primary", size="sm"),
                ]),
            ],
            id="modal-form-oc",
            size="xl",  # Modal extra grande
        ),
        
        # Modal para adicionar produto rapidamente
        dbc.Modal(
            [
                dbc.ModalHeader("Adicionar Produto"),
                dbc.ModalBody([
                    dbc.Form([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Nome do Produto"),
                                dbc.Input(id="produto-nome", type="text", placeholder="Informe o nome do produto"),
                            ], width=12),
                        ], className="mb-3"),
                        # Mensagem de feedback
                        html.Div(id="feedback-form-produto", className="mt-2"),
                    ]),
                ]),
                dbc.ModalFooter([
                    dbc.Button("Cancelar", id="btn-cancelar-produto", className="me-2", color="secondary", size="sm"),
                    dbc.Button("Adicionar", id="btn-salvar-produto", className="ms-auto", color="success", size="sm"),
                ]),
            ],
            id="modal-add-produto",
            size="md",
        ),
        
        # Modal para confirmação de exclusão
        dbc.Modal([
            dbc.ModalHeader("Confirmar Exclusão"),
            dbc.ModalBody([
                html.P("Tem certeza que deseja excluir esta ordem de compra?"),
                html.P("Esta ação não pode ser desfeita.", className="text-danger fw-bold"),
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="btn-cancelar-exclusao", color="secondary", size="sm"),
                dbc.Button("Confirmar Exclusão", id="btn-confirmar-exclusao", color="danger", size="sm"),
            ]),
        ], id="modal-confirmar-exclusao", is_open=False),
        
        # Adicionar o formulário de cotação
        get_form_cotacao(),
        
        # Modal para visualizar a imagem da cotação
        dbc.Modal(
            [
                dbc.ModalHeader("Imagem da Cotação"),
                dbc.ModalBody(html.Img(id="imagem-modal-content", style={"width": "100%"})),
            ],
            id="modal-imagem-cotacao",
            size="lg",
            is_open=False,
            centered=True,
        ),
    ])

# Callbacks

# Callback para fechar o modal da Ordem de Compra
@app.callback(
    Output("modal-form-oc", "is_open", allow_duplicate=True),
    [
        Input("btn-fechar-oc", "n_clicks"),
    ],
    prevent_initial_call=True
)
def toggle_modal_close(n_fechar):
    if callback_context.triggered_id == "btn-fechar-oc":
        return False
    return dash.no_update  # Não alteramos o estado do modal em outros casos

# Callback para abrir o modal de adicionar produto
@app.callback(
    Output("modal-add-produto", "is_open"),
    [
        Input("btn-add-produto", "n_clicks"),
        Input("btn-cancelar-produto", "n_clicks"),
        Input("btn-salvar-produto", "n_clicks"),
    ],
    [State("modal-add-produto", "is_open")],
)
def toggle_modal_produto(n_add, n_cancelar, n_salvar, is_open):
    if callback_context.triggered_id == "btn-add-produto":
        return True
    elif callback_context.triggered_id in ["btn-cancelar-produto", "btn-salvar-produto"]:
        return False
    return is_open

# Callback combinado para gerenciar produtos e fornecedores
@app.callback(
    [
        Output("oc-produto-id", "options"),
        Output("oc-fornecedor-id", "options"),
        Output("oc-categoria-id", "options"),
        Output("feedback-form-produto", "children")
    ],
    [
        Input("modal-form-oc", "is_open"),
        Input("btn-salvar-produto", "n_clicks")
    ],
    [
        State("produto-nome", "value")
    ]
)
def gerenciar_produtos_e_fornecedores(modal_is_open, n_salvar_produto, nome_produto):
    triggered_id = callback_context.triggered_id
    
    # Inicializar variáveis de retorno
    produto_options = []
    fornecedor_options = []
    categoria_options = []
    feedback_message = ""
    
    try:
        # Carregar fornecedores (sempre)
        df_fornecedores = banco.ler_tabela("fornecedores")
        if not df_fornecedores.empty:
            fornecedor_options = [{"label": row['for_nome'], "value": row['for_id']} for _, row in df_fornecedores.iterrows()]
        else:
            fornecedor_options = [{"label": "Nenhum fornecedor encontrado", "value": ""}]

        # Carregar categorias (sempre)
        df_categorias = banco.ler_tabela("categoria_compras")
        if not df_categorias.empty:
            categoria_options = [{"label": row['categoria_nome'], "value": row['id_categoria']} for _, row in df_categorias.iterrows()]
        else:
            categoria_options = [{"label": "Nenhuma categoria encontrada", "value": ""}]
        
        # Salvar produto se o botão foi clicado
        if triggered_id == "btn-salvar-produto" and n_salvar_produto and nome_produto:
            # Inserir o novo produto no banco de dados
            dados = {"nome": nome_produto}
            banco.inserir_dados("produto_compras", **dados)
            feedback_message = dbc.Alert("Produto adicionado com sucesso!", color="success")
        
        # Carregar lista de produtos (sempre)
        df_produtos = banco.ler_tabela("produto_compras")
        if not df_produtos.empty:
            produto_options = [{"label": row['nome'], "value": row['prod_comp_id']} for _, row in df_produtos.iterrows()]
        else:
            produto_options = [{"label": "Nenhum produto encontrado", "value": ""}]
        
    except Exception as e:
        print(f"Erro ao gerenciar produtos e fornecedores: {e}")
        import traceback
        traceback.print_exc()
        
        # Se o erro ocorreu ao salvar o produto, mostrar feedback
        if triggered_id == "btn-salvar-produto":
            feedback_message = dbc.Alert(f"Erro ao salvar produto: {str(e)}", color="danger")
    
    return produto_options, fornecedor_options, categoria_options, feedback_message

# Callback para salvar a ordem de compra
@app.callback(
    Output("feedback-form-oc", "children"),
    Input("btn-salvar-oc", "n_clicks"),
    [
        State("oc-id", "value"),
        State("oc-nome-solicitacao", "value"),
        State("oc-solicitacao", "value"),
        State("oc-solicitante", "value"),
        State("oc-setor", "value"),
        State("oc-numero", "value"),
        State("oc-produto-id", "value"),
        State("oc-fornecedor-id", "value"),
        State("oc-sku", "value"),
        State("oc-status", "value"),
        State("oc-qtd-solicitada", "value"),
        State("oc-qtd-recebida", "value"),
        State("oc-unid-compra", "value"),
        State("oc-conversao", "value"),
        State("oc-unidade-conversao", "value"),
        State("oc-valor-unit", "value"),
        State("oc-ipi", "value"),
        State("oc-icms", "value"),
        State("oc-frete", "value"),
        State("oc-data-necessaria", "date"),
        State("oc-data-emissao", "date"),
        State("oc-data-entrega", "date"),
        State("oc-observacao", "value"),
        State("oc-pcp-id", "value"),
        State("oc-nota", "value"),
        State("oc-categoria-id", "value"),
    ],
)
def salvar_ordem_compra(n_clicks, oc_id, nome_solicitacao, solicitacao, solicitante, setor, numero, 
                       produto_id, fornecedor_id, sku, status, qtd_solicitada, qtd_recebida, 
                       unid_compra, conversao, unidade_conversao, valor_unit, ipi, icms, frete, 
                       data_necessaria, data_emissao, data_entrega, observacao, pcp_id, oc_nota, categoria_id):
    if not n_clicks:
        return ""
    
    # Validação de campos obrigatórios
    erros = []
    if not status:
        erros.append("Status")
    if not unid_compra:
        erros.append("Un. Compra")
    if qtd_solicitada is None or str(qtd_solicitada).strip() == '':
        erros.append("Qtd. Solicitada")
    if valor_unit is None or str(valor_unit).strip() == '':
        erros.append("Valor Unit.")
    if ipi is None or str(ipi).strip() == '':
        erros.append("IPI (%)")
    if icms is None or str(icms).strip() == '':
        erros.append("ICMS (%)")


    if erros:
        return dbc.Alert(f"Os seguintes campos são obrigatórios: {', '.join(erros)}.", color="danger")

    try:
        # Converter valores numéricos - ajustar para tratar strings vazias
        if qtd_solicitada and str(qtd_solicitada).strip() != '':
            qtd_solicitada = float(qtd_solicitada)
        else:
            qtd_solicitada = None
            
        if qtd_recebida and str(qtd_recebida).strip() != '':
            qtd_recebida = float(qtd_recebida)
        else:
            qtd_recebida = None
            
        if conversao and str(conversao).strip() != '':
            conversao = float(conversao)
        else:
            conversao = None
            
        if valor_unit and str(valor_unit).strip() != '':
            valor_unit = float(valor_unit)
        else:
            valor_unit = None
            
        if ipi and str(ipi).strip() != '':
            ipi = float(ipi)
        else:
            ipi = None
            
        if icms and str(icms).strip() != '':
            icms = float(icms)
        else:
            icms = None
            
        if frete and str(frete).strip() != '':
            frete = float(frete)
        else:
            frete = None
            
        if pcp_id and str(pcp_id).strip() != '':
            pcp_id = int(pcp_id)
        else:
            pcp_id = None
        
        # Converter datas de string para objetos date
        # As datas vêm no formato ISO 'YYYY-MM-DD' do componente DatePickerSingle
        if data_necessaria:
            if isinstance(data_necessaria, str):
                data_necessaria = datetime.strptime(data_necessaria, '%Y-%m-%d').date()
        
        if data_emissao:
            if isinstance(data_emissao, str):
                data_emissao = datetime.strptime(data_emissao, '%Y-%m-%d').date()
        else:
            # Se não for fornecida, usar a data atual
            data_emissao = date.today()
        
        if data_entrega:
            if isinstance(data_entrega, str):
                data_entrega = datetime.strptime(data_entrega, '%Y-%m-%d').date()
        
        # Preparar os dados para inserção/atualização
        dados = {}
        
        # Adicionar apenas os campos que têm valor
        if nome_solicitacao:
            dados["oc_nome_solicitacao"] = nome_solicitacao
        if solicitacao:
            dados["oc_solicitacao"] = solicitacao
        if solicitante:
            dados["oc_solicitante"] = solicitante
        if setor:
            dados["oc_setor"] = setor
        if numero:
            dados["oc_numero"] = numero
        if produto_id and produto_id != '':
            dados["oc_produto_id"] = produto_id
        if fornecedor_id and fornecedor_id != '':
            dados["oc_fornecedor_id"] = fornecedor_id
        if sku:
            dados["oc_sku"] = sku
        if status:
            dados["oc_status"] = status
        if qtd_solicitada is not None:
            dados["oc_qtd_solicitada"] = qtd_solicitada
        if qtd_recebida is not None:
            dados["oc_qtd_recebida"] = qtd_recebida
        if unid_compra:
            dados["oc_unid_compra"] = unid_compra
        if conversao is not None:
            dados["oc_conversao"] = conversao
        if unidade_conversao:
            dados["oc_unidade_conversao"] = unidade_conversao
        if valor_unit is not None:
            dados["oc_valor_unit"] = valor_unit
        if ipi is not None:
            dados["oc_ipi"] = ipi
        if icms is not None:
            dados["oc_icms"] = icms
        if frete is not None:
            dados["oc_frete"] = frete
        if data_necessaria:
            dados["oc_data_necessaria"] = data_necessaria
        if data_emissao:
            dados["oc_data_emissao"] = data_emissao
        if data_entrega:
            dados["oc_data_entrega"] = data_entrega
        if observacao:
            dados["oc_observacao"] = observacao
        if pcp_id is not None:
            dados["oc_pcp_id"] = pcp_id
        if oc_nota:
            dados["oc_nota"] = oc_nota
        if categoria_id:
            dados["oc_categoria_id"] = categoria_id
        
        # Usar a classe Banco para inserir ou editar dados
        if oc_id:
            # Atualizar ordem existente
            resultado = banco.editar_dado("ordem_compra", oc_id, **dados)
            if resultado:
                return dbc.Alert("Ordem de compra atualizada com sucesso!", color="success")
            else:
                return dbc.Alert("Não foi possível atualizar a ordem de compra.", color="danger")
        else:
            # Criar nova ordem
            banco.inserir_dados("ordem_compra", **dados)
            return dbc.Alert("Ordem de compra criada com sucesso!", color="success")
            
    except Exception as e:
        print(f"Erro ao salvar ordem de compra: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Erro ao salvar ordem de compra: {str(e)}", color="danger")

# Callback para controlar o modal de confirmação de exclusão
@app.callback(
    Output("modal-confirmar-exclusao", "is_open", allow_duplicate=True),
    [
        Input("btn-excluir-oc", "n_clicks"),
        Input("btn-cancelar-exclusao", "n_clicks"),
        Input("btn-confirmar-exclusao", "n_clicks")
    ],
    [State("modal-confirmar-exclusao", "is_open"),
     State("oc-id", "value")],
    prevent_initial_call=True
)
def toggle_modal_exclusao(n_excluir, n_cancelar, n_confirmar, is_open, oc_id):
    ctx = callback_context
    
    if not ctx.triggered:
        return is_open
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Abrir modal apenas se há uma ordem para excluir
    if trigger_id == "btn-excluir-oc" and oc_id:
        return True
    elif trigger_id == "btn-excluir-oc" and not oc_id:
        # Se não há ID, não abrir o modal (não há nada para excluir)
        return False
    elif trigger_id in ["btn-cancelar-exclusao", "btn-confirmar-exclusao"]:
        return False
    
    return is_open

# Callback para excluir a ordem de compra
@app.callback(
    [Output("feedback-form-oc", "children", allow_duplicate=True),
     Output("modal-form-oc", "is_open", allow_duplicate=True)],
    Input("btn-confirmar-exclusao", "n_clicks"),
    State("oc-id", "value"),
    prevent_initial_call=True
)
def excluir_ordem_compra(n_clicks, oc_id):
    if not n_clicks or not oc_id:
        raise dash.exceptions.PreventUpdate
    
    try:
        # Usar a classe Banco para excluir a ordem
        resultado = banco.deletar_dado("ordem_compra", oc_id)
        
        if resultado:
            return (
                dbc.Alert("Ordem de compra excluída com sucesso!", color="success"),
                False  # Fechar o modal principal
            )
        else:
            return (
                dbc.Alert("Não foi possível excluir a ordem de compra.", color="danger"),
                dash.no_update
            )
            
    except Exception as e:
        print(f"Erro ao excluir ordem de compra: {e}")
        import traceback
        traceback.print_exc()
        return (
            dbc.Alert(f"Erro ao excluir ordem de compra: {str(e)}", color="danger"),
            dash.no_update
        )

# Callback para o cálculo do valor alvo
@app.callback(
    Output("valor-alvo-display", "children"),
    [
        Input("oc-valor-unit", "value"),
        Input("oc-qtd-solicitada", "value"),
        Input("oc-conversao", "value"),
        Input("oc-categoria-id", "value"),
    ]
)
def calcular_valor_alvo(valor_unit, qtd_solicitada, conversao, categoria_id):
    if not all([valor_unit, qtd_solicitada, conversao, categoria_id]):
        return ""

    try:
        valor_unit = float(valor_unit)
        qtd_solicitada = float(qtd_solicitada)
        conversao = float(conversao)
        categoria_id = int(categoria_id)

        df_valor_alvo = banco.ler_tabela('valor_alvo')
        
        if df_valor_alvo.empty:
            return "N/A"
            
        df_categoria = df_valor_alvo[df_valor_alvo['categoria_id'] == categoria_id]
        
        if df_categoria.empty:
            return "N/A"

        df_categoria['data'] = pd.to_datetime(df_categoria['data'])
        preco_alvo = df_categoria.sort_values('data', ascending=False).iloc[0]['preco']
        
        if preco_alvo is None or preco_alvo == 0:
            return "Preço Alvo Inválido"

        numerador = valor_unit * qtd_solicitada
        denominador = preco_alvo * conversao * qtd_solicitada

        if denominador == 0:
            return "Orçamento é zero"
        
        resultado = numerador / denominador
        
        return html.Div([
            html.Div(f"Custo: R$ {numerador:,.2f}"),
            html.Div(f"Orçamento: R$ {denominador:,.2f}"),
            html.Hr(style={'margin': '2px 0'}),
            html.Strong(f"{resultado:.2%}", style={'font-size': '16px', 'color': 'blue' if resultado <= 1 else 'red'})
        ])

    except (ValueError, TypeError, IndexError):
        return "Cálc. inválido"
    except Exception as e:
        print(f"Erro no cálculo do valor alvo: {e}")
        return "Erro"

# Callback para exibir informações do fornecedor selecionado
@app.callback(
    Output("fornecedor-info-display", "children"),
    Input("oc-fornecedor-id", "value"),
    prevent_initial_call=False
)
def exibir_info_fornecedor(fornecedor_id):
    if not fornecedor_id or fornecedor_id == "":
        return "Selecione um fornecedor para ver suas informações"
    
    try:
        # Mapeamento para formas de pagamento
        formas_pagamento_map = {
            "avista": "À vista",
            "boleto": "Boleto",
            "cartao_credito": "Cartão de Crédito",
            "cartao_debito": "Cartão de Débito",
            "transferencia": "Transferência Bancária",
            "pix": "PIX",
            "cheque": "Cheque",
            "crediario": "Crediário"
        }
        
        # Buscar informações do fornecedor
        df_fornecedores = banco.ler_tabela("fornecedores")
        
        # Certificar que o fornecedor_id é um inteiro
        try:
            fornecedor_id = int(fornecedor_id)
        except (ValueError, TypeError):
            return "ID do fornecedor inválido"
        
        fornecedor = df_fornecedores[df_fornecedores['for_id'] == fornecedor_id]
        
        if fornecedor.empty:
            return "Fornecedor não encontrado"
        
        fornecedor_data = fornecedor.iloc[0]
        
        # Obter forma de pagamento formatada
        forma_pagamento = fornecedor_data.get('for_forma_pagamento', '')
        forma_pagamento_display = formas_pagamento_map.get(forma_pagamento, forma_pagamento or 'Não informado')
        
        # Criar layout com as informações do fornecedor
        info_layout = html.Div([
            html.Div([
                html.Strong("Nome: "),
                html.Span(fornecedor_data['for_nome'], style={"color": "#0066cc"})
            ], className="mb-1"),
            html.Div([
                html.Strong("Prazo de Pagamento: "),
                html.Span(str(fornecedor_data.get('for_prazo', 'Não informado')), style={"color": "#28a745"})
            ], className="mb-1"),
            html.Div([
                html.Strong("Forma de Pagamento: "),
                html.Span(forma_pagamento_display, style={"color": "#dc3545"})
            ], className="mb-1"),
            html.Div([
                html.Strong("Observações: "),
                html.Span(
                    fornecedor_data.get('for_observacao', 'Nenhuma observação') if fornecedor_data.get('for_observacao') else 'Nenhuma observação',
                    style={"color": "#6c757d", "font-style": "italic"}
                )
            ], className="mb-1")
        ])
        
        return info_layout
        
    except Exception as e:
        print(f"Erro ao buscar informações do fornecedor: {e}")
        import traceback
        traceback.print_exc()
        return "Erro ao carregar informações do fornecedor" 

# =================================================================================================
# Callbacks para Cotações
# =================================================================================================

# Callback para abrir/fechar o modal de cotação e carregar fornecedores
@app.callback(
    [Output("modal-form-cotacao", "is_open"),
     Output("cot-id", "value", allow_duplicate=True),
     Output("cot-valor-unit", "value", allow_duplicate=True),
     Output("cot-ipi", "value", allow_duplicate=True),
     Output("cot-icms", "value", allow_duplicate=True),
     Output("cot-valor-entrada", "value", allow_duplicate=True),
     Output("cot-condicao-pagamento", "value", allow_duplicate=True),
     Output("cot-forma-pagamento", "value", allow_duplicate=True),
     Output("cot-observacao", "value", allow_duplicate=True),
     Output("output-cotacao-imagem-upload", "children", allow_duplicate=True),
     Output("cot-fornecedor-id", "options")],


    [Input("btn-abrir-modal-cotacao", "n_clicks"),
     Input({"type": "editar-cotacao", "index": dash.dependencies.ALL}, "n_clicks"),
     Input("btn-fechar-cotacao", "n_clicks")],
     
    [State("modal-form-cotacao", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_cotacao(n_abrir, editar_cotacao, n_fechar, is_open):
    
    fornecedor_options = []
    try:
        df_fornecedores = banco.ler_tabela("fornecedores")
        if not df_fornecedores.empty:
            fornecedor_options = [{"label": row['for_nome'], "value": row['for_id']} for _, row in df_fornecedores.iterrows()]
    except Exception as e:
        print(f"Erro ao carregar fornecedores: {e}")

    if n_abrir or n_fechar:
        if n_abrir:
            return not is_open, None, None, None, None, None, None, None, None, None, fornecedor_options
        return not is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, fornecedor_options
    
    return is_open, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, fornecedor_options


# Callback para carregar as cotações na lista
@app.callback(
    Output("lista-cotacoes", "children"),
    [Input("modal-form-oc", "is_open"), 
     Input("store-cotacao-update", "data"),
    Input("oc-id", "value"),
    ],
    prevent_initial_call=True,
)
def carregar_cotacoes(is_open, update_trigger, oc_id):
    #ctx = callback_context
    #triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if not (is_open and oc_id):
        raise dash.exceptions.PreventUpdate
    try:
        # Join para buscar o nome do fornecedor
        query = """
        SELECT cot.*, forn.for_nome 
        FROM cotacao cot 
        LEFT JOIN fornecedores forn ON cot.fornecedor_id = forn.for_id
        WHERE cot.oc_id = :oc_id
        """
        df_cotacoes = pd.read_sql(query, banco.engine, params={"oc_id": oc_id})

        if df_cotacoes.empty:
            return dbc.Alert("Nenhuma cotação encontrada.", color="info")
        
        cards_cotacoes = []
        for _, row in df_cotacoes.iterrows():
            imagem_src = ""
            if row['imagem']:
                path = Path(row['imagem']).as_posix()
                if path.startswith('assets/'):
                    imagem_src = app.get_asset_url(path.replace('assets/', '', 1))
                else:
                    imagem_src = app.get_asset_url(path)

            fornecedor_nome = row.get('for_nome', 'Fornecedor não definido')
            card_content = dbc.Row([
                # Coluna Esquerda: Detalhes e Botões
                dbc.Col([
                    dbc.Row([
dbc.Col([
    dbc.Row([
        dbc.Col(html.H6(f"Cot. ID: {row['cot_id']}"), width='auto'),
        dbc.Col(html.P(f"{fornecedor_nome}", className="text-info"), width='auto'),
    ], align="center"),
    dbc.Row([
        dbc.Col(html.P(f"Obs: {row['observacao'] or 'N/A'}", className="text-muted"), width=12)
    ]),
])
]),
                    html.P([
                        f"Valor Unit: R$ {row['valor_unit']:.2f}",
                        html.Span(
                            f"  (c/ IPI: R$ {row['valor_unit'] + (row['valor_unit'] * row['ipi'] / 100):.2f})" if row['ipi'] is not None else "",
                            style={"marginLeft": "8px", "color": "#888", "fontSize": "90%"}
                        )
                    ], className="mb-1"),
                    html.P(f"Valor Entrada: R$ {row['valor_entrada']:.2f}" if row['valor_entrada'] else "Valor Entrada: N/A", className="mb-1"),
                    html.P(f"Cond. Pagamento: {row['condicao_pagamento'] or 'N/A'}", className="mb-1"),
                    html.P(f"Forma Pagamento: {row['forma_pagamento'] or 'N/A'}", className="mb-1"),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col(dbc.Button("Editar", id={"type": "editar-cotacao", "index": row['cot_id']}, color="primary", size="sm"), width="auto"),
                        dbc.Col(dbc.Button("Excluir", id={"type": "excluir-cotacao", "index": row['cot_id']}, color="danger", size="sm"), width="auto")
                    ]),
                ], width=7),
                
                # Coluna Direita: Imagem
                dbc.Col(
                    html.A(
                        html.Img(src=imagem_src, style={'height': '150px', 'max-width': '100%', 'object-fit': 'cover'}),
                        id={"type": "abrir-imagem-cotacao", "index": row['cot_id']},
                        href="#",
                    ) if imagem_src else html.Div("Nenhuma imagem", className="text-center text-muted"),
                    width=5,
                    className="d-flex align-items-center justify-content-center"
                )
            ])
            
            card = dbc.Card(dbc.CardBody(card_content), className="mb-2")
            cards_cotacoes.append(card)
        
        return cards_cotacoes
    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Erro ao carregar cotações: {e}", color="danger")
    return ""

# Callback para abrir a imagem da cotação em um modal
@app.callback(
    [Output("modal-imagem-cotacao", "is_open"),
     Output("imagem-modal-content", "src")],
    Input({"type": "abrir-imagem-cotacao", "index": dash.dependencies.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def abrir_modal_imagem(n_clicks):
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate

    ctx = callback_context
    triggered_id_dict = eval(ctx.triggered[0]['prop_id'].split('.')[0])
    cot_id = triggered_id_dict['index']
    
    if cot_id is None:
        raise dash.exceptions.PreventUpdate
        
    try:
        df_cotacao = banco.ler_tabela("cotacao", cot_id=cot_id)
        if not df_cotacao.empty:
            imagem_path = df_cotacao.iloc[0]['imagem']
            if imagem_path:
                path = Path(imagem_path).as_posix()
                if path.startswith('assets/'):
                    imagem_src = app.get_asset_url(path.replace('assets/', '', 1))
                else:
                    imagem_src = app.get_asset_url(path)
                return True, imagem_src
    except Exception as e:
        print(f"Erro ao abrir imagem da cotação: {e}")

    return False, ""


# Callback para salvar/editar cotação
@app.callback(
    [Output("feedback-form-cotacao", "children"),
     Output("modal-form-cotacao", "is_open", allow_duplicate=True),
     Output("store-cotacao-update", "data")],
    Input("btn-salvar-cotacao", "n_clicks"),
    [State("cot-id", "value"),
     State("oc-id", "value"),
     State("cot-fornecedor-id", "value"),
     State("cot-valor-unit", "value"),
     State("cot-ipi", "value"),
     State("cot-icms", "value"),
     State("cot-valor-entrada", "value"),
     State("cot-condicao-pagamento", "value"),
     State("cot-forma-pagamento", "value"),
     State("cot-observacao", "value"),
     State("upload-cotacao-imagem", "contents"),
     State("store-cotacao-update", "data")],
     prevent_initial_call=True
)
def salvar_cotacao(n_clicks, cot_id, oc_id, fornecedor_id, valor_unit, ipi, icms, valor_entrada, cond_pag, forma_pag, obs, imagem_contents, update_trigger):
    if not n_clicks:
        return "", dash.no_update, dash.no_update
    
    if not valor_unit or not fornecedor_id:
        return dbc.Alert("Os campos 'Fornecedor' e 'Valor Unitário' são obrigatórios.", color="warning"), True, dash.no_update

    dados = {
        "oc_id": oc_id,
        "fornecedor_id": fornecedor_id,
        "valor_unit": float(valor_unit) if valor_unit else None,
        "ipi": float(ipi) if ipi else None,
        "icms": float(icms) if icms else None,
        "valor_entrada": float(valor_entrada) if valor_entrada else None,
        "condicao_pagamento": cond_pag,
        "forma_pagamento": forma_pag,
        "observacao": obs
    }

    if imagem_contents:
        content_type, content_string = imagem_contents.split(',')
        
        decoded = base64.b64decode(content_string)
        
        # Otimização da imagem com Pillow
        img = Image.open(io.BytesIO(decoded))
        
        # Redimensiona a imagem mantendo a proporção
        max_size = (800, 800)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Converte para RGB se for RGBA (para salvar em JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        upload_folder = Path('assets/cotacoes')
        upload_folder.mkdir(parents=True, exist_ok=True)
        
        # Salva em formato JPEG com qualidade otimizada
        filename = f"cotacao_{uuid.uuid4().hex}.jpg"
        filepath_server = upload_folder / filename
        
        img.save(filepath_server, "JPEG", quality=85)
            
        # Salva o caminho com barras normais (posix)
        dados['imagem'] = filepath_server.as_posix()

    try:
        if cot_id: # Edição
            banco.editar_dado("cotacao", cot_id, **dados)
            msg = "Cotação atualizada com sucesso!"
        else: # Criação
            banco.inserir_dados("cotacao", **dados)
            msg = "Cotação criada com sucesso!"
        
        return dbc.Alert(msg, color="success"), False, update_trigger + 1
    except Exception as e:
        return dbc.Alert(f"Erro ao salvar cotação: {e}", color="danger"), True, dash.no_update

# Callback para exibir a prévia da imagem no formulário de cotação
@app.callback(
    Output('output-cotacao-imagem-upload', 'children', allow_duplicate=True),
    Input('upload-cotacao-imagem', 'contents'),
    State('upload-cotacao-imagem', 'filename'),
    prevent_initial_call=True
)
def update_output(contents, filename):
    if contents is not None:
        return html.Div([
            html.P(f"Arquivo selecionado: {filename}"),
            html.Img(src=contents, style={'height': '200px', 'margin-top': '10px'})
        ])
    return html.Div()

        
# Callback para preencher o formulário de cotação para edição
@app.callback(
    [Output("cot-id", "value"),
     Output("cot-fornecedor-id", "value"),
     Output("cot-valor-unit", "value"),
     Output("cot-ipi", "value"),
     Output("cot-icms", "value"),
     Output("cot-valor-entrada", "value"),
     Output("cot-condicao-pagamento", "value"),
     Output("cot-forma-pagamento", "value"),
     Output("cot-observacao", "value"),
     Output("modal-form-cotacao", "is_open", allow_duplicate=True),
     Output('output-cotacao-imagem-upload', 'children', allow_duplicate=True)],
    Input({"type": "editar-cotacao", "index": dash.dependencies.ALL}, "n_clicks"),
    prevent_initial_call=True
)
def preencher_form_cotacao_edicao(n_clicks):
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate

    ctx = callback_context
    cot_id = ctx.triggered[0]['prop_id'].split('.')[0]
    cot_id = eval(cot_id)['index']

    try:
        df_cotacao = banco.ler_tabela("cotacao", cot_id=cot_id)
        if not df_cotacao.empty:
            cotacao = df_cotacao.iloc[0]
            
            imagem_preview = html.Div()
            if cotacao['imagem']:
                imagem_src = app.get_asset_url(Path(cotacao['imagem']).as_posix().replace('assets/', '', 1))
                imagem_preview = html.Div([
                    html.P(f"Imagem atual: {Path(cotacao['imagem']).name}"),
                    html.Img(src=imagem_src, style={'height': '200px', 'margin-top': '10px'})
                ])

            return (
                cotacao['cot_id'],
                cotacao['fornecedor_id'],
                cotacao['valor_unit'],
                cotacao['ipi'],
                cotacao['icms'],
                cotacao['valor_entrada'],
                cotacao['condicao_pagamento'],
                cotacao['forma_pagamento'],
                cotacao['observacao'],
                True, # Abrir o modal
                imagem_preview
            )
    except Exception as e:
        print(f"Erro ao preencher formulário de cotação: {e}")

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update


# Callback para excluir cotação
@app.callback(
    [Output("feedback-lista-cotacoes", "children"),
     Output("feedback-lista-cotacoes", "is_open"),
     Output("feedback-lista-cotacoes", "color"),
     Output("store-cotacao-update", "data", allow_duplicate=True)],
    Input({"type": "excluir-cotacao", "index": dash.dependencies.ALL}, "n_clicks"),
    [State("store-cotacao-update", "data")],
    prevent_initial_call=True
)
def excluir_cotacao(n_clicks, update_trigger):
    if not any(n_clicks):
        raise dash.exceptions.PreventUpdate

    ctx = callback_context
    triggered_id_dict = eval(ctx.triggered[0]['prop_id'].split('.')[0])
    cot_id = triggered_id_dict['index']

    if cot_id is None:
        raise dash.exceptions.PreventUpdate

    try:
        banco.deletar_dado("cotacao", cot_id)
        # Retorna a mensagem de sucesso e aciona a atualização
        return "Cotação excluída com sucesso!", True, "success", (update_trigger or 0) + 1
    except Exception as e:
        # Retorna a mensagem de erro
        return f"Erro ao excluir cotação: {e}", True, "danger", dash.no_update


 