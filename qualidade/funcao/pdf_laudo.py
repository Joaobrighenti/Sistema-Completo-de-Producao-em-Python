from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
import os


def _fmt(value, default=""):
    if value is None:
        return ""
    # Preserva quebras de linha convertendo \n em <br/> para HTML
    # Também trata caracteres especiais que podem causar problemas no PDF
    text = str(value)
    # Escapa caracteres especiais HTML
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    # Converte quebras de linha
    text = text.replace('\n', '<br/>')
    return text


def _fmt_int(value):
    if value is None:
        return ""
    try:
        if isinstance(value, (int,)):
            return str(value)
        if isinstance(value, float):
            return str(int(value))
        # string or other
        return str(int(float(str(value).replace(',', '.'))))
    except Exception:
        return str(value)


def _build_qpp_table(qpp: dict, total_width: float):
    data = [["Parte", "Total", "Volumes", "Por Volume"]]
    if isinstance(qpp, dict):
        for parte, vals in qpp.items():
            total = vals.get('total') if isinstance(vals, dict) else None
            volumes = vals.get('volumes') if isinstance(vals, dict) else None
            por_volume = vals.get('por_volume') if isinstance(vals, dict) else None
            data.append([_fmt(parte), _fmt(total), _fmt(volumes), _fmt(por_volume)])
    # Distribui largura: Parte 30%, demais 70%/3 cada
    col_widths = [total_width * 0.30, total_width * 0.233, total_width * 0.233, total_width * 0.233]
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    return tbl


def _build_image_from_medidas(medidas_value, max_w_mm: float, max_h_mm: float):
    if not medidas_value:
        return None
    # medidas_value is stored like 'qualidade/<file>' relative to assets
    candidates = []
    if isinstance(medidas_value, str):
        candidates.append(medidas_value)
        candidates.append(os.path.join('assets', medidas_value))
        candidates.append(os.path.join('assets', 'qualidade', os.path.basename(medidas_value)))
    img_path = None
    for cand in candidates:
        if isinstance(cand, str) and os.path.exists(cand):
            img_path = cand
            break
    if not img_path:
        return None
    try:
        img = RLImage(img_path)
        # Fit into a box while keeping aspect ratio
        max_w = max_w_mm * mm
        max_h = max_h_mm * mm
        iw, ih = float(getattr(img, 'imageWidth', 0) or 0), float(getattr(img, 'imageHeight', 0) or 0)
        if iw > 0 and ih > 0:
            ratio = min(max_w / iw, max_h / ih)
            img.drawWidth = iw * ratio
            img.drawHeight = ih * ratio
        return img
    except Exception:
        return None


def generate_laudo_pdf_bytes(laudo: dict, pcp: dict, produto_espec: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=10*mm, bottomMargin=10*mm)

    styles = getSampleStyleSheet()
    story = []

    # Cabeçalho com imagem
    header_candidates = ['cabecalho.png', os.path.join('assets', 'cabecalho.png'), os.path.join('assets', 'qualidade', 'cabecalho.png')]
    header_path = next((p for p in header_candidates if os.path.exists(p)), None)
    if header_path:
        try:
            hdr = RLImage(header_path)
            iw, ih = float(getattr(hdr, 'imageWidth', 0) or 0), float(getattr(hdr, 'imageHeight', 0) or 0)
            max_w = float(doc.width)
            max_h = 35 * mm
            if iw > 0 and ih > 0:
                ratio = min(max_w / iw, max_h / ih)
                hdr.drawWidth = iw * ratio
                hdr.drawHeight = ih * ratio
            story.append(hdr)
            story.append(Spacer(1, 6))
        except Exception:
            pass

    #title = Paragraph("Laudo de Qualidade", styles['Title'])
    #story.append(title)
    story.append(Spacer(1, 6))

    # Bloco superior com imagem à esquerda e detalhes à direita
    prod_espec_cat = produto_espec.get('categoria') if isinstance(produto_espec, dict) else None
    left_w = doc.width * 0.35
    right_w = doc.width * 0.65
    medidas_value = produto_espec.get('medidas') if isinstance(produto_espec, dict) else None
    img = _build_image_from_medidas(medidas_value, max_w_mm=left_w / mm, max_h_mm=70)
    img_cell = img if img is not None else Paragraph("", styles['Normal'])

    # Use Paragraph para permitir quebra de linha
    details_data = [
        ["Lote", Paragraph(_fmt_int(pcp.get('pcp_pcp')), styles['Normal'])],
        ["Nota Fiscal", Paragraph(_fmt(laudo.get('nota_fiscal')), styles['Normal'])],
        ["Produto", Paragraph(_fmt(pcp.get('produto_nome')), styles['Normal'])],
        ["Cliente", Paragraph(_fmt(pcp.get('cliente_nome')), styles['Normal'])],
        ["Categoria", Paragraph(_fmt(prod_espec_cat), styles['Normal'])],
    ]
    details_tbl = Table(details_data, colWidths=[right_w * 0.25, right_w * 0.65])
    details_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))

    # Add a small spacer column between image and details to avoid "encostar"
    spacer_w = 6 * mm
    right_eff = max(10, right_w - spacer_w)
    top_tbl = Table([[img_cell, Paragraph('', styles['Normal']), details_tbl]], colWidths=[left_w, spacer_w, right_eff])
    top_tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (2,0), (2,-1), 4),
    ]))
    story.append(top_tbl)
    story.append(Spacer(1, 8))

    # Tabela de Qtd por Plano
    qpp = laudo.get('qtd_por_plano') if isinstance(laudo, dict) else {}
    qpp_tbl = _build_qpp_table(qpp or {}, doc.width)
    story.append(qpp_tbl)
    story.append(Spacer(1, 8))

    # Bloco de especificações: título em cima (cinza) e valor embaixo (branco)
    def _title_value_table(title: str, value: str):
        # Cria um estilo personalizado que permite quebras de linha
        custom_style = ParagraphStyle(
            'CustomStyle',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=2,
            spaceBefore=2,
            leftIndent=0,
            rightIndent=0,
            alignment=0,  # 0=left, 1=center, 2=right
        )
        
        data = [
            [Paragraph(title, custom_style)],
            [Paragraph(_fmt(value), custom_style)],
        ]
        tbl = Table(data, colWidths=[doc.width])
        tbl.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('WORDWRAP', (0,0), (-1,-1), True),  # Permite quebra de palavras
        ]))
        return tbl

    espec_fields = [
        ('Substrato', produto_espec.get('substrato') if isinstance(produto_espec, dict) else None),
        ('Acabamento', produto_espec.get('acabamento') if isinstance(produto_espec, dict) else None),
        ('Embalagem', produto_espec.get('embalagem') if isinstance(produto_espec, dict) else None),
        ('Especificações', produto_espec.get('especificacoes') if isinstance(produto_espec, dict) else None),
        ('Info Adicional', produto_espec.get('info_adicional') if isinstance(produto_espec, dict) else None),
    ]

    for title, value in espec_fields:
        story.append(_title_value_table(title, value))
        story.append(Spacer(1, 6))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

