import os
import logging
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")  # SMS-capable Twilio number

def _normalize_number(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0")   # default to India; adjust if needed
    return phone

def send_appointment_sms(patient_name, patient_phone, doctor_name, service_name,
                         date_str, time_str, clinic_name, clinic_address) -> dict:
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        to_number = _normalize_number(patient_phone)
        body = (
            f"Hi {patient_name}, your appointment with {doctor_name} is confirmed.\n"
            f"Service: {service_name}\n"
            f"Date: {date_str} at {time_str}\n"
            f"{clinic_name}, {clinic_address}\n"
            f"- Medoria"
        )
        message = client.messages.create(body=body, from_=TWILIO_FROM_NUMBER, to=to_number)
        logging.info(f"SMS sent to {to_number}, sid={message.sid}")
        return {"success": True, "sid": message.sid, "to": to_number}
    except Exception as e:
        logging.error(f"Error sending SMS: {e}")
        return {"success": False, "error": str(e)}