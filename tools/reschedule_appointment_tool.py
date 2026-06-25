import logging
from datetime import datetime, timedelta
import pytz
from tools.calendar_tool import get_calendar_service, check_slot_availability
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


def _send_reschedule_sms(patient_phone, patient_name, doctor_name,
                         new_date_str, new_time_str):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        to_number = _normalize_number(patient_phone)
        body = (
            f"Hi {patient_name}, your appointment with {doctor_name} has been "
            f"rescheduled to {new_date_str} at {new_time_str}.\n- Medoria"
        )
        msg = client.messages.create(body=body, from_=TWILIO_FROM_NUMBER, to=to_number)
        logging.info(f"Reschedule SMS sent to {to_number}, sid={msg.sid}")
        return True
    except Exception as e:
        logging.error(f"Error sending reschedule SMS: {e}")
        return False


def reschedule_appointment(calendar_id: str, patient_phone: str,
                           old_date_str: str, new_date_str: str, new_time_str: str,
                           doctor_name: str, old_time_str: str = None,
                           duration_minutes: int = 30) -> dict:
    """
    Move a future appointment to a new date/time.
    Looks up the existing appointment by phone + old_date_str (future only).
    If old_time_str is given, it disambiguates when there are multiple that day.
    Checks the new slot is free before moving. Patches the event in place
    (keeps the same event, just changes its time) and sends a confirmation SMS.
    """
    matches = find_future_appointments(calendar_id, patient_phone, old_date_str)

    if not matches:
        return {"success": False, "error": "no_appointment_found",
                "message": "I couldn't find any upcoming appointment with that number on that date."}

    if old_time_str:
        matches = [m for m in matches if m["time_str"] == old_time_str]
        if not matches:
            return {"success": False, "error": "no_appointment_at_time",
                    "message": "I couldn't find an appointment at that time on that date."}

    if len(matches) > 1:
        return {"success": False, "error": "multiple_found",
                "options": matches,
                "message": "There are multiple appointments that day. Which time should I move?"}

    appt = matches[0]

    # Make sure the new slot is free
    if not check_slot_availability(calendar_id, new_date_str, new_time_str):
        return {"success": False, "error": "new_slot_taken",
                "message": "That new slot is already taken. Please choose a different time."}

    # Patch the existing event with the new start/end
    try:
        service = get_calendar_service()
        start_dt = datetime.strptime(f"{new_date_str} {new_time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        service.events().patch(
            calendarId=calendar_id,
            eventId=appt["event_id"],
            body={
                "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Kolkata"}
            },
            sendUpdates="none"
        ).execute()
        logging.info(f"Rescheduled event {appt['event_id']} to {new_date_str} {new_time_str}")
    except Exception as e:
        logging.error(f"Error rescheduling event: {e}")
        return {"success": False, "error": str(e),
                "message": "Something went wrong while rescheduling. Please try again."}

    _send_reschedule_sms(patient_phone, appt.get("patient_name") or "there",
                         doctor_name, new_date_str, new_time_str)

    return {"success": True,
            "message": f"Appointment moved to {new_date_str} at {new_time_str}. A confirmation SMS has been sent."}