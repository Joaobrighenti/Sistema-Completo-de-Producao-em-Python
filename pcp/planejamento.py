from dash import html, dcc, callback, Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import locale
import json
from dash.exceptions import PreventUpdate

from app import app
from banco_dados.banco import Banco, listar_pcp
from calculos import Filtros
from pcp.tabela_principal import obter_status_ordem_compra_em_lote

banco = Banco()

def calcular_totais_categoria(df_merged, semana=31, comparacao_semana='=='):
    try:
        # Aplicar filtro de semana primeiro
        if semana is not None and comparacao_semana:
            df_merged['semana_prog'] = df_merged['data_programacao'].dt.isocalendar().week.astype('Int64')
            df_filtered = Filtros.filtrar(df_merged.copy(), {
                'semana_prog': ('comparar_num', (comparacao_semana, semana))
            })
        else:
            df_filtered = df_merged

        if 'is_part' in df_filtered.columns:
            df_calculo = df_filtered[df_filtered['is_part'] == False].copy()
        else:
            df_calculo = df_filtered.copy()

        if df_calculo.empty:
            return []

        # Carregar dados de baixas uma única vez
        banco = Banco()
        df_baixas = banco.ler_tabela('baixa')
        
        # Preparar dados de baixas
        if not df_baixas.empty:
            df_baixas['data'] = pd.to_datetime(df_baixas['data'], errors='coerce')
            df_baixas['semana'] = df_baixas['data'].dt.isocalendar().week
            df_baixas['ano'] = df_baixas['data'].dt.year
            
            # Agrupar baixas por pcp_id, semana e ano
            baixas_agrupadas = df_baixas.groupby(['pcp_id', 'semana', 'ano'])['qtd'].sum().reset_index()
        else:
            baixas_agrupadas = pd.DataFrame(columns=['pcp_id', 'semana', 'ano', 'qtd'])

        # Calcular totais por categoria
        totais_por_categoria = []
        for categoria in df_calculo['pcp_categoria'].unique():
            plan_categoria = df_calculo[df_calculo['pcp_categoria'] == categoria].copy()
            qtd_programada = plan_categoria['quantidade'].sum()
            
            # --- LÓGICA DE CÁLCULO REFINADA ---
            if not baixas_agrupadas.empty:
                plan_categoria['semana_prog'] = plan_categoria['data_programacao'].dt.isocalendar().week
                plan_categoria['ano_prog'] = plan_categoria['data_programacao'].dt.year

                merged_baixas = pd.merge(
                    plan_categoria[['pcp_id', 'semana_prog', 'ano_prog']],
                    baixas_agrupadas.rename(columns={'semana': 'semana_prog', 'ano': 'ano_prog'}),
                    on=['pcp_id', 'semana_prog', 'ano_prog'],
                    how='left'
                )
                qtd_feita = merged_baixas['qtd'].sum()
            else:
                qtd_feita = 0
            
            totais_por_categoria.append({
                'categoria': categoria,
                'programado': qtd_programada,
                'feito': qtd_feita
            })

        # Criar cards de forma otimizada
        return [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H5(total['categoria'], className="card-title m-0", style={
                            'color': '#333', 
                            'fontSize': '0.8rem',
                            'fontWeight': 'bold',
                        }),
                        html.P([
                            html.Span(f"{total['programado']:,.0f}".replace(",", "."), style={'color': '#007bff'}),
                            html.Span(" | ", style={'color': '#ccc'}),
                            html.Br(),
                            html.Span(f"{total['feito']:,.0f}".replace(",", "."), style={'color': '#28a745'})
                        ], className="card-text m-0", style={
                            'fontSize': '1rem',
                            'fontWeight': 'bold',
                        })
                    ],
                    style={'padding': '0.5rem'}),
                    style={
                        'textAlign': 'center',
                        'border': '1px solid #e0e0e0',
                        'borderRadius': '4px',
                        'boxShadow': '0 2px 4px rgba(0,0,0,0.05)',
                        'backgroundColor': '#f8f9fa'
                    }
                ),
                xs=6, sm=4, md=3, lg=1,
                style={'padding': '0.25rem'}
            )
            for total in totais_por_categoria
        ]
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []

