from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from app import app
from banco_dados.banco import Banco
from datetime import datetime, timedelta, time
import pandas as pd


banco = Banco()

layout = html.Div([
    

    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Gerenciar Agendamentos de Máquinas")),
            dbc.ModalBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Setor:"),
                        dcc.Dropdown(
                            id="dropdown-setor",
                            placeholder="Selecione um setor",
                            className="mb-3"
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Máquina:"),
                        dcc.Dropdown(
                            id="dropdown-maquina",
                            placeholder="Selecione uma máquina",
                            className="mb-3"
                        )
                    ], width=6)
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Label("Categoria:"),
                        dcc.Dropdown(
                            id="dropdown-categoria-horario",
                            placeholder="Selecione uma categoria",
                            className="mb-3"
                        )
                    ], width=6),
         
                ]),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Dia:"),
                        dcc.DatePickerSingle(
                            id="input-dia",
                            placeholder="Selecione o dia",
                            display_format="DD/MM/YYYY",
                            className="mb-3",
                            style={'width': '100%'}
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Hora Inicial:"),
                        dcc.Input(
                            id="input-hora-inicial",
                            type="text",
                            className="form-control mb-3",
                            placeholder="HH:MM:SS"
                        )
                    ], width=6)
                ]),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Hora Final:"),
                        dcc.Input(
                            id="input-hora-final",
                            type="text",
                            className="form-control mb-3",
                            placeholder="HH:MM:SS"
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Hora de Espaçamento:"),
                        dcc.Input(
                            id="input-hora-espaçamento",
                            type="text",
                            className="form-control mb-3",
                            placeholder="HH:MM:SS"
                        )
                    ], width=6)
                ]),
                
                dbc.Button("Adicionar Agendamento", id="btn-add-agendamento", color="success", className="w-100 mb-3"),
                
                html.Div(id="div-mensagem-erro", className="text-danger mt-3")
            ]),
            dbc.ModalFooter(
                dbc.Button("Fechar", id="close-modal-agendamento", className="ms-auto", n_clicks=0)
            ),
        ],
        id="modal-horario",
        is_open=False,
    ),
])

@app.callback(
    Output("modal-horario", "is_open"),
    [Input("btn_add_horarios", "n_clicks"), Input("close-modal-agendamento", "n_clicks")],
    [State("modal-horario", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_horario(n_clicks_open, n_clicks_close, is_open):
    if n_clicks_open or n_clicks_close:
        return not is_open
    return is_open

@app.callback(
    Output("dropdown-setor", "options"),
    Input("modal-horario", "is_open")
)
def carregar_setores(is_open):

    if is_open:
        df_setores = banco.ler_tabela("setor")
   
        if df_setores.empty:
            return []
        
        setores = [
            {"label": row["setor_nome"], "value": row["setor_id"]} 
            for _, row in df_setores.iterrows()
        ]
  
        return setores
    return []

@app.callback(
    Output("dropdown-maquina", "options"),
    Input("dropdown-setor", "value")
)
def carregar_maquinas(setor_id):
    if setor_id:
        df_maquinas = banco.ler_tabela("maquina")
        if df_maquinas.empty:
            return []
        maquinas = [
            {"label": row["maquina_nome"], "value": row["maquina_id"]} 
            for _, row in df_maquinas.query(f"setor_id == {setor_id}").iterrows()
        ]
        return maquinas
    return []

@app.callback(
    Output("div-mensagem-erro", "children"),
    Input("btn-add-agendamento", "n_clicks"),
    State("dropdown-setor", "value"),
    State("dropdown-maquina", "value"),
    State("input-dia", "date"),
    State("input-hora-inicial", "value"),
    State("input-hora-final", "value"),
    State("input-hora-espaçamento", "value"),
)
def agendar_producao(n_clicks, setor_id, maquina_id, data, hora_inicio, hora_final, espacamento):
    if not n_clicks:
        return ""
    
    # Verificar se todos os campos foram preenchidos
    if not all([setor_id, maquina_id, data, hora_inicio, hora_final, espacamento]):
        return "Preencha todos os campos antes de agendar."
    
    # Verificação do formato da hora
    hora_format = "%H:%M:%S"
    try:
        datetime.strptime(hora_inicio, hora_format)
        datetime.strptime(hora_final, hora_format)
        datetime.strptime(espacamento, hora_format)
    except ValueError:
        return "Verifique o formato das horas. O formato correto é 01:00:00"
    
    # Converter string de data para objeto datetime.date
    data = datetime.strptime(data, "%Y-%m-%d").date()
    
    # Converter string de hora (hora_inicio e hora_final) para objetos datetime.time
    hora_inicio = datetime.strptime(hora_inicio, hora_format).time()
    hora_final = datetime.strptime(hora_final, hora_format).time()

    # Verificar se a hora final é menor que a hora inicial
    if hora_final <= hora_inicio:
        return "A hora final deve ser maior que a hora inicial."
    
    # Converter espaçamento de hora para timedelta (ex: '01:00:00' para 1 hora)
    espacamento = timedelta(hours=int(espacamento.split(":")[0]), minutes=int(espacamento.split(":")[1]), seconds=int(espacamento.split(":")[2]))
    
    df_producao = banco.ler_tabela("producao")

    if not df_producao.empty:
        agendamentos_existentes = df_producao[
            (df_producao["pr_maquina_id"] == maquina_id) & 
            (df_producao["pr_data"] == (data))  # Converter data para string se necessário
        ]

        if not agendamentos_existentes.empty:
            return "Já existe um agendamento para esta máquina nesta data."
    # Criar registros de produção
    registros = []
    
    # Inicia com o horário 00:00:00 do dia selecionado
    hora_atual = datetime.combine(data, time(0, 0))  # Combina data e hora (00:00:00)

    while hora_atual <= datetime.combine(data, time(23, 59, 59)):  # Verifica até 23:59:59 do mesmo dia
        hora_termino = (hora_atual + espacamento).time()

        # Verificar se o horário está dentro do intervalo desejado (hora_inicio a hora_final)
        if hora_inicio <= hora_atual.time() < hora_final:

            pr_categoria_produto_id = None
            pr_fechado = 0

        else:

            pr_categoria_produto_id = None
            pr_fechado = 1
        
        # Adicionar o registro de produção
        registros.append({
            "pr_setor_id": setor_id,
            "pr_maquina_id": maquina_id,
            "pr_data": hora_atual.date(),  # Usa a data correta
            "pr_inicio": hora_atual.time(),  # Usa o horário correto
            "pr_termino": hora_termino,  # Usa o horário de término correto
            "pr_fechado": pr_fechado,  # Usa o horário de término correto

        })
        
        # Avançar para o próximo intervalo
        hora_atual += espacamento

    # Inserir os registros na tabela de produção
    for registro in registros:
        banco.inserir_dados("producao", **registro)
    
    return "Agendamento realizado com sucesso!"