from banco_dados.banco import *
from dash import dash_table
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from calculos import Filtros


def calcular_somas(pcp_ids):
    with Session(engine) as session:
        soma_qtd_baixa = dict(session.query(BAIXA.pcp_id, func.sum(BAIXA.qtd))
                              .filter(BAIXA.pcp_id.in_(pcp_ids))
                              .group_by(BAIXA.pcp_id).all())
        
        soma_qtd_retirada = dict(session.query(RETIRADA.ret_id_pcp, func.sum(RETIRADA.ret_qtd))
                                 .filter(RETIRADA.ret_id_pcp.in_(pcp_ids))
                                 .group_by(RETIRADA.ret_id_pcp).all())
    
    return soma_qtd_baixa, soma_qtd_retirada


def formatar_numero(val):
    return '{:,.0f}'.format(val).replace(',', '.') if val is not None else val


def tabela_pcp_formacao(df):
    banco = Banco()
    df_produtos = banco.ler_tabela("produtos")
    
    df = df.merge(df_produtos[['produto_id', 'nome']], left_on='pcp_produto_id', right_on='produto_id', how='left')
    df['pcp_entrega'] = pd.to_datetime(df['pcp_entrega'], errors='coerce')
    df['pcp_emissao'] = pd.to_datetime(df['pcp_emissao'], errors='coerce')
    df['pcp_semana'] = df['pcp_entrega'].dt.isocalendar().week
    
    pcp_ids = df['pcp_id'].tolist()
    soma_qtd_baixa, soma_qtd_retirada = calcular_somas(pcp_ids)
    
    df['qtd_baixa'] = df['pcp_id'].map(soma_qtd_baixa).fillna(0)
    df['qtd_retirada'] = df['pcp_id'].map(soma_qtd_retirada).fillna(0)
    df['saldo_em_processo'] = (df['pcp_qtd'] - df['qtd_baixa']).clip(lower=0)
    df['saldo_em_estoque'] = (df['qtd_baixa'] - df['qtd_retirada']).clip(lower=0)
    df['pcp_entrega_formatada'] = df['pcp_entrega'].dt.strftime('%d/%m/%Y').fillna('')
    df.sort_values(by='pcp_entrega', ascending=True, inplace=True)
    
    return df


