import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from core.email_breaker import email_breaker as breaker
from core.settings import settings


def sync_send(message: MIMEMultipart):
    async def smtp_operation():
        with smtplib.SMTP(
            host=settings.EMAIL_SERVER,
            port=settings.EMAIL_PORT,
            timeout=5,
        ) as server:
            if settings.EMAIL_USE_TLS:
                server.starttls()

            server.login(
                settings.EMAIL_USER,
                settings.EMAIL_PASSWORD,
            )

            server.send_message(message)

    return breaker.sync_call(smtp_operation)


async def async_send(message):
    async def smtp_operation():
        await aiosmtplib.send(
            message,
            hostname=settings.EMAIL_SERVER,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_USER,
            password=settings.EMAIL_PASSWORD,
            start_tls=settings.EMAIL_USE_TLS,
        )

    return await breaker.call(smtp_operation)


async def send_verification_email(email: str, otp: str, token: str, name: str):

    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Email Verification</h2>
            <p>Hello {name},</p>
            <p>Your one-time password (OTP) is:</p>
            <h3 style="color:#007bff;">{otp}</h3>
            <p>You can also verify your email by clicking the link below:</p>
            <a href="{verify_link}" style="display:inline-block;background:#28a745;color:white;padding:10px 20px;
               text-decoration:none;border-radius:4px;">Verify Email</a>
            <p>This link will expire in 1 hour.</p>
            <hr>
            <p>If you did not request this, please ignore this message.</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

    message = MIMEMultipart("alternative")
    message["Subject"] = "Verify Your Email"
    message["From"] = settings.EMAIL_USER
    message["To"] = email
    message.attach(MIMEText(html_content, "html"))

    try:
        await async_send(message)
    except Exception as e:
        print(f"Error sending verification email: {e}")
        raise


async def send_password_reset_link(email: str, otp: str, token: str):

    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Email Verification</h2>
            <p>Hello,</p>
            <p>Your one-time password (OTP) is:</p>
            <h3 style="color:#007bff;">{otp}</h3>
            <p>You can also verify your email by clicking the link below:</p>
            <a href="{reset_link}" style="display:inline-block;background:#28a745;color:white;padding:10px 20px;
               text-decoration:none;border-radius:4px;">Verify Email</a>
            <p>This link will expire in 1 hour.</p>
            <hr>
            <p>If you did not request this, please ignore this message.</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

    message = MIMEMultipart("alternative")
    message["Subject"] = "Reset Your Password"
    message["From"] = settings.EMAIL_USER
    message["To"] = email
    message.attach(MIMEText(html_content, "html"))

    try:
        await async_send(message)
    except Exception as e:
        print(f"Error sending verification email: {e}")
        raise


def sync_send_event_email(
    email: str,
    email_type: str,
    name: str,
    amount: str | None = None,
    event_name: str | None = None,
    ticket_id: int | None = None
):
    """
    email_type:
        - "ticket_expired"
        - "payment_success"
        - "refund_processing"
        - "refund_completed"
    """

    # -------- SUBJECT + CONTENT BUILDER --------

    if email_type == "ticket_expired":

        subject = "Reserved Ticket Expired"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #f0ad4e;">Ticket Reservation Expired</h2>

            <p>Dear {name},</p>

            <p>Your reserved ticket with this id:{ticket_id} has expired.</p>

            <p>Please book again if you are still interested.</p>

            <br>
            <p>Best regards,<br><strong>Support Team</strong></p>
        </body>
        </html>
        """

    elif email_type == "payment_success":

        subject = "Payment Successful"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #5cb85c;">Payment Confirmation</h2>

            <p>Dear {name},</p>

            <p>Your payment was successful.</p>

            {"<p><strong>Event:</strong> " + event_name + "</p>" if event_name else ""}

            <p>Your ticket has been confirmed.</p>

            <br>
            <p>Best regards,<br><strong>Support Team</strong></p>
        </body>
        </html>
        """

    elif email_type == "refund_processing":

        subject = "Refund Processing"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #f0ad4e;">Refund In Progress</h2>

            <p>Dear {name},</p>

            <p>Your refund is currently being processed.</p>

            {"<p><strong>Event:</strong> " + event_name + "</p>" if event_name else ""}

            <p>The amount will reflect shortly.</p>

            <br>
            <p>Best regards,<br><strong>Support Team</strong></p>
        </body>
        </html>
        """
    elif email_type == "ticket_reserved":

        subject = "Ticket Successfully Reserved"

        html_content = f"""<html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #0275d8;">Ticket Reserved Successfully</h2>

        <p>Dear {name},</p>

        <p>
            Your ticket has been successfully reserved.
        </p>

        {"<p><strong>Event:</strong> " + event_name + "</p>" if event_name else ""}

        <p>
            Please complete your payment before the reservation expires 
            to secure your spot.
        </p>

        <p>
            If payment is not completed within the allowed time, 
            the ticket will be released automatically.
        </p>

        <br>
        <p>Best regards,<br>
        <strong>Support Team</strong></p>
      </body>
      </html>
      """

    elif email_type == "refund_completed":

        subject = "Refund Confirmation"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #d9534f;">Refund Completed</h2>

            <p>Dear {name},</p>

            <p>
                Your payment of <strong>{amount}</strong> has been successfully refunded.
            </p>

            {"<p><strong>Event:</strong> " + event_name + "</p>" if event_name else ""}

            <p>
                The refunded amount will reflect based on your bank's processing timeline.
            </p>

            <p>If you need assistance, please contact support.</p>

            <br>
            <p>Best regards,<br><strong>Support Team</strong></p>
        </body>
        </html>
        """

    else:
        raise ValueError("Invalid email_type provided")

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.EMAIL_USER
    message["To"] = email
    message.attach(MIMEText(html_content, "html"))

    try:
        sync_send(message)
    except Exception as e:
        print(f"Error sending  email: {e}")
        raise
