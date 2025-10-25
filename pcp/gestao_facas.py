import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, callback_context, no_update
from dash.dependencies import Input, Output, State
import pandas as pd
from banco_dados.banco import listar_dados, Banco
from pcp.formularios import form_faca
from app import app
import os
import base64
import uuid

# Definir pasta de upload para as facas
UPLOAD_FOLDER_FACAS = "assets/facas"
if not os.path.exists(UPLOAD_FOLDER_FACAS):
    os.makedirs(UPLOAD_FOLDER_FACAS)

def salvar_base64_como_arquivo(base64_str, filename):
    try:
        if "," not in base64_str:
            return None
            
        content_type, content_string = base64_str.split(",")
        decoded = base64.b64decode(content_string)
        
        ext = os.path.splitext(filename)[1].lower() if filename else ".png"
        if not ext or ext == ".":
            ext = ".png"
            
        nome_arquivo = f"faca_{uuid.uuid4().hex}{ext}"
        caminho_salvo = os.path.join(UPLOAD_FOLDER_FACAS, nome_arquivo)
        
        with open(caminho_salvo, "wb") as f:
            f.write(decoded)
            
        return f"/{UPLOAD_FOLDER_FACAS}/{nome_arquivo}"
        
    except Exception as e:
        print(f"Erro ao salvar imagem da faca: {str(e)}")
        return None

def layout_gestao_facas():
    # Carregar dados das facas do banco
    df_facas = listar_dados('faca')
   
    # Criar colunas para a tabela
    columns = [
        {'name': 'Código', 'id': 'fac_cod'},
        {'name': 'Descrição', 'id': 'fac_descricao'},
        {'name': 'Medida', 'id': 'fac_medida'},
        {'name': 'Máquina', 'id': 'fac_maquina'},
        {'name': 'Status', 'id': 'fac_status'},
        {'name': 'Localização', 'id': 'fac_localizacao'},
        {'name': 'Tipo de Papel', 'id': 'fac_tipo_papel'}
    ]
 
    layout = dbc.Container([
        # Incluir o modal/form
        form_faca.layout,
 
        dbc.Row([
            dbc.Col([
                # Filtros
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Input(
                                    id="filtro-codigo",
                                    placeholder="Filtrar por código...",
                                    type="text",
                                    className="mb-2"
                                ),
                            ], width=2),
                            dbc.Col([
                                dbc.Input(
                                    id="filtro-descricao",
                                    placeholder="Filtrar por descrição...",
                                    type="text",
                                    className="mb-2"
                                ),
                            ], width=2),
                            dbc.Col([
                                dcc.Dropdown(
                                    id="filtro-maquina",
                                    placeholder="Filtrar por máquina...",
                                    options=[
                                        {"label": "CORTE E VINCO SAPO", "value": "CORTE E VINCO SAPO"},
                                        {"label": "CORTE E VINCO SBB", "value": "CORTE E VINCO SBB"},
                                        {"label": "CORTE E VINCO SBL", "value": "CORTE E VINCO SBL"},
                                    ],
                                    className="mb-2"
                                ),
                            ], width=2),
                            dbc.Col([
                                dcc.Dropdown(
                                    id="filtro-status",
                                    placeholder="Filtrar por status...",
                                    options=[
                                        {"label": "ATIVA", "value": "ATIVA"},
                                        {"label": "MANUTENÇÃO", "value": "MANUTENCAO"},
                                        {"label": "INATIVA", "value": "INATIVA"},
                                    ],
                                    className="mb-2"
                                ),
                            ], width=2),
                            dbc.Col([
                                dbc.Button(
                                    "Nova Faca",
                                    id="btn-nova-faca",
                                    color="success",
                                    className="me-2"
                                ),
                                dbc.Button(
                                    "Filtrar",
                                    id="btn-filtrar",
                                    color="primary",
                                ),
                            ], width=4, className="d-flex justify-content-end align-items-start"),
                        ]),
                    ])
                ], className="mb-3"),
               
                # Tabela de Facas
                dash_table.DataTable(
                    id='tabela-facas',
                    columns=columns,
                    data=df_facas.to_dict('records') if not df_facas.empty else [],
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '10px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    page_size=15,
                    sort_action="native",
                    sort_mode="multi",
                    row_selectable="single",
                    selected_rows=[],
                    style_data={
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'cursor': 'pointer'
                    },
                )
            ])
        ]),
       
        # Div para mensagens de feedback
        html.Div(id="feedback-facas", className="mt-3"),
       
    ], fluid=True)
   
    return layout
 
