import dash_bootstrap_components as dbc
from datetime import date
from dash import html, dcc, callback_context, dash_table
from banco_dados.banco import df_pcp, Banco

from dash.dependencies import Input, Output, State, ALL

from datetime import timedelta, date
import json
import pandas as pd
from app import *
from pcp.pag_principal import *

layout = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle('Retirada de Produção')),
    dbc.ModalBody([
        dbc.Row([
            dbc.Col([
                dbc.Label("ID RETIRADA"),
                dbc.Input(id="id_retirada", placeholder="Id...", type="number", disabled=True)
            ], sm=12, md=3),
            dbc.Col([
                dbc.Label("ID PCP"),
                dcc.Dropdown(
                    id="retirada_pcp",
                    options=[{'label': pcp, 'value': pcp} for pcp in df_pcp['pcp_id']],  # Substitua 'df_pcp' com a sua lista de códigos PCP
                    placeholder="Selecione o id PCP...",
                    clearable=False
                )
            ], sm=12, md=3),
            dbc.Col([
                dbc.Label("QUANTIDADE"),
                dbc.Input(id="retirada_quantidade", placeholder="Quantidade retirada...", type="number")
            ], sm=12, md=6),
        ]),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.Label("DATA")
                ]),
                dbc.Row([
                    dcc.DatePickerSingle(id="retirada_data", className='dbc', date=date.today(), initial_visible_month=date.today())
                ]),
            ], sm=12, md=6),
        ]),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                dbc.Label("OBSERVAÇÃO"),
                dbc.Textarea(id="retirada_observacao", placeholder="Observação geral...", style={'height': '80%'})
            ]),
        ]),   
        html.H5(id='div_erro8')
    ]),
    dbc.ModalFooter([
        dbc.Button('Registrar Retirada', id="registrar_retirada", color="success")
    ])
], id='modal_retirada_producao', size='lg', is_open=False)

@app.callback(
    Output('modal_retirada_producao', 'is_open'),
    Output('store_int_retirada', 'data'),
    Output('retirada_pcp', 'options'), #dash.no_update
    Input({'type': 'editar_reti', 'index': ALL}, 'n_clicks'),
    #Input('btn_retirar_produto', 'n_clicks'),
    Input('retirar_produto', 'n_clicks'),
    
    
    State('modal_retirada_producao', 'is_open'),
    State('store_int_retirada', 'data'),
    prevent_initial_call=True
)
def abrir_modal_retirada(n_editar, btn_abr_form, is_open, store_intermedio):

    df_pcp = listar_pcp()  # Atualize com sua lógica de carregamento dinâmico
    options = [{'label': (pcp), 'value': pcp} for pcp in df_pcp['pcp_id']]

    df_retirada = listar_dados('retirada')
    store_retirada = df_retirada.to_dict()

    trigg_id = callback_context.triggered[0]['prop_id'].split('.')[0]
    first_call = True if callback_context.triggered[0]['value'] == None else False
   
    if first_call:
        return is_open, store_intermedio, options
    
    if (trigg_id == 'btn_baixar_material') or (trigg_id == 'cancel_button_novo_processo'):
        df_int = pd.DataFrame(store_intermedio)
        df_int = df_int[:-1]
        store_intermedio = df_int.to_dict()

        return not is_open, store_intermedio, options
    
    if 'editar_reti' in trigg_id:
   
        trigg_dict = json.loads(callback_context.triggered[0]['prop_id'].split('.')[0])
        n_id = trigg_dict['index']
        
        df_int = pd.DataFrame(store_intermedio)
        df_retirada = pd.DataFrame(store_retirada)
        
        valores = df_retirada.loc[df_retirada['ret_id'] == n_id].values.tolist()
        
        if valores:
            valores = valores[0] + [True]
        else:
            # Handle the case where valores is empty
            print("valores is empty!")


      
        if df_int is None or df_int.empty:
            df_int = pd.DataFrame(columns=['id_ret', 'ret_pcp_id', 'ret_qtd', 'ret_data', 'ret_obs', 'disabled'])

        df_int = df_int[:-1]
        df_int.loc[len(df_int)] = valores
        store_intermedio = df_int.to_dict()

        return not is_open, store_intermedio , options
        


    return not is_open, {} , options


