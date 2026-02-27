from core.cloudinary import CloudinaryClient
from core.pdf_geenrate import PDFGenerator
from models.enums import PDFStatus, TicketStatus
from repositories.ticket_repo import TicketRepo
from utils.security_generate import UserGenerate


class GenerateMultipleTicketService:

    def __init__(self, db):

        self.ticket_repo = TicketRepo(db)
        self.generate = UserGenerate()
        self.pdf = PDFGenerator()
        self.cloudinary = CloudinaryClient()

    def generate_multiple_tickets(self, payment, quantity, ticket_type_id: str):

        created_tickets = []

        try:
            for _ in range(quantity):

                ticket = self.ticket_repo.create_ticket(
                    user_id=payment.user_id,
                    event_id=payment.event_id,
                    ticket_type_id=ticket_type_id,
                    payment_id=payment.id,
                    price_paid=payment.amount / quantity,
                    status=TicketStatus.SOLD,
                )

                ticket.pdf_status = PDFStatus.GENERATING
                self.ticket_repo.sync_db_flush()

                ticket_number = self.generate.generate_ticket_number(ticket.id)

                qr_code_path = self.generate.generate_qr(ticket_number)

                self.ticket_repo.sync_set_ticket_details(
                    ticket.id,
                    ticket_number,
                    qr_code_path,
                )

                pdf_path = self.pdf.generate_ticket_pdf(ticket, qr_code_path)

                result = self.cloudinary.backend_upload(
                    resource_type="raw",
                    file_path=pdf_path,
                    folder="ticket_pass",
                )

                if not result:

                    raise Exception("Cloudinary upload failed")

                public_id = result.get("public_id")
                file_url = result.get("secure_url")

                self.ticket_repo.sync_set_ticket_url(
                    ticket.id,
                    file_url,
                    public_id,
                )

                ticket.pdf_status = PDFStatus.READY
                self.ticket_repo.sync_db_flush()

                created_tickets.append(ticket)

            self.ticket_repo.sync_db_commit()

            return created_tickets

        except Exception as e:
            self.ticket_repo.sync_db_rollback()

            ticket.pdf_status = PDFStatus.FAILED
            self.cloudinary.sync_delete(
                public_id=public_id, resource_type="raw"
            )
            self.ticket_repo.sync_db_commit()
            raise

        finally:
            if pdf_path and pdf_path.exists():
                try:
                    pdf_path.unlink()
                except Exception:
                    pass

    def generate_ticket_pass(self, ticket_id: int):

        try:

            ticket = self.ticket_repo.sync_get_ticket_id(ticket_id)

            self.ticket_repo.sync_update_pdf_status(
                ticket.id, PDFStatus.GENERATING)

            ticket_number = self.generate.generate_ticket_number(ticket.id)

            qr_code_path = self.generate.generate_qr(ticket_number)

            self.ticket_repo.sync_set_ticket_details(
                ticket.id,
                ticket_number,
                qr_code_path,
            )

            pdf_path = self.pdf.generate_ticket_pdf(ticket, qr_code_path)

            result = self.cloudinary.backend_upload(
                resource_type="raw",
                file_path=pdf_path,
                folder="ticket_pass",
            )

            if not result:

                raise Exception("Cloudinary upload failed")

            public_id = result.get("public_id")
            file_url = result.get("secure_url")

            self.ticket_repo.sync_set_ticket_url(
                ticket.id,
                file_url,
                public_id,
            )

            self.ticket_repo.sync_update_pdf_status(ticket.id, PDFStatus.READY)

        except Exception as e:
            self.ticket_repo.sync_db_rollback()
            self.ticket_repo.sync_update_pdf_status(
                ticket.id, PDFStatus.FAILED)
            self.cloudinary.sync_delete(
                public_id=public_id, resource_type="raw"
            )

            raise

        finally:
            if pdf_path and pdf_path.exists():
                try:
                    pdf_path.unlink()
                except Exception:
                    pass
