from banco_dados.banco import *
from dash import dash_table
from datetime import datetime, timedelta
import pandas as pd
from dash import html
import dash_bootstrap_components as dbc
import numpy as np
from calculos import *
from sqlalchemy.orm import Session

def obter_status_ordem_compra_em_lote(pcp_ids):
    """
    Obtém o status das ordens de compra para uma lista de pcp_ids
    Retorna um dicionário {pcp_id: status}
    """
    with Session(engine) as session:
        resultados = session.query(ORDEM_COMPRA.oc_pcp_id, ORDEM_COMPRA.oc_status) \
                            .filter(ORDEM_COMPRA.oc_pcp_id.in_(pcp_ids)) \
                            .filter(ORDEM_COMPRA.oc_pcp_id.isnot(None)) \
                            .all()
        return dict(resultados)

def obter_dados_em_lote(pcp_ids):
    """
    Combina todas as consultas ao banco em uma única função para reduzir o número de conexões
    """
    with Session(engine) as session:
        # Baixas
        baixas = session.query(BAIXA.pcp_id, func.sum(BAIXA.qtd).label("qtd_baixa")) \
                        .filter(BAIXA.pcp_id.in_(pcp_ids)) \
                        .group_by(BAIXA.pcp_id).all()
        
        # Retiradas
        retiradas = session.query(RETIRADA.ret_id_pcp, func.sum(RETIRADA.ret_qtd).label("qtd_retirada")) \
                          .filter(RETIRADA.ret_id_pcp.in_(pcp_ids)) \
                          .group_by(RETIRADA.ret_id_pcp).all()
        
        # Status ordem compra
        status_oc = session.query(ORDEM_COMPRA.oc_pcp_id, ORDEM_COMPRA.oc_status) \
                          .filter(ORDEM_COMPRA.oc_pcp_id.in_(pcp_ids)) \
                          .filter(ORDEM_COMPRA.oc_pcp_id.isnot(None)) \
                          .all()
        
        # Subquery for latest apontamento per pcp
        latest_apontamento_subq = session.query(
            APONTAMENTO_PRODUTO.atp_pcp,
            func.max(APONTAMENTO_PRODUTO.atp_id).label('max_atp_id')
        ).filter(
            APONTAMENTO_PRODUTO.atp_pcp.in_(pcp_ids)
        ).group_by(APONTAMENTO_PRODUTO.atp_pcp).subquery()

        # Query for last machine
        last_machine = session.query(
            APONTAMENTO_PRODUTO.atp_pcp,
            MAQUINA.maquina_nome
        ).join(
            latest_apontamento_subq,
            APONTAMENTO_PRODUTO.atp_id == latest_apontamento_subq.c.max_atp_id
        ).join(
            PRODUCAO, APONTAMENTO_PRODUTO.atp_producao == PRODUCAO.pr_id
        ).join(
            MAQUINA, PRODUCAO.pr_maquina_id == MAQUINA.maquina_id
        ).all()
        
        return {
            'baixas': dict(baixas),
            'retiradas': dict(retiradas),
            'status_oc': dict(status_oc),
            'last_machine': dict(last_machine)
        }

def formatar_numero(val):
    if pd.isna(val):
        return val
    return '{:,.0f}'.format(val).replace(',', '.')

