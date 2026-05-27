import os
import base64
import logging
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

def get_gmail_service():
    credentials = service_account.Credentials.from_service_account_info(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
        scopes=SCOPES
    ).with_subject(SENDER_EMAIL)
    service = build("gmail", "v1", credentials=credentials)
    return service

def create_ics_content(patient_name: str, doctor_name: str, service_name: str, date_str: str, time_str: str, clinic_name: str, clinic_address: str, duration_minutes: int = 30) -> str:
    """Creates .ics calendar invite content."""
    start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Medoria AI//EN
BEGIN:VEVENT
DTSTART:{start_dt.strftime("%Y%m%dT%H%M%S")}
DTEND:{end_dt.strftime("%Y%m%dT%H%M%S")}
SUMMARY:Appointment with {doctor_name}
DESCRIPTION:Service: {service_name}\\nPatient: {patient_name}\\nClinic: {clinic_name}\\nAddress: {clinic_address}
LOCATION:{clinic_address}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    return ics

def send_appointment_email(patient_name: str, patient_email: str, doctor_name: str, doctor_email: str, service_name: str, date_str: str, time_str: str, clinic_name: str, clinic_address: str) -> dict:
    """
    Sends appointment confirmation email with .ics calendar invite
    to both patient and doctor.
    """
    try:
        service = get_gmail_service()

        ics_content = create_ics_content(
            patient_name=patient_name,
            doctor_name=doctor_name,
            service_name=service_name,
            date_str=date_str,
            time_str=time_str,
            clinic_name=clinic_name,
            clinic_address=clinic_address
        )

        recipients = [
            {
                "email": patient_email,
                "subject": f"Appointment Confirmed - {doctor_name} on {date_str} at {time_str}",
                "body": f"""Dear {patient_name},

Your appointment has been confirmed. Here are your details:

Doctor: {doctor_name}
Service: {service_name}
Date: {date_str}
Time: {time_str}
Clinic: {clinic_name}
Address: {clinic_address}

A calendar invite is attached. Please click Accept to add it to your calendar.

For any changes please call us at Medoria.

Thank you,
Medoria AI Team"""
            },
            {
                "email": doctor_email,
                "subject": f"New Appointment - {patient_name} on {date_str} at {time_str}",
                "body": f"""Dear {doctor_name},

A new appointment has been booked via Medoria AI. Here are the details:

Patient: {patient_name}
Patient Email: {patient_email}
Service: {service_name}
Date: {date_str}
Time: {time_str}

A calendar invite is attached. Please click Accept to add it to your calendar.

Thank you,
Medoria AI Team"""
            }
        ]

        for recipient in recipients:
            msg = MIMEMultipart("mixed")
            msg["From"] = SENDER_EMAIL
            msg["To"] = recipient["email"]
            msg["Subject"] = recipient["subject"]

            msg.attach(MIMEText(recipient["body"], "plain"))

            ics_attachment = MIMEBase("text", "calendar", method="REQUEST")
            ics_attachment.set_payload(ics_content.encode("utf-8"))
            encoders.encode_base64(ics_attachment)
            ics_attachment.add_header("Content-Disposition", "attachment", filename="appointment.ics")
            msg.attach(ics_attachment)

            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(
                userId="me",
                body={"raw": raw}
            ).execute()

            logging.info(f"Email sent to {recipient['email']}")

        return {
            "success": True,
            "message": f"Confirmation emails sent to {patient_email} and {doctor_email}"
        }

    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return {
            "success": False,
            "error": str(e)
        }