def calcular_totais_setor(df_planejamento, df_setores):
    try:
        if df_planejamento.empty:
            return []

        # Prepare lookups
        setores_info = {
            row['setor_id']: {'nome': row['setor_nome'], 'setups': 0, 'unidades': 0}
            for _, row in df_setores.iterrows()
        }
        setor_id_to_tipo_plano = df_setores.set_index('setor_id')['tipo_plano'].to_dict()
        setor_id_to_set_padrao = df_setores.set_index('setor_id')['set_padrao'].to_dict()
        
        # Get unique planning entries
        df_unique_plans = df_planejamento.drop_duplicates(subset=['plan_id'])

        # Group 1: Plans with saved JSON data
        df_com_json = df_unique_plans.dropna(subset=['plano_setor_dict'])
        df_com_json = df_com_json[df_com_json['plano_setor_dict'].apply(lambda d: isinstance(d, dict) and bool(d))]

        for _, row in df_com_json.iterrows():
            plano_setor = row['plano_setor_dict']
            for part_name, sector_values in plano_setor.items():
                if isinstance(sector_values, dict):
                    for sector_id_str, quantity in sector_values.items():
                        try:
                            sector_id, qty_val = int(sector_id_str), int(quantity or 0)
                            if sector_id in setores_info and qty_val > 0:
                                setores_info[sector_id]['setups'] += 1
                                setores_info[sector_id]['unidades'] += qty_val
                        except (ValueError, TypeError):
                            continue

        # Group 2: Plans WITHOUT saved JSON data (use default calculation)
        df_sem_json = df_unique_plans[~df_unique_plans['plan_id'].isin(df_com_json['plan_id'])]
        df_sem_json = df_sem_json[df_sem_json['is_part'] == False] # Only calculate defaults for parent items

        for _, row in df_sem_json.iterrows():
            partes_dict = json.loads(row['pap_parte']) if isinstance(row['pap_parte'], str) else row.get('pap_parte')
            if not isinstance(partes_dict, dict):
                continue
            
            for parte_nome, multiplicador in partes_dict.items():
                for sector_id in setores_info.keys():
                    if setor_id_to_set_padrao.get(sector_id) != 2:
                        tipo_plano = setor_id_to_tipo_plano.get(sector_id)
                        parent_qty = row.get('quantidade', 0)
                        
                        default_value = 0
                        if tipo_plano == 2: # Unidade
                            default_value = parent_qty
                        elif tipo_plano == 1: # Plano
                            default_value = parent_qty // multiplicador if multiplicador > 0 else 0
                        
                        if default_value > 0:
                            setores_info[sector_id]['setups'] += 1
                            setores_info[sector_id]['unidades'] += default_value
        
        # Filter and create cards
        active_sectors = [info for info in setores_info.values() if info['unidades'] > 0]
        return [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.H5(sector['nome'], className="card-title m-0", style={
                            'color': '#333', 'fontSize': '0.8rem', 'fontWeight': 'bold'
                        }),
                        html.P([
                            html.Span(f"Setups: {sector['setups']}", style={'color': '#dc3545'}),
                            html.Span(" | ", style={'color': '#ccc'}),
                            html.Span(f"Unid: {sector['unidades']:,.0f}".replace(",", "."), style={'color': '#17a2b8'})
                        ], className="card-text m-0", style={'fontSize': '1rem', 'fontWeight': 'bold'})
                    ], style={'padding': '0.5rem'}),
                    style={'textAlign': 'center', 'border': '1px solid #e0e0e0', 'borderRadius': '4px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.05)', 'backgroundColor': '#f8f9fa'}
                ),
                xs=6, sm=4, md=3, lg=2, style={'padding': '0.25rem'}
            )
            for sector in active_sectors
        ]
    except Exception as e:
        import traceback
        traceback.print_exc()
        return []

