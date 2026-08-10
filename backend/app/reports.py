"""
PDF rendering shared by Invoices (Invoices.jsx), the Monthly Performance
Report (Reports.jsx), and the Monthly Task Report (MonthlyTaskReports.jsx).
Plain tabular PDFs via reportlab/platypus — no charts (that would need
matplotlib) — the frontend already shows the interactive charts; the PDF is
the "take it with you" artifact.

All three share one branded letterhead/footer (`_draw_letterhead`), drawn via
SimpleDocTemplate's onFirstPage/onLaterPages canvas hooks, so the firm's logo
(or a text fallback if none has been uploaded yet), name, and contact details
appear identically on every generated document. Files land in the same
uploads/ directory and are served the same way as files.py's regular uploads
(UPLOAD_DIR / UPLOAD_BASE_URL).
"""

import io
import uuid
from functools import partial
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .config import settings
from .services._shared.uploaded_files import read_uploaded_file

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

NAVY = colors.HexColor("#1e3a5f")
YELLOW = colors.HexColor("#fbbf24")
RED = colors.HexColor("#dc2626")
GREEN = colors.HexColor("#16a34a")
GRAY = colors.HexColor("#64748b")
LIGHT_GRID = colors.HexColor("#cbd5e1")

_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ("TOPPADDING", (0, 0), (-1, 0), 8),
    ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_GRID),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
])

_PAGE_W, _PAGE_H = letter
_HEADER_H = 1.05 * inch
_FOOTER_TOP = 0.55 * inch

_INVOICE_STATUS_HEX = {
    "Paid": "#16a34a",
    "Partial": "#2563eb",
    "Overdue": "#dc2626",
    "Pending": "#b45309",
}


def _logo_bytes(firm: dict) -> bytes | None:
    logo_url = (firm or {}).get("logo_url")
    if not logo_url:
        return None
    try:
        return read_uploaded_file(logo_url)
    except Exception:
        return None


def _fit_font_size(canvas, text: str, font_name: str, max_width: float, max_size: float, min_size: float = 9) -> float:
    """Shrinks font size until `text` fits `max_width` — the title zone
    length varies (an invoice number vs. "Monthly Performance Report") and
    must never be able to run into the firm-name zone next to it."""
    size = max_size
    while size > min_size and canvas.stringWidth(text, font_name, size) > max_width:
        size -= 0.5
    return size


def _truncate_to_width(canvas, text: str, font_name: str, size: float, max_width: float) -> str:
    if canvas.stringWidth(text, font_name, size) <= max_width:
        return text
    truncated = text
    while truncated and canvas.stringWidth(truncated + "…", font_name, size) > max_width:
        truncated = truncated[:-1]
    return f"{truncated}…" if truncated else text[:1]


# Hard boundary between the logo/firm-name zone and the title/subtitle zone
# in the header band, so a long firm name and a long title (e.g. "Monthly
# Performance Report") can never overlap regardless of either one's length.
_HEADER_SPLIT_OFFSET = 3.3 * inch


