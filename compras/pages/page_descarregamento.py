import dash
from dash import html, dash_table, dcc
import dash_bootstrap_components as dbc
import pandas as pd
from app import app
from banco_dados.banco import Banco
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import io

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Recebimentos')
    output.seek(0)
    return output

def create_layout():
    banco = Banco()
    
    try:
        with banco.engine.connect() as conn:
            # Query to fetch ONLY existing shipments for OCs that match the criteria.
            query = """
            SELECT 
                oc.oc_id,
                c.car_id,
                oc.oc_unid_compra,
                c.car_qtd,
                c.car_data,
                pc.nome as produto_nome,
                oc.oc_observacao,
                oc.oc_status,
                f.for_nome as fornecedor_nome
            FROM 
                carregamento c
            JOIN 
                ordem_compra oc ON c.car_oc_id = oc.oc_id
            LEFT JOIN 
                produto_compras pc ON oc.oc_produto_id = pc.prod_comp_id
            LEFT JOIN
                fornecedores f ON oc.oc_fornecedor_id = f.for_id
            WHERE
                oc.oc_status IN ('Aguardando Aprovação', 'Aguardando Recebimento', 'Entregue Parcial')
                AND oc.oc_data_entrega >= '2024-06-18'
            ORDER BY
                f.for_nome, c.car_data DESC
            """
            df = pd.read_sql(query, conn)
    except Exception as e:
        return html.Div([
            html.H5("Erro ao carregar dados de entrega.", className="text-danger"),
            html.P(str(e))
        ])

    if df.empty:
        return dbc.Container(html.H4("Nenhum carregamento encontrado para o período e status selecionados."), className="text-center mt-5")

    # Formatar data
    df['car_data'] = pd.to_datetime(df['car_data']).dt.strftime('%d/%m/%Y')
    
    # Formatar números
    df['car_qtd'] = df['car_qtd'].apply(
        lambda x: f"{float(x):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        if pd.notnull(x) else ""
    )

    # Agrupar por fornecedor
    grouped = df.groupby('fornecedor_nome')
    
    cards = []
    for fornecedor, group_df in grouped:
        table = dash_table.DataTable(
            columns=[
                {'name': 'OC ID', 'id': 'oc_id'},
                {'name': 'Car. ID', 'id': 'car_id'},
                {'name': 'Produto', 'id': 'produto_nome'},
                {'name': 'Qtd. A Receber', 'id': 'car_qtd'},
                {'name': 'Unidade', 'id': 'oc_unid_compra'},
                {'name': 'Data Entrega', 'id': 'car_data'},
                {'name': 'Status OC', 'id': 'oc_status'},
                {'name': 'Observação', 'id': 'oc_observacao'},
            ],
            data=group_df.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '8px',
                'whiteSpace': 'normal',
                'height': 'auto',
            },
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            page_size=10,
            sort_action='native',
        )
        
        card = dbc.Card([
            dbc.CardHeader(html.H5(f"Fornecedor: {fornecedor}")),
            dbc.CardBody(table)
        ], className="mb-4")
        
        cards.append(card)

    page_layout = dbc.Container([
        dbc.Row([
            dbc.Col(html.H1("Recebimento de Mercadorias", className="my-4"), width='auto'),
            dbc.Col(
                [
                    dbc.Button("Exportar para Excel", id="btn-export-excel-descarregamento", color="success", className="my-4"),
                    dcc.Download(id="download-excel-descarregamento"),
                ],
                width='auto',
                className="d-flex align-items-center"
            )
        ], justify="between"),
        *cards
    ], fluid=True)

    return page_layout

layout = dbc.Container([
    dcc.Interval(id="interval-atualiza-dados", interval=30*1000, n_intervals=0),  # Atualiza a cada 30s
    html.Div(id="conteudo-dinamico")
], fluid=True)

@app.callback(
    Output("conteudo-dinamico", "children"),
    Input("interval-atualiza-dados", "n_intervals")  # Atualiza em intervalo
)
def atualizar_tela(n):
    return create_layout()

