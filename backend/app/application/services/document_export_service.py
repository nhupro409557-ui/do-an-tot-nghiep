from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

SHOP_NAME = "ELECTROMART VIỆT NAM"
SHOP_DESCRIPTION = "Hệ thống bán lẻ điện thoại, laptop và phụ kiện công nghệ"
RECEIPT_REASON_LABELS = {
    "NK_MUA": "Nhập mua từ nhà cung cấp",
    "NK_TRA_NCC": "Nhà cung cấp trả lại hàng",
    "NK_KH_TRA": "Khách hàng trả hàng",
    "NK_BH": "Nhập bảo hành",
    "NK_DIEUCHINH": "Điều chỉnh tăng tồn kho",
    "NK_CHUYEN": "Nhập từ kho khác",
    "NK_SANXUAT": "Nhập thành phẩm",
    "NK_KHOI_TAO": "Nhập kho khởi tạo",
    "NK_KHAC": "Nhập khác",
}


def _register_pdf_fonts() -> tuple[str, str, str]:
    windows_fonts = Path("C:/Windows/Fonts")
    regular = windows_fonts / "arial.ttf"
    bold = windows_fonts / "arialbd.ttf"
    italic = windows_fonts / "ariali.ttf"
    try:
        if regular.exists():
            pdfmetrics.registerFont(TTFont("EMVArial", str(regular)))
        if bold.exists():
            pdfmetrics.registerFont(TTFont("EMVArial-Bold", str(bold)))
        if italic.exists():
            pdfmetrics.registerFont(TTFont("EMVArial-Italic", str(italic)))
        return "EMVArial", "EMVArial-Bold", "EMVArial-Italic"
    except Exception:
        pass
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


def _num(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _money(value: Any) -> str:
    return f"{int(round(float(_num(value)))):,}".replace(",", ".")


def _date_label(value: Any) -> str:
    if isinstance(value, datetime):
        date = value
    elif value:
        try:
            date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            date = datetime.now()
    else:
        date = datetime.now()
    return f"Ngày {date.day:02d} tháng {date.month:02d} năm {date.year}"


def _receipt_reason(code: str | None) -> str:
    normalized = str(code or "NK_MUA").upper()
    label = RECEIPT_REASON_LABELS.get(normalized, RECEIPT_REASON_LABELS["NK_MUA"])
    return f"{normalized} - {label}"


def _variant_description(line: dict) -> str:
    parts = [
        str(line.get("variantColor") or "").strip(),
        str(line.get("variantConfiguration") or "").strip(),
    ]
    return " - ".join(part for part in parts if part)


def _actor(value: Any, label: Any = None) -> str:
    if label:
        return str(label)
    if value:
        text = str(value)
        return text[:8]
    return "-"


def _safe_filename(value: str, extension: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in value).strip("-")
    return f"{cleaned or 'phieu-nhap-kho'}.{extension}"


def amount_in_vietnamese(value: Any) -> str:
    units = ["", "nghìn", "triệu", "tỷ"]
    digits = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]

    def read_triple(num: int, full: bool = False) -> str:
        hundred = num // 100
        ten = (num % 100) // 10
        one = num % 10
        parts: list[str] = []
        if hundred > 0 or full:
            parts.append(f"{digits[hundred]} trăm")
        if ten > 1:
            parts.append(f"{digits[ten]} mươi")
            if one == 1:
                parts.append("mốt")
            elif one == 5:
                parts.append("lăm")
            elif one > 0:
                parts.append(digits[one])
        elif ten == 1:
            parts.append("mười")
            if one == 5:
                parts.append("lăm")
            elif one > 0:
                parts.append(digits[one])
        elif one > 0:
            if hundred > 0 or full:
                parts.append("lẻ")
            parts.append(digits[one])
        return " ".join(parts)

    rounded = int(round(float(_num(value))))
    if rounded <= 0:
        return "Không đồng."
    groups: list[int] = []
    current = rounded
    while current > 0:
        groups.append(current % 1000)
        current //= 1000
    words: list[str] = []
    for index, group in enumerate(groups):
        if group == 0:
            continue
        full = index < len(groups) - 1 and group < 100
        words.append(f"{read_triple(group, full)} {units[index]}".strip())
    result = " ".join(reversed(words))
    return f"{result[:1].upper()}{result[1:]} đồng."


