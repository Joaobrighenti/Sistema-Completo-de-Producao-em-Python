from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import datetime
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from banco_dados.banco import engine, PCP, PRODUTO, CLIENTE, BAIXA, RETIRADA, VALOR_PRODUTO, Base, ORDEM_COMPRA, FORNECEDORES
from sqlalchemy import func, or_
from pcp.tabela_principal import obter_dados_em_lote
from app import app
import io
from dash.exceptions import PreventUpdate

def calculate_payment_schedule(base_date, total_value, prazo_str):
    """
    Calculates the payment schedule based on a prazo string (e.g., '0,15,30').
    Returns a dictionary of {date: value}.
    Adjusts for weekends, moving payments to the next Monday.
    """
    if pd.isna(total_value) or total_value == 0:
        return {}
    
    # Default to 'at sight' (0 days) if prazo is not provided
    prazo_str = prazo_str if prazo_str and pd.notna(prazo_str) else '0'

    try:
        days_diffs = [int(p.strip()) for p in prazo_str.split(',')]
        num_installments = len(days_diffs)
        if num_installments == 0:
            return {}
        
        # Use precise division and distribute remainder to the first installment
        base_installment = total_value / num_installments
        schedule = {}
        
        # Calculate schedule based on precise values
        for days in days_diffs:
            due_date = base_date + datetime.timedelta(days=days)
            # Adjust for weekends
            if due_date.weekday() == 5: # Saturday
                due_date += datetime.timedelta(days=2)
            elif due_date.weekday() == 6: # Sunday
                due_date += datetime.timedelta(days=1)
            
            schedule[due_date] = schedule.get(due_date, 0) + base_installment
            
        return schedule
    except (ValueError, AttributeError):
        # Return as a single payment on the base date if prazo is invalid
        return {base_date: total_value}

def format_currency(value):
    """Formats a float into a Brazilian currency string."""
    if pd.isna(value):
        value = 0
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_daily_headers(num_weeks=9):
    """Generates headers for a daily DRE view over several weeks."""
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=today.isoweekday() - 1)

    week_header_data = []
    day_headers_content = []
    target_days = []

    for i in range(num_weeks):
        week_start_date = start_date + datetime.timedelta(weeks=i)
        iso_week = week_start_date.isocalendar()[1]
        week_header_data.append({'name': f"Semana {iso_week}", 'colspan': 7})

        for d in range(7):
            current_day = week_start_date + datetime.timedelta(days=d)
            target_days.append(current_day)
            day_name = current_day.strftime("%a")
            day_headers_content.append(html.Div([day_name, html.Br(), current_day.strftime('%d/%m')]))
    
    return week_header_data, day_headers_content, target_days

