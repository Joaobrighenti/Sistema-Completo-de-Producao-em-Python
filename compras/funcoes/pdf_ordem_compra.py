import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image


def generate_ordem_compra_pdf(oc_numero: str, items_df):
    """Gera um PDF (paisagem) da Ordem de Compra agrupado pelo oc_numero.

    Colunas: data entrega, data emissao, obs, produto, unidade, qtd solicitada,
    valor, qtd recebida, conversao, qtd, valor
    
    Linhas com status diferente do grupo são destacadas em cor diferente.
    """
    buffer = io.BytesIO()
    # Usar A4 paisagem para ganhar largura e margens menores
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        rightMargin=0.35 * inch,
        leftMargin=0.35 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.35 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Cell', alignment=0, fontSize=7.3, leading=9))
    styles.add(ParagraphStyle(name='TitleBold', alignment=0, fontSize=14, leading=16))
    styles.add(ParagraphStyle(name='SmallBold', alignment=0, fontSize=8, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Small', alignment=0, fontSize=8, leading=10))

    elements = []

    # Cabeçalho com logo, título e dados da empresa (canto direito superior)
    logo_path = "assets/logo.png"
    try:
        logo = Image(logo_path, width=2.2 * inch, height=0.8 * inch)
    except Exception:
        logo = Paragraph("NICOPEL", styles['TitleBold'])

    left_header = Table([[logo], [Paragraph("<b>Pedido de Compras</b>", styles['TitleBold'])]], colWidths=[2.6 * inch])
    left_header.setStyle(TableStyle([
        ('ALIGN', (0, 1), (0, 1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    company_info_lines = [
        Paragraph('<b>NICOPEL EMBALAGENS LTDA</b>', styles['SmallBold']),
        Paragraph('CNPJ: 10.815.855/0001-24  Insc. Est.: 90479518-68', styles['Small']),
        Paragraph('compras@nicopel.com.br', styles['Small']),
        Paragraph('ROD RODOVIA CARLOS JOAO STRASS 780 - FUNDOS- GLP B', styles['Small']),
        Paragraph('LONDRINA - PR - CEP: 86.087-350', styles['Small']),
    ]
    right_header = Table([[line] for line in company_info_lines], colWidths=[4.8 * inch])
    right_header.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    header = Table([[left_header, right_header]], colWidths=[2.8 * inch, None])
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header)
    elements.append(Spacer(1, 0.06 * inch))

    # Blocos de informações
    fornecedor_nome = str(items_df.iloc[0].get('fornecedor_nome') or '')
    # Define helpers aqui para evitar UnboundLocalError
    def _fmt_date_local(value):
        if not value:
            return ""
        try:
            from datetime import datetime as _dt
            if hasattr(value, 'strftime'):
                return value.strftime('%d/%m/%Y')
            s = str(value)
            if '/' in s:
                return s
            return _dt.strptime(s[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            try:
                return str(value)
            except Exception:
                return ""
    def _fmt_num_local(value, decimals=0):
        try:
            f = float(value)
            fmt = f"{{:,.{decimals}f}}".format(f).replace(',', 'X').replace('.', ',').replace('X', '.')
            return fmt
        except Exception:
            return ""

    data_emissao = _fmt_date_local(items_df.iloc[0].get('oc_data_emissao'))
    forma_pag = str(items_df.iloc[0].get('fornecedor_forma_pagamento') or '')
    prazo_pag = str(items_df.iloc[0].get('fornecedor_prazo') or '')
    info_left = [
        [Paragraph('<b>Fornecedor:</b>', styles['SmallBold']), Paragraph(fornecedor_nome, styles['Cell'])],
        [Paragraph('<b>Forma Pgto.:</b>', styles['SmallBold']), Paragraph(forma_pag, styles['Cell'])],
    ]
    info_right = [
        [Paragraph('<b>Número:</b>', styles['SmallBold']), Paragraph(str(oc_numero), styles['Cell'])],
        [Paragraph('<b>Prazo:</b>', styles['SmallBold']), Paragraph(str(prazo_pag), styles['Cell'])],
    
    ]
    info_table = Table([
        [Table(info_left, colWidths=[1.0 * inch, 4.0 * inch]), Table(info_right, colWidths=[1.0 * inch, 2.0 * inch])]
    ], colWidths=[5.0 * inch, None])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E2E8F0')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.08 * inch))

    # Cabeçalho da tabela
    headers = [
        "Data Entrega",
        "Data Emissão",
        "Obs.",
        "Produto",
        "Un",
        "Qtd Solicitada",
        
        "Valor Unit",
        "IPI (%)",
        "Qtd Recebida",
        "Valor",
    ]

    data = [headers]

    def fmt_date(value):
        if not value:
            return ""
        # aceita datetime, pandas timestamp, 'YYYY-mm-dd', 'dd/mm/YYYY'
        try:
            from datetime import datetime as _dt
            if hasattr(value, 'strftime'):
                return value.strftime('%d/%m/%Y')
            s = str(value)
            # se já estiver no formato brasileiro, mantém
            if '/' in s:
                return s
            # tenta ISO
            return _dt.strptime(s[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            try:
                return str(value)
            except Exception:
                return ""

    def fmt_num(value, decimals=0):
        try:
            f = float(value)
            fmt = f"{{:,.{decimals}f}}".format(f).replace(',', 'X').replace('.', ',').replace('X', '.')
            return fmt
        except Exception:
            return ""

    # Construir linhas
    row_styles = []
    for idx, row in items_df.iterrows():
        qtd_solic = row.get('oc_qtd_solicitada')
        valor_unit = row.get('oc_valor_unit')
        valor_total = None
        try:
            if qtd_solic is not None and valor_unit is not None:
                valor_total = float(qtd_solic) * float(valor_unit)
        except Exception:
            valor_total = None

        # Preparar IPI e valores
        try:
            ipi_raw = row.get('oc_ipi')
            ipi_percent = float(ipi_raw) if ipi_raw is not None else 0.0
        except Exception:
            ipi_percent = 0.0

        ipi_str = '0' if ipi_percent == 0 else fmt_num(ipi_percent, 2)
        valor_unit_str = fmt_num(valor_unit, 4)

        valor_total_with_ipi = None
        try:
            if valor_total is not None:
                valor_total_with_ipi = float(valor_total) * (1.0 + (ipi_percent / 100.0))
        except Exception:
            valor_total_with_ipi = valor_total
        valor_total_str = fmt_num(valor_total_with_ipi, 2)

        data.append([
            fmt_date(row.get('oc_data_entrega')),
            fmt_date(row.get('oc_data_emissao')),
            Paragraph(str(row.get('oc_observacao') or ''), styles['Cell']),
            Paragraph(str(row.get('produto_nome') or ''), styles['Cell']),
            str(row.get('oc_unid_compra') or ''),
            fmt_num(qtd_solic, 0),
            
            valor_unit_str,
            ipi_str,
            fmt_num(row.get('oc_qtd_recebida'), 0),
            valor_total_str,
        ])

        # Destacar linhas com status diferente do grupo
        if row.get('oc_status_no_grupo_diferente'):
            # linha 0 é o header; +1 para compensar
            line_index = len(data) - 1
            row_styles.append(('BACKGROUND', (0, line_index), (-1, line_index), colors.HexColor('#FFF3CD')))  # amarelo claro

    # Tabela com larguras proporcionais ao espaço disponível
    page_width, page_height = page_size
    available_width = page_width - (doc.leftMargin + doc.rightMargin)
    # Larguras relativas com coluna IPI antes de Valor Unit
    rel_widths = [8, 8, 22, 28, 6, 9, 8, 7, 9, 12]
    total_rel = float(sum(rel_widths))
    col_widths = [available_width * (w / total_rel) for w in rel_widths]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    base_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0E0E0')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (3, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]
    table.setStyle(TableStyle(base_style + row_styles))
    elements.append(table)

    # Total geral
    try:
        total_geral = 0.0
        for _, r in items_df.iterrows():
            qtd = float(r.get('oc_qtd_solicitada') or 0)
            vunit = float(r.get('oc_valor_unit') or 0)
            ipi = float(r.get('oc_ipi') or 0)
            total_geral += qtd * vunit * (1.0 + (ipi / 100.0))
    except Exception:
        total_geral = 0.0

    total_tbl = Table([
        [Paragraph('<b>Valor Total</b>', styles['SmallBold']), Paragraph(f"R$ {fmt_num(total_geral, 2)}", styles['Cell'])]
    ], colWidths=[available_width - 1.6 * inch, 1.6 * inch])
    total_tbl.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF7ED')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#FDBA74')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(Spacer(1, 0.06 * inch))
    elements.append(total_tbl)

    # Quadros adicionais no fim: Local/forma de entrega e Informações Gerais (placeholders)
    elements.append(Spacer(1, 0.08 * inch))
    entrega_text = (
        '<b>Local de Entrega:</b> <br/>'
        '<b>Endereço:</b> ROD RODOVIA CARLOS JOAO STRASS 780 - FUNDOS- GLP B<br/>'
        '<b>Cidade/UF:</b> LONDRINA - PR   <b>CEP:</b> 86.087-350<br/>'
        '<b>Horário de Recebimento:</b> 07:30 às 14:00<br/>'
    )
    quadro1 = Table([
        [Paragraph('<b>Local e Forma de Entrega</b>', styles['SmallBold'])],
        [Paragraph(entrega_text, styles['Small'])]
    ], colWidths=[available_width/2 - 6])
    quadro1.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#9CA3AF')),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#D1D5DB')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    info_gerais_text = (
        '- É indispensável registrar nas observações o <b>número do pedido</b>.<br/>'
        '- A <b>Nota Fiscal</b> deve estar em total conformidade com este pedido; diferenças podem gerar atraso na conferência, recebimento e pagamento. Havendo divergências, o título poderá ser devolvido e <b>protestos não serão aceitos</b>.<br/>'
        '- Caso o produto entregue não atenda à especificação solicitada, os <b>custos de devolução e reposição</b> serão de responsabilidade do fornecedor.<br/>'
        '- Enviar <b>DANFE</b> e arquivo <b>XML</b> para os e-mails: compras@nicopel.com.br; fiscal@nicopel.com.br.<br/>'
        '- Em caso de dúvidas, <b>contate o comprador antes do faturamento</b>.'
    )
    quadro2 = Table([
        [Paragraph('<b>Informações Gerais</b>', styles['SmallBold'])],
        [Paragraph(info_gerais_text, styles['Small'])]
    ], colWidths=[available_width/2 - 6])
    quadro2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#9CA3AF')),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#D1D5DB')),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    quadros = Table([[quadro1, quadro2]], colWidths=[available_width/2, available_width/2])
    quadros.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    elements.append(quadros)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

