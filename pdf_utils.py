"""Shared ReportLab helpers for GR AMS PDF exports."""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PRIMARY = colors.HexColor('#1a3a5c')
MUTED = colors.HexColor('#6b7280')
LANDSCAPE_PAGE = landscape(A4)
PDF_MARGIN = 28
HEADER_HEIGHT = 72


def gr_logo_path():
    return os.path.join(os.path.dirname(__file__), 'static', 'img', 'GR.jpg')


def build_gr_header_table(width, report_title=None):
    """Platypus header block: optional centered report title, logo + GR branding, divider."""
    logo_cell = Spacer(1, 1)
    path = gr_logo_path()
    if os.path.isfile(path):
        try:
            logo_cell = Image(path, width=50, height=50)
        except Exception:
            pass

    title_style = ParagraphStyle(
        'GRTitle', fontName='Helvetica-Bold', fontSize=20,
        textColor=PRIMARY, leading=22, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        'GRSub', fontName='Helvetica', fontSize=10,
        textColor=MUTED, leading=12, spaceAfter=2,
    )
    report_center_style = ParagraphStyle(
        'GRReportCenter', fontName='Helvetica-Bold', fontSize=13,
        textColor=PRIMARY, leading=15, alignment=TA_CENTER,
    )
    date_style = ParagraphStyle(
        'GRDate', fontName='Helvetica', fontSize=8,
        textColor=MUTED, leading=10,
    )

    text_block = Table([
        [Paragraph('GR', title_style)],
        [Paragraph('Asset Management System', sub_style)],
        [Paragraph(f'Printed: {datetime.utcnow().strftime("%d %B %Y")}', date_style)],
    ], colWidths=[max(width - 64, 200)])
    text_block.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    brand_row = Table([[logo_cell, text_block]], colWidths=[58, max(width - 58, 200)])
    brand_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    if report_title:
        title_row = Table(
            [[Paragraph(report_title, report_center_style)]],
            colWidths=[width],
        )
        title_row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        header = Table([[title_row], [brand_row]], colWidths=[width])
    else:
        header = brand_row

    header.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, -1), (-1, -1), 2, PRIMARY),
    ]))
    return header


def draw_gr_page_header(canvas, doc, report_title=None):
    """Draw the GR header in the top margin on every page."""
    canvas.saveState()
    w, h = doc.pagesize
    avail = w - 2 * PDF_MARGIN
    title = report_title if report_title is not None else getattr(doc, 'report_title', None)
    header = build_gr_header_table(avail, title)
    _, hh = header.wrap(avail, HEADER_HEIGHT)
    y = h - doc.topMargin + max((doc.topMargin - hh) / 2, 6)
    header.drawOn(canvas, PDF_MARGIN, y)
    canvas.restoreState()


def gr_pdf_doc(buffer, extra_header=0):
    return SimpleDocTemplate(
        buffer,
        pagesize=LANDSCAPE_PAGE,
        rightMargin=PDF_MARGIN,
        leftMargin=PDF_MARGIN,
        topMargin=PDF_MARGIN + HEADER_HEIGHT + extra_header + 20,
        bottomMargin=PDF_MARGIN,
    )


def _scaled_col_widths(weights, available_width):
    total = sum(weights)
    return [available_width * w / total for w in weights]


def asset_register_col_widths(available_width):
    return _scaled_col_widths(
        [52, 38, 62, 48, 44, 38, 42, 26, 48, 34, 38],
        available_width,
    )


def return_log_col_widths(available_width):
    return _scaled_col_widths([68, 110, 82, 56, 46, 120], available_width)


def scaled_col_widths(weights, available_width):
    return _scaled_col_widths(weights, available_width)


def gr_table_style():
    return [
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 6.5),
        ('FONTSIZE', (0, 1), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#d1d5db')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]


def _clean_cell(value):
    if value is None:
        return '—'
    text = str(value).strip()
    return text if text and text.lower() != 'none' else '—'


def build_pdf_table(rows, col_widths):
    """Convert string rows to a wrapped platypus table that fits the page."""
    header_style = ParagraphStyle(
        'PdfHeaderCell', fontName='Helvetica-Bold', fontSize=6.5,
        textColor=colors.white, leading=8,
    )
    cell_style = ParagraphStyle(
        'PdfBodyCell', fontName='Helvetica', fontSize=6,
        textColor=colors.black, leading=7.5,
    )

    def para(value, is_header):
        text = _clean_cell(value)
        safe = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return Paragraph(safe, header_style if is_header else cell_style)

    data = [
        [para(cell, is_header=(row_idx == 0)) for cell in row]
        for row_idx, row in enumerate(rows)
    ]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(TableStyle(gr_table_style()))
    return table


def pdf_response(pdf_bytes, filename):
    from flask import make_response
    response = make_response(pdf_bytes)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response


def build_gr_pdf(elements_fn, report_title=None):
    """Build a landscape GR PDF with logo header on every page."""
    import io
    buffer = io.BytesIO()
    extra_header = 18 if report_title else 0
    doc = gr_pdf_doc(buffer, extra_header=extra_header)
    doc.report_title = report_title

    def _draw_header(canvas, doc):
        draw_gr_page_header(canvas, doc, report_title)

    elements = list(elements_fn(doc))
    doc.build(elements, onFirstPage=_draw_header, onLaterPages=_draw_header)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