def receipt_line_summaries(receipt: dict) -> list[dict]:
    summaries_by_key: dict[tuple[Any, ...], dict] = {}
    for line in receipt.get("lines") or []:
        planned = _int(line.get("plannedQuantity") or line.get("quantity"))
        tracks_imei = bool(line.get("tracksImei"))
        tracks_serial = bool(line.get("tracksSerialNumber"))
        imeis = line.get("imeis") if isinstance(line.get("imeis"), list) else []
        serial_numbers = line.get("serialNumbers") if isinstance(line.get("serialNumbers"), list) else []
        identifier_counts: list[int] = []
        if tracks_imei:
            identifier_counts.append(len(imeis))
        if tracks_serial:
            identifier_counts.append(len(serial_numbers))
        received = min(identifier_counts) if identifier_counts else _int(line.get("receivedQuantity") or planned)
        if received <= 0 and not identifier_counts:
            received = planned
        unit_cost = _num(line.get("unitCost"))
        identifier_status = "Không quản lý mã định danh"
        if tracks_imei or tracks_serial:
            parts: list[str] = []
            if tracks_imei:
                parts.append("Đủ IMEI" if len(imeis) >= planned else f"Thiếu {planned - len(imeis)} IMEI")
            if tracks_serial:
                parts.append(
                    "Đủ Serial"
                    if len(serial_numbers) >= planned
                    else f"Thiếu {planned - len(serial_numbers)} Serial"
                )
            identifier_status = " / ".join(parts)
        export_key = (
            line.get("productName"),
            line.get("variantSku"),
            line.get("variantColor"),
            line.get("variantConfiguration"),
            line.get("unitName") or "Cái",
            str(unit_cost),
        )
        existing = summaries_by_key.get(export_key)
        if existing:
            existing["planned"] += planned
            existing["received"] += received
            existing["amount"] += unit_cost * Decimal(received)
            existing["tracks_identifier"] = bool(existing["tracks_identifier"] or tracks_imei or tracks_serial)
            if identifier_status != "Không quản lý mã định danh":
                existing["identifier_status"] = identifier_status
            continue
        summaries_by_key[export_key] = {
            "line": line,
            "planned": planned,
            "received": received,
            "unit_cost": unit_cost,
            "amount": unit_cost * Decimal(received),
            "tracks_identifier": tracks_imei or tracks_serial,
            "identifier_status": identifier_status,
        }
    return list(summaries_by_key.values())


def _receipt_totals(summaries: list[dict]) -> tuple[int, int, Decimal]:
    planned = sum(item["planned"] for item in summaries)
    received = sum(item["received"] for item in summaries)
    total = sum((item["amount"] for item in summaries), Decimal("0"))
    return planned, received, total


