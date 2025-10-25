import dash
from dash import html, dcc, dash_table, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd
from app import app
from banco_dados.banco import Banco
from dash.exceptions import PreventUpdate
import os
import base64
import uuid
from flask import request

# Definir pasta de upload para as chapas
UPLOAD_FOLDER = "assets/chapas"

# Função para salvar imagem base64 como arquivo
def salvar_base64_como_arquivo(base64_str, filename):
    try:
        # Verificar se a string base64 está no formato correto
        if "," not in base64_str:
            print("Erro: formato de base64 inválido")
            return None
            
        content_type, content_string = base64_str.split(",")
        decoded = base64.b64decode(content_string)
        
        # Obter extensão do arquivo ou usar .png como padrão
        ext = os.path.splitext(filename)[1].lower() if filename else ".png"
        if not ext or ext == ".":
            ext = ".png"
            
        # Criar nome de arquivo único
        nome_arquivo = f"chapa_{uuid.uuid4().hex}{ext}"
        caminho_salvo = os.path.join(UPLOAD_FOLDER, nome_arquivo)
        
        # Garantir que a pasta existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # Salvar o arquivo
        with open(caminho_salvo, "wb") as f:
            f.write(decoded)
            
        print(f"Imagem salva com sucesso em: {caminho_salvo}")
        return f"/assets/chapas/{nome_arquivo}"
        
    except Exception as e:
        print(f"Erro ao salvar imagem: {str(e)}")
        return None

layout = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle("Cadastro de Chapa")),

    dbc.ModalBody([
        # Layout principal com duas colunas
        dbc.Row([
            # Coluna esquerda: Campos do formulário
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Código:", className="fw-bold"),
                        dcc.Dropdown(id="input_codigo", placeholder="Código", options=[])
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Semana:", className="fw-bold"),
                        dbc.Input(id="input_semana", type="number", placeholder="Semana")
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Folhas:", className="fw-bold"),
                        dbc.Input(id="input_folhas", type="number", placeholder="Folhas")
                    ], width=4),
                ], className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Tamanho:", className="fw-bold"),
                        dcc.Dropdown(
                            id="input_tamanho",
                            placeholder="Tamanho",
                            options=[{"label": i, "value": i} for i in [
                                'CAIXA 5L', 'CAIXA 10L', 'CAIXA 7L', 'TAMPA 10L', 'TAMPA 5L', 'ESPECIAL', 'CINTA', 'PIZZA',
                                'POTE 500ML', 'POTE 480ML', 'POTE 240ML', 'POTE 250ML',
                                'POTE 1L', 'POTE 360ML', 'POTE 180ML', 'POTE 150ML',
                                'POTE 120ML', 'POTE 80ML', 'COPO 360ML', 'COPO 200ML', 'COPO 100ML'
                            ]],
                            value=None,  # para ser preenchido na edição ou limpo após ação
                            clearable=True
                        )
                    ], width=12),
                ], className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Observações:", className="fw-bold"),
                        dbc.Input(id="input_obs", type="text", placeholder="Observações")
                    ], width=12),
                ], className="mb-3"),
                
                # Botões abaixo dos campos
                dbc.Row([
                    dbc.Col([
                        dbc.Button("Criar", id="btn_criar", color="success", className="w-100")
                    ], width=6),
                    dbc.Col([
                        dbc.Button("Editar", id="btn_editar", color="warning", className="w-100")
                    ], width=6),
                ], className="mb-3"),
            ], width=8),  # Fim da coluna esquerda
            
            # Coluna direita: Upload da imagem
            dbc.Col([
                dbc.Label("Imagem da Chapa:", className="fw-bold"),
                dcc.Upload(
                    id="upload_chapa_imagem",
                    children=html.Div([
                        html.I(className="fas fa-upload mr-2"),
                        html.Span("Arraste ou clique para selecionar uma imagem")
                    ], style={
                        'textAlign': 'center',
                        'padding': '20px 0',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'cursor': 'pointer'
                    }),
                    multiple=False,
                    accept="image/*",
                    style={"marginTop": "10px"}
                ),
                html.Div(id="upload_chapa_path", style={"marginTop": "10px", "fontSize": "small"}),
                html.Div(id="upload_error", style={"color": "red", "fontSize": "small", "marginTop": "5px"}),
                html.Div(id="imagem_chapa_preview", style={"marginTop": "10px", "maxHeight": "300px", "overflow": "auto"}),
                dcc.Store(id="stored_chapa_path"),
                html.Small("Formatos aceitos: JPG, PNG, GIF, BMP. Tamanho máximo: 5MB", style={"marginTop": "10px", "display": "block", "color": "#666"})
            ], width=4),  # Fim da coluna direita
        ], className="mb-3"),  # Fim do layout principal

        # Tabela
        html.H5("Chapas Cadastradas", className="mt-4 mb-2"),
        dash_table.DataTable(
            id="tabela_chapas",
            columns=[
                {"name": "Código", "id": "ch_codigo"},
                {"name": "Semana", "id": "ch_semana"},
                {"name": "Tamanho", "id": "ch_tamanho"},
                {"name": "Folhas", "id": "ch_folhas"},
                {"name": "Observações", "id": "ch_obs"},
                
            ],
            data=[],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left'},
            page_size=5
        )
    ]),

    dbc.ModalFooter([
        dbc.Button("Fechar", id="btn_fechar", className="ms-auto", color="secondary")
    ])
], id="modal_chapa", size="xl", is_open=False)



