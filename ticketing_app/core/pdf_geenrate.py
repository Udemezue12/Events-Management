from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import os
from pathlib import Path
BASE_PATH = Path("media/tickets")
BASE_PATH.mkdir(parents=True, exist_ok=True)


class PDFGenerator:
    @staticmethod
    def generate_ticket_pdf(ticket, qr_path):

        file_path = BASE_PATH / f"{ticket.ticket_number}.pdf"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        doc = SimpleDocTemplate(file_path)
        elements = []

        styles = getSampleStyleSheet()

        elements.append(
            Paragraph(f"<b>{ticket.event.title}</b>", styles["Title"]))
        elements.append(Spacer(1, 0.2 * inch))

        elements.append(Paragraph(
            f"Name: {ticket.user.first_name} {ticket.user.last_name}", styles["Normal"]))
        elements.append(
            Paragraph(f"Ticket Number: {ticket.ticket_number}", styles["Normal"]))
        elements.append(
            Paragraph(f"Type: {ticket.ticket_type.ticket_type.value}", styles["Normal"]))
        elements.append(
            Paragraph(f"Status: {ticket.status.value}", styles["Normal"]))
        elements.append(
            Paragraph(f"Event Date: {ticket.event.start_time}", styles["Normal"]))

        elements.append(Spacer(1, 0.5 * inch))

        elements.append(Image(qr_path, width=2*inch, height=2*inch))

        doc.build(elements)

        return file_path