def get_dre_entradas_data(view_mode: str):
    """
    Calculates the 'Entradas' values for the DRE dashboard, with a daily client breakdown.
    """
    with Session(engine) as session:
        _, _, target_days = get_daily_headers()
        start_date = target_days[0]
        num_days = len(target_days)

        # Get latest product values
        latest_value_subq = session.query(
            VALOR_PRODUTO.produto_id,
            func.max(VALOR_PRODUTO.data).label('max_data')
        ).group_by(VALOR_PRODUTO.produto_id).subquery()

        latest_values_q = session.query(
            VALOR_PRODUTO.id,
            VALOR_PRODUTO.produto_id,
            VALOR_PRODUTO.valor,
            VALOR_PRODUTO.data
        ).join(
            latest_value_subq,
            (VALOR_PRODUTO.produto_id == latest_value_subq.c.produto_id) &
            (VALOR_PRODUTO.data == latest_value_subq.c.max_data)
        )
        
        df_valores_raw = pd.read_sql(latest_values_q.statement, session.bind)
        df_valores = df_valores_raw.sort_values('id', ascending=False).drop_duplicates(subset='produto_id').set_index('produto_id')


        # Get ALL PCP data for 'Puxado' products, now with client name
        pcp_data_q = session.query(
            PCP.pcp_id,
            PCP.pcp_produto_id,
            PCP.pcp_qtd,
            PCP.pcp_entrega,
            CLIENTE.nome.label('cliente_nome'),
            CLIENTE.cli_prazo,
            CLIENTE.cli_forma_pagamento
        ).join(PRODUTO, PCP.pcp_produto_id == PRODUTO.produto_id)\
         .join(CLIENTE, PCP.pcp_cliente_id == CLIENTE.cliente_id)\
         .filter(
            PRODUTO.fluxo_producao == 'Puxado',
            PCP.pcp_correncia.is_(None)
        )
        df_pcp = pd.read_sql(pcp_data_q.statement, session.bind)

        if df_pcp.empty:
            zeros = {"totals": ["R$ 0,00"] * (num_days + 1), "by_client": {}}
            return {"pedidos_firmados": zeros, "estoque_pedidos": zeros}

        pcp_ids = df_pcp['pcp_id'].tolist()

        # Get Baixas and Retiradas
        baixas_q = session.query(BAIXA.pcp_id, func.sum(BAIXA.qtd).label('qtd_baixa'))\
            .filter(BAIXA.pcp_id.in_(pcp_ids)).group_by(BAIXA.pcp_id)
        df_baixas = pd.read_sql(baixas_q.statement, session.bind).set_index('pcp_id')

        retiradas_q = session.query(RETIRADA.ret_id_pcp, func.sum(RETIRADA.ret_qtd).label('qtd_retirada'))\
            .filter(RETIRADA.ret_id_pcp.in_(pcp_ids)).group_by(RETIRADA.ret_id_pcp)
        df_retiradas = pd.read_sql(retiradas_q.statement, session.bind).set_index('ret_id_pcp')
        
        # Map data and perform calculations
        df_pcp['qtd_baixa'] = df_pcp['pcp_id'].map(df_baixas['qtd_baixa']).fillna(0)
        df_pcp['qtd_retirada'] = df_pcp['pcp_id'].map(df_retiradas['qtd_retirada']).fillna(0)
        
        df_pcp['saldo_em_processo'] = (df_pcp['pcp_qtd'] - df_pcp['qtd_baixa']).clip(lower=0)
        df_pcp['saldo_em_estoque'] = (df_pcp['qtd_baixa'] - df_pcp['qtd_retirada']).clip(lower=0)

        valores_dict = df_valores['valor'].to_dict()

        df_pcp['valor_unitario'] = df_pcp['pcp_produto_id'].map(valores_dict).fillna(0)
        df_pcp['valor_total_processo'] = df_pcp['saldo_em_processo'] * df_pcp['valor_unitario']
        df_pcp['valor_total_estoque'] = df_pcp['saldo_em_estoque'] * df_pcp['valor_unitario']
        
        df_pcp['pcp_entrega_date'] = pd.to_datetime(df_pcp['pcp_entrega']).dt.date

        # --- Calculate Totals and By Client ---

        # Initialize dictionaries to hold the final processed data
        by_client_proc = {}
        by_client_est = {}

        if view_mode == 'fluxo_caixa':
            # Processo (Pedidos Firmados) - Cash Flow
            daily_proc_total = {day: 0 for day in target_days}
            for _, row in df_pcp.iterrows():
                schedule = calculate_payment_schedule(row['pcp_entrega_date'], row['valor_total_processo'], row['cli_prazo'])
                for p_date, p_value in schedule.items():
                    if p_date in daily_proc_total:
                        daily_proc_total[p_date] += p_value
            
            final_values_proc = [daily_proc_total.get(day, 0) for day in target_days]
            # No accumulated value for cash flow view
            all_values_proc = [format_currency(v) for v in [0] + final_values_proc]

            for client_name, df_client in df_pcp.groupby('cliente_nome'):
                daily_client_total = {day: 0 for day in target_days}
                raw_forma_pgto = df_client['cli_forma_pagamento'].iloc[0] if not df_client.empty else None
                client_form_pg = raw_forma_pgto if pd.notna(raw_forma_pgto) and raw_forma_pgto else 'à vista'
                raw_prazo = df_client['cli_prazo'].iloc[0] if not df_client.empty else None
                client_prazo = raw_prazo if pd.notna(raw_prazo) and raw_prazo else '0'

                for _, row in df_client.iterrows():
                    schedule = calculate_payment_schedule(row['pcp_entrega_date'], row['valor_total_processo'], row['cli_prazo'])
                    for p_date, p_value in schedule.items():
                        if p_date in daily_client_total:
                            daily_client_total[p_date] += p_value
                
                final_values_client = [daily_client_total.get(day, 0) for day in target_days]
                if sum(final_values_client) > 0:
                     by_client_proc[client_name] = {
                        "values": [format_currency(v) for v in [0] + final_values_client],
                        "forma_pgto": client_form_pg,
                        "prazo": client_prazo
                    }

            # Estoque (Estoque Pedidos) - Cash Flow (Similar to Processo)
            daily_est_total = {day: 0 for day in target_days}
            for _, row in df_pcp.iterrows():
                schedule = calculate_payment_schedule(row['pcp_entrega_date'], row['valor_total_estoque'], row['cli_prazo'])
                for p_date, p_value in schedule.items():
                    if p_date in daily_est_total:
                        daily_est_total[p_date] += p_value
            
            final_values_est = [daily_est_total.get(day, 0) for day in target_days]
            all_values_est = [format_currency(v) for v in [0] + final_values_est]
            
            for client_name, df_client in df_pcp.groupby('cliente_nome'):
                daily_client_total = {day: 0 for day in target_days}
                raw_forma_pgto = df_client['cli_forma_pagamento'].iloc[0] if not df_client.empty else None
                client_form_pg = raw_forma_pgto if pd.notna(raw_forma_pgto) and raw_forma_pgto else 'à vista'
                raw_prazo = df_client['cli_prazo'].iloc[0] if not df_client.empty else None
                client_prazo = raw_prazo if pd.notna(raw_prazo) and raw_prazo else '0'

                for _, row in df_client.iterrows():
                    schedule = calculate_payment_schedule(row['pcp_entrega_date'], row['valor_total_estoque'], row['cli_prazo'])
                    for p_date, p_value in schedule.items():
                        if p_date in daily_client_total:
                            daily_client_total[p_date] += p_value

                final_values_client = [daily_client_total.get(day, 0) for day in target_days]
                if sum(final_values_client) > 0:
                    by_client_est[client_name] = {
                        "values": [format_currency(v) for v in [0] + final_values_client],
                        "forma_pgto": client_form_pg,
                        "prazo": client_prazo
                    }

        else: # Competencia View
            # Processo (Pedidos Firmados)
            df_past_proc = df_pcp[df_pcp['pcp_entrega_date'] < start_date]
            acumulado_proc_total = df_past_proc['valor_total_processo'].sum()
            df_future_proc = df_pcp[df_pcp['pcp_entrega_date'] >= start_date]
            daily_proc_total = df_future_proc.groupby('pcp_entrega_date')['valor_total_processo'].sum().to_dict()
            final_values_proc = [daily_proc_total.get(day, 0) for day in target_days]
            all_values_proc = [format_currency(v) for v in [acumulado_proc_total] + final_values_proc]

            for client_name, df_client in df_pcp.groupby('cliente_nome'):
                raw_forma_pgto = df_client['cli_forma_pagamento'].iloc[0] if not df_client.empty else None
                client_form_pg = raw_forma_pgto if pd.notna(raw_forma_pgto) and raw_forma_pgto else 'à vista'
                raw_prazo = df_client['cli_prazo'].iloc[0] if not df_client.empty else None
                client_prazo = raw_prazo if pd.notna(raw_prazo) and raw_prazo else '0'
                df_past_client = df_client[df_client['pcp_entrega_date'] < start_date]
                acumulado_client = df_past_client['valor_total_processo'].sum()
                df_future_client = df_client[df_client['pcp_entrega_date'] >= start_date]
                daily_client = df_future_client.groupby('pcp_entrega_date')['valor_total_processo'].sum().to_dict()
                final_values_client = [daily_client.get(day, 0) for day in target_days]
                
                if (acumulado_client + sum(final_values_client)) > 0:
                    by_client_proc[client_name] = {
                        "values": [format_currency(v) for v in [acumulado_client] + final_values_client],
                        "forma_pgto": client_form_pg,
                        "prazo": client_prazo
                    }

            # Estoque (Estoque Pedidos)
            df_past_est = df_pcp[df_pcp['pcp_entrega_date'] < start_date]
            acumulado_est_total = df_past_est['valor_total_estoque'].sum()
            df_future_est = df_pcp[df_pcp['pcp_entrega_date'] >= start_date]
            daily_est_total = df_future_est.groupby('pcp_entrega_date')['valor_total_estoque'].sum().to_dict()
            final_values_est = [daily_est_total.get(day, 0) for day in target_days]
            all_values_est = [format_currency(v) for v in [acumulado_est_total] + final_values_est]

            for client_name, df_client in df_pcp.groupby('cliente_nome'):
                raw_forma_pgto = df_client['cli_forma_pagamento'].iloc[0] if not df_client.empty else None
                client_form_pg = raw_forma_pgto if pd.notna(raw_forma_pgto) and raw_forma_pgto else 'à vista'
                raw_prazo = df_client['cli_prazo'].iloc[0] if not df_client.empty else None
                client_prazo = raw_prazo if pd.notna(raw_prazo) and raw_prazo else '0'
                df_past_client = df_client[df_client['pcp_entrega_date'] < start_date]
                acumulado_client = df_past_client['valor_total_estoque'].sum()
                df_future_client = df_client[df_client['pcp_entrega_date'] >= start_date]
                daily_client = df_future_client.groupby('pcp_entrega_date')['valor_total_estoque'].sum().to_dict()
                final_values_client = [daily_client.get(day, 0) for day in target_days]
                
                if (acumulado_client + sum(final_values_client)) > 0:
                    by_client_est[client_name] = {
                        "values": [format_currency(v) for v in [acumulado_client] + final_values_client],
                        "forma_pgto": client_form_pg,
                        "prazo": client_prazo
                    }

        return {
            "pedidos_firmados": {"totals": all_values_proc, "by_client": by_client_proc},
            "estoque_pedidos": {"totals": all_values_est, "by_client": by_client_est}
        }