def _draw_letterhead(canvas, doc, firm=None, title="", subtitle=""):
    """onFirstPage/onLaterPages hook — draws the navy header band (logo or
    text fallback + firm name + document title/subtitle) and the footer
    (yellow rule, firm contact line, page number) on every page."""
    firm = firm or {}
    canvas.saveState()

    canvas.setFillColor(NAVY)
    canvas.rect(0, _PAGE_H - _HEADER_H, _PAGE_W, _HEADER_H, stroke=0, fill=1)

    firm_name = firm.get("legal_name") or firm.get("name") or "Go-Get"
    text_x = doc.leftMargin
    logo_bytes = _logo_bytes(firm)
    if logo_bytes:
        try:
            logo_size = 0.6 * inch
            canvas.drawImage(
                ImageReader(io.BytesIO(logo_bytes)),
                doc.leftMargin,
                _PAGE_H - _HEADER_H + (_HEADER_H - logo_size) / 2,
                width=logo_size,
                height=logo_size,
                mask="auto",
                preserveAspectRatio=True,
            )
            text_x = doc.leftMargin + logo_size + 0.18 * inch
        except Exception:
            pass
    else:
        # No logo uploaded yet (Settings > Company) — a clean two-tone
        # wordmark stand-in instead of leaving the header bare.
        mark_size = 0.5 * inch
        canvas.setFillColor(YELLOW)
        canvas.rect(
            doc.leftMargin, _PAGE_H - _HEADER_H + (_HEADER_H - mark_size) / 2,
            mark_size, mark_size, stroke=0, fill=1,
        )
        canvas.setFillColor(NAVY)
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawCentredString(
            doc.leftMargin + mark_size / 2,
            _PAGE_H - _HEADER_H / 2 - 6,
            (firm_name[:1] or "G").upper(),
        )
        text_x = doc.leftMargin + mark_size + 0.18 * inch

    split_x = doc.leftMargin + _HEADER_SPLIT_OFFSET
    firm_zone_width = max(split_x - text_x - 0.15 * inch, 0.5 * inch)
    title_zone_width = (_PAGE_W - doc.rightMargin) - split_x

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(text_x, _PAGE_H - _HEADER_H / 2 + 5, _truncate_to_width(canvas, firm_name, "Helvetica-Bold", 14, firm_zone_width))
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#cbd5e1"))
    canvas.drawString(text_x, _PAGE_H - _HEADER_H / 2 - 9, "Accounting & Tax Services")

    title_text = title.upper()
    title_size = _fit_font_size(canvas, title_text, "Helvetica-Bold", title_zone_width, max_size=18, min_size=11)
    canvas.setFillColor(YELLOW)
    canvas.setFont("Helvetica-Bold", title_size)
    canvas.drawRightString(_PAGE_W - doc.rightMargin, _PAGE_H - _HEADER_H / 2 + 3, title_text)
    if subtitle:
        subtitle_size = _fit_font_size(canvas, subtitle, "Helvetica", title_zone_width, max_size=10, min_size=8)
        canvas.setFont("Helvetica", subtitle_size)
        canvas.setFillColor(colors.white)
        canvas.drawRightString(_PAGE_W - doc.rightMargin, _PAGE_H - _HEADER_H / 2 - 13, subtitle)

    canvas.setStrokeColor(YELLOW)
    canvas.setLineWidth(1.5)
    canvas.line(doc.leftMargin, _FOOTER_TOP, _PAGE_W - doc.rightMargin, _FOOTER_TOP)

    address = ", ".join(
        bit for bit in (firm.get("address"), firm.get("city"), firm.get("province"), firm.get("postal_code")) if bit
    )
    contact = " • ".join(bit for bit in (firm.get("phone"), firm.get("email")) if bit)
    footer_left = " — ".join(bit for bit in (address, contact) if bit) or firm_name

    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(doc.leftMargin, _FOOTER_TOP - 13, footer_left)
    canvas.drawRightString(_PAGE_W - doc.rightMargin, _FOOTER_TOP - 13, f"Page {canvas.getPageNumber()}")

    canvas.restoreState()


def _save(build_with_letterhead, filename_prefix: str, firm: dict, title: str, subtitle: str = "") -> str:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{filename_prefix}-{uuid.uuid4().hex[:8]}.pdf"
    destination = upload_dir / stored_name
    doc = SimpleDocTemplate(
        str(destination),
        pagesize=letter,
        topMargin=_HEADER_H + 0.3 * inch,
        bottomMargin=_FOOTER_TOP + 0.3 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
    )
    on_page = partial(_draw_letterhead, firm=firm, title=title, subtitle=subtitle)
    build_with_letterhead(doc, on_page)
    return f"{settings.upload_base_url.rstrip('/')}/{stored_name}"