def render_inventory_receipt_pdf(receipt: dict) -> tuple[bytes, str]:
    normal_font, bold_font, italic_font = _register_pdf_fonts()
    summaries = receipt_line_summaries(receipt)
    total_planned, total_received, total_amount = _receipt_totals(summaries)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("ReceiptBody", parent=styles["Normal"], fontName=normal_font, fontSize=9, leading=12)
    small = ParagraphStyle("ReceiptSmall", parent=body, fontSize=8, leading=10)
    center = ParagraphStyle("ReceiptCenter", parent=body, alignment=TA_CENTER)
    right = ParagraphStyle("ReceiptRight", parent=body, alignment=TA_RIGHT)
    title = ParagraphStyle("ReceiptTitle", parent=center, fontName=bold_font, fontSize=18, leading=22)
    bold = ParagraphStyle("ReceiptBold", parent=body, fontName=bold_font)
    italic = ParagraphStyle("ReceiptItalic", parent=body, fontName=italic_font)

    receipt_date = _date_label(receipt.get("postedAt") or receipt.get("createdAt"))
    status = str(receipt.get("status") or "COMPLETED")
    is_official = status == "COMPLETED"

    story: list[Any] = [
        Table(
            [
                [
                    [
                        Paragraph(SHOP_NAME, bold),
                        Paragraph(SHOP_DESCRIPTION, body),
                        Paragraph("Địa chỉ: ..............................................................", body),
                        Paragraph("Điện thoại: ...........................................................", body),
                    ]
                ]
            ],
            colWidths=[173 * mm],
            style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), 0, colors.white)],
        ),
        Spacer(1, 8),
        Paragraph("PHIẾU NHẬP KHO", title),
        Paragraph(receipt_date, ParagraphStyle("DateCenter", parent=italic, alignment=TA_CENTER, fontName=bold_font)),
        Paragraph(f"Số: {receipt.get('referenceCode') or '-'}", center),
    ]
    if not is_official:
        story.append(Paragraph(f"Phiếu nhập tạm - {status}", center))
    story.extend(
        [
            Spacer(1, 8),
            Paragraph(f"- Người giao hàng / Nhà cung cấp: <b>{receipt.get('supplierName') or '-'}</b>", body),
            Paragraph(f"- Theo chứng từ / Lý do nhập: {_receipt_reason(receipt.get('receiptReasonCode'))}", body),
            Paragraph(f"- Nhập tại kho: <b>{receipt.get('locationName') or 'Kho chính'}</b> &nbsp;&nbsp;&nbsp;&nbsp; Địa điểm: ........................................................", body),
            Paragraph(f"- Ghi chú: {receipt.get('note') or '-'}", body),
            Spacer(1, 5),
        ]
    )

    table_data: list[list[Any]] = [
        [
            Paragraph("STT", center),
            Paragraph("Tên, nhãn hiệu, quy cách phẩm chất sản phẩm, hàng hóa", center),
            Paragraph("Mã số", center),
            Paragraph("Đơn vị tính", center),
            Paragraph("Theo chứng từ", center),
            Paragraph("Thực nhập", center),
            Paragraph("Đơn giá", center),
            Paragraph("Thành tiền", center),
        ]
    ]
    for index, summary in enumerate(summaries, start=1):
        line = summary["line"]
        product_text = xml_escape(str(line.get("productName") or "-"))
        variant_description = _variant_description(line)
        if variant_description:
            product_text += f"<br/><font size='8'>{xml_escape(variant_description)}</font>"
        table_data.append(
            [
                Paragraph(str(index), center),
                Paragraph(product_text, body),
                Paragraph(str(line.get("variantSku") or line.get("productSku") or line.get("sku") or "-"), small),
                Paragraph(str(line.get("unitName") or "Cái"), center),
                Paragraph(_money(summary["planned"]), right),
                Paragraph(_money(summary["received"]), right),
                Paragraph(_money(summary["unit_cost"]), right),
                Paragraph(_money(summary["amount"]), right),
            ]
        )
    table_data.append(
        [
            "",
            Paragraph("Cộng", ParagraphStyle("TotalCenter", parent=center, fontName=bold_font)),
            "",
            "",
            Paragraph(_money(total_planned), ParagraphStyle("TotalRight1", parent=right, fontName=bold_font)),
            Paragraph(_money(total_received), ParagraphStyle("TotalRight2", parent=right, fontName=bold_font)),
            "",
            Paragraph(_money(total_amount), ParagraphStyle("TotalRight3", parent=right, fontName=bold_font)),
        ]
    )
    table = Table(
        table_data,
        repeatRows=1,
        colWidths=[12 * mm, 61 * mm, 24 * mm, 17 * mm, 19 * mm, 19 * mm, 24 * mm, 26 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, -1), (-1, -1), bold_font),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ]
        )
    )
    story.extend(
        [
            table,
            Spacer(1, 8),
            Paragraph(f"- Tổng số tiền (Viết bằng chữ): <b><i>{amount_in_vietnamese(total_amount)}</i></b>", body),
            Paragraph("- Số chứng từ gốc kèm theo: ..............................................................", body),
            Spacer(1, 8),
            Paragraph(receipt_date, ParagraphStyle("SignatureDate", parent=italic, alignment=TA_RIGHT)),
            Spacer(1, 6),
        ]
    )
    signatures = Table(
        [
            [
                Paragraph("<b>Người lập phiếu</b><br/><i>(Ký, họ tên)</i>", center),
                Paragraph("<b>Người giao hàng</b><br/><i>(Ký, họ tên)</i>", center),
                Paragraph("<b>Thủ kho</b><br/><i>(Ký, họ tên)</i>", center),
                Paragraph("<b>Kế toán trưởng</b><br/><i>(Hoặc bộ phận có nhu cầu nhập)</i><br/><i>(Ký, họ tên)</i>", center),
            ],
            [
                Paragraph(_actor(receipt.get("createdBy"), receipt.get("createdByName")), center),
                Paragraph(str(receipt.get("supplierName") or ""), center),
                Paragraph(_actor(receipt.get("postedBy"), receipt.get("postedByName")), center),
                Paragraph(_actor(receipt.get("approvedBy"), receipt.get("approvedByName")), center),
            ],
        ],
        colWidths=[43 * mm, 43 * mm, 43 * mm, 43 * mm],
        rowHeights=[26 * mm, 10 * mm],
    )
    signatures.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(signatures)
    doc.build(story)
    return buffer.getvalue(), _safe_filename(str(receipt.get("referenceCode") or "phieu-nhap-kho"), "pdf")


def _docx_text(cell, text: str = "", bold: bool = False, italic: bool = False, align=None) -> None:
    paragraph = cell.paragraphs[0]
    if align is not None:
        paragraph.alignment = align
    run = paragraph.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP


