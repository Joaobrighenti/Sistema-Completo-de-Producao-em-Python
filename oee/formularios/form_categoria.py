import dash
from dash import html, dcc, Input, Output, State, callback_context, dash_table
import dash_bootstrap_components as dbc
from app import app
from banco_dados.banco import Banco  # Certifique-se de importar corretamente sua classe Banco
import pandas as pd

banco = Banco()  # Instância do banco

layout = html.Div([

    dbc.Modal(
        [
            dbc.ModalHeader([
                dbc.ModalTitle("Gerenciar Categorias de Produto"),
                dbc.Button("×", id="close-modal-categoria", className="btn-close", n_clicks=0)
            ]),
            dbc.ModalBody([

                # Estrutura de colunas para apontamentos e tabela
                dbc.Row([
                    # Coluna 1: Apontamentos (Adicionar e Editar Categoria)
                    dbc.Col([
                        html.Label("Adicionar Nova Categoria de Produto:"),
                        dbc.Input(id="input-categoria-nome", type="text", placeholder="Nome da categoria", className="mb-2"),
                        dbc.Input(id="input-categoria-meta", type="number", placeholder="Meta da categoria por hora", className="mb-2"),
                        dbc.Label("Máquina Associada:"),
                        dcc.Dropdown(id="dropdown-maquinas", placeholder="Selecione uma máquina", className="mb-2"),
                        dbc.Button("Adicionar Categoria", id="btn-add-categoria", color="success", className="w-100 mb-3"),

                        html.Hr(),
                        html.Label("Editar Categoria Existente:"),
                        dcc.Dropdown(id="dropdown-categoria-editar", placeholder="Selecione uma categoria para editar", className="mb-2"),
                        dbc.Input(id="input-categoria-editar-nome", type="text", placeholder="Novo nome da categoria", className="mb-2"),
                        dbc.Input(id="input-categoria-editar-meta", type="number", placeholder="Nova meta", className="mb-2"),
                        dcc.Dropdown(id="dropdown-maquinas-editar", placeholder="Selecione uma máquina", className="mb-2"),
                        dbc.Button("Atualizar Categoria", id="btn-editar-categoria", color="warning", className="w-100 mb-3"),

                        html.Hr(),
                        html.Label("Excluir Categoria Existente:"),
                        dcc.Dropdown(id="dropdown-categoria-delete", placeholder="Selecione uma categoria", className="mb-2"),
                        dbc.Button("Excluir Categoria", id="btn-delete-categoria", color="danger", className="w-100"),

                        dbc.Alert(id="alert-mensagem-categoria", color="success", is_open=False, dismissable=True, className="mt-3"),
                    ], width=6),

                    # Coluna 2: Tabela de Categorias Cadastradas
                    dbc.Col([
                        html.Hr(),
                        html.H4("Categorias Cadastradas"),  # Título da tabela
                        dash_table.DataTable(
                            id="table-categorias",
                            columns=[
                                {"name": "ID", "id": "cp_id"},
                                {"name": "Nome da Categoria", "id": "cp_nome"},
                                {"name": "Meta", "id": "cp_meta"},
                                {"name": "Máquina", "id": "maquina_nome"},
                            ],
                            data=[],  # Inicialmente, a tabela está vazia
                            style_table={'height': '650px', 'overflowY': 'auto'},
                            style_cell={'textAlign': 'center'},  # Estiliza as células
                            style_header={'backgroundColor': 'lightgray', 'fontWeight': 'bold'}
                        ),
                    ], width=6)
                ]),

            ]),
        ],
        id="modal-categoria-oee",
        is_open=False,
        className="modal-medio" 
    ),
])

@app.callback(
    Output("modal-categoria-oee", "is_open"),
    [Input("btn_gerenciar_categoria", "n_clicks"), Input("close-modal-categoria", "n_clicks")],
    [State("modal-categoria-oee", "is_open")],
    prevent_initial_call=True
)
def toggle_modal_categoria(n_clicks_open, n_clicks_close, is_open):
    if n_clicks_open or n_clicks_close:
        return not is_open
    return is_open