def planejamento(semana=None, comparacao_semana='==', mostrar_partes='sim'):
    if semana is None:
        semana = 33
    try:
        # Configuração inicial
        locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
        dias_semana = {
            0: 'Segunda-feira', 1: 'Terça-feira', 2: 'Quarta-feira',
            3: 'Quinta-feira', 4: 'Sexta-feira', 5: 'Sábado', 6: 'Domingo'
        }

        # Carregar dados uma única vez
        banco = Banco()
        df_plan = banco.ler_tabela('planejamento')
        df_pcp_full = listar_pcp()
        df_baixas = banco.ler_tabela('baixa')
        df_setores = banco.ler_tabela('setor') # Carregar setores

        # Defina a ordem desejada dos setores aqui.
        # Os nomes devem corresponder aos nomes na tabela 'setor'.
        # Setores não listados aqui aparecerão no final, em ordem alfabética.
        ordem_setores_desejada = [
            "IMP - IMPRESSÃO",
            "LAM - LAMINAÇÃO",
            "ACP - ACOPLAMENTO",
            "CVI - CORTE VINCO",
            "CDC - COLADEIRA DE CARTUCHO",
            "FOR - FORMAÇÃO",
            "PEC - POTE E COPO",
            "TRA - TRANSFORMAÇÃO",
            "PIZ - PIZZA",
        ]

        # Garante que a coluna setor_nome existe antes de prosseguir
        if 'setor_nome' in df_setores.columns:
            # Cria uma categoria para ordenação. Usa o índice da lista para os setores definidos,
            # e um valor alto para os demais, para que fiquem no final.
            df_setores['nome_upper'] = df_setores['setor_nome'].str.upper()
            df_setores['ordem_customizada'] = df_setores['nome_upper'].apply(
                lambda x: ordem_setores_desejada.index(x) if x in ordem_setores_desejada else float('inf')
            )

            # Ordena pela ordem customizada e depois pelo nome, para garantir uma ordem estável para os não listados.
            df_setores = df_setores.sort_values(
                by=['ordem_customizada', 'setor_nome'],
                ascending=[True, True]
            ).drop(columns=['ordem_customizada', 'nome_upper'])
        
        df_partes = banco.ler_tabela('partes_produto') # Carregar dados das partes
        df_produtos = banco.ler_tabela('produtos') # Carregar dados dos produtos

        # Create dictionaries for quick lookups
        setor_id_to_tipo_plano = df_setores.set_index('setor_id')['tipo_plano'].to_dict()
        setor_id_to_set_padrao = df_setores.set_index('setor_id')['set_padrao'].to_dict()

        if df_plan.empty or df_pcp_full.empty:
            return dbc.Alert("Não há dados de planejamento para exibir.", color="warning")

        # Merge otimizado
        df_merged = pd.merge(
            df_plan,
            df_pcp_full, 
            left_on='id_pcp', 
            right_on='pcp_id', 
            how='left'
        )
        
        # Adicionar o pap_id e pap_parte ao df_merged
        df_merged = pd.merge(df_merged, df_produtos[['produto_id', 'pap_id']], left_on='pcp_produto_id', right_on='produto_id', how='left')
        
        # Corrigir tipos de dados para o merge
        df_merged['pap_id'] = pd.to_numeric(df_merged['pap_id'], errors='coerce').astype('Int64')
        df_partes['pap_id'] = pd.to_numeric(df_partes['pap_id'], errors='coerce').astype('Int64')
        
        df_merged = pd.merge(df_merged, df_partes[['pap_id', 'pap_parte']], on='pap_id', how='left')


        # Processamento de datas
        df_merged['data_programacao'] = pd.to_datetime(df_merged['data_programacao'], errors='coerce')
        df_merged = df_merged.dropna(subset=['data_programacao'])
        df_merged = df_merged.sort_values(by='data_programacao', ascending=True)

        # >>> NOVA LÓGICA DE EXPANSÃO DE PRODUTOS COM PARTES <<<
        if mostrar_partes == 'sim':
            expanded_rows = []
            for _, row in df_merged.iterrows():
                # Adiciona a linha principal (pai) primeiro
                parent_row = row.copy()
                parent_row['is_part'] = False  # Flag para identificar a linha pai
                expanded_rows.append(parent_row)

                # Verifica se há partes para criar as linhas filhas
                if 'pap_parte' in row and pd.notna(row['pap_parte']) and row['pap_parte']:
                    try:
                        # Carregar o JSON. Se já for um dict, usa direto.
                        partes_dict = json.loads(row['pap_parte']) if isinstance(row['pap_parte'], str) else row['pap_parte']
                        
                        if isinstance(partes_dict, dict):
                            for parte_nome, multiplicador in partes_dict.items():
                                new_row = row.copy()
                                new_row['is_part'] = True  # Flag para identificar a linha filha
                                new_row['produto_nome'] = parte_nome
                                new_row['part_multiplier'] = multiplicador
                                expanded_rows.append(new_row)
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            df_merged = pd.DataFrame(expanded_rows).reset_index(drop=True)
        else:
            # If not showing parts, just mark all rows as not parts and remove part data
            df_merged['is_part'] = False
            df_merged = df_merged.drop_duplicates(subset=['plan_id']).copy()


        # Filtro por semana
        df_display_filtered = df_merged.copy()
        if semana is not None and comparacao_semana:
            df_display_filtered['semana_prog'] = df_display_filtered['data_programacao'].dt.isocalendar().week.astype('Int64')
            df_display_filtered = Filtros.filtrar(df_display_filtered, {
                'semana_prog': ('comparar_num', (comparacao_semana, semana))
            })
            df_display_filtered = df_display_filtered.drop(columns=['semana_prog'])

        # Processamento de baixas otimizado
        if not df_baixas.empty:
            df_baixas['data'] = pd.to_datetime(df_baixas['data'], errors='coerce')
            df_baixas['semana'] = df_baixas['data'].dt.isocalendar().week
            df_baixas['ano'] = df_baixas['data'].dt.year
            
            # Agrupar baixas por pcp_id, semana e ano
            baixas_agrupadas = df_baixas.groupby(['pcp_id', 'semana', 'ano'])['qtd'].sum().reset_index()
            
            # Calcular Qtd Feita de forma vetorizada
            df_display_filtered['semana_prog'] = df_display_filtered['data_programacao'].dt.isocalendar().week
            df_display_filtered['ano_prog'] = df_display_filtered['data_programacao'].dt.year
            
            def calcular_qtd_feita(row):
                baixas_match = baixas_agrupadas[
                    (baixas_agrupadas['pcp_id'] == row['pcp_id']) &
                    (baixas_agrupadas['semana'] == row['semana_prog']) &
                    (baixas_agrupadas['ano'] == row['ano_prog'])
                ]
                return baixas_match['qtd'].sum()
            
            df_display_filtered['Qtd Feita'] = df_display_filtered.apply(calcular_qtd_feita, axis=1)
            df_display_filtered = df_display_filtered.drop(columns=['semana_prog', 'ano_prog'])
        else:
            df_display_filtered['Qtd Feita'] = 0

        # Processamento de indicadores
        pcp_ids = df_display_filtered['id_pcp'].unique().tolist()
        dict_status_oc = obter_status_ordem_compra_em_lote(pcp_ids)
        df_display_filtered['status_ordem_compra'] = df_display_filtered['id_pcp'].map(dict_status_oc).fillna("")

        # Parse 'plano_setor' JSON so it's ready for the rendering part
        def parse_plano_setor(json_str):
            if not json_str or pd.isna(json_str):
                return {}
            try:
                # If it's already a dict (from SQLAlchemy JSON type), just return it
                if isinstance(json_str, dict):
                    return json_str
                return json.loads(json_str)
            except (json.JSONDecodeError, TypeError):
                return {}
        
        if 'plano_setor' not in df_display_filtered.columns:
            df_display_filtered['plano_setor'] = pd.Series([None] * len(df_display_filtered))
        df_display_filtered['plano_setor'] = df_display_filtered['plano_setor'].astype(object)
        df_display_filtered['plano_setor_dict'] = df_display_filtered['plano_setor'].apply(parse_plano_setor)

        def criar_icone_ordem_compra(row):
            indicadores = []
            if pd.notna(row['status_ordem_compra']) and row['status_ordem_compra'] != "":
                indicadores.append("🛒✅" if row['status_ordem_compra'] == "Entregue Total" else "🛒❌")
            
            if any(row[col] == 1 or row[col] is True for col in ['pcp_tercereizacao', 'pcp_tercerizacao', 'pcp_terceirizacao'] if col in row):
                indicadores.append("🚚")
            
            if 'pcp_bopp' in row and (row['pcp_bopp'] == 1 or row['pcp_bopp'] is True):
                indicadores.append("🔪")
            
            return " ".join(indicadores)

        df_display_filtered['Indicadores'] = df_display_filtered.apply(criar_icone_ordem_compra, axis=1)

        # Preparar dados para exibição
        colunas_display = [
            'plan_id', 'id_pcp', 'pcp_pcp', 'pcp_categoria', 'cliente_nome', 
            'produto_nome', 'pcp_qtd', 'quantidade', 'Qtd Feita', 
            'data_programacao', 'Indicadores', 'observacao', 'plano_setor_dict', 'is_part'
        ]
        if mostrar_partes == 'sim':
            colunas_display.append('part_multiplier')
        
        df_display = df_display_filtered[colunas_display].copy()
        df_display['Data Prog. Formatada'] = df_display['data_programacao'].dt.strftime('%d/%m/%Y')
        
        # Renomear colunas
        mapeamento_colunas = {
            'plan_id': 'ID Plan', 'id_pcp': 'ID PCP', 'pcp_pcp': 'PCP OS', 
            'pcp_categoria': 'Categoria', 'cliente_nome': 'Cliente', 
            'produto_nome': 'Produto', 'pcp_qtd': 'Qtd Total OP', 
            'quantidade': 'Qtd Planejada', 'Data Prog. Formatada': 'Data Prog.',
            'observacao': 'Obs. Plan.'
        }
        df_display.rename(columns=mapeamento_colunas, inplace=True)

        # Agrupar por dia da semana e ordenar
        df_display['Dia da Semana'] = df_display['data_programacao'].dt.dayofweek.map(dias_semana)
        df_display['ordem_dia'] = df_display['data_programacao'].dt.dayofweek
        df_display = df_display.sort_values(by=['ordem_dia', 'Categoria', 'data_programacao', 'ID Plan', 'is_part'])

        # Colunas estáticas
        colunas_estaticas = ['PCP OS', 'Produto', 'Qtd Total OP', 'Qtd Planejada', 'Qtd Feita', 'Data Prog.', 'Indicadores']
        
        # Colunas dinâmicas de setor (só se mostrar_partes for 'sim')
        if mostrar_partes == 'sim':
            setores_nomes = {row['setor_id']: row['setor_nome'][:3].upper() for _, row in df_setores.iterrows()}
            setor_name_to_id = {v: k for k, v in setores_nomes.items()} # Reverse mapping
            colunas_setor = list(setores_nomes.values())
            colunas_tabela = colunas_estaticas + colunas_setor + ['Obs. Plan.'] + ['Aprovar']
        else:
            colunas_setor = []
            setor_name_to_id = {}
            colunas_tabela = colunas_estaticas

        # Criar indicadores de categoria
        indicadores_categoria = dbc.Row(
            dbc.Col(
                dbc.Row(
                    calcular_totais_categoria(df_merged, semana, comparacao_semana),
                    className="g-0",
                    style={
                        'justify-content': 'flex-start',
                        'align-items': 'center',
                        'margin': '4px 0',
                        'padding': '4px 0',
                        'background': 'transparent'
                    }
                ),
                width=12,
                style={'overflow-x': 'hidden'}
            )
        )

        # Criar indicadores de setor (só se mostrar_partes for 'sim')
        indicadores_setor = dbc.Row() # Default to empty row
        if mostrar_partes == 'sim':
            indicadores_setor = dbc.Row(
                dbc.Col(
                    dbc.Row(
                        calcular_totais_setor(df_display_filtered, df_setores),
                        className="g-0",
                        style={
                            'justify-content': 'flex-start',
                            'align-items': 'center',
                            'margin': '4px 0',
                            'padding': '4px 0',
                            'background': 'transparent'
                        }
                    ),
                    width=12,
                    style={'overflow-x': 'hidden'}
                )
            )

        # Criar blocos por dia de forma otimizada
        blocos_por_dia = []
        for i in range(7):
            dia = dias_semana[i]
            grupo = df_display[df_display['ordem_dia'] == i]

            if grupo.empty:
                continue

            # A ordenação agora é feita antes do loop de dias
            grupo_ordenado = grupo

            # Gerar dados para a tabela, mantendo todos os dicionários necessários para a renderização
            table_data = grupo_ordenado.to_dict('records')
            
            # Create table header
            header_cells = []
            for col in colunas_tabela:
                header_style = {'textAlign': 'center'}
                if col in colunas_setor:
                    header_style['width'] = '85px' # Narrower width for sector columns
                    header_style['fontSize'] = '0.8rem' # Smaller font for the header
                header_cells.append(html.Th(col, style=header_style))
            header = html.Thead(html.Tr(header_cells))
            
            # Create table body
            body_rows = []
            for row in table_data:
                cells = []
                is_part_row = row.get('is_part', False)
                row_style = {'backgroundColor': 'rgba(0, 0, 0, 0.03)'} if is_part_row else {}

                for col_name in colunas_tabela:
                    style = {'verticalAlign': 'middle'}
                    cell_value = row.get(col_name, "")
                    
                    if is_part_row:
                        # For part rows
                        if col_name in colunas_estaticas:
                            if col_name == 'Produto':
                                cell_value = f"↳ {cell_value}"
                                style['textAlign'] = 'left'
                                style['paddingLeft'] = '2rem'
                            elif col_name == 'Qtd Planejada':
                                cell_value = "" # Keep this cell blank for parts
                            else:
                                cell_value = "" # Make other static cells blank
                        
                        elif col_name in colunas_setor:
                            plan_id = row.get('ID Plan')
                            part_name = row.get('Produto')
                            sector_id = setor_name_to_id.get(col_name)

                            # 1. Get the user-saved value first
                            plano_setor_dict = row.get('plano_setor_dict', {})
                            part_plans = plano_setor_dict.get(part_name, {}) if isinstance(plano_setor_dict, dict) else {}
                            final_value = part_plans.get(str(sector_id)) if isinstance(part_plans, dict) else None

                            # 2. If no value is saved, calculate the default based on business logic
                            if final_value is None or final_value == '':
                                set_padrao = setor_id_to_set_padrao.get(sector_id)
                                
                                # Only calculate a default value if the sector is not marked as non-standard (set_padrao != 2)
                                if set_padrao != 2:
                                    tipo_plano = setor_id_to_tipo_plano.get(sector_id)
                                    parent_planned_qty = row.get('Qtd Planejada', 0) # This now correctly holds the parent's planned qty
                                    part_multiplier = row.get('part_multiplier', 1)

                                    if tipo_plano == 2: # Unidade
                                        final_value = parent_planned_qty
                                    elif tipo_plano == 1: # Plano
                                        final_value = parent_planned_qty // part_multiplier if part_multiplier > 0 else 0
                                    else:
                                        final_value = '' # Default to empty if no tipo_plano
                                else:
                                    final_value = '' # If set_padrao is 2, it's not a default sector, so leave it empty.
                            
                            if final_value is None: final_value = ''

                            cell_value = dcc.Input(
                                id={'type': 'plan-part-input', 'plan_id': plan_id, 'part': part_name, 'sector_id': sector_id},
                                type='number',
                                value=final_value,
                                style={'width': '100%', 'textAlign': 'center', 'border': 'none', 'backgroundColor': 'transparent', 'MozAppearance': 'textfield'},
                                className='no-arrows'
                            )

                        elif col_name == 'Aprovar':
                            cell_value = dbc.Button(
                                "✔", 
                                id={'type': 'approve-part-btn', 'plan_id': row.get('ID Plan'), 'part': row.get('Produto')}, 
                                color="success", 
                                outline=True,
                                style={'padding': '0.1rem 0.4rem', 'fontSize': '0.7rem', 'lineHeight': '1.2'}
                            )

                    else: # This is a parent row
                        if col_name == 'Aprovar':
                            cell_value = html.Div() # Make the parent row's 'Approve' cell empty
                            
                        if col_name == 'Qtd Planejada':
                            cell_value = f"{row.get('Qtd Planejada', 0):,.0f}".replace(",",".")
                            
                        style['fontWeight'] = 'bold'
                        if col_name == 'Aprovar': style['fontWeight'] = 'normal'
                        if col_name == 'Qtd Feita': style['color'] = '#28a745'
                        if col_name == 'Indicadores' and isinstance(cell_value, str):
                            if "✅" in cell_value: style['backgroundColor'] = 'rgba(40, 167, 69, 0.2)'
                            elif "❌" in cell_value: style['backgroundColor'] = 'rgba(220, 53, 69, 0.2)'

                    cells.append(html.Td(cell_value, style=style))
                body_rows.append(html.Tr(cells, style=row_style))
            
            body = html.Tbody(body_rows)

            bloco = html.Div([
                html.H5(dia, style={
                    'backgroundColor': '#e9ecef',
                    'padding': '10px',
                    'marginTop': '20px',
                    'border': '1px solid #ccc'
                }),
                dbc.Table(
                    [header, body],
                    bordered=True,
                    striped=True,
                    hover=True,
                    responsive=True,
                    style={'fontSize': '13px', 'textAlign': 'center'},
                    className="align-middle"
                )
            ])
            blocos_por_dia.append(bloco)

        return dbc.Container([
            dcc.Location(id='dummy-location-for-refresh'), # Adicionado para forçar refresh

            indicadores_categoria,
            indicadores_setor,
        ] + blocos_por_dia, fluid=True)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"Erro ao carregar dados de planejamento: {e}", color="danger")

