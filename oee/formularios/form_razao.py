import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from banco_dados.banco import Banco  # Certifique-se de importar corretamente sua classe Banco
from app import app

banco = Banco()  # Instância do banco

layout = html.Div([

    dcc.Store(id="store-mensagem-razao", data=""),

    dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Gerenciar Razões")),
            dbc.ModalBody([
                dbc.Row([
                    # Coluna à esquerda para os formulários
                    dbc.Col([
                        html.Label("Adicionar Nova Razão:"),
                        dbc.Input(id="input-razao-nome", type="text", placeholder="Nome da razão", className="mb-2"),
                        dcc.Dropdown(id="dropdown-setor-razao", placeholder="Selecione um setor", className="mb-2"),
                        dcc.Dropdown(
                            id="dropdown-razao-level",
                            options=[{'label': str(i), 'value': str(i)} for i in range(1, 7)],
                            placeholder="Selecione o Nível",
                            className="mb-2"
                        ),
                        dcc.Dropdown(id="dropdown-razao-dependencias", placeholder="Selecione as dependências", className="mb-2", multi=False),
                        dcc.Dropdown(id="dropdown-tipo_oee", placeholder="Selecione o Tipo de parada", className="mb-2",options=['PERFORMANCE', 'DISPONIBILIDADE', 'PARADA REGISTRADA'], multi=False),

                        dbc.Button("Adicionar Razão", id="btn-add-razao", color="success", className="w-100 mb-3"),

                        html.Hr(),

                        # Excluir Razão
                        html.Label("id Razão Existente:"),
                        dbc.Row([
                            dbc.Col(dcc.Dropdown(id="dropdown-razao-id", placeholder="id razão", className="mb-2"), width=4),
                            dbc.Col(html.Div(id="div-razao"), width=8),
                        ]),
                        dbc.Input(id="input-razao-edit-nome", type="text", placeholder="Novo nome da razão", className="mb-2"),
                        dcc.Dropdown(id="dropdown-tipo_oee_edit", placeholder="Selecione o Tipo de parada", className="mb-2",options=['PERFORMANCE', 'DISPONIBILIDADE', 'PARADA REGISTRADA'], multi=False),
                        dbc.Row([
                            dbc.Col(dbc.Button("Excluir Razão", id="btn-delete-razao", color="danger", className="w-100"),width=6),
                            dbc.Col(dbc.Button("Salvar Edição", id="btn-edit-razao", color="warning", className="w-100"),width=6),
                        ]),
                        dbc.Alert(id="alert-mensagem-razao", color="success", is_open=False, dismissable=True, className="mt-3")
                    ], width=4),  # Coluna esquerda

                    # Coluna à direita para exibir as tabelas de níveis de razões
                    dbc.Col([
                        html.H5("Níveis de Razões"),
                        html.Div(id="tabelas-niveis")  # Aqui vamos colocar a tabela de níveis de razão
                    ], width=4, style={
                        "maxHeight": "700px",  # Limita a altura da coluna
                        "overflowY": "auto",  # Adiciona o scroll vertical se o conteúdo ultrapassar 500px
                        "border": "1px solid #ddd",  # Para destacar a borda da coluna, se desejar
                    }),
                    dbc.Col([
                        html.H5("Níveis de Razões"),
                        html.Div(id="tabelas-niveis_2")  # Aqui vamos colocar a tabela de níveis de razão
                    ], width=4, style={
                        "maxHeight": "700px",  # Limita a altura da coluna
                        "overflowY": "auto",  # Adiciona o scroll vertical se o conteúdo ultrapassar 500px
                        "border": "1px solid #ddd",  # Para destacar a borda da coluna, se desejar
                    }),
                    
                ])
            ]),
            dbc.ModalFooter(
                dbc.Button("Fechar", id="close-modal-razao", className="ms-auto", n_clicks=0)
            ),
        ],
        id="modal-razao",
        is_open=False,
        className="modal-custom"  # Ajustando a largura do modal para "large"
    ),
])



