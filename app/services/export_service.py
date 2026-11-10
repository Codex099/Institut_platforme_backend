from decimal import Decimal
import io
from typing import Any, List
import openpyxl
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.colors import HexColor


class ExportService:
    @staticmethod
    def export_to_excel(title: str, headers: List[str], data_rows: List[List[Any]]) -> io.BytesIO:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = title[:30]

        ws.append(headers)
        for row in data_rows:
            formatted_row = []
            for cell in row:
                if isinstance(cell, Decimal):
                    formatted_row.append(float(cell))
                else:
                    formatted_row.append(cell)
            ws.append(formatted_row)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @staticmethod
    def export_to_pdf(title: str, headers: List[str], data_rows: List[List[Any]]) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
        styles = getSampleStyleSheet()

        elements = [
            Paragraph(f"<b>{title}</b>", styles["Heading1"]),
            Spacer(1, 10),
        ]

        table_data = [headers]
        for row in data_rows:
            table_data.append([str(c) if c is not None else "" for c in row])

        table = Table(table_data)
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e3a8a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        return buffer


export_service = ExportService()

