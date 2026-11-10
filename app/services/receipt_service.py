from datetime import datetime, timezone
from decimal import Decimal
import io
from typing import Optional
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.payment import Payment


class ReceiptService:
    @staticmethod
    def generate_next_receipt_number(db: Session, branch_id: int) -> str:
        """Generate sequential receipt number per branch: REC-{CODE}-{YEAR}-{00001}."""
        now = datetime.now(timezone.utc)
        year = now.year
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        b_code = (branch.code or f"BR{branch_id}").upper()

        prefix = f"REC-{b_code}-{year}-"
        # Count existing payments for this branch matching prefix
        count = (
            db.query(func.count(Payment.id))
            .filter(Payment.branch_id == branch_id, Payment.receipt_number.like(f"{prefix}%"))
            .scalar()
            or 0
        )
        return f"{prefix}{count + 1:05d}"

    @classmethod
    def generate_payment_receipt_pdf(
        cls,
        payment: Payment,
        student_name: str,
        group_name: str,
        course_name: str,
        total_fee: Decimal,
        total_paid: Decimal,
        remaining_balance: Decimal,
        branch_name: str,
    ) -> io.BytesIO:
        """Create an official PDF receipt using ReportLab."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A5),
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=HexColor("#1e3a8a"),
            alignment=1,
            spaceAfter=10,
        )
        header_meta = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=HexColor("#4b5563"))
        bold_style = ParagraphStyle("Bold", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold")
        text_style = ParagraphStyle("Text", parent=styles["Normal"], fontSize=10)

        elements = []

        # Header
        elements.append(Paragraph(f"<b>{branch_name.upper()}</b>", title_style))
        elements.append(Paragraph(f"REÇU DE PAIEMENT N° : <b>{payment.receipt_number}</b>", title_style))
        elements.append(Spacer(1, 10))

        # Metadata table
        meta_data = [
            [
                Paragraph(f"<b>Date :</b> {payment.paid_at.strftime('%d/%m/%Y %H:%M')}", header_meta),
                Paragraph(f"<b>Mode de règlement :</b> {payment.method.upper()}", header_meta),
            ],
            [
                Paragraph(f"<b>Étudiant :</b> {student_name}", bold_style),
                Paragraph(f"<b>Formation :</b> {course_name} ({group_name})", text_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[260, 260])
        meta_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ])
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 15))

        # Financial breakdown table
        fin_data = [
            ["Désignation", "Montant (DZD / DA)"],
            ["Total formation & inscription", f"{total_fee:,.2f} DA"],
            ["Montant réglé sur ce versement", f"{payment.amount:,.2f} DA"],
            ["Total cumulé versé", f"{total_paid:,.2f} DA"],
            ["Reste à payer", f"{remaining_balance:,.2f} DA"],
        ]
        fin_table = Table(fin_data, colWidths=[340, 180])
        fin_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e3a8a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 2), (-1, 2), HexColor("#f0fdf4")),  # Highlight this payment
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(fin_table)
        elements.append(Spacer(1, 25))

        # Signatures
        sig_data = [
            ["Signature de l'Agent Administratif", "Signature de l'Étudiant / Parent"],
            ["\n\n_________________________", "\n\n_________________________"],
        ]
        sig_table = Table(sig_data, colWidths=[260, 260])
        sig_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#6b7280")),
            ])
        )
        elements.append(sig_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @classmethod
    def generate_transfer_receipt_pdf(
        cls,
        transfer,
        from_user_name: str,
        to_user_name: str,
        branch_name: str,
    ) -> io.BytesIO:
        """Create PDF receipt for fund transfer."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A5),
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, textColor=HexColor("#1e3a8a"), alignment=1)
        bold_style = ParagraphStyle("Bold", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold")
        text_style = ParagraphStyle("Text", parent=styles["Normal"], fontSize=10)

        elements = [
            Paragraph(f"<b>BORDEREAU DE REMISE DE FONDS</b>", title_style),
            Paragraph(f"Référence : <b>{transfer.reference}</b> | Branche : {branch_name}", text_style),
            Spacer(1, 15),
        ]

        data = [
            ["Détail de l'opération", "Information"],
            ["Émetteur / Remettant", from_user_name],
            ["Bénéficiaire / Réceptionnaire", to_user_name],
            ["Date de création", transfer.created_at.strftime('%d/%m/%Y %H:%M')],
            ["Date de confirmation", transfer.confirmed_at.strftime('%d/%m/%Y %H:%M') if transfer.confirmed_at else "En attente"],
            ["Montant remis", f"{transfer.amount:,.2f} DA"],
            ["Motif", transfer.reason],
            ["Statut", transfer.status.upper()],
        ]
        table = Table(data, colWidths=[200, 320])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e3a8a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 5), (-1, 5), HexColor("#fef3c7")),
                ("FONTNAME", (0, 5), (-1, 5), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        elements.append(table)
        elements.append(Spacer(1, 20))

        doc.build(elements)
        buffer.seek(0)
        return buffer


receipt_service = ReceiptService()

