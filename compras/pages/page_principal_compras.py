from dash import html, dcc, callback_context, dash_table
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, ALL
from banco_dados.banco import *
import pandas as pd
from app import app
from datetime import datetime, timedelta, date
from dash.exceptions import PreventUpdate
import io
import json
from ..funcoes.pdf_file import generate_oc_pdf
from ..funcoes.pdf_ordem_compra import generate_ordem_compra_pdf
from ..funcoes.pdf_cotacao import generate_cotacao_comparison_pdf
from sqlalchemy import text

# Importar os formulários
from compras.formularios import form_fornecedor
from compras.formularios import form_carregamento
from compras.formularios import form_grupo
from compras.formularios import form_categoria_compra
from compras.formularios.form_ordem_compra import get_form as get_form_ordem_compra

# Instanciar o banco de dados
banco = Banco()

df_categorias = banco.ler_tabela("categoria_compras")
categoria_options = [{"label": row['categoria_nome'], "value": row['id_categoria']} for _, row in df_categorias.iterrows()] if not df_categorias.empty else []

# Status possíveis para ordens de compra
STATUS_OPTIONS = [
    "Solicitar ao Fornecedor",
    "Aguardando Aprovação",
    "Aguardando Recebimento",
    "Entregue Parcial",
    "Entregue Total",
    "Cancelado"
]

# Cores para cada status
STATUS_COLORS = {
    "Solicitar ao Fornecedor": "#f2b12e",  # Laranja claro
    "Aguardando Aprovação": "#389aba",  # Azul claro
    "Aguardando Recebimento": "#bdaa00",  # Amarelo claro
    "Entregue Parcial": "#8c0f8c",  # Lavanda
    "Entregue Total": "#00d100",  # Verde claro
    "Cancelado": "#e30022"   # Rosa claro
}

layout = html.Div([
    dcc.Store(id='compras-data-cache'),
    dcc.Interval(id='compras-interval-once', interval=1, max_intervals=1),
    html.Div(id="_", style={"display": "none"}),  # Div invisível para inicialização
    form_fornecedor.layout,
    form_carregamento.layout,
    form_grupo.layout,
    form_categoria_compra.layout,
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Solicitação"),
                    dbc.Input(id="filtro-solicitacao", type="text", placeholder="Solicitação")
                ], xl=1, lg=2, md=3, sm=6, xs=12, className="mb-2"),
                
                dbc.Col([
                    dbc.Label("Solicitante"),
                    dbc.Input(id="filtro-solicitante", type="text", placeholder="Solicitante")
                ], xl=1, lg=2, md=3, sm=6, xs=12, className="mb-2"),
                
                dbc.Col([
                    dbc.Label("Setor"),
                    dbc.Input(id="filtro-setor", type="text", placeholder="Setor")
                ], xl=1, lg=2, md=3, sm=6, xs=12, className="mb-2"),
                
                dbc.Col([
                    dbc.Label("Data Início"),
                    dcc.DatePickerSingle(id="filtro-data-inicio", className="w-100")
                ], xl=1, lg=2, md=3, sm=6, xs=12, className="mb-2"),
                
                dbc.Col([
                    dbc.Label("Data Fim"),
                    dcc.DatePickerSingle(id="filtro-data-fim", className="w-100")
                ], xl=1, lg=2, md=3, sm=6, xs=12, className="mb-2"),
                
                dbc.Col([
                    dbc.Label("Produto"),
                    dbc.Input(id="filtro-produto", type="text", placeholder="Produto")
                ], xl=2, lg=2, md=3, sm=6, xs=12, className="mb-2"),
                
                dbc.Col([
                    dbc.Label("SKU"),
                    dbc.Input(id="filtro-sku", type="text", placeholder="SKU")
                ], xl=1, lg=2, md=3, sm=6, xs=12, className="mb-2"),
                
                dbc.Col([
                    dbc.Label("Fornecedor"),
                    dcc.Dropdown(id="filtro-fornecedor", placeholder="Fornecedor", 
                                 options=[{"label": "Todos", "value": ""}, 
                                *[{"label": row["for_nome"], "value": int(row["for_id"])} 
                                for _, row in banco.ler_tabela("fornecedores").sort_values("for_nome").iterrows()]]
                        if not banco.ler_tabela("fornecedores").empty else [{"label": "Todos", "value": ""}],
                        clearable=True,
                        )
                ], xl=2, lg=4, md=6, sm=12, xs=12, className="mb-2"),

                
            dbc.Row([
                dbc.Col([
                    dbc.Label("Status"),
                    dcc.Dropdown(
                        id="filtro-status",
                        options=[{"label": s, "value": s} for s in STATUS_OPTIONS],
                        value=["Solicitar ao Fornecedor","Aguardando Aprovação", "Aguardando Recebimento"],
                        multi=True,
                        placeholder="Selecione os status"
                    )
                ], xl=12, lg=12, md=12, sm=12, xs=12, className="mb-3"),
                 dbc.Col(
                    # Using d-grid and d-md-flex for responsive button layout
                    html.Div(className="d-grid d-md-flex justify-content-md-start gap-2", children=[
                        dbc.Button("Filtrar", id="btn-filtrar", color="primary"),
                        dbc.Button("Limpar", id="btn-limpar", color="secondary"),
                        dbc.Button("Lançar", id="btn-lancar", color="success"),
                        dbc.Button("Fornecedor", id="btn-fornecedor", color="info"),
                        dbc.Button("Carregamento", id="btn-carregamento", color="warning"),
                        dbc.Button("Cotação", id="btn-cotacao", color="dark"),
                        dbc.Button("Excel", id="btn-export_excel", color="danger"),
                        dbc.Button("Grupos", id="btn_abrir_grupo", color="primary"),
                        dbc.Button("Categorias", id="btn_abrir_categoria", color="info"),
                        dbc.Button(html.I(className="fas fa-sync-alt"), id="btn-atualizar-dados", color="secondary", title="Atualizar Dados", className="ms-2"),
                    ]),
                    width=12
                ),
                
            ], align="end"),
                dcc.Download(id="download-excel-compras"),
                dcc.Download(id="download-oc-pdf"),
                dcc.Download(id="download-cotacao-pdf"),
            ])
        ])
    ], className="mb-4 mt-4"),
    
    # Armazenamento de dados para edição
    dcc.Store(id="ordem-selecionada", data=None),
    dcc.Store(id="ordens-selecionadas-lote", data=[]),  # Para armazenar seleções múltiplas
    # Armazenamento para paginação por fornecedor (mapeia chave -> página atual)
    dcc.Store(id="paginacao-fornecedor", data={}),
    # Metadados de paginação (mapeia chave -> total de páginas)
    dcc.Store(id="paginacao-metadata", data={}),
    # Paginação da lista de fornecedores por status (status -> página)
    dcc.Store(id="paginacao-suppliers", data={}),
    dcc.Store(id="paginacao-suppliers-meta", data={}),
    
    # Container para as tabelas agrupadas por status
    html.Div(id="container-tabelas-ordens"),
    
    # Modal para o formulário de Ordem de Compra
    get_form_ordem_compra(),
    
    # Modal para edição em lote ==================================================================
    dbc.Modal([
        dbc.ModalHeader("Edição em Lote"),
        dbc.ModalBody([
            html.Div([
                html.H6("Ordens Selecionadas:", className="mb-3"),
                html.Div(id="lista-ordens-selecionadas", className="mb-4 lista-ordens-selecionadas"),
                
                dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Novo Status"),
                            dbc.Select(
                                id="lote-status",
                                options=[
                                    {"label": "Manter atual", "value": ""},
                                    {"label": "Solicitar ao Fornecedor", "value": "Solicitar ao Fornecedor"},
                                    {"label": "Aguardando Aprovação", "value": "Aguardando Aprovação"},
                                    {"label": "Aguardando Recebimento", "value": "Aguardando Recebimento"},
                                    {"label": "Entregue Parcial", "value": "Entregue Parcial"},
                                    {"label": "Entregue Total", "value": "Entregue Total"},
                                    {"label": "Cancelado", "value": "Cancelado"}
                                ],
                                value="",
                                size="sm"
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Número da OC"),
                            dbc.Input(
                                id="lote-numero-oc", 
                                type="text", 
                                placeholder="Deixe vazio para manter atual",
                                size="sm"
                            ),
                        ], width=6),
                    ], className="mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Data de Entrega"),
                            dcc.DatePickerSingle(
                                id="lote-data-entrega",
                                placeholder="Deixe vazio para manter atual",
                                display_format="DD/MM/YYYY",
                                style={"width": "100%"},
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Observação (adicionar)"),
                            dbc.Textarea(
                                id="lote-observacao",
                                placeholder="Texto a ser adicionado às observações existentes",
                                style={"height": "38px"},
                                size="sm"
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Nova Categoria"),
                            dbc.Select(
                                id="lote-categoria",
                                options=[{"label": "Manter atual", "value": ""}] + categoria_options,
                                value="",
                                size="sm"
                            ),
                        ], width=6),
                    ], className="mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Novo Fornecedor"),
                            dcc.Dropdown(
                                id="lote-fornecedor",
                                options=[{"label": "Manter atual", "value": ""}] + [
                                    {"label": row["for_nome"], "value": int(row["for_id"])} 
                                    for _, row in banco.ler_tabela("fornecedores").sort_values("for_nome").iterrows()
                                ] if not banco.ler_tabela("fornecedores").empty else [{"label": "Manter atual", "value": ""}],
                                value="",
                                placeholder="Selecione para alterar",
                                clearable=True
                            ),
                        ], width=6),
                        dbc.Col([
                            dbc.Label("IPI (%)"),
                            dbc.Input(id="lote-ipi", type="number", placeholder="Deixe vazio para manter", size="sm"),
                        ], width=3),
                        dbc.Col([
                            dbc.Label("ICMS (%)"),
                            dbc.Input(id="lote-icms", type="number", placeholder="Deixe vazio para manter", size="sm"),
                        ], width=3),
                    ], className="mb-3"),
                ])
            ]),
            
            html.Div(id="feedback-edicao-lote", className="mt-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="btn-cancelar-lote", color="secondary", size="sm"),
            dbc.Button("Aplicar Alterações", id="btn-aplicar-lote", color="primary", size="sm"),
        ]),
    ], id="modal-edicao-lote", size="lg", is_open=False, className="modal-edicao-lote"),
])

