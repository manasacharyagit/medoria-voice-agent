import os
import json
import re
from datetime import datetime, timedelta, timezone
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv
import logging
import json

load_dotenv()
IST = pytz.timezone("Asia/Kolkata") 
SCOPES = ["https://www.googleapis.com/auth/calendar"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"), 
        scopes=SCOPES
    )
    service = build("calendar", "v3", credentials=credentials)
    return service

def extract_calendar_id(doctor_data: str) -> str:
    """Extract calendar ID from doctor's txt file content."""
    for line in doctor_data.splitlines():
        if "Calendar ID:" in line:
            return line.split("Calendar ID:")[-1].strip()
    return None

def check_slot_availability(calendar_id: str, date_str: str, time_str: str, duration_minutes: int = 30) -> bool:
    """
    Check if a slot is available on the doctor's calendar.
    Returns True if available, False if already booked.
    """
    try:
        service = get_calendar_service()

        # Parse date and time
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        start_dt = IST.localize(start_dt)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        # Check for existing events in that time window
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_dt.isoformat() ,
            timeMax=end_dt.isoformat() ,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])

        if events:
            logging.info(f"Slot {date_str} {time_str} is already booked")
            return False
        
        logging.info(f"Slot {date_str} {time_str} is available")
        return True

    except Exception as e:
        logging.error(f"Error checking slot availability: {e}")
        return False

def book_appointment(calendar_id: str, patient_name: str, patient_email: str, doctor_name: str, date_str: str, time_str: str, service_name: str, duration_minutes: int = 30) -> dict:
    """
    Books an appointment on the doctor's Google Calendar.
    Returns booking confirmation details.
    """
    try:
        service = get_calendar_service()

        # Parse date and time
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": f"Appointment - {patient_name}",
            "description": f"Service: {service_name}\nPatient: {patient_name}\nEmail: {patient_email}\nBooked via Medoria AI",
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Asia/Kolkata"
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Asia/Kolkata"
            },
            "attendees": [
                {"email": patient_email}
            ],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 60},
                    {"method": "popup", "minutes": 30}
                ]
            }
        }

        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event,
            sendUpdates="all"
        ).execute()

        logging.info(f"Appointment booked successfully: {created_event.get('id')}")
        
        return {
            "success": True,
            "event_id": created_event.get("id"),
            "event_link": created_event.get("htmlLink"),
            "start": date_str,
            "time": time_str,
            "patient": patient_name,
            "doctor": doctor_name
        }

    except Exception as e:
        logging.error(f"Error booking appointment: {e}")
        return {
            "success": False,
            "error": str(e)
        }