def render_monthly_performance_report(metrics: dict, year: int, month: int, firm: dict) -> str:
    styles = getSampleStyleSheet()
    story = []

    kpi_rows = [
        ["Metric", "Value"],
        ["Total Filings", str(metrics.get("totalFilings", 0))],
        ["Completed Filings", str(metrics.get("completedFilings", 0))],
        ["Avg Turnaround (days)", str(metrics.get("avgTurnaroundTime", 0))],
        ["Total Revenue", f"${metrics.get('totalRevenue', 0):,.2f}"],
        ["Total Collected", f"${metrics.get('totalPaid', 0):,.2f}"],
    ]
    story.append(Table(kpi_rows, style=_TABLE_STYLE, colWidths=[3 * inch, 3 * inch]))
    story.append(Spacer(1, 0.35 * inch))

    revenue_data = metrics.get("revenueData") or []
    if revenue_data:
        story.append(Paragraph("Revenue by Service Type", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))
        rows = [["Service", "Revenue"]] + [
            [item.get("name", ""), f"${item.get('amount', 0):,.2f}"] for item in revenue_data
        ]
        story.append(Table(rows, style=_TABLE_STYLE, colWidths=[4 * inch, 2 * inch]))
        story.append(Spacer(1, 0.35 * inch))

    filing_type_data = metrics.get("filingTypeData") or []
    if filing_type_data:
        story.append(Paragraph("Filings by Service Type", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))
        rows = [["Service", "Count"]] + [
            [item.get("name", ""), str(item.get("count", 0))] for item in filing_type_data
        ]
        story.append(Table(rows, style=_TABLE_STYLE, colWidths=[4 * inch, 2 * inch]))

    return _save(
        lambda doc, on_page: doc.build(story, onFirstPage=on_page, onLaterPages=on_page),
        f"monthly-report-{year}-{month:02d}",
        firm,
        "Monthly Performance Report",
        f"{MONTH_NAMES[month]} {year}",
    )


def render_monthly_task_report(payload: dict, firm: dict) -> str:
    styles = getSampleStyleSheet()
    month = payload.get("month", "")
    tasks = payload.get("tasks") or []
    summary = payload.get("summary") or {}
    clients = {c["id"]: c for c in (payload.get("clients") or [])}
    users = {u["email"]: u for u in (payload.get("users") or [])}

    story = []

    kpi_rows = [
        ["Metric", "Value"],
        ["Total Tasks Completed", str(summary.get("totalTasks", 0))],
        ["Actual Hours", str(summary.get("totalHours", 0))],
        ["Estimated Hours", str(summary.get("estimatedHours", 0))],
        ["Tasks Linked to a Client", str(summary.get("tasksWithClient", 0))],
    ]
    story.append(Table(kpi_rows, style=_TABLE_STYLE, colWidths=[3 * inch, 3 * inch]))
    story.append(Spacer(1, 0.35 * inch))

    if tasks:
        story.append(Paragraph("Completed Tasks", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))
        rows = [["Task", "Client", "Assigned To", "Hours"]]
        for task in tasks:
            client = clients.get(task.get("client_id"))
            user = users.get(task.get("assigned_to"))
            rows.append([
                Paragraph(task.get("title", ""), styles["BodyText"]),
                client.get("legal_name", "") if client else "—",
                (user.get("full_name") if user else None) or task.get("assigned_to") or "—",
                str(task.get("actual_hours", 0)),
            ])
        story.append(Table(rows, style=_TABLE_STYLE, colWidths=[2.6 * inch, 1.6 * inch, 1.6 * inch, 0.8 * inch]))

    return _save(
        lambda doc, on_page: doc.build(story, onFirstPage=on_page, onLaterPages=on_page),
        f"task-report-{month}",
        firm,
        "Monthly Task Report",
        str(month),
    )


