from dash import html, dcc, callback, Input, Output, State, ALL, no_update
import dash_bootstrap_components as dbc
from banco_dados.banco import Banco
import pandas as pd
from datetime import date, datetime # Importar datetime
import json
from app import app # Importar a instância principal do app

# Instanciar a conexão com o banco de dados
banco = Banco()

# --- Carregar dados para os dropdowns ---
try:
    df_setores = banco.ler_tabela('setor')
    setor_options = [{'label': row['setor_nome'], 'value': row['setor_id']} for index, row in df_setores.iterrows()]
except Exception as e:
    print(f"Erro ao carregar setores: {e}")
    setor_options = []

try:
    df_pcp = banco.ler_tabela('pcp')
    # Filtrar PCPs que não são nulos e converter o label para string
    df_pcp_filtered = df_pcp[pd.notna(df_pcp['pcp_pcp'])]
    pcp_options = [{'label': str(int(row['pcp_pcp'])), 'value': row['pcp_id']} for index, row in df_pcp_filtered.iterrows()]
except Exception as e:
    print(f"Erro ao carregar PCP: {e}")
    pcp_options = []
    
try:
    df_maquinas = banco.ler_tabela('maquina')
except Exception as e:
    print(f"Erro ao carregar máquinas: {e}")
    df_maquinas = pd.DataFrame()

# Itens do Checklist por tipo de produto - podem ser modificados diretamente no código
checklist_items_por_produto = {
    "Pote e Copo": {
        "pote_copo_dimensoes": "Dimensões (Diâmetro, comprimento e altura)",
        "pote_copo_selagem": "Selagem (Fundo e Lateral)",
        "pote_copo_resistencia_vazamento": "Resistência à vazamento",
        "pote_copo_ausencia_defeitos": "Ausência de amassados, rasgos e deformações",
        "pote_copo_impressao": "Impressão nítida e sem borrões",
        "pote_copo_limpeza": "Sem sujidades, contaminações ou mal odor",
        "pote_copo_colagem": "Colagem adequada sem falhas ou excessos",
        "pote_copo_empilhamento": "Suporta empilhamento especificado",
    },
    "Chapas Impressas": {
        "chapas_impressas_cromia": "Cromia (encaixe de cores)",
        "chapas_impressas_dimensoes": "Dimensões (Largura e comprimento)",
        "chapas_impressas_verificacao_visual": "Verificação visual",
    },
    "Chapas Acopladas": {
        "chapas_acopladas_adesao": "Adesão entre camadas (delaminação)",
    },
    "Chapas plastificadas": {
        "chapas_plastificadas_centralizacao": "Centralização das camadas",
        "chapas_plastificadas_adesao": "Adesão entre camadas (delaminação)",
        "chapas_plastificadas_verificacao_visual": "Verificação visual (formação de bolhas e/ou rugas)",
    },
    "Papel cortado": {
        "papel_cortado_sentido_corte": "Corte está no sentido correto?",
    },
    "Papel Colado": {
        "papel_colado_centralizacao": "Centralização da chapa",
        "papel_colado_colagem": "Colagem centralizada",
        "papel_colado_adesao": "Adesão da superfície",
    },
    "Guilhotina/Resmadeira/Rebobinadeira": {
        "guilhotina_verificacao_visual": "Verificação visual (Manchas, tonalidade e/ou manchas)",
        "guilhotina_dimensoes": "Dimensões (Largura e comprimento)",
        "guilhotina_aspecto_visual": "Aspecto visual (tonalidade e/ou manchas)",
    },
    "Caixas": {
        "caixas_verificacao_visual": "Verificação visual (bordas sujas de cola, má impressão, cores, rasgos, abas mal coladas)",
        "caixas_formacao": "Verificação se caixa esta se formando (arestas e vértices da caixa precisam estar retas)",
    }
}

produto_options = [{'label': produto, 'value': produto} for produto in checklist_items_por_produto.keys()]

