import dash
from dash import html, dcc, Input, Output, State, callback_context, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
from app import app
from banco_dados.banco import Banco  # Certifique-se de importar corretamente sua classe Banco
from datetime import datetime, date
import json
 
banco = Banco()  # Instância do banco
 
table_style = {"maxHeight": "400px", "overflowY": "auto"}
 
modal_style = {
    "maxWidth": "90%",  # Ajuste o tamanho conforme necessário
    "width": "90%"
}
layout = html.Div([
    dcc.Store(id="store-mensagem-produto", data=""),
    dcc.Store(id="store-produto-valor-update-trigger", data=0),
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Gerenciar Produtos")),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Tabs([
                        dbc.Tab([
                            html.Label("Nome:", className="mt-3"),
                            dbc.Input(id="input-produto-nome", type="text", className="mb-2"),
                            html.Label("Pedido Médio:"),
                            dbc.Input(id="input-produto-pedido-mensal", type="number", className="mb-2"),
                            html.Label("Tempo de Pedido:"),
                            dcc.Dropdown(id="dropdown-produto-tipo-trabalho", options=[
                                 {"label": "Mensal", "value": "Mensal"},
                                 {"label": "Quinzenal", "value": "Quinzenal"},
                                 {"label": "Semanal", "value": "Semanal"},
                            ], className="mb-2"),
                            html.Label("Fluxo de Produção:"),
                            dcc.Dropdown(id="dropdown-produto-fluxo", options=[
                                {"label": "Puxado", "value": "Puxado"},
                                {"label": "Empurrado", "value": "Empurrado"}
                            ], className="mb-2"),
                            html.Label("Dia de Entrega:"),
                            dcc.Dropdown(id="dropdown-produto-dia-entrega", options=[
                                {"label": "Domingo", "value": 1},
                                {"label": "Segunda-feira", "value": 2},
                                {"label": "Terça-feira", "value": 3},
                                {"label": "Quarta-feira", "value": 4},
                                {"label": "Quinta-feira", "value": 5},
                                {"label": "Sexta-feira", "value": 6},
                                {"label": "Sábado", "value": 7}
                            ], className="mb-2"),
                            html.Label("Cliente:"),
                            dcc.Dropdown(id="dropdown-produto-cliente", className="mb-2"),
                            html.Label("Configuração de Partes:"),
                            dcc.Dropdown(id="dropdown-produto-partes", className="mb-2"),
                            html.Div(id='display-partes-json-add', className="mt-2"),
                            html.Label("Observações:"),
                            dbc.Textarea(id="input-produto-observacao", className="mb-2"),
                            dbc.Button("Adicionar", id="btn-add-produto", color="success", className="w-100 mb-3"),
                        ], label="Adicionar"),
                        dbc.Tab([
                            html.Label("Selecionar Produto:", className="mt-3"),
                            dcc.Dropdown(id="dropdown-produto-delete", className="mb-2"),
                            dbc.Button("Excluir", id="btn-delete-produto", color="danger", className="w-100"),
                        ], label="Excluir"),
                        dbc.Tab([
                            html.Label("Selecionar Produto:", className="mt-3"),
                            dcc.Dropdown(id="dropdown-produto-edit", className="mb-2"),
                            html.Label("Novo Nome:"),
                            dbc.Input(id="input-produto-edit-nome", type="text", className="mb-2"),
                            html.Label("Novo Pedido Médio:"),
                            dbc.Input(id="input-produto-edit-pedido-mensal", type="number", className="mb-2"),
                            html.Label("Novo Tempo de Pedido:"),
                            dcc.Dropdown(id="dropdown-produto-edit-tipo-trabalho", options=[
                                 {"label": "Mensal", "value": "Mensal"},
                                 {"label": "Quinzenal", "value": "Quinzenal"},
                                 {"label": "Semanal", "value": "Semanal"},
                            ], className="mb-2"),
                            html.Label("Novo Fluxo de Produção:"),
                            dcc.Dropdown(id="dropdown-produto-edit-fluxo", options=[
                                {"label": "Puxado", "value": "Puxado"},
                                {"label": "Empurrado", "value": "Empurrado"}
                            ], className="mb-2"),
                            html.Label("Novo Dia de Entrega:"),
                            dcc.Dropdown(id="dropdown-produto-edit-dia-entrega", options=[
                                {"label": "Domingo", "value": 1},
                                {"label": "Segunda-feira", "value": 2},
                                {"label": "Terça-feira", "value": 3},
                                {"label": "Quarta-feira", "value": 4},
                                {"label": "Quinta-feira", "value": 5},
                                {"label": "Sexta-feira", "value": 6},
                                {"label": "Sábado", "value": 7}
                            ], className="mb-2"),
                            html.Label("Novo Cliente:"),
                            dcc.Dropdown(id="dropdown-produto-edit-cliente", className="mb-2"),
                            html.Label("Nova Configuração de Partes:"),
                            dcc.Dropdown(id="dropdown-produto-edit-partes", className="mb-2"),
                            html.Div(id='display-partes-json-edit', className="mt-2"),
                            html.Label("Nova Observação:"),
                            dbc.Textarea(id="input-produto-edit-observacao", className="mb-2"),
                            dbc.Button("Salvar", id="btn-edit-produto", color="warning", className="w-100"),
                        ], label="Editar"),
                        dbc.Tab([
                            html.Label("Selecionar Produto:", className="mt-3"),
                            dcc.Dropdown(id="dropdown-valor-produto", className="mb-2"),
                            html.Label("Valor (R$):"),
                            dbc.Input(id="input-valor-produto", type="number", step=0.01, className="mb-2"),
                            html.Label("Orçamento:"),
                            dbc.Input(id="input-orcamento-produto", type="number", className="mb-2"),
                            html.Label("Data:"),
                            dcc.DatePickerSingle(
                                id="date-valor-produto",
                                display_format='DD/MM/YYYY',
                                date=date.today(),
                                className="mb-2"
                            ),
                            dbc.Button("Adicionar Valor", id="btn-add-valor", color="primary", className="w-100 mb-3"),
                            html.Hr(),
                            html.Label("Valores Cadastrados:"),
                            dash_table.DataTable(
                                id='tabela-valores-produto',
                                columns=[
                                    {"name": "ID", "id": "id"},
                                    {"name": "Produto", "id": "produto_nome"},
                                    {"name": "Valor (R$)", "id": "valor", "type": "numeric", "format": {"specifier": ",.2f"}},
                                    {"name": "Orçamento", "id": "orcamento"},
                                    {"name": "Data", "id": "data"},
                                    {"name": "🗑️", "id": "excluir"}
                                ],
                                page_size=10,
                                style_table={"maxHeight": "300px", "overflowY": "auto"},
                                style_cell={'textAlign': 'center'},
                                style_data_conditional=[
                                    {
                                        'if': {'column_id': 'excluir'},
                                        'backgroundColor': '#ff6b6b',
                                        'color': 'white',
                                        'cursor': 'pointer'
                                    }
                                ]
                            )
                        ], label="Valores"),
                    ])
                ], width=4),
 
                dbc.Col([
                    html.Label("Produtos Cadastrados:"),
                    dash_table.DataTable(id='tabela-produtos',
                        columns=[
                            {"name": "ID", "id": "produto_id"},
                            {"name": "Nome", "id": "nome"},
                            {"name": "Último Valor (R$)", "id": "ultimo_valor", "type": "numeric", "format": {"specifier": ",.2f"}},
                            {"name": "Pedido Médio", "id": "pedido_mensal"},
                            {"name": "Tempo de Pedido", "id": "tipo_trabalho"},
                            {"name": "Fluxo", "id": "fluxo_producao"},
                            {"name": "Dia de Entrega", "id": "dia_entrega"},
                            {"name": "Cliente", "id": "cliente_nome"},
                            {"name": "Config. Partes", "id": "partes_nome"},
                            {"name": "Observação", "id": "observacao"}
                        ],
                        page_size=20,
                        style_table={"width": "100%", "overflowX": "auto"},
                    )
                ], width=8),
            ]),
        ]),
        dbc.ModalFooter([
            html.Div(id="alert-container-produto", className="me-auto"),
            dbc.Button("Fechar", id="btn_fechar_produto", color="secondary")
        ])
    ], id="modal-produto-item", is_open=False, className="custom-modal-produto"),
])
 
