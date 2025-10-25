from logging import exception
import dash
import plotly.express as px
from dash import html, dcc, callback_context, dash_table
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
from datetime import timedelta, date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import os
import json
import pandas as pd
from app import *
from datetime import datetime, timedelta
from pcp.pag_principal import *

from banco_dados.banco import df_pcp, listar_pcp, listar_dados, Banco

col_centered_style={'display': 'flex', 'justify-content': 'center'}

layout = dbc.Modal([
dbc.ModalHeader(dbc.ModalTitle('Baixa de Produção')),
dbc.ModalBody([
    dbc.Row([
        dbc.Col([
                dbc.Label("ID MOV"),
                dbc.Input(id="id_movimentacao", placeholder="Id...", type="number", disabled=True)
], sm=12, md=3),
            dbc.Col([
                dbc.Label("ID PCP"),
                dcc.Dropdown(
                    id="baixa_pcp",
                options=[{'label': pcp, 'value': pcp} for pcp in df_pcp['pcp_id']],  # Substitua 'df_pcp' com a sua lista de códigos PCP
                placeholder="Selecione o id PCP...",
        clearable=False
    )
], sm=12, md=3),
            dbc.Col([
                dbc.Label("Unidades por Pacote"),
                dbc.Input(id="baixa_pallet", placeholder="Apenas números...", type="number")
            ], sm=12, md=6),
        ]),
    html.Hr(),
    dbc.Row([
            dbc.Col([
    dbc.Label([
        html.I(className="fa fa-eye", style={"color": "#0d6efd"}),  # ícone azul Bootstrap
        "  Lote de Qualidade"
    ]),
    dbc.Input(
        id="baixa_turno",
        type="text",
        placeholder="Digite o lote...",
        className="dbc",
        style={"backgroundColor": "#e6f0ff"}  # azul bem claro
    )
], sm=12, md=6),
            dbc.Col([
                dbc.Label("Volumes"),
                dbc.Input(id="baixa_maquina", placeholder="Quantidade da Ordem...", type="number"),
            ], sm=12, md=6),
        ]),
    html.Hr(),
    
    dbc.Row([
            dbc.Col([
                dbc.Label("QUANTIDADE"),
                dbc.Input(id="baixa_quantidade", placeholder="Quantidade da Ordem...", type="number")
            ], sm=12, md=6),
            dbc.Col([
                dbc.Row([
                dbc.Label("DATA")
                ]),
                dbc.Row([
                dcc.DatePickerSingle(id="baixa_data", className='dbc', date=date.today(), initial_visible_month=date.today())
                ]),
                
            ]),
        ]),
    html.Br(),
    dbc.Row([
            dbc.Col([
                dbc.Label("OBSERVAÇÃO"),
                dbc.Textarea(id="baixa_observacao", placeholder="Observação geral...", style={'height': '80%'})
            ], sm=12, md=8),
            dbc.Col([
                html.Br(),
                dbc.Checklist(
                    options=[{"label": "Ajuste", "value": 1}],
                    value=[],
                    id="ajuste_checkbox",
                    inline=True,
                    style={"margin-top": "10px"}
                )
            ], sm=12, md=4),
        ]),   
        html.H5(id='div_erro1')
    ]),
    dbc.ModalFooter([
        dbc.Button('Baixar', id="baixar_produto", color="success"),
        dbc.Button('Imprimir', id="imprimir_baixa", color="primary", className="ms-2")
    ])
], id='modal_baixa_producao', size='lg', is_open=False)

