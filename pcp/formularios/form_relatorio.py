from logging import exception
import dash
import plotly.express as px
from dash import html, dcc, callback_context, dash_table
from dash.dependencies import Input, Output, State, ALL
import dash_bootstrap_components as dbc
from datetime import timedelta, date

import json
import pandas as pd
from app import *
from datetime import datetime, timedelta
from pcp.pag_principal import *

from banco_dados.banco import df_pcp, listar_dados, listar_pcp




layout = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle('RELATÓRIO')),
    dbc.ModalBody([
        html.Ul(id='lista_qtd_categoria'),  # Lista para exibir categorias e quantidades
    ]),
], id='modal_relatorio_rapido', size='lg', is_open=False)

# @app.callback(
#     Output('modal_relatorio_rapido', "is_open"),
#     Output('lista_qtd_categoria', 'children'),  # Alterar para children
#     Input('btn_relatorio_rapido', 'n_clicks'),
#     Input('select_ano', 'value'),
#     Input('select_semana', 'value'),
#     State('modal_relatorio_rapido', "is_open"),
# )
# def atualizar_relatorio(n_clicks, select_ano, select_semana, is_open):
#     # Obter o ano e semana atuais caso os valores sejam None
#     df_pcp = listar_pcp()
#     ano_atual = datetime.now().year
#     semana_atual = datetime.now().isocalendar().week
#     ano_filtro = int(select_ano) if select_ano is not None else ano_atual
#     semana_filtro = int(select_semana) if select_semana is not None else semana_atual

#     # Garantir que 'pcp_entrega' seja datetime e extrair ano e semana
#     df_pcp['pcp_entrega'] = pd.to_datetime(df_pcp['pcp_entrega'], errors='coerce')  # Ignora valores inválidos
#     df_pcp['pcp_ano'] = df_pcp['pcp_entrega'].dt.year.astype('Int64')  # Inteiro, mas permite valores NaN
#     df_pcp['pcp_sem'] = df_pcp['pcp_entrega'].dt.isocalendar().week.astype('Int64')  # Inteiro, mas permite valores NaN

#     # Filtrar pelo ano e semana
#     df_filtrado = df_pcp[
#         (df_pcp['pcp_ano'] == ano_filtro) & (df_pcp['pcp_sem'] == semana_filtro)
#     ]

#     # Criar uma lista de tópicos
#     if df_filtrado.empty:
#         return not is_open, [html.Li(f"Nenhum dado encontrado para o Ano: {ano_filtro}, Semana: {semana_filtro}")]
#     else:
#         # Agrupar e contar quantidade de itens por categoria
#         categoria_counts = df_filtrado.groupby('pcp_categoria')['pcp_qtd'].sum().reset_index()

#         # Criar a lista de tópicos com as quantidades formatadas
#         lista_categoria = [
#             html.Li(f'{categoria}: {quantidade:,.0f}'.replace(',', '.') + ' itens') 
#             for categoria, quantidade in zip(categoria_counts['pcp_categoria'], categoria_counts['pcp_qtd'])
#         ]

#     # Abrir ou fechar o modal apenas com o botão
#     if callback_context.triggered and 'btn_relatorio_rapido' in callback_context.triggered[0]['prop_id']:
#         return not is_open, lista_categoria

#     # Retornar a lista sem alterar o estado do modal
#     return is_open, lista_categoria