def render_inventory_receipt_docx(receipt: dict) -> tuple[bytes, str]:
    summaries = receipt_line_summaries(receipt)
    total_planned, total_received, total_amount = _receipt_totals(summaries)
    receipt_date = _date_label(receipt.get("postedAt") or receipt.get("createdAt"))
    status = str(receipt.get("status") or "COMPLETED")
    document = Document()
    section = document.sections[0]
    section.start_type = WD_SECTION.NEW_PAGE
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.2)
    section.bottom_margin = Cm(1.2)
    section.left_margin = Cm(1.2)
    section.right_margin = Cm(1.2)
    normal_style = document.styles["Normal"]
    normal_style.font.name = "Times New Roman"
    normal_style.font.size = Pt(11)

    header = document.add_table(rows=1, cols=1)
    header.alignment = WD_TABLE_ALIGNMENT.CENTER
    _docx_text(header.cell(0, 0), f"{SHOP_NAME}\n{SHOP_DESCRIPTION}\nĐịa chỉ: ..............................................................\nĐiện thoại: ...........................................................", bold=True)

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("PHIẾU NHẬP KHO")
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(18)
    date_p = document.add_paragraph()
    date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_run = date_p.add_run(receipt_date)
    date_run.bold = True
    date_run.italic = True
    document.add_paragraph(f"Số: {receipt.get('referenceCode') or '-'}").alignment = WD_ALIGN_PARAGRAPH.CENTER
    if status != "COMPLETED":
        temp_p = document.add_paragraph(f"Phiếu nhập tạm - {status}")
        temp_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph(f"- Người giao hàng / Nhà cung cấp: {receipt.get('supplierName') or '-'}")
    document.add_paragraph(f"- Theo chứng từ / Lý do nhập: {_receipt_reason(receipt.get('receiptReasonCode'))}")
    document.add_paragraph(f"- Nhập tại kho: {receipt.get('locationName') or 'Kho chính'}    Địa điểm: ........................................................")
    document.add_paragraph(f"- Ghi chú: {receipt.get('note') or '-'}")

    table = document.add_table(rows=1, cols=8)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["STT", "Tên, nhãn hiệu, quy cách phẩm chất sản phẩm, hàng hóa", "Mã số", "Đơn vị tính", "Theo chứng từ", "Thực nhập", "Đơn giá", "Thành tiền"]
    for index, header_text in enumerate(headers):
        _docx_text(table.rows[0].cells[index], header_text, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for index, summary in enumerate(summaries, start=1):
        line = summary["line"]
        row = table.add_row().cells
        product_text = str(line.get("productName") or "-")
        variant_description = _variant_description(line)
        if variant_description:
            product_text += f"\n{variant_description}"
        values = [
            str(index),
            product_text,
            str(line.get("variantSku") or line.get("productSku") or line.get("sku") or "-"),
            str(line.get("unitName") or "Cái"),
            _money(summary["planned"]),
            _money(summary["received"]),
            _money(summary["unit_cost"]),
            _money(summary["amount"]),
        ]
        for cell_index, value in enumerate(values):
            align = WD_ALIGN_PARAGRAPH.RIGHT if cell_index >= 4 else WD_ALIGN_PARAGRAPH.CENTER if cell_index in {0, 3} else WD_ALIGN_PARAGRAPH.LEFT
            _docx_text(row[cell_index], value, align=align)
    total_row = table.add_row().cells
    totals = ["", "Cộng", "", "", _money(total_planned), _money(total_received), "", _money(total_amount)]
    for cell_index, value in enumerate(totals):
        align = WD_ALIGN_PARAGRAPH.RIGHT if cell_index in {4, 5, 7} else WD_ALIGN_PARAGRAPH.CENTER
        _docx_text(total_row[cell_index], value, bold=True, align=align)

    document.add_paragraph(f"- Tổng số tiền (Viết bằng chữ): {amount_in_vietnamese(total_amount)}")
    document.add_paragraph("- Số chứng từ gốc kèm theo: ..............................................................")
    date_sign = document.add_paragraph(receipt_date)
    date_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    signature = document.add_table(rows=2, cols=4)
    signature.alignment = WD_TABLE_ALIGNMENT.CENTER
    labels = [
        "Người lập phiếu\n(Ký, họ tên)",
        "Người giao hàng\n(Ký, họ tên)",
        "Thủ kho\n(Ký, họ tên)",
        "Kế toán trưởng\n(Hoặc bộ phận có nhu cầu nhập)\n(Ký, họ tên)",
    ]
    names = [
        _actor(receipt.get("createdBy"), receipt.get("createdByName")),
        str(receipt.get("supplierName") or ""),
        _actor(receipt.get("postedBy"), receipt.get("postedByName")),
        _actor(receipt.get("approvedBy"), receipt.get("approvedByName")),
    ]
    for index, label in enumerate(labels):
        _docx_text(signature.rows[0].cells[index], label, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        _docx_text(signature.rows[1].cells[index], names[index], align=WD_ALIGN_PARAGRAPH.CENTER)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue(), _safe_filename(str(receipt.get("referenceCode") or "phieu-nhap-kho"), "docx")