@app.callback(
    Output('modal_baixa_producao', 'is_open'),
    Output('store_int_baixa', 'data'),
    Output('baixa_pcp', 'options'), #dash.no_update
    Input({'type': 'editar_movi', 'index': ALL}, 'n_clicks'),
    #Input('btn_baixar_material', 'n_clicks'),
    Input('baixar_produto_pcp', 'n_clicks'),
    
    
    State('modal_baixa_producao', 'is_open'),
    State('store_int_baixa', 'data')
)
def abrir_modal_baixa(n_editar, btn_abr_form, is_open, store_intermedio):

    df_pcp = listar_pcp()  # Atualize com sua lógica de carregamento dinâmico
    options = [{'label': (pcp), 'value': pcp} for pcp in df_pcp['pcp_id']]

    df_baixas = listar_dados('baixa')
    store_baixa = df_baixas.to_dict()

    trigg_id = callback_context.triggered[0]['prop_id'].split('.')[0]
    first_call = True if callback_context.triggered[0]['value'] == None else False
   
    if first_call:
        return is_open, store_intermedio, options
    
    if (trigg_id == 'btn_baixar_material') or (trigg_id == 'cancel_button_novo_processo'):
        df_int = pd.DataFrame(store_intermedio)
        df_int = df_int[:-1]
        store_intermedio = df_int.to_dict()

        return not is_open, store_intermedio, options
    
    if n_editar:
        trigg_dict = json.loads(callback_context.triggered[0]['prop_id'].split('.')[0])
        n_id = trigg_dict['index']
        
        df_int = pd.DataFrame(store_intermedio)
        df_baixa = pd.DataFrame(store_baixa)
        
        valores = df_baixa.loc[df_baixa['baixa_id'] == n_id].values.tolist()
        
        if valores:
            valores = valores[0] + [True]
        else:
            print("valores is empty!")
      
        # Verificar se o DataFrame tem colunas definidas
        if df_int is None or df_int.empty:
            df_int = pd.DataFrame(columns=['baixa_id', 'pcp_id', 'qtd', 'pallets', 'turno', 'maquina', 'observacao', 'data','categoria_qualidade', 'status','notafiscal' ,'ajuste', 'disabled'])
        
        df_int = df_int[:-1]

        df_int.loc[len(df_int)] = valores
        store_intermedio = df_int.to_dict()

        return not is_open, store_intermedio, options
        


    return not is_open, {} , options