@app.callback(
    Output("modal-produto-item", "is_open"),
    [Input("btn_abrir_produto", "n_clicks")],
    [State("modal-produto-item", "is_open")]
)
def toggle_modal_produto(n1, is_open):
 
    if n1:
     
        return not is_open
   
    return is_open
 
@app.callback(
    Output("alert-container-produto", "children"),
    Input("store-mensagem-produto", "data"),
    prevent_initial_call=True
)
def show_alert(mensagem):
    if mensagem:
        return dbc.Alert(mensagem, color="success", duration=4000, dismissable=True)
    return []
 
@app.callback(
    [Output("dropdown-produto-delete", "options"),
     Output("dropdown-produto-edit", "options"),
     Output("dropdown-produto-cliente", "options"),
     Output("dropdown-produto-edit-cliente", "options"),
     Output("dropdown-produto-partes", "options"),
     Output("dropdown-produto-edit-partes", "options"),
     Output("tabela-produtos", "data"),
     Output("store-mensagem-produto", "data"),
     Output("input-produto-nome", "value"),
     Output("input-produto-pedido-mensal", "value"),
     Output("dropdown-produto-tipo-trabalho", "value"),
     Output("dropdown-produto-fluxo", "value"),
     Output("dropdown-produto-dia-entrega", "value"),
     Output("dropdown-produto-cliente", "value"),
     Output("dropdown-produto-partes", "value"),
     Output("input-produto-observacao", "value"),
     Output("dropdown-produto-delete", "value"),
     Output("dropdown-produto-edit", "value"),
     Output("input-produto-edit-nome", "value"),
     Output("input-produto-edit-pedido-mensal", "value"),
     Output("dropdown-produto-edit-tipo-trabalho", "value"),
     Output("dropdown-produto-edit-fluxo", "value"),
     Output("dropdown-produto-edit-dia-entrega", "value"),
     Output("dropdown-produto-edit-cliente", "value"),
     Output("dropdown-produto-edit-partes", "value"),
     Output("input-produto-edit-observacao", "value")],
    [Input("btn-add-produto", "n_clicks"),
     Input("btn-delete-produto", "n_clicks"),
     Input("btn-edit-produto", "n_clicks"),
     Input("modal-produto-item", "is_open"),
     Input("dropdown-produto-edit", "value"),
     Input("store-produto-valor-update-trigger", "data")],
    [State("input-produto-nome", "value"),
     State("input-produto-pedido-mensal", "value"),
     State("dropdown-produto-tipo-trabalho", "value"),
     State("dropdown-produto-fluxo", "value"),
     State("dropdown-produto-dia-entrega", "value"),
     State("dropdown-produto-cliente", "value"),
     State("dropdown-produto-partes", "value"),
     State("input-produto-observacao", "value"),
     State("dropdown-produto-delete", "value"),
     State("input-produto-edit-nome", "value"),
     State("input-produto-edit-pedido-mensal", "value"),
     State("dropdown-produto-edit-tipo-trabalho", "value"),
     State("dropdown-produto-edit-fluxo", "value"),
     State("dropdown-produto-edit-dia-entrega", "value"),
     State("dropdown-produto-edit-cliente", "value"),
     State("dropdown-produto-edit-partes", "value"),
     State("input-produto-edit-observacao", "value")],
    prevent_initial_call=True
)
def manage_produto(n_add, n_delete, n_edit, is_open, prod_id_edit, valor_update_trigger,
                   nome, pedido_mensal, tipo_trabalho, fluxo, dia_entrega, cliente_id, partes_id, observacao,
                   prod_id_del,
                   novo_nome, novo_pedido, novo_tipo, novo_fluxo, novo_dia_entrega, novo_cliente_id, novo_partes_id, nova_obs):
    ctx = callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    mensagem = ""
 
    # Initialize all return values to no_update
    (
        dropdown_opts_del, dropdown_opts_edit, dropdown_opts_cliente, dropdown_opts_edit_cliente,
        dropdown_opts_partes, dropdown_opts_edit_partes,
        table_data, msg_data,
        add_nome, add_pedido, add_tipo, add_fluxo, add_dia, add_cliente, add_partes, add_obs,
        del_dropdown,
        edit_dropdown, edit_nome, edit_pedido, edit_tipo, edit_fluxo, edit_dia, edit_cliente, edit_partes, edit_obs
    ) = [dash.no_update] * 26
 
    # When opening modal or performing an action, update the table and dropdowns
    if triggered_id in ["modal-produto-item", "btn-add-produto", "btn-delete-produto", "btn-edit-produto", "store-produto-valor-update-trigger"]:
        if triggered_id == "btn-add-produto" and nome:
            banco.inserir_dados("produtos", nome=nome, pedido_mensal=pedido_mensal, tipo_trabalho=tipo_trabalho, fluxo_producao=fluxo, observacao=observacao, dia_entrega=dia_entrega, cliente_id=cliente_id, pap_id=partes_id)
            mensagem = f"Produto '{nome}' adicionado com sucesso!"
            add_nome, add_pedido, add_tipo, add_fluxo, add_dia, add_cliente, add_partes, add_obs = "", None, None, None, None, None, None, ""
       
        elif triggered_id == "btn-delete-produto" and prod_id_del:
            banco.deletar_dado("produtos", prod_id_del)
            mensagem = "Produto excluído com sucesso!"
            del_dropdown = None
       
        elif triggered_id == "btn-edit-produto" and prod_id_edit:
            banco.editar_dado("produtos", prod_id_edit, nome=novo_nome, pedido_mensal=novo_pedido, tipo_trabalho=novo_tipo, fluxo_producao=novo_fluxo, observacao=nova_obs, dia_entrega=novo_dia_entrega, cliente_id=novo_cliente_id, pap_id=novo_partes_id)
            mensagem = f"Produto '{novo_nome}' editado com sucesso!"
            edit_dropdown, edit_nome, edit_pedido, edit_tipo, edit_fluxo, edit_dia, edit_cliente, edit_partes, edit_obs = None, "", None, None, None, None, None, None, ""
       
        # Buscar clientes para os dropdowns
        clientes = banco.ler_tabela("clientes")
        clientes_options = [{"label": row["nome"], "value": row["cliente_id"]} for _, row in clientes.iterrows()]

        # Buscar partes para os dropdowns
        partes = banco.ler_tabela("partes_produto")
        partes_options = [{"label": row["pap_nome"], "value": row["pap_id"]} for _, row in partes.iterrows()]
       
        # Buscar produtos com join para mostrar nome do cliente e último valor
        try:
            from sqlalchemy import create_engine
            engine = create_engine("sqlite:///banco_dados/bd_pcp.sqlite")
            with engine.connect() as conn:
                query = """
                SELECT
                    p.*,
                    c.nome as cliente_nome,
                    pp.pap_nome as partes_nome,
                    vp.valor as ultimo_valor
                FROM
                    produtos p
                LEFT JOIN
                    clientes c ON p.cliente_id = c.cliente_id
                LEFT JOIN
                    partes_produto pp ON p.pap_id = pp.pap_id
                LEFT JOIN
                    (
                        SELECT 
                            produto_id, 
                            valor,
                            ROW_NUMBER() OVER(PARTITION BY produto_id ORDER BY data DESC, id DESC) as rn
                        FROM 
                            valor_produto
                    ) vp ON p.produto_id = vp.produto_id AND vp.rn = 1
                """
                produtos = pd.read_sql(query, conn)
        except Exception as e:
            print(f"Erro ao buscar produtos com último valor: {e}")
            produtos = banco.ler_tabela("produtos")
            produtos['cliente_nome'] = None
            produtos['ultimo_valor'] = None
            produtos['partes_nome'] = None
        
        dia_semana_map = {1: "Domingo", 2: "Segunda", 3: "Terça", 4: "Quarta", 5: "Quinta", 6: "Sexta", 7: "Sábado"}
        if not produtos.empty and 'dia_entrega' in produtos.columns:
            produtos['dia_entrega'] = produtos['dia_entrega'].map(dia_semana_map).fillna(produtos['dia_entrega'])
 
        dropdown_options = [{"label": row["nome"], "value": row["produto_id"]} for _, row in produtos.iterrows()]
       
        dropdown_opts_del = dropdown_options
        dropdown_opts_edit = dropdown_options
        dropdown_opts_cliente = clientes_options
        dropdown_opts_edit_cliente = clientes_options
        dropdown_opts_partes = partes_options
        dropdown_opts_edit_partes = partes_options
        table_data = produtos.to_dict("records")
        msg_data = mensagem
       
    # When selecting a product to edit, fill the form
    elif triggered_id == "dropdown-produto-edit" and prod_id_edit:
        produto = banco.ler_tabela("produtos").set_index("produto_id").loc[prod_id_edit]
        edit_nome = produto["nome"]
        edit_pedido = produto["pedido_mensal"]
        edit_tipo = produto["tipo_trabalho"]
        edit_fluxo = produto["fluxo_producao"]
        edit_obs = produto["observacao"]
        edit_dia = produto["dia_entrega"]
        edit_cliente = produto["cliente_id"]
        edit_partes = produto.get("pap_id")
 
    return (
        dropdown_opts_del, dropdown_opts_edit, dropdown_opts_cliente, dropdown_opts_edit_cliente,
        dropdown_opts_partes, dropdown_opts_edit_partes,
        table_data, msg_data,
        add_nome, add_pedido, add_tipo, add_fluxo, add_dia, add_cliente, add_partes, add_obs,
        del_dropdown,
        edit_dropdown, edit_nome, edit_pedido, edit_tipo, edit_fluxo, edit_dia, edit_cliente, edit_partes, edit_obs
    )