# Função auxiliar para gerar o layout das tabelas
def gerar_layout_tabelas(df, status_filter, paginacao_data, suppliers_page_by_status):
    """Gera o layout completo das tabelas, agrupadas por status e fornecedor."""
    # Criar componentes para cada status
    components = []
    paginacao_meta = {}
    
    # Determinar quais status devem ser mostrados
    statuses_to_show = status_filter if status_filter and len(status_filter) > 0 else STATUS_OPTIONS
    
    table_counter = 0  # Garantir IDs únicos em toda a página
    for status in statuses_to_show:
        # Filtrar dados para este status
        status_df = df[df['oc_status'] == status].copy()
        
        if not status_df.empty or (status_filter and status in status_filter):
            # Cor de fundo baseada no status
            bg_color = STATUS_COLORS.get(status, "#6c757d") # Cinza para default
            
            # Cabeçalho com o status
            header = html.Div(
                html.H5(f"{status} ({len(status_df)} ordens)", className="mb-0", style={'color': bg_color, 'fontWeight': 'bold'}),
                style={
                    "padding": "12px 20px",
                }
            )
            
            # Container para tabelas específicas do fornecedor
            supplier_components = []
            
            # Ordenar por nome do fornecedor
            all_suppliers = list(status_df['fornecedor_nome'].unique())
            supplier_page_key = f"suppliers|{status}"
            current_suppliers_page = int((suppliers_page_by_status or {}).get(supplier_page_key, 0))
            suppliers_page_size = 5
            total_suppliers_pages = max(1, (len(all_suppliers) + suppliers_page_size - 1) // suppliers_page_size)
            # registro meta
            paginacao_meta[supplier_page_key] = total_suppliers_pages
            start_s = current_suppliers_page * suppliers_page_size
            end_s = start_s + suppliers_page_size
            sorted_suppliers = all_suppliers[start_s:end_s]
            # Controles de paginação para fornecedores
            if len(all_suppliers) > suppliers_page_size:
                components.append(
                    dbc.Row([
                        dbc.Col(dbc.Button("◀", id={'type': 'suppliers-prev', 'index': supplier_page_key}, size='sm', color='secondary', outline=True), width='auto'),
                        dbc.Col(html.Span(f"Fornecedores {current_suppliers_page+1}/{total_suppliers_pages}", className="text-muted ms-2 me-2"), width='auto'),
                        dbc.Col(dbc.Button("▶", id={'type': 'suppliers-next', 'index': supplier_page_key}, size='sm', color='secondary', outline=True), width='auto'),
                    ], className="align-items-center g-2 mb-2")
                )
            
            for supplier in sorted_suppliers:
                if pd.isna(supplier):
                    supplier_df = status_df[status_df['fornecedor_nome'].isna()].copy()
                    supplier_name = "Fornecedor não especificado"
                else:
                    supplier_df = status_df[status_df['fornecedor_nome'] == supplier].copy()
                    supplier_name = supplier

                if not supplier_df.empty:
                    supplier_header = html.H6(supplier_name, className="mt-3 mb-2 pb-2 text-dark", style={'fontWeight': '600', 'borderBottom': '1px solid #dee2e6'})
                    supplier_components.append(supplier_header)

                    # Definir grupos por status
                    if status == "Solicitar ao Fornecedor":
                        # Agrupar por número da Solicitação
                        supplier_df.loc[:, 'solicitacao_group'] = supplier_df['oc_solicitacao'].fillna('Sem Solicitação').astype(str).str.replace(r'\.0$', '', regex=True)
                        all_groups = list(supplier_df['solicitacao_group'].unique())
                        key = f"{status}|{supplier_name}"
                        current_page = (paginacao_data or {}).get(key, 0)
                        page_size = 3
                        total_pages = max(1, (len(all_groups) + page_size - 1) // page_size)
                        paginacao_meta[key] = total_pages
                        start = current_page * page_size
                        end = start + page_size
                        sorted_groups = all_groups[start:end]

                        # Controles de paginação
                        if len(all_groups) > page_size:
                            supplier_components.append(
                                dbc.Row([
                                    dbc.Col(dbc.Button("◀", id={'type': 'supplier-prev', 'index': key}, size='sm', color='secondary', outline=True), width='auto'),
                                    dbc.Col(html.Span(f"Página {current_page+1} de {total_pages}", className="text-muted ms-2 me-2"), width='auto'),
                                    dbc.Col(dbc.Button("▶", id={'type': 'supplier-next', 'index': key}, size='sm', color='secondary', outline=True), width='auto'),
                                ], className="align-items-center g-2")
                            )

                        for group_id in sorted_groups:
                            group_df = supplier_df[supplier_df['solicitacao_group'] == group_id]
                            
                            if group_id != 'Sem Solicitação':
                                solicitante_info = group_df.iloc[0]['oc_solicitante'] if not group_df.empty and pd.notna(group_df.iloc[0]['oc_solicitante']) else None
                                setor_info = group_df.iloc[0]['oc_setor'] if not group_df.empty and pd.notna(group_df.iloc[0]['oc_setor']) else None
                                
                                header_parts = [f"Solicitação ID: {group_id}"]
                                if solicitante_info:
                                    header_parts.append(solicitante_info)
                                if setor_info:
                                    header_parts.append(setor_info.capitalize())
                                group_id_text = " - ".join(header_parts)
                            else:
                                group_id_text = "Itens sem Solicitação"
                            
                            pdf_button_id = {'type': 'btn-pdf-oc', 'index': group_id}
                            group_header = html.Div(
                                dbc.Row([
                                    dbc.Col(group_id_text, width='auto'),
                                    dbc.Col(
                                        dbc.Button(html.I(className="fas fa-file-pdf"), id=pdf_button_id, color="light", size="sm", className="ms-auto", outline=True),
                                        width='auto'
                                    )
                                ], justify="between", align="center"),
                                className="mt-3 mb-2 p-2 rounded text-white",
                                style={'backgroundColor': '#727a82', 'fontWeight': '500'}
                            )
                            supplier_components.append(group_header)
                            
                            # Para solicitações, a tabela é sempre visível
                            supplier_components.append(create_datatable(group_df, status, table_counter, show_supplier_column=False, show_oc_column=True, show_solicitacao_column=False))
                            table_counter += 1
                    else:
                        # Agrupar por número da OC (lógica original com collapse)
                        supplier_df.loc[:, 'oc_numero_group'] = supplier_df['oc_numero'].fillna('Sem O.C.').replace('', 'Sem O.C.')
                        all_groups = list(supplier_df['oc_numero_group'].unique())
                        key = f"{status}|{supplier_name}"
                        current_page = (paginacao_data or {}).get(key, 0)
                        page_size = 3
                        total_pages = max(1, (len(all_groups) + page_size - 1) // page_size)
                        paginacao_meta[key] = total_pages
                        start = current_page * page_size
                        end = start + page_size
                        sorted_ocs = all_groups[start:end]

                        # Controles de paginação
                        if len(all_groups) > page_size:
                            supplier_components.append(
                                dbc.Row([
                                    dbc.Col(dbc.Button("◀", id={'type': 'supplier-prev', 'index': key}, size='sm', color='secondary', outline=True), width='auto'),
                                    dbc.Col(html.Span(f"Página {current_page+1} de {total_pages}", className="text-muted ms-2 me-2"), width='auto'),
                                    dbc.Col(dbc.Button("▶", id={'type': 'supplier-next', 'index': key}, size='sm', color='secondary', outline=True), width='auto'),
                                ], className="align-items-center g-2")
                            )

                        for oc_numero in sorted_ocs:
                            oc_df = supplier_df[supplier_df['oc_numero_group'] == oc_numero]
                            
                            if not oc_df.empty:
                                solicitante_info = oc_df.iloc[0]['oc_solicitante'] if pd.notna(oc_df.iloc[0]['oc_solicitante']) else None
                                setor_info = oc_df.iloc[0]['oc_setor'] if pd.notna(oc_df.iloc[0]['oc_setor']) else None
                                
                                # Calcular o valor total para o grupo de O.C.
                                valor_total_oc = (oc_df['oc_qtd_solicitada'] * oc_df['oc_valor_unit']).sum()
                                
                                header_parts = [f"O.C.: {oc_numero}" if oc_numero != 'Sem O.C.' else "Itens sem O.C."]
                                if solicitante_info:
                                    header_parts.append(solicitante_info)
                                if setor_info:
                                    header_parts.append(setor_info.capitalize())
                                if pd.notna(valor_total_oc) and valor_total_oc > 0:
                                    # Formatando para o padrão brasileiro
                                    valor_formatado = f"R$ {valor_total_oc:_.2f}".replace('.', ',').replace('_', '.')
                                    header_parts.append(f"Valor Total: {valor_formatado}")
                                
                                oc_header_text = " - ".join(header_parts)
                            else:
                                oc_header_text = f"O.C.: {oc_numero}" if oc_numero != 'Sem O.C.' else "Itens sem O.C."
                            
                            oc_numero_sanitized = oc_numero.replace(' ', '_').replace('.', '')
                            collapse_id = {'type': 'oc-collapse', 'index': f"{status}-{table_counter}-{oc_numero_sanitized}"}
                            toggle_id = {'type': 'oc-toggle', 'index': f"{status}-{table_counter}-{oc_numero_sanitized}"}
                            
                            # Botões de ações no cabeçalho por status
                            header_buttons = []
                            if status == "Aguardando Aprovação":
                                header_buttons.append(
                                    dbc.Button(
                                        html.I(className="fas fa-balance-scale"),
                                        id={'type': 'btn-pdf-cotacao', 'index': oc_numero},
                                        color="info",
                                        size="sm",
                                        className="ms-2",
                                        outline=True
                                    )
                                )
                            if status == "Aguardando Recebimento" and oc_numero != 'Sem O.C.':
                                header_buttons.append(
                                    dbc.Button(
                                        html.I(className="fas fa-file-pdf"),
                                        id={'type': 'btn-pdf-ordem', 'index': oc_numero},
                                        color="light",
                                        size="sm",
                                        className="ms-2",
                                        outline=True
                                    )
                                )

                            oc_header = html.Div(
                                dbc.Row([
                                    dbc.Col(oc_header_text, width='auto'),
                                    dbc.Col(header_buttons, width='auto')
                                ], justify="between", align="center"),
                                id=toggle_id,
                                className="mt-3 mb-2 p-2 rounded text-white",
                                style={'backgroundColor': '#727a82', 'fontWeight': '500', 'cursor': 'pointer'}
                            )
                            supplier_components.append(oc_header)
                            
                            table_collapse = dbc.Collapse(
                                create_datatable(oc_df, status, table_counter, show_supplier_column=False, show_oc_column=False, show_solicitacao_column=True),
                                id=collapse_id,
                                is_open=False,
                            )
                            supplier_components.append(table_collapse)
                            table_counter += 1
            
            # Componente de status com tabelas agrupadas
            status_component = html.Div([
                header,
                html.Div(supplier_components, style={"padding": "0 20px 10px 20px"})
            ], style={
                "marginBottom": "25px",
                "border": "1px solid #e9ecef",
                "borderLeft": f"10px solid {bg_color}", # Borda lateral colorida
                "borderRadius": "8px",
                "backgroundColor": "#fff",
                "boxShadow": "0 2px 5px rgba(0,0,0,0.05)",
            })
            
            components.append(status_component)
    
    if not components:
        return html.Div([
            html.H5("Nenhuma ordem de compra encontrada com os filtros aplicados."),
        ], className="text-center p-5"), {}
        
    return components, paginacao_meta

# Função para criar a tabela DataTable com base nos dados
def create_datatable(df, status=None, table_index=0, show_supplier_column=True, show_oc_column=True, show_solicitacao_column=True):
    if df.empty:
        return html.Div([
            html.P("Nenhuma ordem de compra encontrada.")
        ], className="text-center")
    
    
    try:
        # Criar uma cópia do DataFrame para evitar warnings
        df = df.copy()
        # Criar uma cópia temporária da coluna para ordenação
        df['temp_date_for_sorting'] = pd.to_datetime(df['oc_data_entrega'], format='%d/%m/%Y', errors='coerce')
        # Ordenar pelo valor datetime
        df = df.sort_values(by='temp_date_for_sorting', ascending=True)
        # Remover a coluna temporária
        df = df.drop(columns=['temp_date_for_sorting'])
    except Exception as e:
        print(f"Erro ao ordenar por data: {e}")
    
    table_id = f'tabela-{status.replace(" ", "-").lower() if status else "ordens-compra"}-{table_index}'
    
    # Calcular a quantidade convertida
    df['qtd_convertida'] = df.apply(
        lambda row: row['oc_qtd_solicitada'] * row['oc_conversao'] 
        if pd.notnull(row['oc_qtd_solicitada']) and pd.notnull(row['oc_conversao']) else None, 
        axis=1
    )
    
    # Calcular indicador de status (🟠) quando qtd recebida < 90% da solicitada
    def calcular_status_emoji(row):
        try:
            if pd.notnull(row.get('oc_qtd_solicitada')) and pd.notnull(row.get('oc_qtd_recebida')):
                return '🟠' if float(row['oc_qtd_recebida']) < 0.9 * float(row['oc_qtd_solicitada']) else ''
        except Exception:
            return ''
        return ''
    df['status_col'] = df.apply(calcular_status_emoji, axis=1)
    # Calcular o valor total
    df['valor_total'] = df.apply(
        lambda row: row['oc_qtd_solicitada'] * row['oc_valor_unit'] 
        if pd.notnull(row['oc_qtd_solicitada']) and pd.notnull(row['oc_valor_unit']) else None, 
        axis=1
    )
    colunas_para_formatar = [ 'oc_qtd_solicitada', 'oc_qtd_recebida', 'qtd_convertida']
    
    for coluna in colunas_para_formatar:
        if coluna in df.columns:
            df[coluna] = df[coluna].apply(
                lambda x: f"{float(x):,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                if pd.notnull(x) else ""
            )
    
    # Formatar valor total como moeda
    if 'valor_total' in df.columns:
        df['valor_total'] = df['valor_total'].apply(
            lambda x: f"R$ {float(x):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            if pd.notnull(x) else ""
        )
    
    # Definir colunas baseadas no status
    colunas_base = [
        {'name': 'ID', 'id': 'oc_id'},
        {'name': 'Nº Solic.', 'id': 'oc_solicitacao'},
        {'name': 'Data Entrega', 'id': 'oc_data_entrega'},
        {'name': 'Obs.', 'id': 'oc_observacao'},
        {'name': 'Produto', 'id': 'produto_nome'},
        {'name': 'Fornecedor', 'id': 'fornecedor_nome'},
        {'name': 'Unidade', 'id': 'oc_unid_compra'},
        {'name': 'Qtd. Solicitada', 'id': 'oc_qtd_solicitada'},
        {'name': 'Qtd. Recebida', 'id': 'oc_qtd_recebida'},
        {'name': 'Conversão', 'id': 'oc_unidade_conversao'},
        {'name': 'Qtd.', 'id': 'qtd_convertida'},
        {'name': 'O.C.', 'id': 'oc_numero'},
        {'name': 'Data Necessária', 'id': 'oc_data_necessaria'},
        {'name': 'Data Emissão', 'id': 'oc_data_emissao'},
    ]
    
    # Remover colunas com base nos parâmetros
    if not show_supplier_column:
        colunas_base = [col for col in colunas_base if col.get('id') != 'fornecedor_nome']
    if not show_oc_column:
        colunas_base = [col for col in colunas_base if col.get('id') != 'oc_numero']
    if not show_solicitacao_column:
        colunas_base = [col for col in colunas_base if col.get('id') != 'oc_solicitacao']
    
    # Adicionar coluna de valor total, exceto para "Solicitar ao Fornecedor"
    if status != "Solicitar ao Fornecedor":
        try:
            # Inserir a coluna 'Valor' após 'Qtd. Solicitada'
            index_qtd = next(i for i, col in enumerate(colunas_base) if col['id'] == 'oc_qtd_solicitada')
            colunas_base.insert(index_qtd + 1, {'name': 'Valor', 'id': 'valor_total'})
        except StopIteration:
            # Caso 'oc_qtd_solicitada' não seja encontrada, adicione no final
            colunas_base.append({'name': 'Valor', 'id': 'valor_total'})
            
    # Adicionar coluna de Status para status específicos
    if status in ["Aguardando Recebimento", "Entregue Total"]:
        colunas_base.insert(0, {'name': 'Status', 'id': 'status_col'})
    
    # Adicionar coluna de solicitação para status específicos
    if status in ["Solicitar ao Fornecedor", "Aguardando Aprovação"]:
        colunas_base.insert(3, {'name': 'Solicitação', 'id': 'oc_nome_solicitacao'})

    # Container com botão de edição em lote e tabela
    return html.Div([
        # Botão de edição em lote (aparece apenas quando há seleções)
        html.Div([
            dbc.Button(
                "Gerar OC",
                id={'type': 'btn-gerar-oc', 'index': table_id},
                color="success",
                size="sm",
                className="mb-2 me-2",
                style={"display": "none"}
            ),
            dbc.Button(
                "Editar em Lote", 
                id={'type': 'btn-edicao-lote', 'index': table_id},
                color="warning", 
                size="sm",
                className="mb-2 btn-edicao-lote",
                style={"display": "none"}  # Inicialmente oculto
            ),
            html.Span(
                id={'type': 'contador-selecoes', 'index': table_id},
                className="ms-2 text-muted contador-selecoes",
                style={"display": "none"}
            )
        ], className="btn-edicao-lote-container d-flex align-items-center"),
        # DataTable com seleção múltipla
        dash_table.DataTable(
            id={'type': 'tabela-ordens', 'index': table_id},
            data=df.to_dict('records'),
            columns=colunas_base,
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'whiteSpace': 'nowrap',
                'overflow': 'hidden',
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            
            tooltip_duration=None,
            page_size=25,
            sort_action='native',
            sort_mode='multi',
            row_selectable='multi',  # Alterado para permitir seleção múltipla
            selected_rows=[],
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                },
                {
                    'if': {'state': 'selected'},
                    'backgroundColor': 'rgba(255, 193, 7, 0.1)',
                    'border': '1px solid #ffc107'
                }
            ]
        )
    ])

# Callback para carregar dados das tabelas agrupadas por status
@app.callback(
    [
        Output('container-tabelas-ordens', 'children'),
        Output('paginacao-metadata', 'data')
    ],
    [
        Input('btn-filtrar', 'n_clicks'),
        Input('feedback-form-oc', 'children'),  # Esse input será acionado quando uma ordem for salva
        Input('btn-limpar', 'n_clicks'),
        Input('feedback-edicao-lote', 'children'), # Recarregar após edição em lote
        Input({'type': 'supplier-prev', 'index': ALL}, 'n_clicks'),
        Input({'type': 'supplier-next', 'index': ALL}, 'n_clicks'),
        Input({'type': 'suppliers-prev', 'index': ALL}, 'n_clicks'),
        Input({'type': 'suppliers-next', 'index': ALL}, 'n_clicks'),
    ],
    [
        State('filtro-solicitacao', 'value'),
        State('filtro-solicitante', 'value'),
        State('filtro-setor', 'value'),
        State('filtro-data-inicio', 'date'),
        State('filtro-data-fim', 'date'),
        State('filtro-produto', 'value'),
        State('filtro-sku', 'value'),
        State('filtro-fornecedor', 'value'),
        State('filtro-status', 'value'),
        State('paginacao-fornecedor', 'data'),
        State('paginacao-suppliers', 'data')
    ]
)
def carregar_ordens_agrupadas(n_filtrar, feedback, n_limpar, feedback_lote, prev_clicks, next_clicks, prev_suppliers, next_suppliers, solicitacao, solicitante, setor, 
                              data_inicio, data_fim, produto, sku, fornecedor, status_filter, paginacao_data, suppliers_pages):
    try:
        
        ctx = callback_context
        
        # Apenas verificar o gatilho se a callback foi acionada por um input
        if ctx.triggered:
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

            # Verificar o feedback da edição em lote
            if trigger_id == 'feedback-edicao-lote':
                # O feedback_lote é um dicionário que representa o componente dbc.Alert
                if not feedback_lote or not isinstance(feedback_lote, dict):
                    raise PreventUpdate
                
                # Apenas atualizar se o alerta for de sucesso ou aviso
                alert_props = feedback_lote.get('props', {})
                if alert_props.get('color') not in ['success', 'warning']:
                    raise PreventUpdate

        # Consulta SQL com joins para obter os dados relacionados
        with engine.connect() as conn:
            query = """
            SELECT 
                oc.*,
                pc.nome as produto_nome,
                f.for_nome as fornecedor_nome,
                c_sum.total_carregado,
                c_sum.carregamentos_info
            FROM 
                ordem_compra oc
            LEFT JOIN 
                produto_compras pc ON oc.oc_produto_id = pc.prod_comp_id
            LEFT JOIN 
                fornecedores f ON oc.oc_fornecedor_id = f.for_id
            LEFT JOIN (
                SELECT 
                    car_oc_id, 
                    SUM(car_qtd) as total_carregado,
                    GROUP_CONCAT('Data: ' || STRFTIME('%d/%m/%Y', car_data) || ', Qtd: ' || car_qtd) as carregamentos_info
                FROM carregamento
                GROUP BY car_oc_id
            ) c_sum ON oc.oc_id = c_sum.car_oc_id
            """
            
            # Aplicar filtros se fornecidos
            conditions = []
            params = {}
            
            if solicitacao:
                conditions.append("oc.oc_nome_solicitacao LIKE :solicitacao")
                params['solicitacao'] = f"%{solicitacao}%"
                
            if solicitante:
                conditions.append("oc.oc_solicitante LIKE :solicitante")
                params['solicitante'] = f"%{solicitante}%"
                
            if setor:
                conditions.append("oc.oc_setor LIKE :setor")
                params['setor'] = f"%{setor}%"
                
            if data_inicio:
                conditions.append("oc.oc_data_emissao >= :data_inicio")
                params['data_inicio'] = data_inicio
                
            if data_fim:
                conditions.append("oc.oc_data_emissao <= :data_fim")
                params['data_fim'] = data_fim
                
            if produto:
                conditions.append("pc.nome LIKE :produto")
                params['produto'] = f"%{produto}%"
                
            if sku:
                conditions.append("oc.oc_sku LIKE :sku")
                params['sku'] = f"%{sku}%"
                
            if fornecedor:
                try:
                    # Only apply filter if fornecedor is not empty string (from "Todos" option)
                    if fornecedor != "":
                        # Ensure fornecedor is an integer for the comparison
                        fornecedor_id = int(fornecedor)
                        conditions.append("oc.oc_fornecedor_id = :fornecedor")
                        params['fornecedor'] = fornecedor_id
                except (ValueError, TypeError):
                    # If conversion fails, don't apply this filter
                    print(f"Could not convert fornecedor value to int: {fornecedor}")
            
            if status_filter and len(status_filter) > 0:
                placeholders = [f":status{i}" for i in range(len(status_filter))]
                conditions.append(f"oc.oc_status IN ({', '.join(placeholders)})")
                for i, s in enumerate(status_filter):
                    params[f'status{i}'] = s
            
            # Adicionar cláusula WHERE se houver condições
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            # Ordernar por status e ID descendente
            query += " ORDER BY oc.oc_status, oc.oc_id DESC"
            
     
            
            # Executar a consulta e carregar os dados
            df = pd.read_sql(query, conn, params=params)
            
            # Adicionar colunas para o ícone de caminhão
            if not df.empty:
                def get_truck_info(row):
                    icon = ''
                    tooltip = ''
                    if row['oc_status'] in ["Aguardando Recebimento", "Entregue Parcial"]:
                        total_carregado = row['total_carregado'] if pd.notnull(row['total_carregado']) else 0
                        qtd_solicitada = row['oc_qtd_solicitada'] if pd.notnull(row['oc_qtd_solicitada']) else 0

                        if total_carregado > 0:
                            if total_carregado < qtd_solicitada:
                                icon = '🚚'  # Parcial
                            else:
                                icon = '🚛'  # Completo
                            
                            if pd.notnull(row['carregamentos_info']):
                                tooltip = row['carregamentos_info']

                    return icon, tooltip

                df[['truck_icon', 'truck_tooltip']] = df.apply(get_truck_info, axis=1, result_type='expand')
            
            # Formatar datas para exibição e substituir NaT por None (serializável)
            for col in ['oc_data_necessaria', 'oc_data_emissao', 'oc_data_entrega']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d/%m/%Y').replace({pd.NaT: None})

            # Substituir todos os NaNs restantes por None para serialização JSON
            df = df.where(pd.notnull(df), None)
            
            components, meta = gerar_layout_tabelas(df, status_filter, paginacao_data, suppliers_pages)
            return components, meta
            
    except PreventUpdate:
        raise
    except Exception as e:
        print(f"Erro ao carregar ordens de compra: {e}")
        import traceback
        traceback.print_exc()
        return html.Div([
            html.H5(f"Erro ao carregar ordens de compra: {str(e)}"),
        ], className="text-center p-5 text-danger"), dash.no_update

# Callback para limpar filtros
@app.callback(
    [
        Output('filtro-solicitacao', 'value'),
        Output('filtro-solicitante', 'value'),
        Output('filtro-setor', 'value'),
        Output('filtro-data-inicio', 'date'),
        Output('filtro-data-fim', 'date'),
        Output('filtro-produto', 'value'),
        Output('filtro-sku', 'value'),
        Output('filtro-fornecedor', 'value'),
        Output('filtro-status', 'value')
    ],
    [Input('btn-limpar', 'n_clicks')],
    prevent_initial_call=True
)
def limpar_filtros(n_clicks):
    if n_clicks:
        return None, None, None, None, None, None, None, "", []
    raise PreventUpdate

# Callback para preencher o formulário com os dados da ordem de compra selecionada
@app.callback(
    [
        Output("oc-id", "value"),
        Output("oc-nome-solicitacao", "value"),
        Output("oc-solicitacao", "value"),
        Output("oc-solicitante", "value"),
        Output("oc-setor", "value"),
        Output("oc-numero", "value"),
        Output("oc-produto-id", "value"),
        Output("oc-fornecedor-id", "value"),
        Output("oc-sku", "value"),
        Output("oc-status", "value"),
        Output("oc-qtd-solicitada", "value"),
        Output("oc-qtd-recebida", "value"),
        Output("oc-unid-compra", "value"),
        Output("oc-conversao", "value"),
        Output("oc-unidade-conversao", "value"),
        Output("oc-valor-unit", "value"),
        Output("oc-ipi", "value"),
        Output("oc-icms", "value"),
        Output("oc-frete", "value"),
        Output("oc-data-necessaria", "date"),
        Output("oc-data-emissao", "date"),
        Output("oc-data-entrega", "date"),
        Output("oc-observacao", "value"),
        Output("oc-pcp-id", "value"),
        Output("oc-nota", "value"),
        Output("oc-categoria-id", "value"),
    ],
    [
        Input("ordem-selecionada", "data"),
        Input("btn-lancar", "n_clicks"),
        Input("feedback-form-oc", "children"),
        Input("oc-produto-id", "value")
    ],
    [State("oc-id", "value")],
    prevent_initial_call=True
)
def preencher_form_ordem(ordem_selecionada, n_lancar, feedback, produto_id, oc_id):
    ctx = callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Se o botão de lançamento foi clicado, limpar campos para uma nova entrada
    if trigger_id == "btn-lancar":
        return (None,) * 26

    # Após salvar com sucesso, limpar os campos
    if trigger_id == "feedback-form-oc":
        if feedback and "sucesso" in str(feedback).lower():
            return (None,) * 26
        raise PreventUpdate

    # Quando um produto é selecionado, buscar a última ordem para preenchimento automático.
    # Isso deve acontecer ao criar uma nova ordem (sem oc_id) OU ao editar uma ordem
    # que ainda está na fase de "Solicitar ao Fornecedor".
    if trigger_id == "oc-produto-id" and produto_id:
        # Consultar o status atual da ordem que está sendo editada
        status_atual = None
        if oc_id:
            try:
                df_ordem = banco.ler_tabela("ordem_compra", oc_id=oc_id)
                if not df_ordem.empty:
                    status_atual = df_ordem.iloc[0]['oc_status']
            except Exception as e:
                print(f"Erro ao consultar status da ordem {oc_id}: {e}")

        # Permitir preenchimento se for uma nova ordem ou se o status for "Solicitar ao Fornecedor"
        if not oc_id or status_atual == "Solicitar ao Fornecedor":
            try:
                with banco.engine.connect() as conn:
                    query = """
                    SELECT 
                        oc_fornecedor_id, oc_unid_compra, oc_conversao, oc_unidade_conversao,
                        oc_valor_unit, oc_ipi, oc_icms
                    FROM 
                        ordem_compra
                    WHERE 
                        oc_produto_id = :produto_id
                    ORDER BY 
                        oc_data_emissao DESC, oc_id DESC
                    LIMIT 1
                    """
                    resultado = pd.read_sql(query, conn, params={"produto_id": produto_id})
                    if resultado.empty:
                        raise PreventUpdate
                    
                    return (
                        dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                        dash.no_update, produto_id, resultado.iloc[0]['oc_fornecedor_id'],
                        dash.no_update, dash.no_update, dash.no_update, dash.no_update,
                        resultado.iloc[0]['oc_unid_compra'], resultado.iloc[0]['oc_conversao'],
                        resultado.iloc[0]['oc_unidade_conversao'], resultado.iloc[0]['oc_valor_unit'],
                        resultado.iloc[0]['oc_ipi'], resultado.iloc[0]['oc_icms'],
                        dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                    )
            except Exception as e:
                print(f"Erro ao buscar última ordem do produto: {e}")
                raise PreventUpdate

    # Lidar com a seleção de uma ordem para edição
    if trigger_id == "ordem-selecionada" and ordem_selecionada:
        try:
            def safe_float_conversion(value_str):
                if value_str is None or str(value_str).strip() == '': return None
                return float(str(value_str).replace('.', '').replace(',', '.'))

            def safe_date_conversion(date_str):
                if not date_str: return None
                try:
                    return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    return None

            return (
                ordem_selecionada.get('oc_id'),
                ordem_selecionada.get('oc_nome_solicitacao'),
                ordem_selecionada.get('oc_solicitacao'),
                ordem_selecionada.get('oc_solicitante'),
                ordem_selecionada.get('oc_setor'),
                ordem_selecionada.get('oc_numero'),
                ordem_selecionada.get('oc_produto_id'),
                ordem_selecionada.get('oc_fornecedor_id'),
                ordem_selecionada.get('oc_sku'),
                ordem_selecionada.get('oc_status'),
                safe_float_conversion(ordem_selecionada.get('oc_qtd_solicitada')),
                safe_float_conversion(ordem_selecionada.get('oc_qtd_recebida')),
                ordem_selecionada.get('oc_unid_compra'),
                ordem_selecionada.get('oc_conversao'),
                ordem_selecionada.get('oc_unidade_conversao'),
                ordem_selecionada.get('oc_valor_unit'),
                ordem_selecionada.get('oc_ipi'),
                ordem_selecionada.get('oc_icms'),
                ordem_selecionada.get('oc_frete'),
                safe_date_conversion(ordem_selecionada.get('oc_data_necessaria')),
                safe_date_conversion(ordem_selecionada.get('oc_data_emissao')),
                safe_date_conversion(ordem_selecionada.get('oc_data_entrega')),
                ordem_selecionada.get('oc_observacao'),
                ordem_selecionada.get('oc_pcp_id'),
                ordem_selecionada.get('oc_nota'),
                ordem_selecionada.get('oc_categoria_id'),
            )
        except Exception as e:
            print(f"Erro ao preencher formulário: {e}")
            raise PreventUpdate

    raise PreventUpdate

# Novo callback para abrir o modal ao clicar no botão "Lançar"
@app.callback(
    Output("modal-form-oc", "is_open", allow_duplicate=True),
    [Input("btn-lancar", "n_clicks")],
    prevent_initial_call=True
)
def open_modal_from_button(n_clicks):
    if n_clicks:
        return True
    return False

# Novo callback para controlar a abertura do modal - esse usará allow_duplicate
@app.callback(
    Output("modal-form-oc", "is_open", allow_duplicate=True),
    [
        Input("ordem-selecionada", "data"),
        Input("feedback-form-oc", "children")
    ],
    [State("modal-form-oc", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_from_selection(ordem_selecionada, feedback, is_open):
    ctx = callback_context
    
    if not ctx.triggered:
        return is_open
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "ordem-selecionada" and ordem_selecionada:
        # Abrir modal ao selecionar uma ordem
        return True
    
    elif trigger_id == "feedback-form-oc":
        # Fechar após salvar com sucesso
        if feedback and "sucesso" in str(feedback).lower():
            return False
    
    return is_open

# Callback para abrir modal de fornecedor
@app.callback(
    Output("modal-fornecedor", "is_open"),
    [
        Input("btn-fornecedor", "n_clicks"),
        Input("fornecedor-btn-fechar", "n_clicks")
    ],
    [State("modal-fornecedor", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_fornecedor(n_novo, n_fechar, is_open):
    return not is_open

# Callback para abrir modal de carregamento
@app.callback(
    Output("modal-carregamento", "is_open"),
    [
        Input("btn-carregamento", "n_clicks"),
        Input("carregamento-btn-fechar", "n_clicks")
    ],
    [State("modal-carregamento", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_carregamento(n_abrir, n_fechar, is_open):
    if n_abrir or n_fechar:
        return not is_open
    return is_open

# Callback para o botão Excel
@app.callback(
    Output("download-excel-compras", "data"),
    [Input("btn-export_excel", "n_clicks")],
    prevent_initial_call=True
)
def exportar_excel(n_clicks):
    if not n_clicks:
        return dash.no_update
    
    try:
        # Consulta SQL para unir ordem_compra com fornecedores, produto_compras e carregamentos agregados
        with engine.connect() as conn:
            query = """
            SELECT 
                oc.oc_id as "ID",
                oc.oc_nome_solicitacao as "Solicitação",
                oc.oc_solicitante as "Solicitante",
                oc.oc_setor as "Setor",
                oc.oc_numero as "Número OC",
                oc.oc_sku as "SKU",
                oc.oc_pcp_id as "PCP ID",
                oc.oc_status as "Status",
                pc.nome as "Produto",
                f.for_nome as "Fornecedor",
                f.for_prazo as "Prazo Pagamento",
                f.for_forma_pagamento as "Forma Pagamento",
                f.for_observacao as "Observação Fornecedor",
                oc.oc_unid_compra as "Unidade Compra",
                oc.oc_qtd_solicitada as "Qtd Solicitada",
                oc.oc_qtd_recebida as "Qtd Recebida",
                oc.oc_unidade_conversao as "Unidade Conversão",
                oc.oc_conversao as "Fator Conversão",
                oc.oc_valor_unit as "Valor Unitário",
                oc.oc_ipi as "IPI (%)",
                oc.oc_icms as "ICMS (%)",
                oc.oc_frete as "Frete (R$)",
                oc.oc_data_necessaria as "Data Necessária",
                oc.oc_data_emissao as "Data Emissão",
                oc.oc_data_entrega as "Data Entrega",
                oc.oc_nota as "Nota Fiscal",
                oc.oc_observacao as "Observação",
                c_agg."Nº Carregamentos",
                c_agg.carregamentos_str
            FROM 
                ordem_compra oc
            LEFT JOIN 
                produto_compras pc ON oc.oc_produto_id = pc.prod_comp_id
            LEFT JOIN 
                fornecedores f ON oc.oc_fornecedor_id = f.for_id
            LEFT JOIN (
                SELECT
                    car_oc_id,
                    COUNT(car_id) as "Nº Carregamentos",
                    GROUP_CONCAT(
                        COALESCE(car_qtd, '') || '|' || COALESCE(STRFTIME('%d/%m/%Y', car_data), ''),
                        ';'
                    ) as carregamentos_str
                FROM carregamento
                GROUP BY car_oc_id
            ) c_agg ON oc.oc_id = c_agg.car_oc_id
            ORDER BY 
                oc.oc_status, oc.oc_id DESC
            """
            
            # Executar a consulta e carregar os dados em DataFrame
            df = pd.read_sql(query, conn)
            
            # Processar carregamentos se a coluna existir
            dynamic_cols = []
            if 'carregamentos_str' in df.columns and df['carregamentos_str'].notna().any():
                # Determinar o número máximo de carregamentos para criar as colunas
                max_carregamentos = df['carregamentos_str'].str.split(';').str.len().max()
                max_carregamentos = int(max_carregamentos) if pd.notna(max_carregamentos) else 0

                # Criar as novas colunas dinâmicas
                for i in range(1, max_carregamentos + 1):
                    qtd_col = f'Carregamento {i} Qtd'
                    data_col = f'Carregamento {i} Data'
                    df[qtd_col] = None
                    df[data_col] = None
                    dynamic_cols.extend([qtd_col, data_col])

                # Preencher as novas colunas
                for index, row in df.iterrows():
                    if pd.notna(row['carregamentos_str']):
                        carregamentos = row['carregamentos_str'].split(';')
                        for i, carregamento in enumerate(carregamentos):
                            if '|' in carregamento:
                                qtd, data = carregamento.split('|', 1)
                                df.loc[index, f'Carregamento {i+1} Qtd'] = qtd
                                df.loc[index, f'Carregamento {i+1} Data'] = data

            # Limpar a coluna temporária e preencher NaNs
            if 'carregamentos_str' in df.columns:
                df.drop(columns=['carregamentos_str'], inplace=True)
            if 'Nº Carregamentos' in df.columns:
                df['Nº Carregamentos'] = df['Nº Carregamentos'].fillna(0).astype(int)
            else:
                df['Nº Carregamentos'] = 0

            # Reordenar colunas para colocar as de carregamento no final
            base_cols = [col for col in df.columns if col not in dynamic_cols and col != 'Nº Carregamentos']
            
            # Inserir 'Nº Carregamentos' depois de 'Observação'
            try:
                obs_index = base_cols.index('Observação')
                final_cols = base_cols[:obs_index + 1] + ['Nº Carregamentos'] + base_cols[obs_index + 1:] + dynamic_cols
            except ValueError:
                # Se 'Observação' não estiver presente, apenas adicione ao final
                final_cols = base_cols + ['Nº Carregamentos'] + dynamic_cols
            
            df = df[final_cols]
            
            print(f"DataFrame criado com {len(df)} registros")
            print("Colunas disponíveis:", df.columns.tolist())
            
            # Gerar arquivo Excel
            excel_data = to_excel(df)
            
            print("Excel gerado com sucesso!")
            
            return dcc.send_bytes(excel_data.getvalue(), "Relatorio_Compras.xlsx")
            
    except Exception as e:
        print(f"Erro ao consultar banco de dados: {e}")
        import traceback
        traceback.print_exc()
        return dash.no_update

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatório')
    output.seek(0)
    return output

# Callback para controlar a visibilidade dos botões de edição em lote
@app.callback(
    [
        Output({'type': 'btn-edicao-lote', 'index': ALL}, 'style'),
        Output({'type': 'btn-gerar-oc', 'index': ALL}, 'style'),
        Output({'type': 'contador-selecoes', 'index': ALL}, 'children'),
        Output({'type': 'contador-selecoes', 'index': ALL}, 'style'),
        Output('ordens-selecionadas-lote', 'data')
    ],
    [
        Input({'type': 'tabela-ordens', 'index': ALL}, 'selected_rows'),
        Input({'type': 'tabela-ordens', 'index': ALL}, 'derived_virtual_data')
    ],
    prevent_initial_call=True
)
def controlar_botoes_edicao_lote(selected_rows_list, all_data_list):
    """Controla a visibilidade dos botões de edição em lote baseado nas seleções"""
    
    # Inicializar listas de retorno
    btn_styles_edicao = []
    btn_styles_gerar_oc = []
    contador_texts = []
    contador_styles = []
    ordens_selecionadas = []
    
    # Processar cada tabela
    for i, (selected_rows, table_data) in enumerate(zip(selected_rows_list, all_data_list)):
        if selected_rows and len(selected_rows) >= 1 and table_data:
            # Pelo menos uma seleção - mostrar botões
            btn_styles_edicao.append({"display": "inline-block"})
            btn_styles_gerar_oc.append({"display": "inline-block"})
            contador_texts.append(f"({len(selected_rows)} ordens selecionadas)")
            contador_styles.append({"display": "inline"})
            
            # Coletar dados das ordens selecionadas desta tabela
            for row_idx in selected_rows:
                if row_idx < len(table_data):
                    ordens_selecionadas.append(table_data[row_idx])
        else:
            # Nenhuma seleção - ocultar botões
            btn_styles_edicao.append({"display": "none"})
            btn_styles_gerar_oc.append({"display": "none"})
            contador_texts.append("")
            contador_styles.append({"display": "none"})
    
    return btn_styles_edicao, btn_styles_gerar_oc, contador_texts, contador_styles, ordens_selecionadas

# Callback para abrir o modal de edição em lote
@app.callback(
    [
        Output('modal-edicao-lote', 'is_open'),
        Output('lista-ordens-selecionadas', 'children')
    ],
    [
        Input({'type': 'btn-edicao-lote', 'index': ALL}, 'n_clicks'),
        Input('btn-cancelar-lote', 'n_clicks'),
        Input('btn-aplicar-lote', 'n_clicks')
    ],
    [
        State('modal-edicao-lote', 'is_open'),
        State('ordens-selecionadas-lote', 'data')
    ],
    prevent_initial_call=True
)
def toggle_modal_edicao_lote(btn_clicks_list, n_cancelar, n_aplicar, is_open, ordens_selecionadas):
    """Controla a abertura/fechamento do modal de edição em lote"""
    
    ctx = callback_context
    if not ctx.triggered:
        return is_open, []
    
    trigger_id = ctx.triggered[0]["prop_id"]
    
    # Se algum botão de edição em lote foi clicado
    if any(btn_clicks_list) and "btn-edicao-lote" in trigger_id:
        # Criar lista das ordens selecionadas para exibir
        lista_ordens = []
        if ordens_selecionadas:
            for ordem in ordens_selecionadas:
                lista_ordens.append(
                    html.Div([
                        html.Span(f"ID: {ordem.get('oc_id', 'N/A')}", className="badge bg-primary me-2"),
                        html.Span(f"{ordem.get('oc_nome_solicitacao', 'Sem nome')}", className="me-2"),
                        html.Span(f"Status: {ordem.get('oc_status', 'N/A')}", className="badge bg-secondary"),
                    ], className="mb-2")
                )
        
        return True, lista_ordens
    
    # Se cancelar ou aplicar foi clicado, fechar modal
    elif trigger_id in ["btn-cancelar-lote.n_clicks", "btn-aplicar-lote.n_clicks"]:
        return False, []
    
    return is_open, []

# Callback para aplicar edições em lote
@app.callback(
    [
        Output('feedback-edicao-lote', 'children', allow_duplicate=True),
    ],
    [
        Input('btn-aplicar-lote', 'n_clicks'),
        Input({'type': 'btn-gerar-oc', 'index': ALL}, 'n_clicks')
    ],
    [
        State('ordens-selecionadas-lote', 'data'),
        State('lote-status', 'value'),
        State('lote-numero-oc', 'value'),
        State('lote-data-entrega', 'date'),
        State('lote-observacao', 'value'),
        State('lote-categoria', 'value'),
        State('lote-fornecedor', 'value'),
        State('lote-ipi', 'value'),
        State('lote-icms', 'value')
    ],
    prevent_initial_call=True
)
def aplicar_edicao_lote(n_aplicar, n_gerar_oc, ordens_selecionadas, novo_status, numero_oc, data_entrega, observacao_adicional, nova_categoria, novo_fornecedor, novo_ipi, novo_icms):
    """Aplica as alterações em lote ou gera um novo número de OC para as ordens selecionadas"""
    
    ctx = callback_context
    if not ctx.triggered or not ordens_selecionadas:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"]

    # Lógica para gerar e aplicar OC
    if "btn-gerar-oc" in trigger_id:
        try:
            # VERIFICAÇÃO: Checar se alguma ordem selecionada já possui OC
            ordens_com_oc = []
            for ordem in ordens_selecionadas:
                if ordem.get('oc_numero') and str(ordem.get('oc_numero')).strip():
                    ordens_com_oc.append(str(ordem.get('oc_id')))
            
            if ordens_com_oc:
                mensagem_erro = f"Operação cancelada. As seguintes ordens já possuem um número de OC: {', '.join(ordens_com_oc)}."
                return [dbc.Alert(mensagem_erro, color="danger")]

            # Gerar o próximo número da OC
            hoje = datetime.now().strftime('%d%m%y')
            with banco.engine.connect() as conn:
                query = text("SELECT oc_numero FROM ordem_compra WHERE oc_numero LIKE :prefix")
                result = conn.execute(query, {'prefix': f"{hoje}%"}).fetchall()
            
            numeros_existentes = [int(r[0][-2:]) for r in result if r[0] and len(r[0]) == 8 and r[0][-2:].isdigit()]
            proximo_seq = max(numeros_existentes) + 1 if numeros_existentes else 1
            novo_numero_oc = f"{hoje}{proximo_seq:02d}"

            # Aplicar o novo número a todas as ordens selecionadas
            ids_para_atualizar = [ordem['oc_id'] for ordem in ordens_selecionadas]
            for oc_id in ids_para_atualizar:
                banco.editar_dado("ordem_compra", oc_id, oc_numero=novo_numero_oc)

            return [dbc.Alert(f"✅ OC {novo_numero_oc} gerada e aplicada a {len(ids_para_atualizar)} itens.", color="success")]

        except Exception as e:
            return [dbc.Alert(f"❌ Erro ao gerar OC: {e}", color="danger")]

    # Lógica original para editar outros campos em lote
    if "btn-aplicar-lote" in trigger_id:
        try:
            # Preparar dados para atualização
            dados_atualizacao = {}
            
            if novo_status and novo_status != "":
                dados_atualizacao["oc_status"] = novo_status
            
            if numero_oc and numero_oc.strip():
                dados_atualizacao["oc_numero"] = numero_oc.strip()
            
            if data_entrega:
                if isinstance(data_entrega, str):
                    data_entrega = datetime.strptime(data_entrega, '%Y-%m-%d').date()
                dados_atualizacao["oc_data_entrega"] = data_entrega
            
            if nova_categoria and nova_categoria != "":
                dados_atualizacao["oc_categoria_id"] = nova_categoria
                
            if novo_fornecedor and novo_fornecedor != "":
                dados_atualizacao["oc_fornecedor_id"] = novo_fornecedor
                
            if novo_ipi is not None:
                dados_atualizacao["oc_ipi"] = novo_ipi
                
            if novo_icms is not None:
                dados_atualizacao["oc_icms"] = novo_icms
                
            # Processar cada ordem selecionada
            ordens_atualizadas = 0
            erros = []
            
            for ordem in ordens_selecionadas:
                try:
                    oc_id = ordem.get('oc_id')
                    if not oc_id:
                        continue
                    
                    dados_ordem = dados_atualizacao.copy()
                    
                    if observacao_adicional and observacao_adicional.strip():
                        observacao_atual = ordem.get('oc_observacao', '') or ''
                        nova_observacao = f"{observacao_atual}\n{observacao_adicional.strip()}" if observacao_atual else observacao_adicional.strip()
                        dados_ordem["oc_observacao"] = nova_observacao
                    
                    if dados_ordem:
                        resultado = banco.editar_dado("ordem_compra", oc_id, **dados_ordem)
                        if resultado:
                            ordens_atualizadas += 1
                        else:
                            erros.append(f"Erro ao atualizar ordem ID {oc_id}")
                    
                except Exception as e:
                    erros.append(f"Erro ao processar ordem ID {ordem.get('oc_id', 'N/A')}: {str(e)}")
            
            if ordens_atualizadas > 0:
                mensagem = f"✅ {ordens_atualizadas} ordem(ns) atualizada(s) com sucesso!"
                if erros:
                    mensagem += f"\n⚠️ {len(erros)} erro(s) encontrado(s)."
                feedback = dbc.Alert(mensagem, color="success" if not erros else "warning")
            else:
                feedback = dbc.Alert("❌ Nenhuma ordem foi atualizada. Verifique os dados.", color="danger")
            
            return [feedback]
            
        except Exception as e:
            return [dbc.Alert(f"Erro ao aplicar edições em lote: {str(e)}", color="danger")]
            
    raise PreventUpdate

# Modificar o callback existente para tratar seleção única vs múltipla
@app.callback(
    Output("ordem-selecionada", "data", allow_duplicate=True),
    [Input({"type": "tabela-ordens", "index": ALL}, "selected_rows"),
     Input({"type": "tabela-ordens", "index": ALL}, "derived_virtual_data")],
    prevent_initial_call=True
)
def store_selected_order_modified(selected_rows_list, all_data):
    """Armazena ordem selecionada apenas para seleção única (para manter compatibilidade)"""
    ctx = callback_context
    
    if not ctx.triggered:
        return None
        
    # Identificar qual tabela foi clicada e se é seleção única
    for i, sel_rows in enumerate(selected_rows_list):
        if sel_rows and len(sel_rows) == 1 and all_data[i]:  # Apenas seleção única
            row_idx = sel_rows[0]
            if row_idx < len(all_data[i]):
                return all_data[i][row_idx]
    
    return None

# O callback 'recarregar_apos_edicao_lote' foi mesclado em 'carregar_ordens_agrupadas'.
# A lógica agora é centralizada para evitar duplicação e inconsistências.
# O input 'feedback-edicao-lote' foi adicionado ao callback principal
# para acionar a atualização quando necessário.

# Callback para atualizar o estado de paginação ao clicar nos controles
@app.callback(
    Output('paginacao-fornecedor', 'data'),
    [
        Input({'type': 'supplier-prev', 'index': ALL}, 'n_clicks'),
        Input({'type': 'supplier-next', 'index': ALL}, 'n_clicks'),
        Input('paginacao-metadata', 'data')
    ],
    State('paginacao-fornecedor', 'data'),
    prevent_initial_call=True
)
def atualizar_paginacao(prev_clicks, next_clicks, meta, paginacao):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    try:
        trig = ctx.triggered[0]['prop_id']
        paginacao = dict(paginacao or {})
        if 'supplier-prev' in trig or 'supplier-next' in trig:
            # extrai a chave do id acionado
            trig_id = json.loads(trig.split('.')[0])
            key = trig_id.get('index')
            if not key:
                raise PreventUpdate
            current = int(paginacao.get(key, 0))
            total_pages = int((meta or {}).get(key, 1))
            if 'supplier-prev' in trig:
                current = max(0, current - 1)
            elif 'supplier-next' in trig:
                current = min(total_pages - 1, current + 1)
            paginacao[key] = current
        return paginacao
    except Exception:
        raise PreventUpdate

# Callback para paginação da lista de fornecedores
@app.callback(
    Output('paginacao-suppliers', 'data'),
    [
        Input({'type': 'suppliers-prev', 'index': ALL}, 'n_clicks'),
        Input({'type': 'suppliers-next', 'index': ALL}, 'n_clicks'),
        Input('paginacao-metadata', 'data')
    ],
    State('paginacao-suppliers', 'data'),
    prevent_initial_call=True
)
def atualizar_paginacao_suppliers(prev_clicks, next_clicks, meta, pages):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    try:
        trig = ctx.triggered[0]['prop_id']
        pages = dict(pages or {})
        if 'suppliers-prev' in trig or 'suppliers-next' in trig:
            trig_id = json.loads(trig.split('.')[0])
            key = trig_id.get('index')
            if not key:
                raise PreventUpdate
            current = int(pages.get(key, 0))
            total_pages = int((meta or {}).get(key, 1))
            if 'suppliers-prev' in trig:
                current = max(0, current - 1)
            elif 'suppliers-next' in trig:
                current = min(total_pages - 1, current + 1)
            pages[key] = current
        return pages
    except Exception:
        raise PreventUpdate
# Callback para alternar a visibilidade das tabelas de O.C.
@app.callback(
    Output({'type': 'oc-collapse', 'index': ALL}, 'is_open'),
    [Input({'type': 'oc-toggle', 'index': ALL}, 'n_clicks')],
    [State({'type': 'oc-collapse', 'index': ALL}, 'is_open')],
    prevent_initial_call=True,
)
def toggle_oc_collapse(n_clicks_list, is_open_list):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks_list):
        raise PreventUpdate

    try:
        # Get the 'index' part of the ID of the button that was clicked
        triggered_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        clicked_oc_index = triggered_id.get('index')
        if not clicked_oc_index:
            raise PreventUpdate
    except (json.JSONDecodeError, KeyError):
        raise PreventUpdate

    # Get the metadata for all the State components
    all_states_meta = ctx.states_list[0]
    
    # Create a list of the 'index' part from all the state components
    all_oc_indices = [state['id']['index'] for state in all_states_meta]

    # Find the position of the clicked item in the list of all items
    try:
        target_pos = all_oc_indices.index(clicked_oc_index)
    except ValueError:
        # This shouldn't happen if IDs are matched correctly
        raise PreventUpdate

    # Create a new list of states to return
    new_is_open_list = list(is_open_list)
    # Toggle the state at the found position
    new_is_open_list[target_pos] = not new_is_open_list[target_pos]

    return new_is_open_list

@app.callback(
    Output("download-oc-pdf", "data"),
    Input({'type': 'btn-pdf-oc', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def download_oc_pdf_callback(n_clicks):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks):
        raise PreventUpdate

    try:
        # The ID is a stringified dict, so we use json.loads
        triggered_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        solicitacao_id = triggered_id.get('index')
        if solicitacao_id is None: # Check for None explicitly
            raise PreventUpdate
    except (json.JSONDecodeError, KeyError):
        raise PreventUpdate
    
    # Use the main engine from banco.py
    with engine.connect() as conn:
        query = """
        SELECT 
            oc.*,
            pc.nome as produto_nome,
            f.for_nome as fornecedor_nome
        FROM 
            ordem_compra oc
        LEFT JOIN 
            produto_compras pc ON oc.oc_produto_id = pc.prod_comp_id
        LEFT JOIN 
            fornecedores f ON oc.oc_fornecedor_id = f.for_id
        """
        params = {}
        
        if solicitacao_id == 'Sem Solicitação':
            query += " WHERE oc.oc_solicitacao IS NULL"
        else:
            query += " WHERE oc.oc_solicitacao = :solicitacao_id"
            params['solicitacao_id'] = solicitacao_id

        items_df = pd.read_sql(query, conn, params=params)

    if items_df.empty:
        raise PreventUpdate
    
    # OC details are the same for all items in the group
    oc_details = items_df.iloc[0].to_dict()
    
    # Generate PDF from a separate function
    pdf_bytes = generate_oc_pdf(oc_details, items_df)
    
    filename = f"Cotacao_{str(solicitacao_id).replace(' ', '_')}.pdf"
    return dcc.send_bytes(pdf_bytes, filename)

@app.callback(
    Output("download-cotacao-pdf", "data"),
    Input({'type': 'btn-pdf-cotacao', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def download_cotacao_pdf_callback(n_clicks):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks):
        raise PreventUpdate

    try:
        triggered_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        oc_numero = triggered_id.get('index')
        if oc_numero is None:
            raise PreventUpdate
    except (json.JSONDecodeError, KeyError):
        raise PreventUpdate
        
    pdf_bytes = generate_cotacao_comparison_pdf(oc_numero)
    
    if pdf_bytes is None:
        # Você pode retornar uma notificação para o usuário aqui se desejar
        raise PreventUpdate
        
    filename = f"Mapa_Cotacoes_OC_{str(oc_numero).replace(' ', '_')}.pdf"
    return dcc.send_bytes(pdf_bytes, filename)

@app.callback(
    Output("download-oc-pdf", "data", allow_duplicate=True),
    Input({'type': 'btn-pdf-ordem', 'index': ALL}, 'n_clicks'),
    prevent_initial_call=True,
)
def download_ordem_compra_pdf_callback(n_clicks):
    ctx = callback_context
    if not ctx.triggered or not any(n_clicks):
        raise PreventUpdate

    try:
        triggered_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        oc_numero = triggered_id.get('index')
        if not oc_numero:
            raise PreventUpdate
    except (json.JSONDecodeError, KeyError):
        raise PreventUpdate

    # Buscar todos os itens vinculados a esse oc_numero, independente do status
    with engine.connect() as conn:
        query = """
        SELECT 
            oc.*,
            pc.nome as produto_nome,
            f.for_nome as fornecedor_nome,
            f.for_prazo as fornecedor_prazo,
            f.for_forma_pagamento as fornecedor_forma_pagamento
        FROM ordem_compra oc
        LEFT JOIN produto_compras pc ON oc.oc_produto_id = pc.prod_comp_id
        LEFT JOIN fornecedores f ON oc.oc_fornecedor_id = f.for_id
        WHERE oc.oc_numero = :oc_numero
        ORDER BY oc.oc_id
        """
        items_df = pd.read_sql(query, conn, params={"oc_numero": oc_numero})

    if items_df.empty:
        raise PreventUpdate

    # Marcar linhas com status diferente de "Aguardando Recebimento" para destacar
    items_df = items_df.copy()
    items_df['oc_status_no_grupo_diferente'] = items_df['oc_status'] != 'Aguardando Recebimento'

    pdf_bytes = generate_ordem_compra_pdf(oc_numero, items_df)
    filename = f"Ordem_Compra_OC_{str(oc_numero).replace(' ', '_')}.pdf"
    return dcc.send_bytes(pdf_bytes, filename)