def personalizar_tabela(df, tipo_produto, status, semana, comparacao_semana='==', ocorrencia=None):
    banco = Banco()
    
    # Carregar dados do banco uma única vez
    df_produtos = banco.ler_tabela("produtos")
    df_planejamento = banco.ler_tabela("planejamento")
    df_valor_produto = banco.ler_tabela("valor_produto")
    
    # Obter o valor mais recente do produto
    if not df_valor_produto.empty:
        df_valor_produto['data'] = pd.to_datetime(df_valor_produto['data'])
        df_valor_produto = df_valor_produto.sort_values(by='data', ascending=False).drop_duplicates('produto_id')

    # Converter datas uma única vez
    df_planejamento['data_programacao'] = pd.to_datetime(df_planejamento['data_programacao'], errors='coerce')
    df_planejamento['semana_planejamento'] = df_planejamento['data_programacao'].dt.isocalendar().week
    
    # Otimizar merge de planejamento
    df_planejamento_recente = (df_planejamento
                              .sort_values('data_programacao', ascending=False)
                              .drop_duplicates('id_pcp')
                              [['id_pcp', 'semana_planejamento']])
    
    # Otimizar merges
    df_filtrado = (df
                   .merge(df_produtos[['produto_id', 'nome', 'fluxo_producao']], 
                         left_on='pcp_produto_id', 
                         right_on='produto_id', 
                         how='left')
                   .merge(df_planejamento_recente,
                         left_on='pcp_id',
                         right_on='id_pcp',
                         how='left'))
    
    if not df_valor_produto.empty:
        df_filtrado = df_filtrado.merge(df_valor_produto[['produto_id', 'valor']], left_on='pcp_produto_id', right_on='produto_id', how='left')
    else:
        df_filtrado['valor'] = np.nan

    # Vetorizar criação de colunas
    df_filtrado['planejamento_info'] = np.where(
        pd.notna(df_filtrado['semana_planejamento']),
        df_filtrado['semana_planejamento'].fillna(0).astype(int).astype(str) + " ✓",
        ""
    )
    
    # Converter datas de uma vez
    colunas_datas = ['pcp_entrega', 'pcp_emissao', 'pcp_primiera_entrega']
    for col in colunas_datas:
        df_filtrado[col] = pd.to_datetime(df_filtrado[col], format='%Y-%m-%d', errors='coerce')
    
    # Calcular semanas de uma vez
    df_filtrado['pcp_semana'] = df_filtrado['pcp_entrega'].dt.isocalendar().week
    df_filtrado['pcp_semana_primeira'] = df_filtrado['pcp_primiera_entrega'].dt.isocalendar().week
    
    # Aplicar filtros
    if semana is not None:
        df_filtrado['pcp_semana'] = df_filtrado['pcp_semana'].astype('Int64')
        df_filtrado = Filtros.filtrar(df_filtrado, {
            'pcp_semana': ('comparar_num', (comparacao_semana, semana))
        })
    
    if ocorrencia is None or ocorrencia == []:
        df_filtrado = df_filtrado[~df_filtrado['pcp_correncia'].isin([0, 1, 2])]
    else:
        df_filtrado = df_filtrado[df_filtrado['pcp_correncia'] == ocorrencia]
    
    # Obter dados em lote
    pcp_ids = df_filtrado['pcp_id'].unique().tolist()
    dados_lote = obter_dados_em_lote(pcp_ids)
    
    # Aplicar dados em lote
    df_filtrado['qtd_baixa'] = df_filtrado['pcp_id'].map(dados_lote['baixas']).fillna(0)
    df_filtrado['qtd_retirada'] = df_filtrado['pcp_id'].map(dados_lote['retiradas']).fillna(0)
    df_filtrado['status_ordem_compra'] = df_filtrado['pcp_id'].map(dados_lote['status_oc']).fillna("")
    df_filtrado['ultima_maquina'] = df_filtrado['pcp_id'].map(dados_lote['last_machine']).fillna('')
    
    # Calcular status de forma vetorizada
    condicoes = [
        df_filtrado['pcp_correncia'] == 3,
        df_filtrado['qtd_baixa'] == 0,
        (df_filtrado['qtd_baixa'] > 0) & (df_filtrado['qtd_baixa'] < 0.9 * df_filtrado['pcp_qtd']),
        df_filtrado['qtd_baixa'] >= 0.9 * df_filtrado['pcp_qtd']
    ]
    valores = ['FEITO', 'PENDENTE', 'PARCIAL', 'FEITO']
    df_filtrado['status_baixa'] = np.select(condicoes, valores, default='PENDENTE')
    
    # Vetorizar criação de ícones
    def criar_icone_ordem_compra(row, hoje):
        indicadores = []
        if pd.notna(row['status_ordem_compra']) and row['status_ordem_compra'] != "":
            indicadores.append("🛒✅" if row['status_ordem_compra'] == "Entregue Total" else "🛒❌")
        
        if any(row[col] == 1 or row[col] is True for col in ['pcp_tercereizacao', 'pcp_tercerizacao', 'pcp_terceirizacao'] if col in row):
            indicadores.append("🚚")
        
        if 'pcp_bopp' in row and (row['pcp_bopp'] == 1 or row['pcp_bopp'] is True):
            indicadores.append("🔪")
        
        if 'pcp_retrabalho' in row:
            if row['pcp_retrabalho'] == 1:
                indicadores.append("🚫")
            elif row['pcp_retrabalho'] == 3:
                indicadores.append("❌")

        if row['status_baixa'] != 'FEITO' and pd.notna(row['pcp_primiera_entrega']) and row['pcp_primiera_entrega'].date() <= hoje:
            indicadores.append("⏰")
        
        return " ".join(indicadores)
    
    hoje = datetime.now().date()
    df_filtrado['icone_ordem_compra'] = df_filtrado.apply(
        lambda row: criar_icone_ordem_compra(row, hoje),
        axis=1
    )
    
    # Calcular saldos de forma vetorizada
    df_filtrado['saldo_em_processo'] = (df_filtrado['pcp_qtd'] - df_filtrado['qtd_baixa']).clip(lower=0)
    df_filtrado['saldo_em_estoque'] = (df_filtrado['qtd_baixa'] - df_filtrado['qtd_retirada']).clip(lower=0)
    
    # Aplicar filtros
    if status:
        df_filtrado = df_filtrado[df_filtrado['status_baixa'].isin(status)]
    
    df_filtrado = Filtros.filtrar(df_filtrado, {'fluxo_producao': ('exato', tipo_produto)})
    
    # Formatar colunas numéricas de uma vez
    colunas_numericas = ['saldo_em_estoque', 'pcp_qtd', 'saldo_em_processo', 'qtd_retirada']
    for col in colunas_numericas:
        df_filtrado[col] = df_filtrado[col].apply(formatar_numero)
    
    df_filtrado['valor'] = df_filtrado['valor'].apply(lambda x: f'R$ {x:,.2f}'.replace(',', 'v').replace('.', ',').replace('v', '.') if pd.notna(x) else '')

    # Formatar datas de uma vez
    df_filtrado['pcp_entrega_formatada'] = df_filtrado['pcp_entrega'].dt.strftime('%d/%m/%Y').fillna('')
    df_filtrado['pcp_emissao_formatada'] = df_filtrado['pcp_emissao'].dt.strftime('%d/%m/%Y').fillna('')
    df_filtrado['pcp_primiera_entrega_formatada'] = df_filtrado['pcp_primiera_entrega'].dt.strftime('%d/%m/%Y').fillna('')
    
    # Ordenar
    df_filtrado = df_filtrado.sort_values(by='pcp_entrega', ascending=True).head(120)
    
    # Definir colunas do DataTable
    colunas_ordenadas = [
        {"name": nome, "id": col} for nome, col in [
            ("Indicadores", "icone_ordem_compra"),
            ("OC", "pcp_oc"), ("O.S", "pcp_pcp"), ("CATEGORIA", "pcp_categoria"),
            
            ("Valor", "valor"),
            ("Produto", "nome"),  ("QTD OP", "pcp_qtd"), 
            ("PROCESSO", "saldo_em_processo"), ("ESTOQUE", "saldo_em_estoque"), 
            ("RETIRADA", "qtd_retirada"), ("Status", "status_baixa"),
            ("Máquina", "ultima_maquina"),
            ("Data de Entrega", "pcp_entrega_formatada"), ("Sem 2", "pcp_semana"),
            ("CHAPA", "pcp_chapa_id"), ("PL", "planejamento_info"), 
            ("CÓD", "pcp_cod_prod"), ("CLIENTE", "cliente_nome"), 
            ("Data 1ª Entrega", "pcp_primiera_entrega_formatada"), 
            ("Sem 1", "pcp_semana_primeira"), ("Data de Emissão", "pcp_emissao_formatada"), 
            ("ID PCP", "pcp_id"),("ID", "pcp_produto_id") 
        ]
    ]
    
    # Configuração do DataTable
    hoje = datetime.now()
    tabela_pcp_df = dash_table.DataTable(
        id='tabela_pcp_cal',
        columns=colunas_ordenadas,
        data=df_filtrado.to_dict('records'),
        style_table={'height': '900px', 'overflowY': 'auto', 'border': '1px solid #ccc'},
        cell_selectable=True,
        page_size=40,
        style_header={'backgroundColor': '#02083d', 'fontWeight': 'bold', 'textAlign': 'center', 'padding': '10px'},
        style_cell={'textAlign': 'center', 'padding': '8px', 'fontSize': '14px', 'border': '1px solid #ddd'},
        style_header_conditional=[
            {'if': {'column_id': col}, 'backgroundColor': cor, 'color': 'white'} 
            for col, cor in [('pcp_qtd', '#1f77b4'), ('saldo_em_processo', '#ff7f0e'), 
                             ('saldo_em_estoque', '#2ca02c'), ('qtd_retirada', '#d62728')]
        ],
        style_data_conditional=[
            {'if': {'filter_query': '{pcp_entrega} >= "' + (hoje - timedelta(days=hoje.weekday())).strftime('%Y-%m-%d') + '" && {pcp_entrega} <= "' + (hoje + timedelta(days=(6 - hoje.weekday()))).strftime('%Y-%m-%d') + '"'},
             'backgroundColor': 'rgba(255, 255, 0, 0.3)', 'color': 'black'},
            {'if': {'filter_query': '{pcp_entrega} < "' + hoje.strftime('%Y-%m-%d') + '" && {status_baixa} != "FEITO"'},
             'backgroundColor': 'rgba(255, 0, 0, 0.1)', 'color': 'black'},
            {'if': {'column_id': 'status_baixa', 'filter_query': '{status_baixa} = "PENDENTE"'},
             'backgroundColor': 'rgb(255, 99, 71)', 'color': 'white'},
            {'if': {'column_id': 'status_baixa', 'filter_query': '{status_baixa} = "PARCIAL"'},
             'backgroundColor': 'rgb(255, 165, 0)', 'color': 'black'},
            {'if': {'column_id': 'status_baixa', 'filter_query': '{status_baixa} = "FEITO"'},
             'backgroundColor': 'rgb(34, 139, 34)', 'color': 'white'},
            {'if': {'column_id': 'planejamento_info', 'filter_query': '{planejamento_info} contains "✓"'},
             'color': 'green', 'fontWeight': 'bold'},
            {'if': {'column_id': 'icone_ordem_compra', 'filter_query': '{icone_ordem_compra} contains "✅"'},
             'backgroundColor': 'rgba(0, 255, 0, 0.2)', 'color': 'green'},
            {'if': {'column_id': 'icone_ordem_compra', 'filter_query': '{icone_ordem_compra} contains "❌"'},
             'backgroundColor': 'rgba(255, 0, 0, 0.2)', 'color': 'red'}
        ],
        #sort_action="native",
    )
    
    infos = calcular_totais_status(df_filtrado)
    return tabela_pcp_df, infos

