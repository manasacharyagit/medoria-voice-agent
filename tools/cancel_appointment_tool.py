import logging
from datetime import datetime, timedelta
import pytz
from tools.calendar_tool import get_calendar_service
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

IST = pytz.timezone("Asia/Kolkata")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")


def _phone_digits(phone: str) -> str:
    if not phone:
        return ""
    return "".join(ch for ch in phone if ch.isdigit())


def _normalize_number(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        phone = "+91" + phone.lstrip("0")
    return phone


def find_future_appointments(calendar_id: str, patient_phone: str, date_str: str) -> list:
    """Find future appointments on a date for a phone number. Returns list of matches."""
    try:
        service = get_calendar_service()
        day_start = IST.localize(datetime.strptime(f"{date_str} 00:00", "%Y-%m-%d %H:%M"))
        day_end = day_start + timedelta(days=1)
        now = datetime.now(IST)

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        target_digits = _phone_digits(patient_phone)[-10:]
        matches = []
        for event in events_result.get("items", []):
            description = event.get("description", "")
            if not target_digits or target_digits not in _phone_digits(description):
                continue
            start_raw = event.get("start", {}).get("dateTime")
            if not start_raw:
                continue
            start_dt = datetime.fromisoformat(start_raw)
            if start_dt.tzinfo is None:
                start_dt = IST.localize(start_dt)
            if start_dt <= now:
                continue
            service_name = None
            patient_name = None
            for line in description.splitlines():
                if line.startswith("Service:"):
                    service_name = line.split("Service:")[-1].strip()
                if line.startswith("Patient:"):
                    patient_name = line.split("Patient:")[-1].strip()
            matches.append({
                "event_id": event.get("id"),
                "time_str": start_dt.strftime("%H:%M"),
                "service_name": service_name,
                "patient_name": patient_name
            })
        logging.info(f"find_future_appointments: {len(matches)} match(es) on {date_str} for {patient_phone}")
        return matches
    except Exception as e:
        logging.error(f"Error finding appointments: {e}")
        return []


def _send_cancel_sms(patient_phone, patient_name, doctor_name, date_str, time_str):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        to_number = _normalize_number(patient_phone)
        body = (
            f"Hi {patient_name}, your appointment with {doctor_name} on "
            f"{date_str} at {time_str} has been cancelled.\n- Medoria"
        )
        msg = client.messages.create(body=body, from_=TWILIO_FROM_NUMBER, to=to_number)
        logging.info(f"Cancel SMS sent to {to_number}, sid={msg.sid}")
        return True
    except Exception as e:
        logging.error(f"Error sending cancel SMS: {e}")
        return False


def cancel_appointment(calendar_id: str, patient_phone: str, date_str: str,
                       doctor_name: str, time_str: str = None) -> dict:
    """
    Cancel a future appointment for a patient by phone + date.
    If time_str is given, only that exact appointment is cancelled (used to
    disambiguate when a patient has more than one appointment that day).
    Returns success plus a message, or a list of options if disambiguation is needed.
    """
    matches = find_future_appointments(calendar_id, patient_phone, date_str)

    if not matches:
        return {"success": False, "error": "no_appointment_found",
                "message": "I couldn't find any upcoming appointment with that number on that date."}

    # Narrow by time if provided
    if time_str:
        matches = [m for m in matches if m["time_str"] == time_str]
        if not matches:
            return {"success": False, "error": "no_appointment_at_time",
                    "message": "I couldn't find an appointment at that time on that date."}

    # More than one and no time given -> ask caller to pick
    if len(matches) > 1:
        return {"success": False, "error": "multiple_found",
                "options": matches,
                "message": "There are multiple appointments that day. Which time should I cancel?"}

    appt = matches[0]
    try:
        service = get_calendar_service()
        service.events().delete(calendarId=calendar_id, eventId=appt["event_id"]).execute()
        logging.info(f"Cancelled event {appt['event_id']}")
    except Exception as e:
        logging.error(f"Error cancelling event: {e}")
        return {"success": False, "error": str(e),
                "message": "Something went wrong while cancelling. Please try again."}

    _send_cancel_sms(patient_phone, appt.get("patient_name") or "there",
                     doctor_name, date_str, appt["time_str"])

    return {"success": True,
            "message": f"Appointment on {date_str} at {appt['time_str']} cancelled. A confirmation SMS has been sent."}