def get_empurrado_data(dia_entrega_is_none: bool, view_mode: str):
    """
    Calculates projected values for products with 'Empurrado' flow for a daily view,
    with a breakdown by client.
    """
    with Session(engine) as session:
        _, _, target_days = get_daily_headers()
        num_days = len(target_days)

        # 1. Get latest product values
        latest_value_subq = session.query(
            VALOR_PRODUTO.produto_id,
            func.max(VALOR_PRODUTO.data).label('max_data')
        ).group_by(VALOR_PRODUTO.produto_id).subquery()

        latest_values_q = session.query(
            VALOR_PRODUTO.id,
            VALOR_PRODUTO.produto_id,
            VALOR_PRODUTO.valor
        ).join(
            latest_value_subq,
            (VALOR_PRODUTO.produto_id == latest_value_subq.c.produto_id) &
            (VALOR_PRODUTO.data == latest_value_subq.c.max_data)
        )
        df_valores_raw = pd.read_sql(latest_values_q.statement, session.bind)
        df_valores = df_valores_raw.sort_values('id', ascending=False).drop_duplicates(subset='produto_id').set_index('produto_id')

        # 2. Get unique client-product associations for 'Empurrado' products
        subq = session.query(
            PCP.pcp_cliente_id,
            PCP.pcp_produto_id
        ).join(PRODUTO, PCP.pcp_produto_id == PRODUTO.produto_id)\
         .filter(PRODUTO.fluxo_producao == 'Empurrado')\
         .distinct().subquery()

        product_q = session.query(
            CLIENTE.nome.label('cliente_nome'),
            PRODUTO.produto_id,
            PRODUTO.pedido_mensal,
            PRODUTO.tipo_trabalho,
            PRODUTO.dia_entrega,
            CLIENTE.cli_forma_pagamento,
            CLIENTE.cli_prazo
        ).join(subq, CLIENTE.cliente_id == subq.c.pcp_cliente_id)\
         .join(PRODUTO, PRODUTO.produto_id == subq.c.pcp_produto_id)

        # 3. Apply dia_entrega filter
        if dia_entrega_is_none:
            product_q = product_q.filter(or_(PRODUTO.dia_entrega.is_(None), PRODUTO.dia_entrega == 0))
        else:
            product_q = product_q.filter(PRODUTO.dia_entrega.isnot(None), PRODUTO.dia_entrega != 0)

        df_produtos = pd.read_sql(product_q.statement, session.bind)
        
        if df_produtos.empty:
            zeros = ["R$ 0,00"] * (num_days + 1)
            return {"totals": zeros, "by_client": {}}

        # 4. Calculate weekly values
        df_produtos['valor_unitario'] = df_produtos['produto_id'].map(df_valores['valor']).fillna(0)
        df_produtos['base_value'] = df_produtos['pedido_mensal'] * df_produtos['valor_unitario']
        
        conditions = [
            df_produtos['tipo_trabalho'] == 'Semanal',
            df_produtos['tipo_trabalho'] == 'Quinzenal',
        ]
        choices = [
            df_produtos['base_value'],
            df_produtos['base_value'] / 2,
        ]
        df_produtos['weekly_value'] = np.select(conditions, choices, default=df_produtos['base_value'] / 4)

        # 5. Group by client and aggregate
        client_weekly_values = df_produtos.groupby('cliente_nome')['weekly_value'].sum()
        client_info = df_produtos.drop_duplicates(subset=['cliente_nome']).set_index('cliente_nome')
        
        by_client = {}
        for client_name, total_weekly_value in client_weekly_values.items():
            daily_value = total_weekly_value / 7
            formatted_value = format_currency(daily_value)
            final_values = [formatted_value] * num_days
            all_values = [format_currency(0)] + final_values

            info_row = client_info.loc[client_name]
            raw_forma_pgto = info_row['cli_forma_pagamento']
            client_form_pg = raw_forma_pgto if pd.notna(raw_forma_pgto) and raw_forma_pgto else 'à vista'
            raw_prazo = info_row['cli_prazo']
            client_prazo = raw_prazo if pd.notna(raw_prazo) and raw_prazo else '0'

            by_client[client_name] = {
                "values": all_values,
                "forma_pgto": client_form_pg,
                "prazo": client_prazo
            }
        
        # 6. Calculate grand totals
        total_weekly_value = df_produtos['weekly_value'].sum()
        daily_value = total_weekly_value / 7
        formatted_value = format_currency(daily_value)
        final_values = [formatted_value] * num_days
        all_values_total = [format_currency(0)] + final_values

        return {"totals": all_values_total, "by_client": by_client}