def render_invoice_pdf(invoice: dict, client: dict, firm: dict) -> str:
    styles = getSampleStyleSheet()
    label_style = ParagraphStyle(
        "LabelHeading", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9,
        textColor=NAVY, spaceAfter=4,
    )
    body_style = ParagraphStyle("InvoiceBody", parent=styles["Normal"], fontSize=9.5, leading=13)

    def block(lines: list[str]) -> Paragraph:
        return Paragraph("<br/>".join(bit for bit in lines if bit), body_style)

    bill_to_lines = [
        f"<b>{client.get('legal_name') or client.get('operating_name') or '—'}</b>",
        client.get("operating_name") if client.get("operating_name") != client.get("legal_name") else None,
        client.get("address"),
        ", ".join(bit for bit in (client.get("city"), client.get("province"), client.get("postal_code")) if bit),
        client.get("primary_email"),
        client.get("primary_phone"),
        f"GST/HST: {client.get('gst_hst_number')}" if client.get("gst_hst_number") else None,
    ]

    status = invoice.get("payment_status") or "Pending"
    status_hex = _INVOICE_STATUS_HEX.get(status, "#64748b")
    status_html = f'<font color="{status_hex}"><b>{status}</b></font>'
    details_lines = [
        f"<b>Invoice Date:</b> {invoice.get('invoice_date') or '—'}",
        f"<b>Due Date:</b> {invoice.get('due_date') or '—'}",
        f"<b>Terms:</b> {invoice.get('terms') or '—'}",
        f"<b>Status:</b> {status_html}",
    ]

    header_table = Table(
        [[Paragraph("BILL TO", label_style), Paragraph("INVOICE DETAILS", label_style)],
         [block(bill_to_lines), block(details_lines)]],
        colWidths=[3.65 * inch, 3.65 * inch],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
    ]))

    story = [header_table, Spacer(1, 0.3 * inch)]

    line_items = invoice.get("line_items") or []
    rows = [["Description", "Qty", "Rate", "Amount"]]
    for item in line_items:
        qty = item.get("quantity", 1) or 1
        rate = item.get("rate", 0) or 0
        amount = item.get("amount", qty * rate)
        rows.append([
            Paragraph(item.get("description", ""), styles["BodyText"]),
            str(qty),
            f"${rate:,.2f}",
            f"${amount:,.2f}",
        ])
    items_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ])
    story.append(Table(rows, style=items_style, colWidths=[3.7 * inch, 0.9 * inch, 1.2 * inch, 1.5 * inch]))
    story.append(Spacer(1, 0.25 * inch))

    subtotal = invoice.get("subtotal") or 0
    tax_rate = invoice.get("tax_rate") or 0
    tax_amount = invoice.get("tax_amount") or 0
    total_amount = invoice.get("total_amount") or 0
    amount_paid = invoice.get("amount_paid") or 0
    balance_due = invoice.get("balance_due") or 0

    totals_rows = [
        ["Subtotal", f"${subtotal:,.2f}"],
        [f"Tax ({tax_rate * 100:.1f}%)", f"${tax_amount:,.2f}"],
        ["Total", f"${total_amount:,.2f}"],
        ["Amount Paid", f"${amount_paid:,.2f}"],
        ["Balance Due", f"${balance_due:,.2f}"],
    ]
    totals_table = Table(totals_rows, colWidths=[1.7 * inch, 1.4 * inch])
    totals_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 1), (-1, 1), 0.5, LIGHT_GRID),
        ("BACKGROUND", (0, 2), (-1, 2), YELLOW),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 2), (-1, 2), 11),
        ("TOPPADDING", (0, 2), (-1, 2), 6),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 6),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 4), (1, 4), RED if balance_due > 0 else GREEN),
    ]))
    totals_table.hAlign = "RIGHT"
    story.append(totals_table)

    if invoice.get("notes"):
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph("NOTES", label_style))
        story.append(Paragraph(invoice["notes"], body_style))

    return _save(
        lambda doc, on_page: doc.build(story, onFirstPage=on_page, onLaterPages=on_page),
        f"invoice-{invoice.get('invoice_number', 'draft')}",
        firm,
        "Invoice",
        invoice.get("invoice_number", ""),
    )
