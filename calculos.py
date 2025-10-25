from banco_dados.banco import *
from dash import dash_table
from datetime import datetime, timedelta
import pandas as pd
from dash import html
import dash_bootstrap_components as dbc
import json

class Filtros:
    @staticmethod
    def filtrar(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
        df_filtrado = df.copy()

        for coluna, filtro in filtros.items():
            if coluna in df_filtrado.columns and filtro is not None:
                tipo, valor = filtro

                # Ignora filtros com valor None ou string vazia (exceto para 'contem')
                if valor is None or (isinstance(valor, (str, list)) and not valor):
                    # Allow empty string for 'contem' if needed, otherwise skip
                    if tipo != 'contem' or valor is None: 
                       continue 

                try: # Add error handling for robustness
                    if tipo == 'contem' and isinstance(valor, str):
                        df_filtrado = df_filtrado[df_filtrado[coluna].astype(str).str.contains(valor, case=False, na=False)]
                    
                    elif tipo == 'multi' and isinstance(valor, list):
                        # No need for is not valor check here, already handled above
                        df_filtrado = df_filtrado[df_filtrado[coluna].isin(valor)]
                    
                    # --- New Filter Type: 'comparar_num' --- 
                    elif tipo == 'comparar_num' and isinstance(valor, tuple) and len(valor) == 2:
                        operador, num_valor = valor
                        allowed_ops = ['==', '>=', '<=', '>', '<']
                        if operador not in allowed_ops:
                            print(f"Warning: Operador de comparação inválido '{operador}' para a coluna '{coluna}'. Pulando filtro.")
                            continue
                        
                        if num_valor is None or str(num_valor).strip() == '':
                             print(f"Warning: Valor numérico inválido para comparação na coluna '{coluna}'. Pulando filtro.")
                             continue

                        # Convert column and value to numeric, handling errors
                        df_filtrado[coluna] = pd.to_numeric(df_filtrado[coluna], errors='coerce')
                        num_valor_numeric = pd.to_numeric(num_valor, errors='coerce')

                        if pd.isna(num_valor_numeric):
                            print(f"Warning: Não foi possível converter '{num_valor}' para número na coluna '{coluna}'. Pulando filtro.")
                            continue
                        
                        # Drop rows where column conversion failed before querying
                        df_filtrado = df_filtrado.dropna(subset=[coluna])

                        # Use query for dynamic comparison
                        # Note: Ensure column names don't have spaces or special chars for query
                        safe_coluna = f"`{coluna}`" # Backticks for safety if col name has spaces/special chars
                        query_str = f"{safe_coluna} {operador} @num_valor_numeric"
                        df_filtrado = df_filtrado.query(query_str, engine='python')
                    # --- End New Filter Type --- 
                    
                    else:  # Filtro exato (padrão)
                        # Attempt conversion for comparison if types might differ, e.g., int vs str
                        try:
                            col_type = df_filtrado[coluna].dtype
                            if pd.api.types.is_numeric_dtype(col_type):
                                valor_convertido = pd.to_numeric(valor, errors='ignore')
                            elif pd.api.types.is_string_dtype(col_type):
                                valor_convertido = str(valor)
                            else:
                                valor_convertido = valor # Use original value if type is unknown/mixed
                            
                            df_filtrado = df_filtrado[df_filtrado[coluna] == valor_convertido]
                        except Exception as e_conv:
                            print(f"Warning: Erro na comparação exata para coluna '{coluna}' com valor '{valor}': {e_conv}. Usando comparação direta.")
                            df_filtrado = df_filtrado[df_filtrado[coluna] == valor] # Fallback
                            
                except Exception as e:
                    print(f"Erro ao aplicar filtro na coluna '{coluna}' com tipo '{tipo}' e valor '{valor}': {e}")
                    # Decide whether to continue or stop based on the error
                    continue # Example: Skip this filter and continue with others
                    
        return df_filtrado
    
    @staticmethod
    def filtrar_datas(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
        df_filtrado = df.copy()
        
        for coluna, regras in filtros.items():
            if coluna in df_filtrado.columns and pd.api.types.is_datetime64_any_dtype(df_filtrado[coluna]):
                df_filtrado[coluna] = pd.to_datetime(df_filtrado[coluna], errors='coerce')

                # Se regras não for uma lista, transforma em lista para múltiplos filtros
                if not isinstance(regras, list):
                    regras = [regras]

                for tipo, valor in regras:
                    if tipo == 'acima':  # Filtrar datas acima de um valor
                        df_filtrado = df_filtrado[df_filtrado[coluna] >= pd.to_datetime(valor)]
                    elif tipo == 'abaixo':  # Filtrar datas abaixo de um valor
                        df_filtrado = df_filtrado[df_filtrado[coluna] <= pd.to_datetime(valor)]
                    elif tipo == 'entre' and isinstance(valor, tuple) and len(valor) == 2:  # Intervalo de datas
                        df_filtrado = df_filtrado[(df_filtrado[coluna] >= pd.to_datetime(valor[0])) & 
                                                  (df_filtrado[coluna] <= pd.to_datetime(valor[1]))]

        return df_filtrado

class Formulario:

   
    def store_intermediario(n_editar, n_new, is_open, store_intermedio, df, btn_enviar, id):
        
        store = df.to_dict()

        trigg_id = callback_context.triggered[0]['prop_id'].split('.')[0]
        first_call = True if callback_context.triggered[0]['value'] == None else False
       
        if first_call:
            return is_open, store_intermedio
        
        if trigg_id == btn_enviar:
   
            df_int = pd.DataFrame(store_intermedio)
            df_int = df_int[:-1]  # Remove última linha
            store_intermedio = df_int.to_dict()
            return not is_open, store_intermedio

        if n_editar:
            trigg_dict = json.loads(callback_context.triggered[0]['prop_id'].split('.')[0])
            n_id = trigg_dict['index']

            df_intermediario = pd.DataFrame(store_intermedio)
            df_completo = pd.DataFrame(store)

            valores = df_completo.loc[df_completo[id] == n_id].values.tolist()

            if valores:
                valores = valores[0] + [True]  # Adiciona um valor de controle (True)
            else:
                print("valores is empty!")
                valores = [None] * len(df_completo.columns) + [True]

            df_intermediario = df_intermediario[:-1]  # Remove última linha
            df_intermediario.loc[len(df_intermediario)] = valores
            store_intermedio = df_intermediario.to_dict()
          
            return not is_open, store_intermedio

        # Se nenhuma das condições anteriores for satisfeita, retorne um valor padrão
        return not is_open, store_intermedio


def formatar_data(val):
    if isinstance(val, pd.Timestamp):  # Verifica se o valor é um Timestamp
        return val.strftime('%d/%m/%Y')  # Converte para o formato desejado
    elif isinstance(val, str):  # Caso já seja uma string
        return datetime.strptime(val, '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y')
    return val  # Reto

def calcular_soma_qtd_baixa(pcp_pcp: int):
    with Session(engine) as session:
        soma_qtd = session.query(func.sum(BAIXA.qtd)).filter(BAIXA.pcp_id == pcp_pcp).scalar()
        return soma_qtd or 0
    
def formatar_numero(val):
    if val is not None:
        return '{:,.0f}'.format(val).replace(',', '.')  # Substitui vírgula por ponto
    return val

def calcular_soma_qtd_retirada(pcp_id: int):
    with Session(engine) as session:
        soma_qtd = session.query(func.sum(RETIRADA.ret_qtd)).filter(RETIRADA.ret_id_pcp == pcp_id).scalar()
        return soma_qtd or 0
#==================
def format_date(date_value, include_time=False):
    try:
        # Verificar se é do tipo pandas.Timestamp ou datetime
        if isinstance(date_value, (pd.Timestamp, datetime)):
            return date_value  # Retorna como está para manter datetime
        
        # Converter strings para datetime
        if isinstance(date_value, str):
            date_obj = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S') if " " in date_value else datetime.strptime(date_value, '%Y-%m-%d')
            return date_obj
        
        return None  # Caso não seja um formato esperado
    except Exception:
        return None  # Retorna None em caso de erro
    
def is_week_of_today(date):
    hoje = datetime.now()
    # Definir o início e o fim da semana atual
    inicio_semana = hoje - timedelta(days=hoje.weekday())  # Segunda-feira desta semana
    fim_semana = inicio_semana + timedelta(days=6)  # Domingo desta semana
    # Verificar se a data de entrega está dentro da semana
    return inicio_semana <= date <= fim_semana

def relatorio_tabela(df, status=None, semana=None):

    banco = Banco()
    df_produtos = banco.ler_tabela("produtos")


    # Converter colunas 'pcp_entrega' e 'pcp_emissao' para datetime para comparações corretas
    df_filtrado = df.copy()
    df_filtrado = df_filtrado.merge(df_produtos[['produto_id', 'nome', 'pedido_mensal', 'fluxo_producao']], 
                                         left_on='pcp_produto_id', 
                                         right_on='produto_id', 
                                         how='left')
    
    df_filtrado['pcp_entrega'] = pd.to_datetime(df_filtrado['pcp_entrega'], format='%Y-%m-%d', errors='coerce')
    df_filtrado['pcp_emissao'] = pd.to_datetime(df_filtrado['pcp_emissao'], format='%Y-%m-%d', errors='coerce')
    df_filtrado['pcp_primiera_entrega'] = pd.to_datetime(df_filtrado['pcp_primiera_entrega'], format='%Y-%m-%d', errors='coerce')

    df_filtrado['pcp_semana'] = df_filtrado['pcp_entrega'].dt.isocalendar().week
    df_filtrado['pcp_semana_primeira'] = df_filtrado['pcp_primiera_entrega'].dt.isocalendar().week



    if semana:
        df_filtrado = df_filtrado[df_filtrado['pcp_semana'] == semana]

    hoje = datetime.now()

    # Adicionar coluna 'qtd_baixa' com a soma das baixas por pcp_id
    df_filtrado['qtd_baixa'] = df_filtrado['pcp_id'].apply(calcular_soma_qtd_baixa)
    df_filtrado['qtd_retirada'] = df_filtrado['pcp_id'].apply(calcular_soma_qtd_retirada)

    # Calcular o status com base na comparação de 'qtd_baixa' e 'pcp_qtd'
    def calcular_status(row):
        if row['qtd_baixa'] == 0:
            return 'PENDENTE'
        elif row['qtd_baixa'] > 0 and row['qtd_baixa'] < 0.9 * row['pcp_qtd']:
            return 'PARCIAL'
        elif row['qtd_baixa'] >= 0.9 * row['pcp_qtd']:
            return 'FEITO'
        else:
            return 'PENDENTE'

    df_filtrado['status_baixa'] = df_filtrado.apply(calcular_status, axis=1)

    # Filtrar pelo status, se fornecido
    if status:
        df_filtrado = df_filtrado[df_filtrado['status_baixa'].isin(status)]

    df_filtrado['saldo_em_processo'] = (df_filtrado['pcp_qtd'] - df_filtrado['qtd_baixa']).clip(lower=0)
    df_filtrado['saldo_em_estoque'] = (df_filtrado['qtd_baixa'] - df_filtrado['qtd_retirada']).clip(lower=0)

    # Formatar as colunas 'qtd_baixa' e 'pcp_qtd' para exibição
    df_filtrado['saldo_em_estoque'] = df_filtrado['saldo_em_estoque'].apply(formatar_numero)
    df_filtrado['pcp_qtd'] = df_filtrado['pcp_qtd'].apply(formatar_numero)
    df_filtrado['saldo_em_processo'] = df_filtrado['saldo_em_processo'].apply(formatar_numero)
    df_filtrado['qtd_retirada'] = df_filtrado['qtd_retirada'].apply(formatar_numero)

    # Criar colunas formatadas para exibição no DataTable
    df_filtrado['pcp_entrega_formatada'] = df_filtrado['pcp_entrega'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else '')
    df_filtrado['pcp_emissao_formatada'] = df_filtrado['pcp_emissao'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else '')
    df_filtrado['pcp_primiera_entrega'] = df_filtrado['pcp_primiera_entrega'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else '')
    # Ordenar as linhas com base em 'pcp_entrega'
    df_filtrado = df_filtrado.sort_values(by='pcp_entrega', ascending=True)
    

    
    return df_filtrado


def relatorio_planejamento(semana=None, comparacao_semana='=='):
    try:
        banco = Banco()
        df_plan = banco.ler_tabela('planejamento')
        df_pcp_full = listar_pcp()
        df_baixas = banco.ler_tabela('baixa')

        if df_plan.empty or df_pcp_full.empty:
            return pd.DataFrame()

        # Merge planejamento com PCP
        df_merged = pd.merge(
            df_plan,
            df_pcp_full, 
            left_on='id_pcp', 
            right_on='pcp_id', 
            how='left'
        )

        # Converter e processar datas
        df_merged['data_programacao'] = pd.to_datetime(df_merged['data_programacao'], errors='coerce')
        df_merged = df_merged.dropna(subset=['data_programacao'])
        
        # Adicionar semana ao DataFrame
        df_merged['semana_prog'] = df_merged['data_programacao'].dt.isocalendar().week.astype('Int64')
        
        # Filtrar por semana se especificado
        if semana is not None and comparacao_semana:
            df_merged = Filtros.filtrar(df_merged, {
                'semana_prog': ('comparar_num', (comparacao_semana, semana))
            })

        # Processar baixas
        if not df_baixas.empty:
            df_baixas['data'] = pd.to_datetime(df_baixas['data'], errors='coerce')
            df_merged['Qtd Feita'] = 0
            
            for idx, row in df_merged.iterrows():
                pcp_id = row['pcp_id']
                data_prog = row['data_programacao']
                
                baixas_pcp = df_baixas[
                    (df_baixas['pcp_id'] == pcp_id) & 
                    (df_baixas['data'].dt.isocalendar().week == data_prog.isocalendar().week) &
                    (df_baixas['data'].dt.year == data_prog.year)
                ]
                
                df_merged.at[idx, 'Qtd Feita'] = baixas_pcp['qtd'].sum()

        # Organizar e renomear colunas
        df_final = df_merged[[
            'data_programacao',
            'pcp_pcp',
            'pcp_categoria',
            'cliente_nome',
            'produto_nome',
            'quantidade',
            'Qtd Feita',
            'etiqueta',
            'observacao'
        ]].copy()

        df_final.rename(columns={
            'data_programacao': 'Data Programação',
            'pcp_pcp': 'PCP OS',
            'pcp_categoria': 'Categoria',
            'cliente_nome': 'Cliente',
            'produto_nome': 'Produto',
            'quantidade': 'Qtd Planejada',
            'etiqueta': 'Etiqueta',
            'observacao': 'Observação'
        }, inplace=True)

        # Ordenar por data e cliente
        df_final = df_final.sort_values(['Data Programação', 'Cliente'])
        
        # Formatar a data
        df_final['Data Programação'] = df_final['Data Programação'].dt.strftime('%d/%m/%Y')

        return df_final

    except Exception as e:
        print(f"Erro ao gerar relatório de planejamento: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