def get_compras_data(view_mode: str):
    """
    Calculates the 'Compras' values for the DRE dashboard with a daily breakdown.
    """
    with Session(engine) as session:
        _, _, target_days = get_daily_headers()
        start_date = target_days[0]
        num_days = len(target_days)

        compras_q = session.query(
            ORDEM_COMPRA.oc_valor_unit,
            ORDEM_COMPRA.oc_qtd_solicitada,
            ORDEM_COMPRA.oc_data_entrega,
            FORNECEDORES.for_nome,
            FORNECEDORES.for_prazo,
            FORNECEDORES.for_forma_pagamento
        ).join(FORNECEDORES, ORDEM_COMPRA.oc_fornecedor_id == FORNECEDORES.for_id)\
         .filter(
            ORDEM_COMPRA.oc_status == 'Aguardando Recebimento',
            ORDEM_COMPRA.oc_data_entrega.isnot(None)
        )
        df_compras = pd.read_sql(compras_q.statement, session.bind)

        if df_compras.empty:
            zeros = ["R$ 0,00"] * (num_days + 1)
            return {"totals": zeros, "by_supplier": {}}
            
        df_compras['oc_valor_unit'] = pd.to_numeric(df_compras['oc_valor_unit'], errors='coerce').fillna(0)
        df_compras['oc_qtd_solicitada'] = pd.to_numeric(df_compras['oc_qtd_solicitada'], errors='coerce').fillna(0)
        
        df_compras['valor_total'] = df_compras['oc_valor_unit'] * df_compras['oc_qtd_solicitada']
        df_compras['oc_data_entrega_date'] = pd.to_datetime(df_compras['oc_data_entrega']).dt.date

        # --- Calculate by Supplier and Totals ---
        by_supplier = {}
        
        if view_mode == 'fluxo_caixa':
            daily_totals = {day: 0 for day in target_days}
            for _, row in df_compras.iterrows():
                # For cash flow, we ignore accumulated past values
                schedule = calculate_payment_schedule(row['oc_data_entrega_date'], row['valor_total'], row['for_prazo'])
                for p_date, p_value in schedule.items():
                    if p_date in daily_totals:
                        daily_totals[p_date] += p_value
            
            final_values_total = [daily_totals.get(day, 0) for day in target_days]
            all_values_total = [format_currency(v) for v in [0] + final_values_total]

            for supplier_name, df_supplier in df_compras.groupby('for_nome'):
                daily_supplier_total = {day: 0 for day in target_days}
                raw_forma_pgto = df_supplier['for_forma_pagamento'].iloc[0] if not df_supplier.empty else None
                supplier_forma_pgto = raw_forma_pgto if pd.notna(raw_forma_pgto) and raw_forma_pgto else 'à vista'
                raw_prazo = df_supplier['for_prazo'].iloc[0] if not df_supplier.empty else None
                supplier_prazo = str(raw_prazo) if pd.notna(raw_prazo) and raw_prazo is not None else '0'

                for _, row in df_supplier.iterrows():
                    schedule = calculate_payment_schedule(row['oc_data_entrega_date'], row['valor_total'], row['for_prazo'])
                    for p_date, p_value in schedule.items():
                        if p_date in daily_supplier_total:
                            daily_supplier_total[p_date] += p_value
                
                final_values_supplier = [daily_supplier_total.get(day, 0) for day in target_days]
                if sum(final_values_supplier) > 0:
                    by_supplier[supplier_name] = {
                        "values": [format_currency(v) for v in [0] + final_values_supplier],
                        "forma_pgto": supplier_forma_pgto,
                        "prazo": supplier_prazo
                    }
        else: # Competencia view
            # --- Calculate Totals ---
            df_past_total = df_compras[df_compras['oc_data_entrega_date'] < start_date]
            acumulado_total = df_past_total['valor_total'].sum()

            df_future_total = df_compras[df_compras['oc_data_entrega_date'] >= start_date]
            daily_totals_dict = df_future_total.groupby('oc_data_entrega_date')['valor_total'].sum().to_dict()
            final_values_total = [daily_totals_dict.get(day, 0) for day in target_days]
            all_values_total = [format_currency(v) for v in [acumulado_total] + final_values_total]

            # --- Calculate by Supplier ---
            for supplier_name, df_supplier in df_compras.groupby('for_nome'):
                raw_forma_pgto = df_supplier['for_forma_pagamento'].iloc[0] if not df_supplier.empty else None
                supplier_forma_pgto = raw_forma_pgto if pd.notna(raw_forma_pgto) and raw_forma_pgto else 'à vista'
                raw_prazo = df_supplier['for_prazo'].iloc[0] if not df_supplier.empty else None
                supplier_prazo = str(raw_prazo) if pd.notna(raw_prazo) and raw_prazo is not None else '0'
                df_past_supplier = df_supplier[df_supplier['oc_data_entrega_date'] < start_date]
                acumulado_supplier = df_past_supplier['valor_total'].sum()

                df_future_supplier = df_supplier[df_supplier['oc_data_entrega_date'] >= start_date]
                daily_supplier_dict = df_future_supplier.groupby('oc_data_entrega_date')['valor_total'].sum().to_dict()
                
                final_values_supplier = [daily_supplier_dict.get(day, 0) for day in target_days]
                
                if (acumulado_supplier + sum(final_values_supplier)) > 0:
                    all_values_supplier = [format_currency(v) for v in [acumulado_supplier] + final_values_supplier]
                    by_supplier[supplier_name] = {
                        "values": all_values_supplier,
                        "forma_pgto": supplier_forma_pgto,
                        "prazo": supplier_prazo
                    }
        
        return {"totals": all_values_total, "by_supplier": by_supplier}

def parse_currency(value_str: str) -> float:
    """Converts a formatted currency string back to a float."""
    if not isinstance(value_str, str):
        return 0.0
    try:
        cleaned_str = value_str.replace("R$ ", "").replace(".", "").replace(",", ".")
        return float(cleaned_str)
    except (ValueError, AttributeError):
        return 0.0