@app.callback(
    [Output('store_baixa', 'data'),
     Output('div_erro1', 'children'),
     Output('div_erro1', 'style'),
     Output('id_movimentacao', 'value'),
     Output('baixa_pcp', 'value'),
     Output('baixa_pallet', 'value'),
     Output('baixa_turno', 'value'),
     Output('baixa_maquina', 'value'),
     Output('baixa_quantidade', 'value'),
     Output('baixa_data', 'date'),
     Output('baixa_observacao', 'value'),
     Output('baixa_pcp', 'disabled'),
     Output('ajuste_checkbox', 'value')
    ],
    [
    Input('baixar_produto', 'n_clicks'),
    Input('imprimir_baixa', 'n_clicks'),
    Input({'type': 'deletar_movi', 'index': ALL}, 'n_clicks'),
    Input('store_int_baixa', 'data')
    ],
    
    [State('store_baixa', 'data'),
     State('baixa_pcp', 'value'),
     State('baixa_pallet', 'value'),
     State('baixa_turno', 'value'),
     State('baixa_maquina', 'value'),
     State('baixa_quantidade', 'value'),
     State('baixa_data', 'date'),
     State('baixa_observacao', 'value'),
     State('id_pcp_form', 'value'),
     State('id_movimentacao', 'value'),
     State('ajuste_checkbox', 'value')],
    prevent_initial_call=True
)
def registrar_baixa(n, n_print, n_delet, store_int, dataset, pcp_id, pallet, turno, maquina, quantidade, data, observacao, id_pcp, id_mov, ajuste_checkbox):
    banco = Banco()
    
    first_call = True if (callback_context.triggered[0]['value'] == None or callback_context.triggered[0]['value'] == False) else False
    trigg_id = callback_context.triggered[0]['prop_id'].split('.')[0]
   
    if first_call:
        return dataset, [], {},None, None, None, None, None, None, None, None, False, []
    
    if 'imprimir_baixa' in trigg_id:
        # Verificar se todos os campos necessários estão preenchidos
        campos_obrigatorios = {
            'ID MOV': id_mov,
            'PCP': pcp_id,
            'Unidades por Pacote': pallet,
            'Volumes': maquina,
            'Posição': turno
        }
        
        campos_vazios = [campo for campo, valor in campos_obrigatorios.items() if valor is None or valor == '']
        
        if campos_vazios:
            return dataset, [f"Campos obrigatórios não preenchidos: {', '.join(campos_vazios)}"], {'margin-bottom': '15px', 'color': 'red'}, id_mov, pcp_id, pallet, turno, maquina, quantidade, data, observacao, False, ajuste_checkbox
        
        try:
            # Buscar nome do produto do banco de dados
            df_pcp = listar_pcp()
            #nome_produto = df_pcp.loc[df_pcp['pcp_id'] == pcp_id, 'produto'].iloc[0]
            
            # Gerar etiquetas
            filename = gerar_etiquetas(id_mov, pcp_id, 'teste', pallet, maquina, turno)
            
            # Verificar se o arquivo foi criado
            if os.path.exists(filename):
                # Abrir o PDF gerado
                os.startfile(filename)
                # Aguardar um momento para garantir que o arquivo foi aberto
                import time
                time.sleep(2)
                # Excluir o arquivo
                os.remove(filename)
                return dataset, ["Etiquetas geradas com sucesso!"], {'margin-bottom': '15px', 'color': 'green'}, id_mov, pcp_id, pallet, turno, maquina, quantidade, data, observacao, False, ajuste_checkbox
            else:
                return dataset, ["Erro ao gerar etiquetas!"], {'margin-bottom': '15px', 'color': 'red'}, id_mov, pcp_id, pallet, turno, maquina, quantidade, data, observacao, False, ajuste_checkbox
        except Exception as e:
            return dataset, [f"Erro ao gerar etiquetas: {str(e)}"], {'margin-bottom': '15px', 'color': 'red'}, id_mov, pcp_id, pallet, turno, maquina, quantidade, data, observacao, False, ajuste_checkbox
    
    if 'baixar_produto' in trigg_id:
        
        df_int = pd.DataFrame(store_int)

        if len(df_int.index) == 0:  # Novo processo
            if None in [pcp_id]:
                return dataset, ["PCP é obrigatório!"], {'margin-bottom': '15px', 'color': 'red'},None, pcp_id, pallet, turno, maquina, quantidade, data, observacao, False, ajuste_checkbox
            
            if None in [quantidade]:
                return dataset, ["Quantidade é obrigatória!"], {'margin-bottom': '15px', 'color': 'red'},None, pcp_id, pallet, turno, maquina, quantidade, data, observacao, False, ajuste_checkbox

            if None in [data]:
                return dataset, ["Data é obrigatória!"], {'margin-bottom': '15px', 'color': 'red'},None, pcp_id, pallet, turno, maquina, quantidade, data, observacao, False, ajuste_checkbox
            
            data = datetime.strptime(data, '%Y-%m-%d').date() if isinstance(data, str) else data
            
            # Definir valor do ajuste: 1 se checkbox marcado, 0 se não marcado
            valor_ajuste = 1 if ajuste_checkbox and 1 in ajuste_checkbox else 0

            banco.inserir_dados('baixa', pcp_id=pcp_id, qtd=quantidade,turno=turno ,pallets=pallet, maquina=maquina,  
                               observacao=observacao, data=data, status='Estoque', ajuste=valor_ajuste)
            
            return dataset, ["Baixa registrada com sucesso!"], {'margin-bottom': '15px', 'color': 'green'}, None, pcp_id, pallet, turno, maquina, quantidade, data, observacao, False, []
        
        else:
      
            data = datetime.strptime(data, '%Y-%m-%d').date() if isinstance(data, str) else data
            
            # Definir valor do ajuste: 1 se checkbox marcado, 0 se não marcado
            valor_ajuste = 1 if ajuste_checkbox and 1 in ajuste_checkbox else 0
            
            banco.editar_dado('baixa', id_mov, pallets=pallet, turno=turno, qtd=quantidade, maquina=maquina, observacao=observacao, data=data, ajuste=valor_ajuste)
                     
            return dataset, [], {},None, None, None, None, None, None, None, None, False, []

    if 'deletar_movi' in trigg_id:

        trigg_id_dict = json.loads(trigg_id)
        n_id = trigg_id_dict['index']
        banco.deletar_dado('baixa', n_id)
    
    if trigg_id == 'store_int_baixa':
        
        try:

            df = pd.DataFrame(callback_context.triggered[0]['value'])
            valores = df.head(1).values.tolist()[0]
            
            id_mov, pcp, qtd, pallet, turno, maquina, observacao,  data, categoria_qualidade, status, notafiscal, ajuste, disabled = valores
            
            # Definir checkbox baseado no valor da coluna ajuste
            checkbox_value = [1] if ajuste == 1 else []
      
            return dataset, ['Modo de Edição: Número de Ordem não pode ser alterado'], {'margin-bottom': '15px', 'color': 'green'}, id_mov, pcp, pallet, int(turno) if turno is not None else None, int(maquina) if maquina is not None else None, qtd, data, observacao, True, checkbox_value
        
        except Exception as e:
    
            return dataset, [], {}, None, id_pcp, None, None, None, None, date.today(), None, False, []

    return dataset, [], {},None, None, None, None, None, None, None, None, False, []