# Callbacks para abrir/fechar o modal
@app.callback(
    Output("modal-razao", "is_open"),
    [Input("btn_arvore_razoes", "n_clicks"), Input("close-modal-razao", "n_clicks")],
    [State("modal-razao", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_razao(n_clicks_open, n_clicks_close, is_open):
    if n_clicks_open or n_clicks_close:
        return not is_open
    return is_open

def exibir_tabelas_niveis(setor_id, level_razao, state):
    level_razao = str(level_razao)
    if not setor_id or not level_razao:
        return dash.no_update

    # Lê a tabela de razões do banco
    razoens = banco.ler_tabela("razao")
    if razoens.empty:
        return html.Div(f"Tabela Vazia")
    # Filtra as razões pelo setor e nível selecionados
    razoens_filtrados = razoens[(razoens["setor_id"] == setor_id) & (razoens["ra_level"] == level_razao)]

    if razoens_filtrados.empty:
        return html.Div("Nenhuma razão encontrada para esse setor e nível.")

    # Lista para armazenar as tabelas e colunas de cada nível
    tabelas = []

    # Para cada razão no nível selecionado, criamos uma coluna e abaixo dela as dependências
    for _, razao in razoens_filtrados.iterrows():
        ra_id = str(razao["ra_id"])  # Certificando-se de que estamos tratando como string
        ra_nome = razao["ra_razao"]

        # Estilizando o título com fundo verde claro
        coluna = html.Div([
            html.H6(f"id.{ra_id} - {ra_nome}", style={
                "backgroundColor": "#d4edda",  # Verde claro
                "padding": "10px",
                "borderRadius": "5px",
                "color": "#155724",  # Cor de texto verde escuro para contraste
                "fontSize": "18px"
            }),
            
            # Tabela com as dependências do nível abaixo (ra_sub = ra_id)
            html.Div(id=f"tabela-dependencias-{ra_id}")
        ], style={
            "marginBottom": "20px",
            "maxHeight": "500px",  # Definindo a altura máxima da coluna
            "overflowY": "auto",  # Adiciona a rolagem vertical quando necessário
            "paddingRight": "10px",  # Adicionando algum espaço à direita para evitar sobreposição
        })
        
        tabelas.append(coluna)

        # Agora vamos construir as tabelas de dependências para cada razão, usando a coluna ra_sub
        dependencias = razoens[(razoens["ra_level"] == str(int(level_razao) + 1)) & 
                               (razoens["ra_sub"] == ra_id)]  # Assegure-se de comparar como string

        if not dependencias.empty:
            # Filtrando apenas as colunas 'ra_id' e 'ra_razao'
            dependencias_filtradas = dependencias[["ra_id", "ra_razao"]]
            
            # Estilizando a tabela para reduzir o tamanho da fonte e melhorar a legibilidade
            tabela_dependencias = dbc.Table.from_dataframe(
                dependencias_filtradas, 
                striped=True, 
                bordered=True, 
                hover=True, 
                style={
                    "fontSize": "14px",  # Reduzindo o tamanho da fonte para mais legibilidade
                    "marginTop": "10px",  # Espaço entre as tabelas
                    "width": "100%",  # Garantindo que a tabela ocupe toda a largura disponível
                    "textAlign": "center",  # Centralizando o texto nas células
                    "height": "1px",  # Tamanho automático da tabela
                    "lineHeight": "0.3",  # Menor espaçamento entre as linhas para achatar
                    "padding": "1px",  # Menor espaçamento interno das células
                    "borderCollapse": "collapse",  # Fazendo com que as bordas se unam
                }
            )

            # Envolvendo a tabela em um container com overflow
            tabela_com_scroll = html.Div(
                tabela_dependencias,
                style={
                    "maxHeight": "300px",  # Ajuste de altura máxima
                    "overflowY": "auto",  # Adiciona o scroll vertical
                    "marginTop": "10px"
                }
            )
            
            # Adiciona a tabela de dependências abaixo da razão
            tabelas.append(html.Div([
                tabela_com_scroll
            ], style={"marginTop": "10px"}))

    return tabelas

@app.callback(
    Output("dropdown-razao-dependencias", "options"),
    [Input("dropdown-razao-level", "value"),
     Input("dropdown-setor-razao", "value")],
    prevent_initial_call=True
)
def atualizar_dependencias_por_nivel(level_razao, setor_id):
    # Verifica se o nível foi selecionado

    if not level_razao:
        return []
    if not setor_id:
        return []

    # Calcula o nível de dependência (um nível abaixo)
    nivel_dependencia = int(level_razao) - 1
    

    # Consulta as razões do banco para o nível anterior
    razoens = banco.ler_tabela("razao")
    if razoens.empty:
        return []

    dependencias = razoens[razoens["ra_level"] == str(nivel_dependencia)]
    dependencias = dependencias[dependencias["setor_id"] == setor_id]
    # Verifica se alguma dependência foi encontrada
    if dependencias.empty:
        
        return []

    # Cria as opções do dropdown
    dependencias_options = [{"label": row["ra_razao"], "value": row["ra_id"]} for _, row in dependencias.iterrows()]


    return dependencias_options
    
@app.callback(
    [
        Output("dropdown-setor-razao", "options"),
        Output("dropdown-razao-id", "options"),
        Output("store-mensagem-razao", "data"),
        Output("tabelas-niveis", "children"),  # Chamando o segundo callback aqui
        Output("tabelas-niveis_2", "children"),  # Chamando o segundo callback aqui
    ],
    [   
        
        Input("dropdown-setor-razao", "value"),
        Input("dropdown-razao-level", "value"),
        Input("btn-add-razao", "n_clicks"),
        Input("btn-delete-razao", "n_clicks"),
        Input("btn-edit-razao", "n_clicks"),
        Input("modal-razao", "is_open"),
        State("dropdown-razao-id", "value"),
    ],
    [
        State("input-razao-nome", "value"),
        State("dropdown-setor-razao", "value"),
        State("input-razao-edit-nome", "value"),
        State("dropdown-razao-level", "value"),
        State("dropdown-razao-dependencias", "value"),
        State("dropdown-tipo_oee_edit", "value"),
        State("dropdown-tipo_oee", "value")
    ],
    prevent_initial_call=True
)
def manage_razao(set_id,raz_level, n_add, n_delete, n_edit, is_open, razao_id, razao_nome, setor_id, novo_nome_razao, level_razao, ra_sub, edit_tipo, tipo):
    ctx = callback_context
    mensagem = ""

    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if level_razao == "1":
        ra_sub = "base"

    # Verifica se o nível selecionado é 1, e define ra_sub para "base" caso seja
    if ra_sub != "base":
        df_razao = banco.ler_tabela("razao")
        
        # Verifica se o DataFrame não está vazio antes de buscar a coluna 'ra_id'
        if not df_razao.empty:
            tipo_sub = df_razao.loc[df_razao["ra_id"] == ra_sub, "ra_tipo"]
            
            # Verifica se a consulta retornou algum valor
            if not tipo_sub.empty:
                tipo = tipo_sub.values[0]
            else:
                tipo = None  # Ou qualquer valor padrão ou ação que você queira
        else:
            tipo = None  # Ou qualquer valor padrão ou ação que você queira

    # Adicionar Razão
    if button_id == "btn-add-razao":
        
        if not level_razao:
            mensagem = "O level da razão não pode estar vazio."
        elif not ra_sub:
            mensagem = "A depencia da razão não pode estar vazio."
        elif not tipo:
            mensagem = "O Tipo da razão não pode estar vazio."
        elif not razao_nome:
            mensagem = "O nome da razão não pode estar vazio."
        elif not setor_id:
            mensagem = "O Setor da razão não pode estar vazio."
        elif int(level_razao) > 6:
            mensagem = "O nível de razão não pode ser maior que 6."
        else:
            banco.inserir_dados("razao", ra_razao=razao_nome, setor_id=setor_id, ra_level=level_razao, ra_sub=ra_sub, ra_tipo=tipo)
            mensagem = f"Razão '{razao_nome}' adicionada com sucesso no nível {level_razao}!"

    # Excluir Razão
    elif button_id == "btn-delete-razao" and razao_id:
        df_razao = banco.ler_tabela("razao")
        if str(razao_id) not in df_razao["ra_sub"].values:
            banco.deletar_dado("razao", razao_id)
            mensagem = f"Razão {razao_id} excluída com sucesso!"
        else:
            mensagem = f"Não é possível excluir a razão com ID {razao_id}, pois ela tem dependências em outras razões."

    # Editar Razão
    elif button_id == "btn-edit-razao":
        if not razao_id:
            mensagem = "A razão não pode estar vazio."
        elif not novo_nome_razao:
            mensagem = "O nome novo da razão não pode estar vazio."
        else:
            banco.editar_dado("razao", razao_id, ra_razao=novo_nome_razao, ra_tipo=edit_tipo)
            mensagem = f"Razão '{novo_nome_razao}' editada com sucesso!"

    setores = [{"label": row["setor_nome"], "value": row["setor_id"]} for _, row in banco.ler_tabela("setor").iterrows()]
    razoens = [{"label": row["ra_id"], "value": row["ra_id"]} for _, row in banco.ler_tabela("razao").iterrows()]

    # Adiciona chamada do segundo callback para exibir tabelas
    return setores, razoens, mensagem, exibir_tabelas_niveis(setor_id,  (int(level_razao) if level_razao is not None else 0) - 1, setor_id), exibir_tabelas_niveis(setor_id, (int(level_razao) if level_razao is not None else 0), setor_id)

@app.callback(
    Output("div-razao", "children"),
    Output("dropdown-tipo_oee_edit", "value"),
    Output("input-razao-edit-nome", "value"),
    Input("dropdown-razao-id", "value")
)
def exibir_razao(razao_id):
    if not razao_id:
        return "", None, None

    # Filtra a razão correspondente ao ID selecionado
    df_producao = banco.ler_tabela("razao")
    razao_filtrada = df_producao[df_producao["ra_id"] == razao_id]
    

    if razao_filtrada.empty:
        return f"Nenhuma razão encontrada para este ID {razao_id}.", None,  None
    else:
        return f"Razão: {razao_filtrada.iloc[0]['ra_razao']}", razao_filtrada.iloc[0]['ra_tipo'], razao_filtrada.iloc[0]['ra_razao']

# Callback para exibir mensagem de sucesso
@app.callback(
    Output("alert-mensagem-razao", "children"),
    Output("alert-mensagem-razao", "is_open"),
    Input("store-mensagem-razao", "data"),
    prevent_initial_call=True
)
def exibir_mensagem_razao(mensagem):
    if mensagem:
        return mensagem, True
    return dash.no_update
