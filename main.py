import asyncio
import traceback
import json
from videosdk.agents import Agent, AgentSession, Pipeline, JobContext, RoomOptions, WorkerJob, Options, function_tool
from videosdk.plugins.google import GeminiRealtime, GeminiLiveConfig
from dotenv import load_dotenv
import os
import logging

# Add these two lines after existing imports
from tools.calendar_tool import check_slot_availability, book_appointment, extract_calendar_id
from tools.email_tool import send_appointment_email

logging.basicConfig(level=logging.INFO)

load_dotenv()

#-----Data loading fucntions--

def load_specializations():
    with open("specializations.json", "r", encoding = "utf-8") as f:
        return json.load(f)
    
def load_prompt():
    with open("prompt.txt", "r", encoding = "utf-8") as f:
        return f.read()

def build_prompt(specializations: dict):
    template = load_prompt()
    data_text = json.dumps(specializations, indent=2, ensure_ascii=False)
    return template.replace("{DOCTOR_DATA}", data_text)

#----------------------------------------------

class MyVoiceAgent(Agent):
    def __init__(self, specializations: dict):
        self.specializations = specializations
        instructions = build_prompt(specializations=specializations)

        super().__init__(
            instructions=instructions,
            tools=[self.get_doctor_info, self.check_and_book_appointment]
        )

    @function_tool
    async def get_doctor_info(self, doctor_id: str) -> dict:
        """Get full information about a specific doctor by their doctor_id. Call this when the caller asks about a specific doctor."""
        logging.info(f"get_doctor_info called with doctor_id: {doctor_id}")
        path = f"doctors/{doctor_id}.txt"
        if not os.path.exists(path):
            logging.error(f"Doctor file not found: {path}")
            return {"info": f"No information found for doctor_id: {doctor_id}"}
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        logging.info(f"Doctor data loaded successfully for: {doctor_id}")
        return {"info": data}

    @function_tool
    async def check_and_book_appointment(self, doctor_id: str, patient_name: str, patient_email: str, date_str: str, time_str: str, service_name: str) -> dict:
        """Check if a slot is available and book it if free. Call this after patient confirms all booking details."""
        logging.info(f"Booking attempt for {doctor_id} on {date_str} at {time_str}")
        
        # Load doctor data to get calendar ID and email
        path = f"doctors/{doctor_id}.txt"
        if not os.path.exists(path):
            return {"success": False, "error": "Doctor not found"}
        
        with open(path, "r", encoding="utf-8") as f:
            doctor_data = f.read()

        # Extract calendar ID and email from txt file
        calendar_id = None
        doctor_email = None
        doctor_name = None
        clinic_name = None
        clinic_address = None

        for line in doctor_data.splitlines():
            if "Calendar ID:" in line:
                calendar_id = line.split("Calendar ID:")[-1].strip()
            if "Email:" in line:
                doctor_email = line.split("Email:")[-1].strip()
            if "Name:" in line:
                doctor_name = line.split("Name:")[-1].strip()
            if "Clinic:" in line:
                clinic_name = line.split("Clinic:")[-1].strip()
            if "Address:" in line:
                clinic_address = line.split("Address:")[-1].strip()

        if not calendar_id:
            return {"success": False, "error": "Calendar ID not found for this doctor"}

        # Check slot availability
        is_available = check_slot_availability(
            calendar_id=calendar_id,
            date_str=date_str,
            time_str=time_str
        )

        if not is_available:
            return {
                "success": False,
                "error": "Slot is already booked. Please choose a different time."
            }

        # Book the appointment
        booking = book_appointment(
            calendar_id=calendar_id,
            patient_name=patient_name,
            patient_email=patient_email,
            doctor_name=doctor_name,
            date_str=date_str,
            time_str=time_str,
            service_name=service_name
        )

        if not booking["success"]:
            return {"success": False, "error": booking["error"]}

        # Send confirmation emails
        email_result = send_appointment_email(
            patient_name=patient_name,
            patient_email=patient_email,
            doctor_name=doctor_name,
            doctor_email=doctor_email,
            service_name=service_name,
            date_str=date_str,
            time_str=time_str,
            clinic_name=clinic_name,
            clinic_address=clinic_address
        )

        if email_result["success"]:
            return {
                "success": True,
                "message": f"Appointment booked and confirmation emails sent to {patient_email} and {doctor_email}"
            }
        else:
            return {
                "success": True,
                "message": "Appointment booked but email sending failed. Please note the details."
            }

        async def on_enter(self) -> None:
            await self.session.say(
                "Hello! Thank you for calling Medoria. I'm Aria, your virtual assistant. "
                "Are you looking for a specific doctor, or can I help you find the right specialist for your concern?"
            )

        async def on_exit(self) -> None:
            await self.session.say("Thank you for calling Medoria. Have a great day, take care!")

           

        
async def start_session(context: JobContext):
    specialization = load_specializations()
    model = GeminiRealtime(
        model="gemini-2.5-flash-native-audio-preview-12-2025",
        api_key=os.getenv("GOOGLE_API_KEY"),
        config=GeminiLiveConfig(
            voice="Kore",
            response_modalities=["AUDIO"],
            input_audio_transcription={}, #AI talks even in inbound
        ),
    )
    pipeline = Pipeline(llm=model)
    agent = MyVoiceAgent(specializations=specialization)
    session = AgentSession(agent=agent, pipeline=pipeline)

    await context.run_until_shutdown(session=session, wait_for_participant=True)
    
    


def make_context() -> JobContext:
    room_options = RoomOptions()
    return JobContext(room_options=room_options)

if __name__ == "__main__":
    try:
        options = Options(
            agent_id="MyTelephonyAgent",
            register=True,
            max_processes=10,
            host="localhost",
            port=8081,
            auth_token=os.getenv("VIDEOSDK_AUTH_TOKEN")
        )
        job = WorkerJob(entrypoint=start_session, jobctx=make_context, options=options)
        job.start()
    except Exception as e:
        traceback.print_exc()