def tabela_estoque(df, cliente, produto, categoria, tipo_produto):
    df_geral = tabela_pcp_formacao(df)
    
    # Get current month and year for filtering
    data_atual = pd.to_datetime("today")
    mes_atual = data_atual.month
    ano_atual = data_atual.year
    
    # Filter the withdrawals to only include current month data
    banco = Banco()
    df_retiradas = banco.ler_tabela("retirada")
    df_pcp = banco.ler_tabela("pcp")  # Get PCP data to link product IDs
    
    # Join retiradas with PCP to get the product_id
    df_retiradas = df_retiradas.merge(
        df_pcp[['pcp_id', 'pcp_produto_id']], 
        left_on='ret_id_pcp', 
        right_on='pcp_id',
        how='left'
    )
    
    # Convert date column to datetime and filter by current month/year
    df_retiradas['ret_data'] = pd.to_datetime(df_retiradas['ret_data'], errors='coerce')
    df_retiradas = df_retiradas[
        (df_retiradas['ret_data'].dt.month == mes_atual) & 
        (df_retiradas['ret_data'].dt.year == ano_atual)
    ]
    
    # Group by product ID to get the sum of withdrawals for the current month
    df_retiradas_sum = df_retiradas.groupby('pcp_produto_id')['ret_qtd'].sum().reset_index()
    df_retiradas_sum.rename(columns={'pcp_produto_id': 'produto_id', 'ret_qtd': 'qtd_retirada_mes_atual'}, inplace=True)
    
    numeric_cols = ["saldo_em_processo", "saldo_em_estoque", "qtd_retirada"]
    df_geral[numeric_cols] = df_geral[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    df_somas = df_geral.groupby("pcp_produto_id", as_index=False).agg({
        "saldo_em_processo": "sum",
        "saldo_em_estoque": "sum",
        "qtd_retirada": "sum",  # Keep this for reference
        "pcp_categoria": "first",
        "pcp_cliente_id": "first",
        "cliente_nome": "first"
    }).rename(columns={"pcp_produto_id": "produto_id"})
    
    # Replace the old qtd_retirada with current month's data
    df_somas = pd.merge(
        df_somas, 
        df_retiradas_sum, 
        on='produto_id', 
        how='left'
    )
    df_somas['qtd_retirada'] = df_somas['qtd_retirada_mes_atual'].fillna(0)
    df_somas.drop('qtd_retirada_mes_atual', axis=1, inplace=True)
    
    banco = Banco()
    df_produtos = banco.ler_tabela("produtos")
    df_final = df_produtos.merge(df_somas, on="produto_id", how="left").fillna(0)
    
    fim_do_mes = data_atual + pd.offsets.MonthEnd()
    dias_uteis = np.busday_count(data_atual.strftime('%Y-%m-%d'), fim_do_mes.strftime('%Y-%m-%d'))
    dias_uteis_passados = np.busday_count(f"{data_atual.year}-{data_atual.month:02d}-01", data_atual.strftime('%Y-%m-%d'))
    
    df_final['saldo_em_estoque_por_pedido'] = round(df_final['saldo_em_estoque'] / (df_final['pedido_mensal'] / dias_uteis), 2)
    df_final['saldo_em_estoque_por_venda'] = round(df_final['saldo_em_estoque'] / (df_final['qtd_retirada'] / dias_uteis_passados), 2)
    
    def calcular_seta(valor):
        if pd.isna(valor) or valor == float('inf') or valor == -float('inf'):
            return "0", "gray"
        elif valor > 8:
            return f"{int(valor)} ↑", "green"
        elif valor > 3:
            return f"{int(valor)} !", "orange"
        else:
            return f"{int(valor)} ↓", "red"
    
    df_final['seta_por_pedido'], df_final['cor_seta_por_pedido'] = zip(*df_final['saldo_em_estoque_por_pedido'].apply(calcular_seta))
    df_final['seta_por_venda'], df_final['cor_seta_por_venda'] = zip(*df_final['saldo_em_estoque_por_venda'].apply(calcular_seta))
    
    for col in numeric_cols:
        df_final[col] = df_final[col].map(formatar_numero)
    df_final = Filtros.filtrar(df_final, {
        'cliente_nome': ('exato', cliente),
        'nome': ('contem', produto),
        'pcp_categoria': ('multi', categoria),
        'fluxo_producao': ('exato', tipo_produto),
    })
    
    return dash_table.DataTable(
        columns=[
            {"name": "ID PRODUTO", "id": "produto_id"},
            {"name": "PRODUTO", "id": "nome"},
            {"name": "PREVISÃO MENSAL", "id": "pedido_mensal"},
            #{"name": "PROCESSO", "id": "saldo_em_processo"},
            {"name": "ESTOQUE", "id": "saldo_em_estoque"},
            #{"name": "VENDA", "id": "qtd_retirada"},
            {"name": "COBERTURA PROJEÇÃO", "id": "seta_por_pedido"},
            #{"name": "COBERTURA TENDÊNCIA", "id": "seta_por_venda"}
        ],
        data=df_final.to_dict("records"),
        page_size=30,
        style_data_conditional=[
    {
        'if': {'column_id': 'seta_por_pedido', 'filter_query': '{seta_por_pedido} contains "↑"'},
        'color': 'green'
    },
    {
        'if': {'column_id': 'seta_por_pedido', 'filter_query': '{seta_por_pedido} contains "!"'},
        'color': 'orange'
    },
    {
        'if': {'column_id': 'seta_por_pedido', 'filter_query': '{seta_por_pedido} contains "↓"'},
        'color': 'red'
    },
    {
        'if': {'column_id': 'seta_por_venda', 'filter_query': '{seta_por_venda} contains "↑"'},
        'color': 'green'
    },
    {
        'if': {'column_id': 'seta_por_venda', 'filter_query': '{seta_por_venda} contains "!"'},
        'color': 'orange'
    },
    {
        'if': {'column_id': 'seta_por_venda', 'filter_query': '{seta_por_venda} contains "↓"'},
        'color': 'red'
    }
],
        style_table={'height': '800px', 'overflowY': 'auto', 'border': '1px solid #ccc'},
        style_header={'fontWeight': 'bold', 'textAlign': 'center'},
        style_cell={'textAlign': 'center', 'padding': '5px'},
        style_data={
            'color': 'black', 
            'backgroundColor': 'white'
        }
    )


def relatorio_estoque(df, cliente, produto, categoria, tipo_produto):
    df_geral = tabela_pcp_formacao(df)
    
    # Get current month and year for filtering
    data_atual = pd.to_datetime("today")
    mes_atual = data_atual.month
    ano_atual = data_atual.year
    
    banco = Banco()
    df_retiradas = banco.ler_tabela("retirada")
    df_pcp = banco.ler_tabela("pcp")
    
    df_retiradas = df_retiradas.merge(
        df_pcp[['pcp_id', 'pcp_produto_id']], 
        left_on='ret_id_pcp', 
        right_on='pcp_id',
        how='left'
    )
    
    df_retiradas['ret_data'] = pd.to_datetime(df_retiradas['ret_data'], errors='coerce')
    df_retiradas = df_retiradas[
        (df_retiradas['ret_data'].dt.month == mes_atual) & 
        (df_retiradas['ret_data'].dt.year == ano_atual)
    ]
    
    df_retiradas_sum = df_retiradas.groupby('pcp_produto_id')['ret_qtd'].sum().reset_index()
    df_retiradas_sum.rename(columns={'pcp_produto_id': 'produto_id', 'ret_qtd': 'qtd_retirada_mes_atual'}, inplace=True)
    
    numeric_cols = ["saldo_em_processo", "saldo_em_estoque", "qtd_retirada"]
    df_geral[numeric_cols] = df_geral[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    df_somas = df_geral.groupby("pcp_produto_id", as_index=False).agg({
        "saldo_em_processo": "sum",
        "saldo_em_estoque": "sum",
        "qtd_retirada": "sum",
        "pcp_categoria": "first",
        "pcp_cliente_id": "first",
        "cliente_nome": "first"
    }).rename(columns={"pcp_produto_id": "produto_id"})
    
    df_somas = pd.merge(
        df_somas, 
        df_retiradas_sum, 
        on='produto_id', 
        how='left'
    )
    df_somas['qtd_retirada'] = df_somas['qtd_retirada_mes_atual'].fillna(0)
    df_somas.drop('qtd_retirada_mes_atual', axis=1, inplace=True)
    
    df_produtos = banco.ler_tabela("produtos")
    df_final = df_produtos.merge(df_somas, on="produto_id", how="left").fillna(0)
    
    fim_do_mes = data_atual + pd.offsets.MonthEnd()
    dias_uteis = np.busday_count(data_atual.strftime('%Y-%m-%d'), fim_do_mes.strftime('%Y-%m-%d'))
    dias_uteis_passados = np.busday_count(f"{data_atual.year}-{data_atual.month:02d}-01", data_atual.strftime('%Y-%m-%d'))
    
    df_final['saldo_em_estoque_por_pedido'] = round(df_final['saldo_em_estoque'] / (df_final['pedido_mensal'] / dias_uteis), 2)
    df_final['saldo_em_estoque_por_venda'] = round(df_final['saldo_em_estoque'] / (df_final['qtd_retirada'] / dias_uteis_passados), 2)
    
    def calcular_seta(valor):
        if pd.isna(valor) or valor == float('inf') or valor == -float('inf'):
            return "0", "gray"
        elif valor > 8:
            return f"{int(valor)} ↑", "green"
        elif valor > 3:
            return f"{int(valor)} !", "orange"
        else:
            return f"{int(valor)} ↓", "red"
    
    df_final['seta_por_pedido'], df_final['cor_seta_por_pedido'] = zip(*df_final['saldo_em_estoque_por_pedido'].apply(calcular_seta))
    df_final['seta_por_venda'], df_final['cor_seta_por_venda'] = zip(*df_final['saldo_em_estoque_por_venda'].apply(calcular_seta))
    
    for col in numeric_cols:
        df_final[col] = df_final[col].map(formatar_numero)

    df_final = Filtros.filtrar(df_final, {
        'cliente_nome': ('exato', cliente),
        'nome': ('contem', produto),
        'pcp_categoria': ('multi', categoria),
        'fluxo_producao': ('exato', tipo_produto),
    })
    
    return df_final