@app.callback(
    Output("modal_chapa", "is_open"),
    Output("tabela_chapas", "data"),
    Output("input_codigo", "options"),
    Output("input_semana", "value"),
    Output("input_tamanho", "value"),
    Output("input_folhas", "value"),
    Output("input_obs", "value"),
    Output("stored_chapa_path", "data"),
    Output("upload_chapa_path", "children"),
    Output("upload_error", "children"),
    Output("imagem_chapa_preview", "children"),
    Input("abrir_modal_chapa", "n_clicks"),
    Input("btn_fechar", "n_clicks"),
    Input("btn_criar", "n_clicks"),
    Input("btn_editar", "n_clicks"),
    Input("input_codigo", "value"),
    Input("upload_chapa_imagem", "contents"),
    State("modal_chapa", "is_open"),
    State("input_codigo", "value"),
    State("input_semana", "value"),
    State("input_tamanho", "value"),
    State("input_folhas", "value"),
    State("input_obs", "value"),
    State("stored_chapa_path", "data"),
    State("upload_chapa_imagem", "filename"),
    prevent_initial_call=True
)
def gerenciar_modal_chapa(n_abrir, n_fechar, n_criar, n_editar, cod_dropdown, contents,
                          is_open, codigo, semana, tamanho, folhas, obs, chapa_path, filename):
    banco = Banco()
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    imagem_preview = ""
    upload_msg = ""
    erro_msg = ""

    # Processar upload de imagem
    if trigger_id == "upload_chapa_imagem" and contents:
        try:
            # Verificar tamanho da imagem (limite de 5MB)
            content_string = contents.split(",")[1]
            tamanho_bytes = len(base64.b64decode(content_string))
            tamanho_mb = tamanho_bytes / (1024 * 1024)
            
            if tamanho_mb > 5:
                erro_msg = f"Imagem muito grande: {tamanho_mb:.1f}MB. O limite é 5MB."
                return (is_open, no_update, no_update, semana, tamanho, folhas, obs, 
                        None, "", erro_msg, "")
            
            # Verificar formato da imagem
            if filename:
                ext = os.path.splitext(filename)[1].lower()
                formatos_validos = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
                if ext not in formatos_validos and ext != '':
                    erro_msg = f"Formato de arquivo não suportado: {ext}. Use JPG, PNG, GIF ou BMP."
                    return (is_open, no_update, no_update, semana, tamanho, folhas, obs, 
                            None, "", erro_msg, "")
            
            imagem_preview = html.Img(src=contents, style={"maxWidth": "100%", "maxHeight": "200px"})
            upload_msg = f"Imagem carregada: {filename} ({tamanho_mb:.1f}MB)"
            return (is_open, no_update, no_update, semana, tamanho, folhas, obs, 
                    contents, upload_msg, "", imagem_preview)
        except Exception as e:
            erro_msg = f"Erro ao processar imagem: {str(e)}"
            return (is_open, no_update, no_update, semana, tamanho, folhas, obs, 
                    None, "", erro_msg, "")

    # Criar nova chapa
    if trigger_id == "btn_criar" and n_criar:
        try:
            # Salvar a imagem se houver
            caminho_imagem = None
            if chapa_path and isinstance(chapa_path, str) and chapa_path.startswith("data:image/"):
                caminho_imagem = salvar_base64_como_arquivo(chapa_path, filename)
                if caminho_imagem:
                    upload_msg = "Imagem salva com sucesso!"
                else:
                    erro_msg = "Erro ao salvar imagem. Tente novamente."

            banco.inserir_dados(
                "chapa",
                ch_semana=semana,
                ch_tamanho=tamanho,
                ch_folhas=folhas,
                ch_obs=obs,
                ch_imagem=caminho_imagem
            )
        except Exception as e:
            erro_msg = f"Erro ao criar chapa: {str(e)}"
            print(erro_msg)
            raise PreventUpdate

    # Editar chapa existente
    elif trigger_id == "btn_editar" and codigo and n_editar:
        try:
            # Salvar a imagem se houver
            caminho_imagem = chapa_path
            if chapa_path and isinstance(chapa_path, str) and chapa_path.startswith("data:image/"):
                caminho_imagem = salvar_base64_como_arquivo(chapa_path, filename)
                if caminho_imagem:
                    upload_msg = "Imagem salva com sucesso!"
                else:
                    erro_msg = "Erro ao salvar imagem. Tente novamente."

            banco.editar_dado(
                "chapa",
                id=codigo,
                ch_semana=semana,
                ch_tamanho=tamanho,
                ch_folhas=folhas,
                ch_obs=obs,
                ch_imagem=caminho_imagem
            )
        except Exception as e:
            erro_msg = f"Erro ao editar chapa: {str(e)}"
            print(erro_msg)
            raise PreventUpdate

    # Atualiza a tabela e o dropdown
    df = banco.ler_tabela("chapa")
    data = df.to_dict("records")
    options = [{"label": cod, "value": cod} for cod in df["ch_codigo"].unique()] if not df.empty and "ch_codigo" in df.columns else []

    # Preencher os campos ao selecionar um código
    if trigger_id == "input_codigo" and cod_dropdown:
        linha = df[df["ch_codigo"] == cod_dropdown]
        if not linha.empty:
            linha = linha.iloc[0]
            chapa_img_path = linha.get("ch_imagem")
            
            # Preparar preview da imagem se existir
            if chapa_img_path:
                imagem_preview = html.Img(src=chapa_img_path, style={"maxWidth": "100%", "maxHeight": "200px"})
                upload_msg = f"Imagem carregada de: {os.path.basename(chapa_img_path)}"
            
            return (is_open, data, options, linha["ch_semana"], linha["ch_tamanho"], 
                   linha["ch_folhas"], linha["ch_obs"], chapa_img_path, upload_msg, "", imagem_preview)

    # Abrir ou fechar modal
    if trigger_id == "abrir_modal_chapa" and n_abrir:
        return True, data, options, None, None, None, None, None, "", "", ""
    elif trigger_id == "btn_fechar" and n_fechar:
        return False, data, options, None, None, None, None, None, "", "", ""
    else:
        return is_open, data, options, None, None, None, None, None, upload_msg, erro_msg, imagem_preview