# Callback único para todas as operações
@app.callback(
    [
        Output("modal-form-faca", "is_open"),
        Output("modal-faca-title", "children"),
        Output("fac-editing-id", "data"),
        Output("fac-delete-div", "style"),
        Output("fac-codigo", "value"),
        Output("fac-medida", "value"),
        Output("fac-descricao", "value"),
        Output("fac-maquina", "value"),
        Output("fac-status", "value"),
        Output("fac-localizacao", "value"),
        Output("fac-tipo-papel", "value"),
        Output("modal-confirm-delete", "is_open"),
        Output("feedback-facas", "children"),
        Output("tabela-facas", "data"),
        Output("output-faca-upload", "children"),
        Output("stored-faca-path", "data"),
    ],
    [
        Input("btn-nova-faca", "n_clicks"),
        Input("btn-filtrar", "n_clicks"),
        Input("fac-cancel", "n_clicks"),
        Input("fac-submit", "n_clicks"),
        Input("tabela-facas", "selected_rows"),
        Input("fac-delete", "n_clicks"),
        Input("fac-cancel-delete", "n_clicks"),
        Input("fac-confirm-delete", "n_clicks"),
        Input("upload-faca-imagem", "contents"),
    ],
    [
        State("modal-form-faca", "is_open"),
        State("modal-confirm-delete", "is_open"),
        State("tabela-facas", "data"),
        State("fac-editing-id", "data"),
        State("fac-codigo", "value"),
        State("fac-medida", "value"),
        State("fac-descricao", "value"),
        State("fac-maquina", "value"),
        State("fac-status", "value"),
        State("fac-localizacao", "value"),
        State("fac-tipo-papel", "value"),
        # Estados dos filtros
        State("filtro-codigo", "value"),
        State("filtro-descricao", "value"),
        State("filtro-maquina", "value"),
        State("filtro-status", "value"),
        State("upload-faca-imagem", "filename"),
        State("stored-faca-path", "data"),
    ],
    prevent_initial_call=True
)
def handle_all_operations(btn_novo, btn_filtrar, btn_cancel, btn_submit, selected_rows,
                         btn_delete, btn_cancel_delete, btn_confirm_delete,
                         image_contents,
                         is_modal_open, is_delete_modal_open, table_data, faca_id,
                         codigo, medida, descricao, maquina, status, localizacao, tipo_papel,
                         filtro_codigo, filtro_descricao, filtro_maquina, filtro_status,
                         image_filename, stored_image_path):
   
    ctx = callback_context
    if not ctx.triggered:
        return [no_update] * 16
   
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
   
    # Valores padrão para retorno
    modal_open = is_modal_open
    modal_title = "Nova Faca"
    editing_id = faca_id
    delete_style = {"display": "none"}
    form_values = (codigo, medida, descricao, maquina, status, localizacao, tipo_papel)
    delete_modal_open = is_delete_modal_open
    feedback = None
    table_data_out = table_data
    upload_preview = no_update
    image_path_to_store = stored_image_path

    try:
        banco = Banco()

        # Upload de imagem
        if trigger_id == 'upload-faca-imagem':
            if image_contents:
                # Salvar a imagem e obter o caminho
                caminho_salvo = salvar_base64_como_arquivo(image_contents, image_filename)
                if caminho_salvo:
                    upload_preview = html.Div([
                        html.Img(src=caminho_salvo, style={'height': '100px', 'marginTop': '10px'}),
                        html.P(os.path.basename(caminho_salvo), className="mt-1")
                    ])
                    image_path_to_store = caminho_salvo
                else:
                    feedback = dbc.Alert("Erro ao processar a imagem.", color="danger")
                    upload_preview = html.Div("Erro no upload.", style={'color': 'red'})
            return [modal_open, no_update, editing_id, no_update] + list(form_values) + [delete_modal_open, feedback, table_data_out, upload_preview, image_path_to_store]

        # Abrir modal para nova faca
        if trigger_id == "btn-nova-faca":
            return [True, "Nova Faca", None, {"display": "none"}] + [None] * 7 + [False, None, no_update, None, None]

        # Selecionar linha da tabela para edição
        if trigger_id == "tabela-facas" and selected_rows:
            faca_selecionada = table_data[selected_rows[0]]
            editing_id = faca_selecionada.get("fac_id")
            
            # Carregar a imagem existente
            imagem_faca = faca_selecionada.get('fac_imagem')
            if imagem_faca and os.path.exists(imagem_faca.lstrip('/')):
                upload_preview = html.Img(src=imagem_faca, style={'height': '100px', 'marginTop': '10px'})
            else:
                upload_preview = html.Div("Nenhuma imagem.", style={'color': '#888'})


            return [True, f"Editando Faca: {faca_selecionada.get('fac_cod')}", editing_id, {"display": "block"}] + \
                   [faca_selecionada.get(k) for k in ["fac_cod", "fac_medida", "fac_descricao", "fac_maquina", "fac_status", "fac_localizacao", "fac_tipo_papel"]] + \
                   [False, None, no_update, upload_preview, imagem_faca]

        # Botão Excluir abre o modal de confirmação
        if trigger_id == "fac-delete":
            return [modal_open, no_update, editing_id, {"display": "block"}, *form_values, True, feedback, table_data_out, upload_preview, image_path_to_store]

        # Cancelar a exclusão
        if trigger_id == "fac-cancel-delete":
            return [modal_open, no_update, editing_id, {"display": "block"}, *form_values, False, feedback, table_data_out, upload_preview, image_path_to_store]
        
        # Confirmar a exclusão
        if trigger_id == "fac-confirm-delete" and editing_id:
            try:
                # Excluir imagem associada se existir
                faca_a_excluir = banco.ler_tabela('faca').query(f"fac_id == {editing_id}").iloc[0]
                imagem_antiga = faca_a_excluir.get('fac_imagem')
                if imagem_antiga and os.path.exists(imagem_antiga.lstrip('/')):
                    os.remove(imagem_antiga.lstrip('/'))

                banco.deletar_dado('faca', editing_id)
                df_facas = listar_dados('faca')
                feedback = dbc.Alert(f"Faca ID {editing_id} excluída com sucesso!", color="success")
                # Fechar ambos os modais e limpar o formulário
                return [False, "Nova Faca", None, {"display": "none"}] + [None] * 7 + [False, feedback, df_facas.to_dict('records'), None, None]
            except Exception as e:
                feedback = dbc.Alert(f"Erro ao excluir faca: {e}", color="danger")
                return [modal_open, no_update, editing_id, {"display": "block"}, *form_values, False, feedback, table_data_out, upload_preview, image_path_to_store]

        # Salvar (Criar ou Editar)
        if trigger_id == "fac-submit":
            if not all([medida, descricao, maquina, status]):
                return [modal_open, no_update, editing_id, delete_style] + list(form_values) + [delete_modal_open, dbc.Alert("Preencha todos os campos obrigatórios.", color="warning"), table_data_out, upload_preview, image_path_to_store]

            dados_faca = {
                "fac_medida": medida,
                "fac_descricao": descricao,
                "fac_maquina": maquina,
                "fac_status": status,
                "fac_localizacao": localizacao,
                "fac_tipo_papel": tipo_papel,
                "fac_imagem": image_path_to_store
            }

            if editing_id: # Editar
                # Lógica para não apagar a imagem se nenhuma nova for enviada
                if not image_contents and stored_image_path:
                    dados_faca['fac_imagem'] = stored_image_path
                banco.editar_dado('faca', editing_id, **dados_faca)
                feedback = dbc.Alert("Faca atualizada com sucesso!", color="success")
            else: # Criar
                df_facas = banco.ler_tabela('faca')
                proximo_id = 1 if df_facas.empty else df_facas['fac_id'].max() + 1
                codigo_gerado = f'FA-{proximo_id}'
                dados_faca["fac_cod"] = codigo_gerado
                banco.inserir_dados('faca', **dados_faca)
                feedback = dbc.Alert("Nova faca criada com sucesso!", color="success")
            
            df_facas = listar_dados('faca')
            return [False, "Nova Faca", None, {"display": "none"}] + [None] * 7 + [False, feedback, df_facas.to_dict('records'), None, None]

        # Filtrar tabela
        if trigger_id == "btn-filtrar":
            df_facas = listar_dados('faca')
            if filtro_codigo:
                df_facas = df_facas[df_facas['fac_cod'].str.contains(filtro_codigo, case=False, na=False)]
            if filtro_descricao:
                df_facas = df_facas[df_facas['fac_descricao'].str.contains(filtro_descricao, case=False, na=False)]
            if filtro_maquina:
                df_facas = df_facas[df_facas['fac_maquina'] == filtro_maquina]
            if filtro_status:
                df_facas = df_facas[df_facas['fac_status'] == filtro_status]
            return [False, "Nova Faca", None, {"display": "none"}] + [None] * 7 + [False, None, df_facas.to_dict('records'), None, None]

        # Cancelar/Fechar modal
        if trigger_id == "fac-cancel":
            return [False, "Nova Faca", None, {"display": "none"}] + [None] * 7 + [False, None, no_update, None, None]

    except Exception as e:
        feedback = dbc.Alert(f"Ocorreu um erro: {e}", color="danger")

    return [modal_open, modal_title, editing_id, delete_style] + list(form_values) + [delete_modal_open, feedback, table_data_out, upload_preview, image_path_to_store]