@app.callback(
    Output("download-excel-descarregamento", "data"),
    Input("btn-export-excel-descarregamento", "n_clicks"),
    prevent_initial_call=True,
)
def exportar_excel_descarregamento(n_clicks):
    if not n_clicks:
        raise PreventUpdate

    banco = Banco()
    
    def to_safe_numeric(value):
        """Converts a value to a numeric type, returning 0 if it's null or invalid."""
        numeric_val = pd.to_numeric(value, errors='coerce')
        return 0 if pd.isna(numeric_val) else numeric_val

    try:
        with banco.engine.connect() as conn:
            query = """
            SELECT 
                oc.oc_id,
                oc.oc_qtd_solicitada,
                oc.oc_qtd_recebida,
                oc.oc_data_entrega,
                oc.oc_valor_unit,
                oc.oc_ipi,
                oc.oc_icms,
                oc.oc_frete,
                c.car_id,
                c.car_qtd,
                c.car_data,
                pc.nome as produto_nome,
                f.for_nome as fornecedor_nome,
                f.for_prazo
            FROM 
                ordem_compra oc
            LEFT JOIN 
                carregamento c ON c.car_oc_id = oc.oc_id
            LEFT JOIN 
                produto_compras pc ON oc.oc_produto_id = pc.prod_comp_id
            LEFT JOIN
                fornecedores f ON oc.oc_fornecedor_id = f.for_id
            WHERE
                oc.oc_status IN ('Aguardando Aprovação', 'Aguardando Recebimento', 'Entregue Parcial')
                AND oc.oc_data_entrega >= '2024-06-18'
            """
            df_raw = pd.read_sql(query, conn)

        if df_raw.empty:
            raise PreventUpdate

        final_rows = []
        oc_groups = df_raw.groupby('oc_id')

        for oc_id, group in oc_groups:
            oc_info = group.iloc[0]
            fornecedor = oc_info['fornecedor_nome']
            produto = oc_info['produto_nome']
            data_entrega = oc_info['oc_data_entrega']
            qtd_solicitada = to_safe_numeric(oc_info['oc_qtd_solicitada'])
            qtd_recebida = to_safe_numeric(oc_info['oc_qtd_recebida'])

            # Novas infos
            valor_unit = oc_info['oc_valor_unit']
            ipi = oc_info['oc_ipi']
            icms = oc_info['oc_icms']
            frete = oc_info['oc_frete']
            prazo = oc_info['for_prazo']

            # Filtra apenas carregamentos válidos (onde car_id não é nulo)
            carregamentos_existentes = group[group['car_id'].notna()]

            if not carregamentos_existentes.empty:
                # Caso 1: Ordem de compra com carregamentos
                soma_car_qtd = 0
                for _, car_row in carregamentos_existentes.iterrows():
                    final_rows.append({
                        'Fornecedor': fornecedor,
                        'Produto': produto,
                        'OC ID': oc_id,
                        'Carregamento ID': int(car_row['car_id']),
                        'Quantidade': to_safe_numeric(car_row['car_qtd']),
                        'Data': pd.to_datetime(car_row['car_data']).strftime('%d/%m/%Y'),
                        'Valor Unitário': valor_unit,
                        'IPI (%)': ipi,
                        'ICMS (%)': icms,
                        'Frete (R$)': frete,
                        'Prazo Pagamento': prazo
                    })
                    soma_car_qtd += to_safe_numeric(car_row['car_qtd'])

                saldo = qtd_solicitada - qtd_recebida - soma_car_qtd
                if saldo > 0.001:
                    final_rows.append({
                        'Fornecedor': fornecedor,
                        'Produto': produto,
                        'OC ID': oc_id,
                        'Carregamento ID': None,
                        'Quantidade': saldo,
                        'Data': pd.to_datetime(data_entrega).strftime('%d/%m/%Y') if pd.notna(data_entrega) else '',
                        'Valor Unitário': valor_unit,
                        'IPI (%)': ipi,
                        'ICMS (%)': icms,
                        'Frete (R$)': frete,
                        'Prazo Pagamento': prazo
                    })
            else:
                # Caso 2: Ordem de compra sem carregamentos
                quantidade_pendente = qtd_solicitada - qtd_recebida
                if quantidade_pendente > 0.001:
                    final_rows.append({
                        'Fornecedor': fornecedor,
                        'Produto': produto,
                        'OC ID': oc_id,
                        'Carregamento ID': None,
                        'Quantidade': quantidade_pendente,
                        'Data': pd.to_datetime(data_entrega).strftime('%d/%m/%Y') if pd.notna(data_entrega) else '',
                        'Valor Unitário': valor_unit,
                        'IPI (%)': ipi,
                        'ICMS (%)': icms,
                        'Frete (R$)': frete,
                        'Prazo Pagamento': prazo
                    })

        if not final_rows:
            raise PreventUpdate

        # Combinar e ordenar
        df_final = pd.DataFrame(final_rows)
        df_final.sort_values(by=['Fornecedor', 'OC ID', 'Data'], inplace=True)
        
        # Formatação final
        df_final['Quantidade'] = df_final['Quantidade'].apply(lambda x: f"{x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        df_final['OC ID'] = df_final['OC ID'].astype(int)
        df_final['Carregamento ID'] = df_final['Carregamento ID'].apply(lambda x: int(x) if pd.notna(x) else '')

        # Formatação das novas colunas
        def format_currency(x):
            if pd.isna(x): return ''
            return f"R$ {pd.to_numeric(x, errors='coerce'):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        def format_percent(x):
            if pd.isna(x): return ''
            return f"{pd.to_numeric(x, errors='coerce'):.2f}%"

        df_final['Valor Unitário'] = df_final['Valor Unitário'].apply(format_currency)
        df_final['Frete (R$)'] = df_final['Frete (R$)'].apply(format_currency)
        df_final['IPI (%)'] = df_final['IPI (%)'].apply(format_percent)
        df_final['ICMS (%)'] = df_final['ICMS (%)'].apply(format_percent)

        return dcc.send_bytes(to_excel(df_final).getvalue(), "Relatorio_Recebimentos.xlsx")

    except Exception as e:
        print(f"Erro ao gerar Excel de descarregamento: {e}")
        import traceback
        traceback.print_exc()
        raise PreventUpdate