def create_data_table(data):
    """Creates the main data table for the DRE dashboard."""
    week_header_info, day_headers, _ = get_daily_headers()
    num_columns = 2 + len(day_headers)
    num_value_columns = 1 + len(day_headers)

    # Cell styles for better width management
    desc_style = {'minWidth': '300px'}
    acum_style = {'minWidth': '140px'}
    day_style = {'minWidth': '130px'}
    forma_pgto_style = {'minWidth': '150px'}
    prazo_pgto_style = {'minWidth': '120px'}

    # Unpack data for Entradas
    pedidos_firmados_data = data.get("pedidos_firmados", {})
    pedidos_firmados_totals = pedidos_firmados_data.get("totals", ["R$ 0,00"] * num_value_columns)
    pedidos_firmados_by_client = pedidos_firmados_data.get("by_client", {})

    estoque_pedidos_data = data.get("estoque_pedidos", {})
    estoque_pedidos_totals = estoque_pedidos_data.get("totals", ["R$ 0,00"] * num_value_columns)
    estoque_pedidos_by_client = estoque_pedidos_data.get("by_client", {})

    retirada_franquias_data = data.get("retirada_franquias", {})
    retirada_franquias_totals = retirada_franquias_data.get("totals", ["R$ 0,00"] * num_value_columns)
    retirada_franquias_by_client = retirada_franquias_data.get("by_client", {})

    retirada_estoque_data = data.get("retirada_estoque", {})
    retirada_estoque_totals = retirada_estoque_data.get("totals", ["R$ 0,00"] * num_value_columns)
    retirada_estoque_by_client = retirada_estoque_data.get("by_client", {})


    header_row_1 = [
        html.Th("Descrição", rowSpan=2, className="text-center align-middle", style=desc_style),
        html.Th("Forma Pgto", rowSpan=2, className="text-center align-middle", style=forma_pgto_style),
        html.Th("Prazo Pgto", rowSpan=2, className="text-center align-middle", style=prazo_pgto_style),
        html.Th("Acumulado", rowSpan=2, className="text-center align-middle", style=acum_style)
    ]
    for week_info in week_header_info:
        header_row_1.append(html.Th(week_info['name'], colSpan=week_info['colspan'], className="text-center"))

    header_row_2 = [html.Th(day_header, className="text-center", style=day_style) for day_header in day_headers]
    
    table_header = [html.Thead([html.Tr(header_row_1), html.Tr(header_row_2)], className="table-dark")]
    
    # "Entradas" row
    entradas_row = html.Tr(
        html.Td(
            "Entradas",
            colSpan=num_columns,
            className="text-center text-white fw-bold",
            style={'backgroundColor': '#28a745'}
        )
    )

    # Pedidos Firmados collapsible section
    pedidos_firmados_header = html.Tr([
        html.Td(html.Div([
            html.I(className="fa fa-chevron-right me-2", id="pedidos-firmados-icon"),
            "Pedidos Firmados"
        ], id='pedidos-firmados-toggle', style={'cursor': 'pointer', 'fontWeight': 'bold'}), style=desc_style),
        html.Td("", style=forma_pgto_style),
        html.Td("", style=prazo_pgto_style)
    ] + [html.Td(val, className="text-end", style=acum_style if i == 0 else day_style) for i, val in enumerate(pedidos_firmados_totals)])
    
    pedidos_firmados_details = html.Tbody([
        html.Tr([
            html.Td(f"  \u2023 {client}", style={'paddingLeft': '30px', **desc_style}),
            html.Td(details.get('forma_pgto', ''), style=forma_pgto_style),
            html.Td(details.get('prazo', ''), style=prazo_pgto_style),
        ] + [html.Td(val, className="text-end", style=acum_style if i == 0 else day_style) for i, val in enumerate(details.get("values", []))])
        for client, details in pedidos_firmados_by_client.items()
    ], id='pedidos-firmados-details-tbody', style={'display': 'none'})

    # Estoque Pedidos collapsible section
    estoque_pedidos_header = html.Tr([
        html.Td(html.Div([
            html.I(className="fa fa-chevron-right me-2", id="estoque-pedidos-icon"),
            "Estoque Pedidos"
        ], id='estoque-pedidos-toggle', style={'cursor': 'pointer', 'fontWeight': 'bold'}), style=desc_style),
        html.Td("", style=forma_pgto_style),
        html.Td("", style=prazo_pgto_style)
    ] + [html.Td(val, className="text-end", style=acum_style if i == 0 else day_style) for i, val in enumerate(estoque_pedidos_totals)])

    estoque_pedidos_details = html.Tbody([
        html.Tr([
            html.Td(f"  \u2023 {client}", style={'paddingLeft': '30px', **desc_style}),
            html.Td(details.get('forma_pgto', ''), style=forma_pgto_style),
            html.Td(details.get('prazo', ''), style=prazo_pgto_style),
        ] + [html.Td(val, className="text-end", style=acum_style if i == 0 else day_style) for i, val in enumerate(details.get("values", []))])
        for client, details in estoque_pedidos_by_client.items()
    ], id='estoque-pedidos-details-tbody', style={'display': 'none'})

    # Other Entradas rows
    retirada_franquias_header = html.Tr([
        html.Td(html.Div([
            html.I(className="fa fa-chevron-right me-2", id="retirada-franquias-icon"),
            "Retirada de Franquias"
        ], id='retirada-franquias-toggle', style={'cursor': 'pointer', 'fontWeight': 'bold'}), style=desc_style),
        html.Td("", style=forma_pgto_style),
        html.Td("", style=prazo_pgto_style)
    ] + [html.Td(val, className="text-end", style=acum_style if i == 0 else day_style) for i, val in enumerate(retirada_franquias_totals)])

    retirada_franquias_details = html.Tbody([
        html.Tr([
            html.Td(f"  \u2023 {client}", style={'paddingLeft': '30px', **desc_style}),
            html.Td(details.get('forma_pgto', ''), style=forma_pgto_style),
            html.Td(details.get('prazo', ''), style=prazo_pgto_style),
        ] + [html.Td(val, className="text-end", style=acum_style if i == 0 else day_style) for i, val in enumerate(details.get("values", []))])
        for client, details in retirada_franquias_by_client.items()
    ], id='retirada-franquias-details-tbody', style={'display': 'none'})

    retirada_estoque_header = html.Tr([
        html.Td(html.Div([
            html.I(className="fa fa-chevron-right me-2", id="retirada-estoque-icon"),
            "Retirada de Estoque"
        ], id='retirada-estoque-toggle', style={'cursor': 'pointer', 'fontWeight': 'bold'}), style=desc_style),
        html.Td("", style=forma_pgto_style),
        html.Td("", style=prazo_pgto_style)
    ] + [html.Td(val, className="text-end", style=acum_style if i == 0 else day_style) for i, val in enumerate(retirada_estoque_totals)])

    retirada_estoque_details = html.Tbody([
        html.Tr([
            html.Td(f"  \u2023 {client}", style={'paddingLeft': '30px', **desc_style}),
            html.Td(details.get('forma_pgto', ''), style=forma_pgto_style),
            html.Td(details.get('prazo', ''), style=prazo_pgto_style),
        ] + [html.Td(val, className="text-end", style=acum_style if i == 0 else day_style) for i, val in enumerate(details.get("values", []))])
        for client, details in retirada_estoque_by_client.items()
    ], id='retirada-estoque-details-tbody', style={'display': 'none'})


    # Calculate Total Entradas
    entradas_rows_for_sum = {
        "Pedidos Firmados": pedidos_firmados_totals,
        "Estoque Pedidos": estoque_pedidos_totals,
        "Retirada de Franquias": retirada_franquias_totals,
        "Retirada de Estoque": retirada_estoque_totals,
    }
    total_entradas_values = [0.0] * num_value_columns
    for row_values in entradas_rows_for_sum.values():
        for i, value_str in enumerate(row_values):
            total_entradas_values[i] += parse_currency(value_str)

    formatted_totals = [format_currency(v) for v in total_entradas_values]

    # Total row for Entradas
    total_entradas_row = html.Tr(
        [
            html.Td("Total Entradas", className="fw-bold", style={'backgroundColor': '#ffc107', **desc_style}),
            html.Td("", style={'backgroundColor': '#ffc107', **forma_pgto_style}),
            html.Td("", style={'backgroundColor': '#ffc107', **prazo_pgto_style}),
        ] + [
            html.Td(val, className="text-end fw-bold", style={'backgroundColor': '#ffc107', **(acum_style if i == 0 else day_style)}) 
            for i, val in enumerate(formatted_totals)
        ]
    )

    # "Saídas" row
    saidas_row = html.Tr(
        html.Td(
            "Saídas",
            colSpan=num_columns,
            className="text-center text-white fw-bold",
            style={'backgroundColor': '#dc3545'}
        )
    )

    # Compras section with manual collapse
    compras_data = data.get("compras", {"totals": [], "by_supplier": {}})
    compras_total_values = compras_data.get("totals", ["R$ 0,00"] * num_value_columns)
    compras_by_supplier = compras_data.get("by_supplier", {})

    compras_header_row = html.Tr([
        html.Td(
            html.Div([
                html.I(className="fa fa-chevron-right me-2", id="compras-details-icon"),
                "Compras"
            ], id='compras-row-toggle', style={'cursor': 'pointer', 'fontWeight': 'bold'}),
            style=desc_style
        ),
        html.Td("", style=forma_pgto_style),
        html.Td("", style=prazo_pgto_style)
    ] + [
        html.Td(val, className="text-end fw-bold", style=acum_style if i == 0 else day_style) for i, val in enumerate(compras_total_values)
    ])

    supplier_rows = [
        html.Tr([
            html.Td(f"  \u2023 {supplier_name}", style={'paddingLeft': '30px', **desc_style}),
            html.Td(details.get('forma_pgto', ''), style=forma_pgto_style),
            html.Td(details.get('prazo', ''), style=prazo_pgto_style),
        ] + [
            html.Td(val, className="text-end", style=acum_style if i == 0 else day_style) for i, val in enumerate(details.get("values", []))
        ])
        for supplier_name, details in compras_by_supplier.items()
    ]
    
    compras_details_tbody = html.Tbody(supplier_rows, id='compras-details-tbody', style={'display': 'none'})
    
    table_body = [
        html.Tbody([entradas_row, pedidos_firmados_header]),
        pedidos_firmados_details,
        html.Tbody([estoque_pedidos_header]),
        estoque_pedidos_details,
        html.Tbody([retirada_franquias_header]),
        retirada_franquias_details,
        html.Tbody([retirada_estoque_header]),
        retirada_estoque_details,
        html.Tbody([total_entradas_row, saidas_row, compras_header_row]),
        compras_details_tbody
    ]
    
    table = dbc.Table(
        table_header + table_body,
        bordered=True,
        striped=True,
        hover=True,
        responsive=True,
        className="mt-4 shadow"
    )
    
    return table