def calcular_totais_status(df_filtrado):
    # Otimizar conversão de colunas numéricas
    colunas_soma = ["pcp_qtd", "saldo_em_processo", "saldo_em_estoque", "qtd_retirada"]
    df_filtrado[colunas_soma] = (
        df_filtrado[colunas_soma]
        .astype(str)
        .apply(lambda x: x.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
    )
    
    totais = {
        "QTD OP": (df_filtrado["pcp_qtd"].sum(), "blue"),
        "PROCESSO": (df_filtrado["saldo_em_processo"].sum(), "orange"),
        "ESTOQUE": (df_filtrado["saldo_em_estoque"].sum(), "green"),
        "RETIRADA": (df_filtrado["qtd_retirada"].sum(), "red")
    }
    
    cards = [
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H6(nome, className="card-title", style={'color': cor}),
                        html.P(f"{valor:,.0f}", className="card-text", style={'font-size': '20px', 'font-weight': 'bold'})
                    ]),
                    style={'text-align': 'center', 'height': '80px'}
                ),
                width=12
            ),
            className="mb-2"
        )
        for nome, (valor, cor) in totais.items()
    ]
    
    return html.Div([
        html.H5("RESUMO", style={'text-align': 'center', 'margin-bottom': '10px'}),
        *cards
    ], id="informacoes-personalizadas", style={'margin-top': '15px'})