def create_checklist_layout(product_type=None):
    """Cria dinamicamente as linhas do checklist com base no tipo de produto."""
    if not product_type or product_type not in checklist_items_por_produto:
        return html.Div("Selecione um tipo de produto para ver o checklist.")

    items = checklist_items_por_produto[product_type]
    rows = []
    for key, name in items.items():
        rows.append(
            dbc.Row([
                dbc.Col(html.Label(name), lg=3, md=4),
                dbc.Col(
                    dbc.RadioItems(
                        id={'type': 'checklist-radio', 'index': key},
                        options=[
                            {'label': 'Conforme', 'value': 'conforme'},
                            {'label': 'Não Conforme', 'value': 'nao_conforme'},
                            {'label': 'Não se aplica', 'value': 'nao_aplica'},
                        ],
                        value='nao_aplica', # Valor padrão
                        inline=True,
                        labelClassName="me-3",
                        inputClassName="me-1"
                    ),
                    lg=6, md=8
                ),
                dbc.Col(
                    dbc.Input(id={'type': 'checklist-qty', 'index': key}, type="number", min=0, placeholder="Qtd"),
                    lg=3, md=4
                )
            ], className="mb-2 align-items-center")
        )
    return html.Div(rows)

def get_layout():
    """Retorna o layout do modal do formulário de inspeção."""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Registrar Inspeção de Processo")),
            dbc.ModalBody(
                dbc.Form([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Setor", htmlFor="inspecao-setor-dropdown"),
                            dcc.Dropdown(
                                id="inspecao-setor-dropdown",
                                options=setor_options,
                                placeholder="Selecione o Setor",
                            ),
                        ], md=6),
                        dbc.Col([
                            html.Label("Máquina", htmlFor="inspecao-maquina-dropdown"),
                            dcc.Dropdown(
                                id="inspecao-maquina-dropdown",
                                placeholder="Selecione primeiro o setor",
                                disabled=True,
                            ),
                        ], md=6),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Data", htmlFor="inspecao-data-picker"),
                            dcc.DatePickerSingle(
                                id='inspecao-data-picker',
                                date=date.today(),
                                display_format='DD/MM/YYYY',
                                className="w-100"
                            ),
                        ], md=6),
                         dbc.Col([
                            html.Label("Lote (PCP)", htmlFor="inspecao-pcp-dropdown"),
                            dcc.Dropdown(
                                id="inspecao-pcp-dropdown",
                                options=[],  # <- começa vazio
                                placeholder="Selecione o Lote",
                            ),
                        ], md=6),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Produto Analisado", htmlFor="inspecao-tipo-produto-dropdown"),
                            dcc.Dropdown(
                                id="inspecao-tipo-produto-dropdown",
                                options=produto_options,
                                placeholder="Selecione o Tipo de Produto",
                            ),
                        ], md=6),
                         dbc.Col([
                            html.Label("Qtd. Inspecionada", htmlFor="inspecao-qtd-input"),
                            dbc.Input(id="inspecao-qtd-input", type="number", min=0),
                        ], md=6),
                    ], className="mb-3"),
                    
                    html.Hr(),
                    html.H5("Checklist de Qualidade", className="mb-3"),
                    html.Div(id='checklist-container'), # Container para o checklist dinâmico
                    
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Observações", htmlFor="inspecao-observacao-textarea"),
                            dbc.Textarea(id="inspecao-observacao-textarea", style={'height': '100px'}),
                        ])
                    ], className="mb-3")
                ])
            ),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="inspecao-cancelar-btn", color="secondary", n_clicks=0),
                dbc.Button("Salvar", id="inspecao-salvar-btn", color="primary", n_clicks=0),
            ]),
            dcc.Store(id='inspecao-store-temp-data') # Armazenamento temporário
        ],
        id="modal-form-inspecao",
        is_open=False,
        size="lg",
    )

form_inspecao_layout = get_layout() # Mantemos isso para compatibilidade se houver outros usos, mas a função é o principal

# Callback para atualizar o checklist dinamicamente
@app.callback(
    Output('checklist-container', 'children'),
    Input('inspecao-tipo-produto-dropdown', 'value')
)
def update_checklist_layout(product_type):
    if not product_type:
        return html.Div("Selecione um tipo de produto para ver o checklist.", className="text-muted")
    return create_checklist_layout(product_type)

# Callback para atualizar o dropdown de máquinas com base no setor selecionado
@app.callback(
    Output("inspecao-maquina-dropdown", "options"),
    Output("inspecao-maquina-dropdown", "disabled"),
    Input("inspecao-setor-dropdown", "value")
)
def update_maquina_dropdown(setor_id):
    if not setor_id:
        return [], True
    
    maquinas_filtradas = df_maquinas[df_maquinas['setor_id'] == setor_id]
    maquina_options = [{'label': row['maquina_nome'], 'value': row['maquina_id']} for _, row in maquinas_filtradas.iterrows()]
    
    return maquina_options, False

