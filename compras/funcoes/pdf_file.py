import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image


def generate_oc_pdf(oc_details, items_df):
    """
    Gera um PDF para uma Solicitação de Cotação.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(name='Right', alignment=2, fontSize=9))
    styles.add(ParagraphStyle(name='Left', alignment=0, fontSize=9))
    styles.add(ParagraphStyle(name='Justify', alignment=4, leading=12))
    styles.add(ParagraphStyle(name='MainTitle', alignment=0, fontSize=18, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SectionHeader', alignment=0, fontSize=10, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=5))

    elements = []

    # --- Cabeçalho com Logo e Título ---
    logo_path = "assets/logo.png"
    try:
        logo = Image(logo_path, width=2*inch, height=0.75*inch)
    except Exception:
        logo = Paragraph("NICOPEL", styles['Left'])

    header_data = [
        [logo, Paragraph("Solicitação de Cotação", styles['MainTitle'])],
        ['', Paragraph("<b>GRUPO NICOPEL</b><br/>CNPJ: 10.815.855/0001-24<br/>Rodovia Carlos João Strass, 780<br/>86087-350 - Londrina - PR", styles['Right'])]
    ]
    header_table = Table(header_data, colWidths=[2.5*inch, 5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 1), 'RIGHT'),
        ('SPAN', (1, 0), (1, 0)),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))

    # --- Informações da Cotação e Fornecedor ---
    order_info_data = [
        [Paragraph("<b>Cotação Nº:</b>", styles['Left']), oc_details.get('oc_solicitacao', 'N/A')]
    ]
    order_info_table = Table(order_info_data, colWidths=[1.2*inch, 6.3*inch])
    order_info_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey),('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),]))
    elements.append(Paragraph("DADOS DA COTAÇÃO", styles['SectionHeader']))
    elements.append(order_info_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # --- Endereço de Entrega ---
    delivery_address_data = [
        [Paragraph("<b>Endereço:</b>", styles['Left']), "Rodovia Carlos João Strass", Paragraph("<b>Número:</b>", styles['Left']), "780"],
        [Paragraph("<b>Bairro:</b>", styles['Left']), "Jardim Tropical", Paragraph("<b>CEP:</b>", styles['Left']), "86087-350"],
        [Paragraph("<b>Cidade:</b>", styles['Left']), "Londrina", Paragraph("<b>Estado:</b>", styles['Left']), "PR"]
    ]
    delivery_address_table = Table(delivery_address_data, colWidths=[0.8*inch, 3*inch, 0.8*inch, 2.9*inch])
    delivery_address_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey),('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),]))
    elements.append(Paragraph("ENDEREÇO DE ENTREGA", styles['SectionHeader']))
    elements.append(delivery_address_table)
    elements.append(Spacer(1, 0.2*inch))

    # --- Tabela de Itens ---
    table_header = ["Item", "Cod", "Descrição dos Produtos", "Un", "Qtde", "Necessidade"]
    items_data = [table_header]

    for i, row in items_df.iterrows():
        qtd = row.get('oc_qtd_solicitada', 0) or 0
        items_data.append([
            i + 1,
            row.get('oc_id'),
            Paragraph(str(row.get('oc_nome_solicitacao') or 'N/A'), styles['Justify']),
            row.get('oc_unid_compra'),
            f"{qtd:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            row.get('oc_data_necessaria', 'N/A')
        ])

    items_table = Table(items_data, colWidths=[0.4*inch, 0.5*inch, 4.6*inch, 0.4*inch, 0.8*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E0E0E0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
    ]))
    elements.append(Paragraph("ITENS PARA COTAÇÃO", styles['SectionHeader']))
    elements.append(items_table)
    elements.append(Spacer(1, 0.4*inch))

    # --- Observações Finais ---
    obs_text = str(oc_details.get('oc_observacao') or 'Aguardamos o retorno com os melhores valores e condições.')
    elements.append(Paragraph("OBSERVAÇÕES", styles['SectionHeader']))
    elements.append(Paragraph(obs_text, styles['Left']))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