def dre_data_to_excel(data):
    """Converts the DRE data dictionary into a formatted Excel file."""
    week_header_info, _, target_days = get_daily_headers()
    
    header_columns = ["Descrição", "Forma Pgto", "Prazo Pgto", "Acumulado"] + [d.strftime("%a %d/%m") for d in target_days]
    
    all_rows = []

    def add_row(title, values, forma_pgto="", prazo_pgto="", is_bold=False, is_total=False, indent=0):
        prefix = " " * indent
        row_data = {header_columns[i]: val for i, val in enumerate([f"{prefix}{title}", forma_pgto, prazo_pgto, *values])}
        all_rows.append(row_data)

    # --- ENTRADAS ---
    pedidos_firmados = data.get("pedidos_firmados", {})
    add_row("Pedidos Firmados", pedidos_firmados.get("totals", []), is_bold=True)
    for client, details in pedidos_firmados.get("by_client", {}).items():
        add_row(client, details.get("values", []), forma_pgto=details.get("forma_pgto", ""), prazo_pgto=details.get("prazo", ""), indent=4)

    estoque_pedidos = data.get("estoque_pedidos", {})
    add_row("Estoque Pedidos", estoque_pedidos.get("totals", []), is_bold=True)
    for client, details in estoque_pedidos.get("by_client", {}).items():
        add_row(client, details.get("values", []), forma_pgto=details.get("forma_pgto", ""), prazo_pgto=details.get("prazo", ""), indent=4)

    retirada_franquias = data.get("retirada_franquias", {})
    add_row("Retirada de Franquias", retirada_franquias.get("totals", []), is_bold=True)
    for client, details in retirada_franquias.get("by_client", {}).items():
        add_row(client, details.get("values", []), forma_pgto=details.get("forma_pgto", ""), prazo_pgto=details.get("prazo", ""), indent=4)

    retirada_estoque = data.get("retirada_estoque", {})
    add_row("Retirada de Estoque", retirada_estoque.get("totals", []), is_bold=True)
    for client, details in retirada_estoque.get("by_client", {}).items():
        add_row(client, details.get("values", []), forma_pgto=details.get("forma_pgto", ""), prazo_pgto=details.get("prazo", ""), indent=4)
    
    num_value_cols = len(header_columns) - 3
    entradas_rows_for_sum = {
        "Pedidos Firmados": data.get("pedidos_firmados", {}).get("totals", []),
        "Estoque Pedidos": data.get("estoque_pedidos", {}).get("totals", []),
        "Retirada de Franquias": data.get("retirada_franquias", {}).get("totals", []),
        "Retirada de Estoque": data.get("retirada_estoque", {}).get("totals", []),
    }
    total_entradas_values = [0.0] * num_value_cols
    for row_values in entradas_rows_for_sum.values():
        for i, value_str in enumerate(row_values):
            if i < num_value_cols:
                total_entradas_values[i] += parse_currency(value_str)

    add_row("Total Entradas", [format_currency(v) for v in total_entradas_values], is_bold=True, is_total=True)

    # --- SAÍDAS ---
    compras = data.get("compras", {})
    add_row("Compras", compras.get("totals", []), is_bold=True)
    for supplier, details in compras.get("by_supplier", {}).items():
        add_row(supplier, details.get("values", []), forma_pgto=details.get("forma_pgto", ""), prazo_pgto=details.get("prazo", ""), indent=4)
        
    df = pd.DataFrame(all_rows, columns=header_columns)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='DRE', startrow=2, header=False)
        workbook = writer.book
        worksheet = writer.sheets['DRE']

        merge_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'border': 1})

        worksheet.merge_range('A1:A2', 'Descrição', merge_format)
        worksheet.merge_range('B1:B2', 'Forma Pgto', merge_format)
        worksheet.merge_range('C1:C2', 'Prazo Pgto', merge_format)
        worksheet.merge_range('D1:D2', 'Acumulado', merge_format)
        
        col_idx = 4
        for week in week_header_info:
            end_col_idx = col_idx + week['colspan'] - 1
            if col_idx <= end_col_idx:
                 worksheet.merge_range(0, col_idx, 0, end_col_idx, week['name'], merge_format)
            col_idx = end_col_idx + 1

        for col_num, value in enumerate(df.columns[4:]):
            worksheet.write(1, col_num + 4, value, header_format)
            
        worksheet.set_column('A:A', 35)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:ZZ', 15)

    output.seek(0)
    return output