@app.callback(
    [Output('store_retirada', 'data'),
     Output('div_erro8', 'children'),
     Output('div_erro8', 'style'),
     Output('id_retirada', 'value'),
     Output('retirada_pcp', 'value'),
     Output('retirada_quantidade', 'value'),
     Output('retirada_data', 'date'),
     Output('retirada_observacao', 'value'),
     Output('retirada_pcp', 'disabled')
    ],
    [
    Input('registrar_retirada', 'n_clicks'),
    Input({'type': 'deletar_reti', 'index': ALL}, 'n_clicks'),
    Input('store_int_retirada', 'data')

    ],
    
    [State('store_retirada', 'data'),
     State('retirada_pcp', 'value'),
     State('retirada_quantidade', 'value'),
     State('retirada_data', 'date'),
     State('retirada_observacao', 'value'),
     State('id_pcp_form', 'value'),
     State('id_retirada', 'value')],
    prevent_initial_call=True
)
def registrar_baixa(n, n_delet, store_int,
    dataset, ret_pcp_id, ret_qtd, ret_data, ret_obs, id_pcp, id_ret):
    banco = Banco()
    
    first_call = True if (callback_context.triggered[0]['value'] == None or callback_context.triggered[0]['value'] == False) else False
    trigg_id = callback_context.triggered[0]['prop_id'].split('.')[0]
   
    if first_call:
        return dataset, [], {},None, None, None, date.today(), None, False
    
    if 'registrar_retirada' in trigg_id:
        
        df_int = pd.DataFrame(store_int)
    
        if len(df_int.index) == 0:  # Novo processo
            if None in [ret_pcp_id]:
                return dataset, ["PCP é obrigatório!"], {'margin-bottom': '15px', 'color': 'red'},None, ret_pcp_id, ret_qtd, ret_data, ret_obs, False
            
            if None in [ret_qtd]:
                return dataset, ["Quantidade é obrigatória!"], {'margin-bottom': '15px', 'color': 'red'},None, ret_pcp_id, ret_qtd, ret_data, ret_obs, False

            if None in [ret_data]:
                return dataset, ["Data é obrigatória!"], {'margin-bottom': '15px', 'color': 'red'},None, ret_pcp_id, ret_qtd, ret_data, ret_obs, False
            
            ret_data = datetime.strptime(ret_data, '%Y-%m-%d').date() if isinstance(ret_data, str) else ret_data
            

            banco.inserir_dados('retirada', ret_id_pcp=ret_pcp_id, ret_qtd=ret_qtd, ret_data=ret_data, ret_obs=ret_obs) 
            
            return dataset, ["Baixa registrada com sucesso!"], {'margin-bottom': '15px', 'color': 'green'},None, None, None, None, None,  False
        
        else:
       
            ret_data = datetime.strptime(ret_data, '%Y-%m-%d').date() if isinstance(ret_data, str) else ret_data
            banco.editar_dado('retirada', id_ret, ret_qtd=ret_qtd, ret_data=ret_data, ret_obs=ret_obs)
                     
            return dataset, [], {},None, None, None, None, None, False

    if 'deletar_reti' in trigg_id:

        trigg_id_dict = json.loads(trigg_id)
        n_id = trigg_id_dict['index']
        banco.deletar_dado('retirada', n_id)
    
    if trigg_id == 'store_int_retirada':
        
        try:

            df = pd.DataFrame(callback_context.triggered[0]['value'])
            valores = df.head(1).values.tolist()[0]

            id_ret, ret_pcp_id, ret_qtd, ret_data, ret_obs, disabled = valores
      
            return dataset, ['Modo de Edição: Número de Ordem não pode ser alterado'], {'margin-bottom': '15px', 'color': 'green'}, id_ret, ret_pcp_id, ret_qtd, ret_data, ret_obs, False
        
        except Exception as e:
           
            return dataset, [], {}, None, id_pcp, None, date.today(), None, False

    return dataset, [], {},None, None, None, date.today(), None, False