# Callback para salvar os dados do formulário no banco
@app.callback(
    Output("inspecao-store-success-signal", "data", allow_duplicate=True),
    Output("modal-form-inspecao", "is_open", allow_duplicate=True),
    Input("inspecao-salvar-btn", "n_clicks"),
    [
        State("inspecao-setor-dropdown", "value"),
        State("inspecao-maquina-dropdown", "value"),
        State("inspecao-data-picker", "date"),
        State("inspecao-pcp-dropdown", "value"),
        State("inspecao-tipo-produto-dropdown", "value"),
        State("inspecao-qtd-input", "value"),
        State({'type': 'checklist-radio', 'index': ALL}, 'id'),
        State({'type': 'checklist-radio', 'index': ALL}, 'value'),
        State({'type': 'checklist-qty', 'index': ALL}, 'value'),
        State("inspecao-observacao-textarea", "value")
    ],
    prevent_initial_call=True
)
def salvar_inspecao(n_clicks, setor_id, maquina_id, data_str, pcp_id, tipo_produto, qtd, checklist_ids, checklist_values, checklist_qtys, observacao):
    if not n_clicks:
        return no_update, no_update

    if not all([setor_id, maquina_id, data_str, pcp_id, tipo_produto, qtd]):
        print("Campos obrigatórios não preenchidos.")
        return no_update, True # Mantém o modal aberto

    # Converte a string de data para um objeto date
    try:
        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        print(f"Erro: Formato de data inválido - {data_str}")
        return no_update, True # Mantém o modal aberto

    # Constrói o JSON do checklist
    checklist_keys = [item['index'] for item in checklist_ids]
    checklist_json = {
        key: {"status": checklist_values[i], "quantidade": checklist_qtys[i] or 0}
        for i, key in enumerate(checklist_keys)
    }

    dados_para_salvar = {
        "setor_id": setor_id,
        "maquina_id": maquina_id,
        "data": data_obj, # Usa o objeto date convertido
        "pcp_id": pcp_id,
        "tipo_produto": tipo_produto,
        "qtd_inspecionada": qtd,
        "checklist": checklist_json,
        "observacao": observacao
    }
    

    try:
        banco.inserir_dados(
            "inspecao_processo",
            **dados_para_salvar
        )
        
        return {'type': 'save'}, False
    except Exception as e:
        print(f"Erro ao salvar inspeção: {e}")
        return no_update, True

# Callback para fechar o modal ao clicar em "Cancelar"
@app.callback(
    Output("modal-form-inspecao", "is_open", allow_duplicate=True),
    Input("inspecao-cancelar-btn", "n_clicks"),
    prevent_initial_call=True,
)
def fechar_modal(n_clicks):
    if n_clicks:
        return False
    return no_update



def _get_pcp_options():
    """Lê PCPs do banco e retorna options do Dropdown sempre atualizadas."""
    try:
        df_pcp = banco.ler_tabela('pcp')
        # filtra apenas linhas com pcp_pcp não nulo
        df_pcp = df_pcp[pd.notna(df_pcp['pcp_pcp'])]
        # cuidado com conversão para int/str (pode ter valores não numéricos)
        options = []
        for _, row in df_pcp.iterrows():
            label = str(row['pcp_pcp'])  # mantém como string para evitar erro
            options.append({'label': label, 'value': row['pcp_id']})
        return options
    except Exception as e:
        print(f"Erro ao carregar PCP dinamicamente: {e}")
        return []
    

@app.callback(
    Output("inspecao-pcp-dropdown", "options"),
    Output("inspecao-pcp-dropdown", "value"),
    Input("modal-form-inspecao", "is_open"),
    prevent_initial_call=False  # permite rodar na primeira abertura
)
def refresh_pcp_options_on_modal(is_open):
    # Só atualiza quando o modal abrir (True). Quando fechar, não mexe.
    if not is_open:
        return no_update, no_update
    options = _get_pcp_options()
    return options, None  # limpa o valor selecionado ao abrir