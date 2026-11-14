"""Export a filtered report as CSV, Excel or PDF.

PDF contains the figures as text and tables. Chart images are not embedded,
because a server-side chart render is not part of this application.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Font

ZURICH = ZoneInfo("Europe/Zurich")


def _lines(report: dict[str, object], *, title: str) -> list[str]:
    filters = report["filters"]
    assert isinstance(filters, dict)
    lines = [
        title,
        f"Zeitraum: {report['period_from']} bis {report['period_to']}",
        f"Erstellt: {datetime.now(ZURICH).strftime('%d.%m.%Y %H:%M')} Europe/Zurich",
        f"Filter Partner: {filters.get('partner_id') or 'alle'}",
        f"Filter Region: {filters.get('region') or 'alle'}",
        f"Filter Partnertyp: {filters.get('partner_type') or 'alle'}",
        f"Filter Zuständig: {filters.get('owner') or 'alle'}",
        f"Datenquelle: {report['source']}",
        "Diagramme sind als Wertetabellen enthalten, nicht als Bild.",
        "",
        "Kennzahlen",
    ]
    for kpi in report["kpis"]:
        assert isinstance(kpi, dict)
        value = "nicht berechenbar" if kpi["value"] is None else str(kpi["value"])
        lines.append(f"{kpi['section']}: {kpi['label']} = {value} ({kpi['unit']})")
        lines.append(f"Hinweis: {kpi['note']}")
    for chart in report["charts"]:
        assert isinstance(chart, dict)
        lines.append("")
        lines.append(str(chart["title"]))
        lines.append(str(chart["note"]))
        for point in chart["points"]:
            assert isinstance(point, dict)
            amount = point.get("amount")
            count = point.get("count")
            shown = amount if amount is not None else count
            lines.append(f"{point['label']}: {shown}")
    for table in report["tables"]:
        assert isinstance(table, dict)
        lines.append("")
        lines.append(str(table["title"]))
        columns = table["columns"]
        assert isinstance(columns, list)
        lines.append(" | ".join(str(column["label"]) for column in columns))
        for row in table["rows"]:
            assert isinstance(row, dict)
            lines.append(" | ".join(str(row.get(str(column["key"]), "")) for column in columns))
        lines.append(str(table["note"]))
    return lines


def render_csv(report: dict[str, object], *, title: str) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Bereich", "Art", "Bezeichnung", "Wert", "Einheit", "Hinweis"])
    filters = report["filters"]
    assert isinstance(filters, dict)
    writer.writerow(["meta", "titel", title, "", "", ""])
    writer.writerow(["meta", "zeitraum", f"{report['period_from']} bis {report['period_to']}", "", "", ""])
    writer.writerow(["meta", "erstellt", datetime.now(ZURICH).isoformat(), "", "", ""])
    writer.writerow(["meta", "filter", str(filters), "", "", str(report["source"])])
    for kpi in report["kpis"]:
        assert isinstance(kpi, dict)
        writer.writerow([kpi["section"], "kennzahl", kpi["label"], "" if kpi["value"] is None else kpi["value"], kpi["unit"], kpi["note"]])
    for chart in report["charts"]:
        assert isinstance(chart, dict)
        for point in chart["points"]:
            assert isinstance(point, dict)
            value = point["amount"] if point.get("amount") is not None else point.get("count")
            writer.writerow([chart["section"], "reihe", f"{chart['title']}: {point['label']}", value, chart["unit"], chart["note"]])
    for table in report["tables"]:
        assert isinstance(table, dict)
        for row in table["rows"]:
            assert isinstance(row, dict)
            writer.writerow([table["section"], "tabelle", table["title"], str(row), "", table["note"]])
    return buffer.getvalue().encode("utf-8-sig")


def render_xlsx(report: dict[str, object], *, title: str) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Bericht"
    bold = Font(bold=True)
    sheet["A1"] = title
    sheet["A1"].font = bold
    sheet["A2"] = f"Zeitraum {report['period_from']} bis {report['period_to']}"
    sheet["A3"] = f"Erstellt {datetime.now(ZURICH).strftime('%d.%m.%Y %H:%M')} Europe/Zurich"
    filters = report["filters"]
    sheet["A4"] = f"Filter {filters}"
    sheet["A5"] = str(report["source"])
    sheet["A6"] = "Diagramme sind als Wertetabellen enthalten, nicht als Bild."
    headers = ["Bereich", "Art", "Bezeichnung", "Wert", "Einheit", "Hinweis"]
    sheet.append([])
    sheet.append(headers)
    for cell in sheet[8]:
        cell.font = bold
    for kpi in report["kpis"]:
        assert isinstance(kpi, dict)
        sheet.append([kpi["section"], "Kennzahl", kpi["label"], kpi["value"], kpi["unit"], kpi["note"]])
    for chart in report["charts"]:
        assert isinstance(chart, dict)
        for point in chart["points"]:
            assert isinstance(point, dict)
            value = point["amount"] if point.get("amount") is not None else point.get("count")
            sheet.append([chart["section"], chart["title"], point["label"], value, chart["unit"], chart["note"]])
    for table in report["tables"]:
        assert isinstance(table, dict)
        columns = table["columns"]
        assert isinstance(columns, list)
        sheet.append([table["section"], table["title"], " | ".join(str(column["label"]) for column in columns), "", "", table["note"]])
        for row in table["rows"]:
            assert isinstance(row, dict)
            sheet.append(
                [
                    table["section"],
                    table["title"],
                    " | ".join(str(row.get(str(column["key"]), "")) for column in columns),
                    "",
                    "",
                    "",
                ]
            )
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _pdf_escape(value: str) -> str:
    encoded = value.encode("latin-1", errors="replace").decode("latin-1")
    return encoded.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_pdf(report: dict[str, object], *, title: str) -> bytes:
    lines = _lines(report, title=title)
    wrapped: list[str] = []
    for line in lines:
        text = line.replace("\n", " ")
        while len(text) > 95:
            wrapped.append(text[:95])
            text = text[95:]
        wrapped.append(text)
    page_lines = 46
    pages = [wrapped[index : index + page_lines] for index in range(0, max(len(wrapped), 1), page_lines)]
    objects: list[bytes] = []

    def add(payload: bytes) -> int:
        objects.append(payload)
        return len(objects)

    page_ids: list[int] = []
    content_ids: list[int] = []
    font_id_placeholder = 0
    catalog_id = add(b"")
    pages_id = add(b"")
    for page in pages:
        commands = ["BT", "/F1 10 Tf", "13 TL", "40 800 Td"]
        for index, line in enumerate(page):
            if index:
                commands.append("T*")
            commands.append(f"({_pdf_escape(line)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", errors="replace")
        content_ids.append(
            add(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")
        )
        page_ids.append(add(b""))
    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    assert font_id_placeholder == 0
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode("latin-1")
    objects[catalog_id - 1] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("latin-1")
    for page_id, content_id in zip(page_ids, content_ids, strict=True):
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        ).encode("latin-1")
    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets = [0]
    for number, payload in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{number} 0 obj\n".encode("latin-1"))
        buffer.write(payload)
        buffer.write(b"\nendobj\n")
    xref = buffer.tell()
    buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    buffer.write(f"trailer << /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF".encode("latin-1"))
    return buffer.getvalue()