@app.callback(
    Output({'type': 'approve-part-btn', 'plan_id': MATCH, 'part': MATCH}, 'color'),
    Input({'type': 'approve-part-btn', 'plan_id': MATCH, 'part': MATCH}, 'n_clicks'),
    State({'type': 'plan-part-input', 'plan_id': MATCH, 'part': ALL, 'sector_id': ALL}, 'value'),
    State({'type': 'plan-part-input', 'plan_id': MATCH, 'part': ALL, 'sector_id': ALL}, 'id'),
    State({'type': 'approve-part-btn', 'plan_id': MATCH, 'part': MATCH}, 'id'),
    prevent_initial_call=True
)
def save_part_planning(n_clicks, all_values, all_ids, button_id):
    if not n_clicks:
        raise PreventUpdate

    plan_id = button_id['plan_id']
    
    # 1. Build a new data dictionary from scratch based on current input values.
    new_data = {}
    for i, input_id in enumerate(all_ids):
        # The MATCH in the State selector should already scope this, but a safety check is good.
        if input_id['plan_id'] == plan_id:
            part_name = input_id['part']
            sector_id = str(input_id['sector_id'])
            value = all_values[i]

            # Only add to the new data if there's a value.
            if value is not None and value != '':
                # Ensure the nested structure exists
                if part_name not in new_data:
                    new_data[part_name] = {}
                
                new_data[part_name][sector_id] = value
    
    # 2. Write the new, complete data structure back to DB, overwriting the old one.
    banco.editar_dado('planejamento', plan_id, plano_setor=json.dumps(new_data))

    # 3. Provide feedback by changing button color
    return "success"