def get_raw_cash_flow_events():
    """
    Gathers and calculates all individual cash flow events from various sources,
    including the original delivery date that generated the payment.
    Only includes events from the report's start date onwards for a true cash flow projection.
    """
    events = []
    _, _, target_days = get_daily_headers()
    start_date = target_days[0] if target_days else datetime.date.today()

    with Session(engine) as session:
        # --- 1. Entradas from 'Puxado' products (Pedidos Firmados & Estoque) ---
        latest_value_subq = session.query(
            VALOR_PRODUTO.produto_id, func.max(VALOR_PRODUTO.data).label('max_data')
        ).group_by(VALOR_PRODUTO.produto_id).subquery()
        latest_values_q = session.query(
            VALOR_PRODUTO.id, VALOR_PRODUTO.produto_id, VALOR_PRODUTO.valor
        ).join(
            latest_value_subq,
            (VALOR_PRODUTO.produto_id == latest_value_subq.c.produto_id) & (VALOR_PRODUTO.data == latest_value_subq.c.max_data)
        )
        df_valores_raw = pd.read_sql(latest_values_q.statement, session.bind)
        df_valores = df_valores_raw.sort_values('id', ascending=False).drop_duplicates(subset='produto_id').set_index('produto_id')

        pcp_data_q = session.query(
            PCP.pcp_id, PCP.pcp_produto_id, PCP.pcp_qtd, PCP.pcp_entrega,
            CLIENTE.nome.label('cliente_nome'), CLIENTE.cli_prazo, CLIENTE.cli_forma_pagamento
        ).join(PRODUTO, PCP.pcp_produto_id == PRODUTO.produto_id)\
         .join(CLIENTE, PCP.pcp_cliente_id == CLIENTE.cliente_id)\
         .filter(PRODUTO.fluxo_producao == 'Puxado', PCP.pcp_correncia.is_(None))
        df_pcp = pd.read_sql(pcp_data_q.statement, session.bind)

        if not df_pcp.empty:
            pcp_ids = df_pcp['pcp_id'].tolist()
            baixas_q = session.query(BAIXA.pcp_id, func.sum(BAIXA.qtd).label('qtd_baixa'))\
                .filter(BAIXA.pcp_id.in_(pcp_ids)).group_by(BAIXA.pcp_id)
            df_baixas = pd.read_sql(baixas_q.statement, session.bind).set_index('pcp_id')
            retiradas_q = session.query(RETIRADA.ret_id_pcp, func.sum(RETIRADA.ret_qtd).label('qtd_retirada'))\
                .filter(RETIRADA.ret_id_pcp.in_(pcp_ids)).group_by(RETIRADA.ret_id_pcp)
            df_retiradas = pd.read_sql(retiradas_q.statement, session.bind).set_index('ret_id_pcp')

            df_pcp['qtd_baixa'] = df_pcp['pcp_id'].map(df_baixas['qtd_baixa']).fillna(0)
            df_pcp['qtd_retirada'] = df_pcp['pcp_id'].map(df_retiradas['qtd_retirada']).fillna(0)
            df_pcp['saldo_em_processo'] = (df_pcp['pcp_qtd'] - df_pcp['qtd_baixa']).clip(lower=0)
            df_pcp['saldo_em_estoque'] = (df_pcp['qtd_baixa'] - df_pcp['qtd_retirada']).clip(lower=0)
            df_pcp['valor_unitario'] = df_pcp['pcp_produto_id'].map(df_valores['valor']).fillna(0)
            df_pcp['valor_total_processo'] = df_pcp['saldo_em_processo'] * df_pcp['valor_unitario']
            df_pcp['valor_total_estoque'] = df_pcp['saldo_em_estoque'] * df_pcp['valor_unitario']
            df_pcp['pcp_entrega_date'] = pd.to_datetime(df_pcp['pcp_entrega']).dt.date

            for _, row in df_pcp.iterrows():
                if row['valor_total_processo'] > 0:
                    schedule = calculate_payment_schedule(row['pcp_entrega_date'], row['valor_total_processo'], row['cli_prazo'])
                    for p_date, p_value in schedule.items():
                        if p_value > 0 and p_date >= start_date:
                            events.append({
                                "Data": p_date, "Data Entrega": row['pcp_entrega_date'],
                                "Parceiro": row['cliente_nome'], "Tipo": "Pedido Firmado",
                                "Valor": p_value, "Forma de Pagamento": row['cli_forma_pagamento'] if pd.notna(row['cli_forma_pagamento']) else 'à vista'
                            })
                if row['valor_total_estoque'] > 0:
                    schedule = calculate_payment_schedule(row['pcp_entrega_date'], row['valor_total_estoque'], row['cli_prazo'])
                    for p_date, p_value in schedule.items():
                        if p_value > 0 and p_date >= start_date:
                            events.append({
                                "Data": p_date, "Data Entrega": row['pcp_entrega_date'],
                                "Parceiro": row['cliente_nome'], "Tipo": "Estoque Pedido",
                                "Valor": p_value, "Forma de Pagamento": row['cli_forma_pagamento'] if pd.notna(row['cli_forma_pagamento']) else 'à vista'
                            })

        # --- 2. Entradas from 'Empurrado' products ---
        for is_none in [True, False]:
            empurrado_q = session.query(
                CLIENTE.nome.label('cliente_nome'), PRODUTO.pedido_mensal, PRODUTO.tipo_trabalho,
                PRODUTO.produto_id, CLIENTE.cli_forma_pagamento, CLIENTE.cli_prazo
            ).join(PCP, PRODUTO.produto_id == PCP.pcp_produto_id)\
             .join(CLIENTE, PCP.pcp_cliente_id == CLIENTE.cliente_id)\
             .filter(PRODUTO.fluxo_producao == 'Empurrado').distinct()
            if is_none:
                empurrado_q = empurrado_q.filter(or_(PRODUTO.dia_entrega.is_(None), PRODUTO.dia_entrega == 0))
                tipo = "Retirada Franquia"
            else:
                empurrado_q = empurrado_q.filter(PRODUTO.dia_entrega.isnot(None), PRODUTO.dia_entrega != 0)
                tipo = "Retirada Estoque"
            df_empurrado = pd.read_sql(empurrado_q.statement, session.bind)
            if not df_empurrado.empty:
                df_empurrado['valor_unitario'] = df_empurrado['produto_id'].map(df_valores['valor']).fillna(0)
                df_empurrado['base_value'] = df_empurrado['pedido_mensal'] * df_empurrado['valor_unitario']
                conditions = [df_empurrado['tipo_trabalho'] == 'Semanal', df_empurrado['tipo_trabalho'] == 'Quinzenal']
                choices = [df_empurrado['base_value'], df_empurrado['base_value'] / 2]
                df_empurrado['weekly_value'] = np.select(conditions, choices, default=df_empurrado['base_value'] / 4)
                for _, row in df_empurrado.iterrows():
                    daily_value = row['weekly_value'] / 7
                    if daily_value > 0:
                        for day in target_days:
                            if day >= start_date:
                                events.append({
                                    "Data": day, "Data Entrega": None,
                                    "Parceiro": row['cliente_nome'], "Tipo": tipo,
                                    "Valor": daily_value, "Forma de Pagamento": row['cli_forma_pagamento'] if pd.notna(row['cli_forma_pagamento']) else 'à vista'
                                })

        # --- 3. Saídas - Compras ---
        compras_q = session.query(
            ORDEM_COMPRA.oc_valor_unit, ORDEM_COMPRA.oc_qtd_solicitada, ORDEM_COMPRA.oc_data_entrega,
            FORNECEDORES.for_nome, FORNECEDORES.for_prazo, FORNECEDORES.for_forma_pagamento
        ).join(FORNECEDORES, ORDEM_COMPRA.oc_fornecedor_id == FORNECEDORES.for_id)\
         .filter(ORDEM_COMPRA.oc_status == 'Aguardando Recebimento', ORDEM_COMPRA.oc_data_entrega.isnot(None))
        df_compras = pd.read_sql(compras_q.statement, session.bind)

        if not df_compras.empty:
            df_compras['oc_valor_unit'] = pd.to_numeric(df_compras['oc_valor_unit'], errors='coerce').fillna(0)
            df_compras['oc_qtd_solicitada'] = pd.to_numeric(df_compras['oc_qtd_solicitada'], errors='coerce').fillna(0)
            df_compras['valor_total'] = df_compras['oc_valor_unit'] * df_compras['oc_qtd_solicitada']
            df_compras['oc_data_entrega_date'] = pd.to_datetime(df_compras['oc_data_entrega']).dt.date

            for _, row in df_compras.iterrows():
                if row['valor_total'] > 0:
                    schedule = calculate_payment_schedule(row['oc_data_entrega_date'], row['valor_total'], row['for_prazo'])
                    for p_date, p_value in schedule.items():
                        if p_value > 0 and p_date >= start_date:
                            events.append({
                                "Data": p_date, "Data Entrega": row['oc_data_entrega_date'],
                                "Parceiro": row['for_nome'], "Tipo": "Compras",
                                "Valor": -p_value, "Forma de Pagamento": row['for_forma_pagamento'] if pd.notna(row['for_forma_pagamento']) else 'à vista'
                            })
                            
    return pd.DataFrame(events)