@app.callback(
    [Output('display-partes-json-add', 'children'),
     Output('display-partes-json-edit', 'children')],
    [Input('dropdown-produto-partes', 'value'),
     Input('dropdown-produto-edit-partes', 'value')],
    prevent_initial_call=True
)
def display_selected_partes_json(add_id, edit_id):
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    def format_json_display(pap_id):
        if not pap_id:
            return None
        
        df = banco.ler_tabela("partes_produto", pap_id=int(pap_id))
        if df.empty:
            return None
        
        partes_json_str = df.iloc[0]['pap_parte']
        if not isinstance(partes_json_str, str): # Ensure it's a string before loading JSON
            return dbc.Card(dbc.CardBody("Configuração de partes vazia."), className="mt-2")
            
        try:
            partes_dict = json.loads(partes_json_str)
            if not isinstance(partes_dict, dict):
                 return dbc.Alert("Formato de configuração inválido.", color="warning")

            display_items = [html.Li(f"{key}: {value} un.") for key, value in partes_dict.items()]
            return dbc.Card(dbc.CardBody([html.H6("Detalhes da Configuração:", className="card-title"), html.Ul(display_items)]), className="mt-2 bg-light")
            
        except (json.JSONDecodeError, TypeError):
            return dbc.Alert("Erro ao ler a configuração de partes.", color="danger")

    if triggered_id == 'dropdown-produto-partes':
        return format_json_display(add_id), dash.no_update
    
    if triggered_id == 'dropdown-produto-edit-partes':
        return dash.no_update, format_json_display(edit_id)
        
    return dash.no_update, dash.no_update

