import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import pandas as pd
from banco_dados.banco import Banco

def generate_cotacao_comparison_pdf(oc_numero):
    """
    Gera um PDF de mapa de cotações para um determinado número de Ordem de Compra.
    """
    banco = Banco()
    
    # Busca todos os itens e cotações associados ao número da OC
    with banco.engine.connect() as conn:
        query = """
        SELECT
            oc.oc_id, oc.oc_qtd_solicitada,
            p.nome as produto_nome,
            cot.fornecedor_id,
            f.for_nome as fornecedor_nome,
            cot.valor_unit, cot.valor_entrada,
            cot.condicao_pagamento, cot.forma_pagamento,
            cot.observacao
        FROM ordem_compra oc
        LEFT JOIN produto_compras p ON oc.oc_produto_id = p.prod_comp_id
        LEFT JOIN cotacao cot ON oc.oc_id = cot.oc_id
        LEFT JOIN fornecedores f ON cot.fornecedor_id = f.for_id
        WHERE oc.oc_numero = :oc_numero
        """
        df = pd.read_sql(query, conn, params={'oc_numero': oc_numero})

    if df.empty:
        return None

    # --- Estruturação dos Dados ---
    # Pega todos os produtos únicos da OC
    products_in_oc = df[['produto_nome', 'oc_qtd_solicitada']].drop_duplicates().to_dict('records')
    
    # Pega todos os fornecedores que têm cotações (pelo fornecedor_id da cotação)
    suppliers = df[['fornecedor_id', 'fornecedor_nome']].drop_duplicates()
    suppliers = suppliers[~suppliers['fornecedor_id'].isna()]
    suppliers = suppliers.sort_values('fornecedor_nome')
    suppliers_list = suppliers.to_dict('records')
    if not suppliers_list:
        suppliers_list = [{'fornecedor_id': None, 'fornecedor_nome': 'Nenhuma Cotação'}]

    # --- Geração do PDF ---
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallText', fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='Header', fontSize=9, fontName='Helvetica-Bold'))

    elements = [Paragraph(f"Mapa de Cotações - O.C. Nº: {oc_numero}", styles['h1'])]
    
    # --- Montagem da Tabela ---
    header = [
        Paragraph("<b>Produto</b>", styles['Header']),
        Paragraph("<b>Qtd.</b>", styles['Header']),
    ] + [Paragraph(f"<b>{s['fornecedor_nome']}</b>", styles['SmallText']) for s in suppliers_list]
    
    table_data = [header]

    for product_info in products_in_oc:
        product = product_info['produto_nome']
        qty = product_info['oc_qtd_solicitada']
        row_data = [Paragraph(product, styles['SmallText']), f"{qty or 0:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")]
        for s in suppliers_list:
            # Encontra a cotação para o produto e fornecedor atuais
            quote = df[(df['produto_nome'] == product) & (df['fornecedor_id'] == s['fornecedor_id'])]
            quote = quote.iloc[0] if not quote.empty else None
            cell_text = ""
            if quote is not None and pd.notna(quote['valor_unit']):
                valor_unit = quote['valor_unit']
                valor_entrada = quote.get('valor_entrada')  # Remove default, handle None below
                cond_pag = quote.get('condicao_pagamento', 'N/A')
                forma_pag = quote.get('forma_pagamento', 'N/A')
                obs = quote.get('observacao', '')
                
                # Formata o valor de entrada, tratando o caso de ser None
                entrada_formatada = f"R$ {valor_entrada:,.2f}" if valor_entrada is not None else "N/A"

                cell_text = (
                    f"<b>Valor Unit.:</b> R$ {valor_unit:,.2f}<br/>"
                    f"<b>Entrada:</b> {entrada_formatada}<br/>"
                    f"<b>Cond.:</b> {cond_pag}<br/>"
                    f"<b>Forma:</b> {forma_pag}"
                ).replace(",", "X").replace(".", ",").replace("X", ".")
                if obs:
                    cell_text += f"<br/><b>Obs:</b> {obs}"
            row_data.append(Paragraph(cell_text, styles['SmallText']))
        table_data.append(row_data)

    # Distribui melhor o espaço das colunas
    usable_width = 10 * inch  # 11" (landscape) - 1" (margins)
    product_col_width = 3.0 * inch
    qty_col_width = 0.7 * inch
    if suppliers_list:
        supplier_cols_width = usable_width - product_col_width - qty_col_width
        supplier_col_width = supplier_cols_width / len(suppliers_list)
    else:
        supplier_col_width = 0
    col_widths = [product_col_width, qty_col_width] + [supplier_col_width] * len(suppliers_list)
    row_height = 60  # altura fixa em pontos (~60px)
    tbl = Table(table_data, colWidths=col_widths, rowHeights=[row_height] * len(table_data), repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(tbl)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