def cash_flow_to_excel(df_events):
    """Converts the cash flow events dataframe into a formatted Excel file."""
    if df_events.empty:
        df_events = pd.DataFrame([{
            "Data": "Sem dados", "Data Entrega": "", "Parceiro": "", 
            "Tipo": "", "Valor": 0, "Forma de Pagamento": ""
        }])

    # Define the column order explicitly
    column_order = ["Data", "Data Entrega", "Parceiro", "Tipo", "Valor", "Forma de Pagamento"]
    df_events = df_events.reindex(columns=column_order)

    df_events = df_events.sort_values(by="Data")
    
    # Format dates
    df_events['Data'] = pd.to_datetime(df_events['Data']).dt.strftime('%d/%m/%Y')
    # Format 'Data Entrega' only where it's not NaT
    df_events['Data Entrega'] = pd.to_datetime(df_events['Data Entrega'], errors='coerce').dt.strftime('%d/%m/%Y')
    df_events['Data Entrega'] = df_events['Data Entrega'].fillna('') # Replace NaT with empty string after formatting

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_events.to_excel(writer, index=False, sheet_name='Fluxo_de_Caixa')
        workbook = writer.book
        worksheet = writer.sheets['Fluxo_de_Caixa']

        # Formatting
        money_format = workbook.add_format({'num_format': 'R$ #,##0.00'})
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        
        worksheet.set_column('A:A', 12, date_format) # Data
        worksheet.set_column('B:B', 12, date_format) # Data Entrega
        worksheet.set_column('C:C', 35) # Parceiro
        worksheet.set_column('D:D', 20) # Tipo
        worksheet.set_column('E:E', 15, money_format) # Valor
        worksheet.set_column('F:F', 20) # Forma de Pagamento

    output.seek(0)
    return output


# --- Main Layout and Callbacks ---
# (The rest of the file remains largely the same)

initial_data = get_dre_entradas_data('competencia')
initial_data['retirada_franquias'] = get_empurrado_data(dia_entrega_is_none=True, view_mode='competencia')
initial_data['retirada_estoque'] = get_empurrado_data(dia_entrega_is_none=False, view_mode='competencia')
initial_data['compras'] = get_compras_data('competencia')

layout = dbc.Container([
    dcc.Store(id='dre-data-store', data=initial_data),
    dcc.Download(id="download-dre-excel"),
    dcc.Download(id="download-cashflow-excel"),
    dbc.Row([
        dbc.Col([
            html.H2(["Demonstrativo de Resultados Projetado "]),
        ], width='auto'),
        dbc.Col([
            dcc.Dropdown(
                id='dre-view-selector',
                options=[
                    {'label': 'Competência', 'value': 'competencia'},
                    {'label': 'Fluxo de Caixa', 'value': 'fluxo_caixa'}
                ],
                value='competencia',
                clearable=False,
                style={'width': '200px'}
            ),
        ], width='auto', className="ms-3"),
        dbc.Col([
            dbc.Button(html.I(className="fa fa-sync-alt"), id="refresh-dre-data", color="primary", className="ms-2"),
            dbc.Button(html.I(className="fa fa-file-excel"), id="export-dre-excel", color="success", className="ms-2"),
            dbc.Button("Exportar Fluxo de Caixa", id="export-cashflow-excel", color="info", className="ms-2")
        ], width='auto')
    ], align="center", justify="center", className="mb-4"),
    dbc.Row(html.Hr()),
    dbc.Row([
        dbc.Col(id='dre-table-container', children=create_data_table(initial_data))
    ])
], fluid=True, className="py-4")

@app.callback(
    Output('dre-data-store', 'data'),
    Input('dre-view-selector', 'value'),
    Input('refresh-dre-data', 'n_clicks'),
    prevent_initial_call=True
)
def update_dre_data(view_mode, n_clicks):
    # This will re-run the data fetching functions when the button is clicked or the view mode changes
    data = get_dre_entradas_data(view_mode)
    data['retirada_franquias'] = get_empurrado_data(dia_entrega_is_none=True, view_mode=view_mode)
    data['retirada_estoque'] = get_empurrado_data(dia_entrega_is_none=False, view_mode=view_mode)
    data['compras'] = get_compras_data(view_mode)
    return data

@app.callback(
    Output("download-cashflow-excel", "data"),
    Input("export-cashflow-excel", "n_clicks"),
    prevent_initial_call=True,
)
def export_cash_flow_excel(n_clicks):
    if not n_clicks:
        raise PreventUpdate
    
    df_events = get_raw_cash_flow_events()
    excel_file = cash_flow_to_excel(df_events)
    return dcc.send_bytes(excel_file.getvalue(), "Fluxo_de_Caixa_Detalhado.xlsx")

@app.callback(
    Output("download-dre-excel", "data"),
    Input("export-dre-excel", "n_clicks"),
    State("dre-data-store", "data"),
    prevent_initial_call=True,
)
def export_dre_to_excel(n_clicks, data):
    if not n_clicks:
        raise PreventUpdate
    
    excel_file = dre_data_to_excel(data)
    return dcc.send_bytes(excel_file.getvalue(), "DRE_Projetado.xlsx")

@app.callback(
    Output('pedidos-firmados-details-tbody', 'style'),
    Output('pedidos-firmados-icon', 'className'),
    Input('pedidos-firmados-toggle', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_pedidos_firmados_details(n_clicks):
    if n_clicks and n_clicks > 0 and n_clicks % 2 != 0:
        return {'display': 'table-row-group'}, "fa fa-chevron-down me-2"
    return {'display': 'none'}, "fa fa-chevron-right me-2"

@app.callback(
    Output('estoque-pedidos-details-tbody', 'style'),
    Output('estoque-pedidos-icon', 'className'),
    Input('estoque-pedidos-toggle', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_estoque_pedidos_details(n_clicks):
    if n_clicks and n_clicks > 0 and n_clicks % 2 != 0:
        return {'display': 'table-row-group'}, "fa fa-chevron-down me-2"
    return {'display': 'none'}, "fa fa-chevron-right me-2"

@app.callback(
    Output('retirada-franquias-details-tbody', 'style'),
    Output('retirada-franquias-icon', 'className'),
    Input('retirada-franquias-toggle', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_retirada_franquias_details(n_clicks):
    if n_clicks and n_clicks > 0 and n_clicks % 2 != 0:
        return {'display': 'table-row-group'}, "fa fa-chevron-down me-2"
    return {'display': 'none'}, "fa fa-chevron-right me-2"

@app.callback(
    Output('retirada-estoque-details-tbody', 'style'),
    Output('retirada-estoque-icon', 'className'),
    Input('retirada-estoque-toggle', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_retirada_estoque_details(n_clicks):
    if n_clicks and n_clicks > 0 and n_clicks % 2 != 0:
        return {'display': 'table-row-group'}, "fa fa-chevron-down me-2"
    return {'display': 'none'}, "fa fa-chevron-right me-2"

@app.callback(
    Output('compras-details-tbody', 'style'),
    Output('compras-details-icon', 'className'),
    Input('compras-row-toggle', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_compras_details(n_clicks):
    if n_clicks and n_clicks > 0:
        if n_clicks % 2 != 0:  # Odd clicks -> open
            return {'display': 'table-row-group'}, "fa fa-chevron-down me-2"
    return {'display': 'none'}, "fa fa-chevron-right me-2"

@app.callback(
    Output('dre-table-container', 'children'),
    Input('dre-data-store', 'data')
)
def update_dre_table(data):
    return create_data_table(data)