# Callback para gerenciar valores dos produtos
@app.callback(
    [Output("dropdown-valor-produto", "options"),
     Output("tabela-valores-produto", "data"),
     Output("input-valor-produto", "value"),
     Output("input-orcamento-produto", "value"),
     Output("date-valor-produto", "date"),
     Output("dropdown-valor-produto", "value"),
     Output("store-produto-valor-update-trigger", "data")],
    [Input("btn-add-valor", "n_clicks"),
     Input("modal-produto-item", "is_open"),
     Input("tabela-valores-produto", "active_cell"),
     Input("dropdown-valor-produto", "value")],
    [State("input-valor-produto", "value"),
     State("input-orcamento-produto", "value"),
     State("date-valor-produto", "date"),
     State("tabela-valores-produto", "data"),
     State("store-produto-valor-update-trigger", "data")],
    prevent_initial_call=True
)
def manage_valores_produto(n_add, is_open, active_cell, produto_id, valor, orcamento, data_valor, table_data, trigger_count):
    ctx = callback_context
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    trigger_output = dash.no_update

    # Carregar produtos para o dropdown
    produtos = banco.ler_tabela("produtos")
    produto_options = [{"label": row["nome"], "value": row["produto_id"]} for _, row in produtos.iterrows()]
    
    # Carregar valores existentes (filtrar por produto se selecionado)
    try:
        from sqlalchemy import create_engine
        engine = create_engine("sqlite:///banco_dados/bd_pcp.sqlite")
        with engine.connect() as conn:
            if produto_id:
                # Filtrar por produto específico
                query = """
                SELECT vp.*, p.nome as produto_nome
                FROM valor_produto vp
                JOIN produtos p ON vp.produto_id = p.produto_id
                WHERE vp.produto_id = :produto_id
                ORDER BY vp.data DESC
                """
                valores = pd.read_sql(query, conn, params={'produto_id': int(produto_id)})
            else:
                # Mostrar todos os valores
                query = """
                SELECT vp.*, p.nome as produto_nome
                FROM valor_produto vp
                JOIN produtos p ON vp.produto_id = p.produto_id
                ORDER BY vp.data DESC
                """
                valores = pd.read_sql(query, conn)
            
        # Adicionar coluna de exclusão
        if not valores.empty:
            valores['excluir'] = '🗑️'
        
        valores_data = valores.to_dict("records") if not valores.empty else []
    except Exception as e:
        print(f"Erro ao buscar valores: {e}")
        valores_data = []
    
    # Limpar campos após adicionar
    clear_valor = dash.no_update
    clear_orcamento = dash.no_update
    clear_data = date.today() if triggered_id == "modal-produto-item" else dash.no_update
    clear_produto = dash.no_update
    
    if triggered_id == "btn-add-valor" and produto_id and valor and data_valor:
        try:
            # Converter data para o formato correto
            if isinstance(data_valor, str):
                data_formatada = datetime.strptime(data_valor, '%Y-%m-%d').date()
            else:
                data_formatada = data_valor
                
            banco.inserir_dados("valor_produto", 
                               produto_id=produto_id, 
                               valor=valor, 
                               orcamento=orcamento if orcamento else None, 
                               data=data_formatada)
            
            trigger_output = trigger_count + 1

            # Recarregar valores após inserção (mantendo o filtro)
            engine = create_engine("sqlite:///banco_dados/bd_pcp.sqlite")
            with engine.connect() as conn:
                if produto_id:
                    query = """
                    SELECT vp.*, p.nome as produto_nome
                    FROM valor_produto vp
                    JOIN produtos p ON vp.produto_id = p.produto_id
                    WHERE vp.produto_id = :produto_id
                    ORDER BY vp.data DESC
                    """
                    valores = pd.read_sql(query, conn, params={'produto_id': int(produto_id)})
                else:
                    query = """
                    SELECT vp.*, p.nome as produto_nome
                    FROM valor_produto vp
                    JOIN produtos p ON vp.produto_id = p.produto_id
                    ORDER BY vp.data DESC
                    """
                    valores = pd.read_sql(query, conn)
                
            if not valores.empty:
                valores['excluir'] = '🗑️'
            
            valores_data = valores.to_dict("records") if not valores.empty else []
            
            # Limpar campos (manter produto selecionado para facilitar múltiplas inserções)
            clear_valor = None
            clear_orcamento = None
            clear_data = date.today()
            clear_produto = produto_id  # Manter produto selecionado
            
        except Exception as e:
            print(f"Erro ao adicionar valor: {e}")
    
    # Verificar se clicou em uma ação de exclusão
    elif triggered_id == "tabela-valores-produto" and active_cell and table_data:
        if active_cell.get('column_id') == 'excluir':
            row_index = active_cell.get('row')
            if row_index is not None and row_index < len(table_data):
                valor_id = table_data[row_index]['id']
                try:
                    banco.deletar_dado("valor_produto", valor_id)
                    trigger_output = trigger_count + 1
                    
                    # Recarregar valores após exclusão (mantendo o filtro)
                    engine = create_engine("sqlite:///banco_dados/bd_pcp.sqlite")
                    with engine.connect() as conn:
                        if produto_id:
                            query = """
                            SELECT vp.*, p.nome as produto_nome
                            FROM valor_produto vp
                            JOIN produtos p ON vp.produto_id = p.produto_id
                            WHERE vp.produto_id = :produto_id
                            ORDER BY vp.data DESC
                            """
                            valores = pd.read_sql(query, conn, params={'produto_id': int(produto_id)})
                        else:
                            query = """
                            SELECT vp.*, p.nome as produto_nome
                            FROM valor_produto vp
                            JOIN produtos p ON vp.produto_id = p.produto_id
                            ORDER BY vp.data DESC
                            """
                            valores = pd.read_sql(query, conn)
                        
                    if not valores.empty:
                        valores['excluir'] = '🗑️'
                    
                    valores_data = valores.to_dict("records") if not valores.empty else []
                    
                except Exception as e:
                    print(f"Erro ao excluir valor: {e}")
    
    if triggered_id == 'dropdown-valor-produto':
        return produto_options, valores_data, None, None, date.today(), produto_id, trigger_output

    return produto_options, valores_data, clear_valor, clear_orcamento, clear_data, clear_produto, trigger_output