def gerar_etiquetas(id_mov, pcp_id, nome_produto, quantidade, volumes, posicao):
    # Criar diretório temporário para etiquetas
    temp_dir = os.path.join(os.getcwd(), 'temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # Nome do arquivo PDF temporário
    filename = os.path.join(temp_dir, f'etiquetas_{id_mov}.pdf')
    
    # Criar o PDF
    c = canvas.Canvas(filename, pagesize=A4)
    
    # Dimensões da etiqueta
    label_width = 99 * mm  # Largura da etiqueta
    label_height = 34 * mm  # Altura da etiqueta
    margin_x = 6 * mm  # Margem horizontal
    margin_y = 6 * mm  # Margem vertical
    
    # Fonte e tamanho
    c.setFont("Helvetica-Bold", 12)
    
    # Calcular número total de etiquetas e posição inicial
    total_etiquetas = volumes
    posicao_inicial = posicao if posicao and posicao > 0 else 0
    
    # Gerar etiquetas (2 colunas x 6 linhas)
    etiqueta_atual = 0
    for row in range(6):
        for col in range(2):
            # Pular etiquetas até a posição inicial
            if etiqueta_atual < posicao_inicial:
                etiqueta_atual += 1
                continue
                
            # Parar se já gerou todas as etiquetas necessárias
            if etiqueta_atual >= posicao_inicial + total_etiquetas:
                break
                
            x = margin_x + (col * (label_width + margin_x))
            y = A4[1] - margin_y - (row * (label_height + margin_y))
            
            # Desenhar borda da etiqueta
            c.rect(x, y - label_height, label_width, label_height)
            
            # Adicionar informações
            c.drawString(x + 5, y - 15, f"ID MOV: {id_mov}")
            c.drawString(x + 5, y - 30, f"PCP: {pcp_id}")
            c.drawString(x + 5, y - 45, f"Produto: {nome_produto}")
            c.drawString(x + 5, y - 60, f"Qtd: {quantidade}")
            
            etiqueta_atual += 1
        
        # Parar se já gerou todas as etiquetas necessárias
        if etiqueta_atual >= posicao_inicial + total_etiquetas:
            break
    
    c.save()
    return filename