@app.callback(
    [Output("alert-mensagem-categoria", "children"),
     Output("alert-mensagem-categoria", "is_open"),
     Output("table-categorias", "data"),
     Output("dropdown-maquinas", "options"),
     Output("dropdown-categoria-delete", "options"),
     Output("dropdown-categoria-editar", "options"),
     Output("input-categoria-editar-nome", "value"),
     Output("input-categoria-editar-meta", "value"),
     Output("dropdown-maquinas-editar", "value"),
     Output("dropdown-maquinas-editar", "options")],

    [Input("btn-add-categoria", "n_clicks"),
     Input("btn-editar-categoria", "n_clicks"),
     Input("btn-delete-categoria", "n_clicks"),
     Input("dropdown-maquinas", "value"),
     Input("dropdown-categoria-editar", "value")],
    [State("input-categoria-nome", "value"),
     State("input-categoria-meta", "value"),
     State("input-categoria-editar-nome", "value"),
     State("input-categoria-editar-meta", "value"),
     State("dropdown-maquinas-editar", "value"),
     State("dropdown-categoria-delete", "value"),
     State("dropdown-categoria-editar", "value")]
)
def manage_categories(add_clicks, edit_clicks, delete_clicks, maquina_id, categoria_editar_id, categoria_nome, categoria_meta, 
                      categoria_nome_editar, categoria_meta_editar, maquina_id_editar, categoria_id, categoria_editar_id_estado):
    ctx = callback_context
    mensagem = ""

    # Puxando as máquinas cadastradas
    maquinas = banco.ler_tabela("maquina")
    maquina_options = [{"label": maquina["maquina_nome"], "value": maquina["maquina_id"]} for maquina in maquinas.to_dict('records')] if not maquinas.empty else []

    # Atualizando as opções de edição de categoria
    categorias = banco.ler_tabela("categoria_produto")
    categoria_edit_options = [{"label": categoria["cp_nome"], "value": categoria["cp_id"]} for categoria in categorias.to_dict('records')] if not categorias.empty else []

    # Caso a ação seja de adicionar uma nova categoria
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "btn-add-categoria.n_clicks":
        if not all([categoria_nome, maquina_id]):
            mensagem = "Preencha todos os campos."
        else:
            # Garantir que cp_meta tenha um valor válido
            if categoria_meta is None or categoria_meta == '':
                categoria_meta = 0  # Valor padrão para meta
            
            try:
                categoria_meta = float(categoria_meta)  # Converter para float
                banco.inserir_dados("categoria_produto", 
                                  cp_nome=categoria_nome, 
                                  cp_meta=categoria_meta, 
                                  c_maq_id=maquina_id)
                mensagem = "Categoria Inserida"
            except ValueError:
                mensagem = "A meta deve ser um número válido."

    # Caso a ação seja de editar uma categoria existente
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "btn-editar-categoria.n_clicks" and categoria_editar_id_estado:
        if not all([categoria_nome_editar, maquina_id_editar]):
            mensagem = "Preencha todos os campos para editar."
        else:
            # Garantir que cp_meta tenha um valor válido
            if categoria_meta_editar is None or categoria_meta_editar == '':
                categoria_meta_editar = 0  # Valor padrão para meta
            
            try:
                categoria_meta_editar = float(categoria_meta_editar)  # Converter para float
                banco.editar_dado("categoria_produto", 
                                categoria_editar_id_estado, 
                                cp_nome=categoria_nome_editar, 
                                cp_meta=categoria_meta_editar, 
                                c_maq_id=maquina_id_editar)
                mensagem = "Categoria Atualizada"
            except ValueError:
                mensagem = "A meta deve ser um número válido."

    # Caso a ação seja de excluir uma categoria
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "btn-delete-categoria.n_clicks" and categoria_id:
        # Verificar se a categoria está em uso na tabela 'producao'
        df_producao = banco.ler_tabela("producao")
        # Verificar qual coluna existe para a categoria
        if 'categoria_id' in df_producao.columns:
            categoria_em_uso = df_producao[df_producao["categoria_id"] == categoria_id]
        elif 'cp_id' in df_producao.columns:
            categoria_em_uso = df_producao[df_producao["cp_id"] == categoria_id]
        else:
            categoria_em_uso = pd.DataFrame()  # Se não encontrar a coluna, assume que não está em uso

        if categoria_em_uso.empty:
            # Se não houver registros na tabela 'producao' com o 'categoria_id', pode excluir
            banco.deletar_dado("categoria_produto", categoria_id)
            mensagem = "Categoria Deletada"
        else:
            # Se houver registros, não pode excluir devido à dependência
            mensagem = "Não é possível excluir a categoria, pois ela está em uso na produção."

    # **Aqui fazemos a consulta novamente para garantir que as categorias sejam atualizadas após qualquer operação**
    categorias = banco.ler_tabela("categoria_produto")

    # Filtrar a tabela de categorias com base na máquina selecionada
    categorias_filtradas = []
    if not categorias.empty and maquina_id:
        # Verificar qual coluna existe
        if 'maquina_id' in categorias.columns:
            categorias_filtradas = categorias[categorias['maquina_id'] == maquina_id].to_dict('records')
        elif 'c_maq_id' in categorias.columns:
            categorias_filtradas = categorias[categorias['c_maq_id'] == maquina_id].to_dict('records')
        else:
            categorias_filtradas = categorias.to_dict('records')
    else:
        categorias_filtradas = categorias.to_dict('records')

    # Atualiza a tabela de categorias
    categoria_data = []
    if categorias_filtradas:
        for categoria in categorias_filtradas:
            # Determinar o ID da máquina baseado nas colunas disponíveis
            maquina_id_categoria = categoria.get('maquina_id') or categoria.get('c_maq_id')
            
            # Encontrar o nome da máquina correspondente
            maquina_nome = 'Desconhecida'
            if maquina_id_categoria and not maquinas.empty:
                for maquina in maquinas.to_dict('records'):
                    if maquina['maquina_id'] == maquina_id_categoria:
                        maquina_nome = maquina['maquina_nome']
                        break
            
            categoria_data.append({
                'cp_id': categoria['cp_id'],
                'cp_nome': categoria['cp_nome'],
                'cp_meta': categoria['cp_meta'],
                'maquina_nome': maquina_nome
            })

    # Atualiza as opções do dropdown de exclusão e edição
    categoria_delete_options = [{"label": categoria["cp_nome"], "value": categoria["cp_id"]} for categoria in categorias.to_dict('records')] if not categorias.empty else []

    categoria_selecionada = None
    
    # Atualiza os campos de edição, caso uma categoria seja selecionada no dropdown
    if categoria_editar_id and not categorias.empty:
        for categoria in categorias.to_dict('records'):
            if categoria["cp_id"] == categoria_editar_id:
                categoria_selecionada = categoria
                break
        
        if categoria_selecionada:
            categoria_nome_editar = categoria_selecionada['cp_nome']
            categoria_meta_editar = categoria_selecionada['cp_meta']
            maquina_id_editar = categoria_selecionada.get('maquina_id') or categoria_selecionada.get('c_maq_id')

    # Preencher o dropdown de máquinas para edição com todas as opções
    maquina_id_editar = (categoria_selecionada.get('maquina_id') or categoria_selecionada.get('c_maq_id')) if categoria_selecionada else None

    # Aqui garantimos que o dropdown de máquinas para edição também tenha a opção correta
    dropdown_maquinas_editar_value = maquina_id_editar  # Define o valor selecionado do dropdown
    
    return mensagem, True, categoria_data, maquina_options, categoria_delete_options, categoria_edit_options, categoria_nome_editar, categoria_meta_editar, dropdown_maquinas_editar_value, maquina_options  # Atualizando a tabela de categorias


