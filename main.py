import asyncio
import traceback
import json

from datetime import date
from videosdk.plugins.silero import SileroVAD
from videosdk.plugins.turn_detector import NamoTurnDetectorV1, pre_download_namo_turn_v1_model

from videosdk.agents import Agent, AgentSession, Pipeline, JobContext, RoomOptions, WorkerJob, EOUConfig, InterruptConfig, Options, function_tool
from videosdk.plugins.google import GeminiRealtime, GoogleLLM, GeminiLiveConfig
from videosdk.plugins.sarvamai import SarvamAISTT, SarvamAITTS
from dotenv import load_dotenv
from tools.cancel_appointment_tool import cancel_appointment
from tools.reschedule_appointment_tool import reschedule_appointment
import os

import logging

# Add these two lines after existing imports
from tools.calendar_tool import check_slot_availability, book_appointment, extract_calendar_id
from tools.email_tool import send_doctor_email
from tools.sms_tool import send_appointment_sms
from tools.transcript_manager import TranscriptManager
logging.basicConfig(level=logging.INFO)

load_dotenv()


#-----Data loading fucntions--

def load_specializations():
    with open("specializations.json", "r", encoding = "utf-8") as f:
        return json.load(f)
    
def load_prompt():
    with open("prompt.txt", "r", encoding = "utf-8") as f:
        return f.read()

def build_prompt(doctor_data: str, doctor_id: str, caller_number: str = "unknown") -> str:
    today = date.today().strftime("%Y-%m-%d")
    template = load_prompt()
    doctor_name = "the doctor"
    for line in doctor_data.splitlines():
        if "Name:" in line:
            doctor_name = line.split("Name:")[-1].strip()
            break
    return template.replace("{DOCTOR_DATA}", doctor_data)\
                   .replace("{DOCTOR_NAME}", doctor_name)\
                   .replace("{DOCTOR_ID}", doctor_id)\
                   .replace("{CALLER_NUMBER}", caller_number)\
                   .replace("{TODAY}", today)


def find_doctor_by_number(phone_number: str):
    for filename in os.listdir("doctors"):
        if filename.endswith(".txt"):
            with open(f"doctors/{filename}", "r", encoding="utf-8") as f:
                content = f.read()
            for line in content.splitlines():
                if "Phone:" in line:
                    file_number = line.split("Phone:")[-1].strip()
                    if file_number == phone_number:
                        doctor_id = filename.replace(".txt", "")
                        logging.info(f"Doctor found: {doctor_id} for number {phone_number}")
                        return doctor_id, content
    logging.warning(f"No doctor found for number: {phone_number}")
    return None, None
    

#----------------------------------------------

class MyVoiceAgent(Agent):
    def __init__(self, doctor_id: str, doctor_data: str, caller_number: str = "unknown"):
        self.doctor_id = doctor_id
        self.doctor_data = doctor_data
        self.caller_number = caller_number or "unknown"
        instructions = build_prompt(doctor_data, doctor_id, self.caller_number)
        super().__init__(instructions=instructions, tools=[])
        self._tools = [self.get_doctor_info, self.schedule_appointment,self.cancel_booking, self.reschedule_booking]

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
    async def schedule_appointment(self, doctor_id: str, patient_name: str, patient_phone: str, date_str: str, time_str: str, service_name: str) -> dict:
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
            doctor_name=doctor_name,
            date_str=date_str,
            time_str=time_str,
            service_name=service_name,
            patient_phone=patient_phone
        )

        if not booking["success"]:
            return {"success": False, "error": booking["error"]}

        # Send SMS to patient
        sms_result = send_appointment_sms(
            patient_name=patient_name,
            patient_phone=patient_phone,
            doctor_name=doctor_name,
            service_name=service_name,
            date_str=date_str,
            time_str=time_str,
            clinic_name=clinic_name,
            clinic_address=clinic_address
        )

        # Notify doctor by email
        send_doctor_email(
            doctor_name=doctor_name,
            doctor_email=doctor_email,
            patient_name=patient_name,
            patient_phone=patient_phone,
            service_name=service_name,
            date_str=date_str,
            time_str=time_str
        )

        if sms_result["success"]:
            return {
                "success": True,
                "message": f"Appointment booked and confirmation SMS sent to {patient_phone}"
            }
        else:
            return {
                "success": True,
                "message": "Appointment booked but SMS sending failed. Please note the details."
            }
        
    @function_tool
    async def cancel_booking(self, doctor_id: str, patient_phone: str, date_str: str, time_str: str = None) -> dict:
        """Cancel a future appointment by patient phone and date. Pass time_str only if the caller has specified which appointment when they have more than one that day."""
        path = f"doctors/{doctor_id}.txt"
        if not os.path.exists(path):
            return {"success": False, "error": "Doctor not found"}
        with open(path, "r", encoding="utf-8") as f:
            doctor_data = f.read()
        calendar_id = None
        doctor_name = None
        for line in doctor_data.splitlines():
            if "Calendar ID:" in line:
                calendar_id = line.split("Calendar ID:")[-1].strip()
            if "Name:" in line:
                doctor_name = line.split("Name:")[-1].strip()
        if not calendar_id:
            return {"success": False, "error": "Calendar ID not found for this doctor"}
        return cancel_appointment(
            calendar_id=calendar_id,
            patient_phone=patient_phone,
            date_str=date_str,
            doctor_name=doctor_name,
            time_str=time_str
        )

    @function_tool
    async def reschedule_booking(self, doctor_id: str, patient_phone: str, old_date_str: str, new_date_str: str, new_time_str: str, old_time_str: str = None) -> dict:
        """Move a future appointment to a new date and time. Pass old_time_str only if the caller specifies which appointment when they have more than one on the old date."""
        path = f"doctors/{doctor_id}.txt"
        if not os.path.exists(path):
            return {"success": False, "error": "Doctor not found"}
        with open(path, "r", encoding="utf-8") as f:
            doctor_data = f.read()
        calendar_id = None
        doctor_name = None
        for line in doctor_data.splitlines():
            if "Calendar ID:" in line:
                calendar_id = line.split("Calendar ID:")[-1].strip()
            if "Name:" in line:
                doctor_name = line.split("Name:")[-1].strip()
        if not calendar_id:
            return {"success": False, "error": "Calendar ID not found for this doctor"}
        return reschedule_appointment(
            calendar_id=calendar_id,
            patient_phone=patient_phone,
            old_date_str=old_date_str,
            new_date_str=new_date_str,
            new_time_str=new_time_str,
            doctor_name=doctor_name,
            old_time_str=old_time_str
        )


    

    async def on_enter(self) -> None:
        doctor_name = "the doctor"
        logging.info(f"doctor_data preview: {self.doctor_data[:100] if hasattr(self, 'doctor_data') else 'NOT SET'}")
        for line in self.doctor_data.splitlines():
            if "Name:" in line:
                doctor_name = line.split("Name:")[-1].strip()
                break
        logging.info(f"Extracted doctor_name: {doctor_name}")
        await self.session.say(
            f"Hello! Thank you for calling {doctor_name}'s clinic. I'm Aria, your virtual assistant. How can I help you today?"
        )

    async def on_exit(self) -> None:
        await self.session.say("Thank you for calling Medoria. Have a great day, take care!")

        
async def start_session(context: JobContext):

    # Create fresh transcript for this call
    from tools.transcript_manager import TranscriptManager
    call_transcript = TranscriptManager()

    # Hook into logging inside this process
    class CallTranscriptHandler(logging.Handler):
        def emit(self, record):
            msg = record.getMessage()
            if "user input speech:" in msg:
                text = msg.split("user input speech:")[-1].strip()
                call_transcript.add_user(text)
            elif "agent output speech:" in msg:
                text = msg.split("agent output speech:")[-1].strip()
                call_transcript.add_agent(text)
            elif "Audio stream enabled for participant:" in msg:
                phone = msg.split("Audio stream enabled for participant:")[-1].strip()
                call_transcript.set_phone_number(phone)

    handler = CallTranscriptHandler()
    logging.getLogger("videosdk.agents.metrics.metrics_collector").addHandler(handler)
    logging.getLogger("videosdk.agents.room.room").addHandler(handler)

    
    dialed_number = context.metadata.get("sipCallTo")
    caller_number = context.metadata.get("sipCallFrom") or "unknown"
    logging.info(f"Dialed number: {dialed_number}")
    logging.info(f"Caller number: {caller_number}")
    doctor_id, doctor_data = find_doctor_by_number(dialed_number)
    if not doctor_data:
        logging.error(f"No doctor found for {dialed_number}")
        doctor_id = "unknown"
        doctor_data = "No doctor information available for this number."

    stt = SarvamAISTT(
        model="saaras:v3",
        language="en-IN",  # handles Hindi, Punjabi, English all correctly
    )

    llm = GoogleLLM(
        # model="gemini-3.5-flash",
        model="gemini-3.1-flash-lite",
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    tts = SarvamAITTS(
    model="bulbul:v3",
    speaker="shubh",
    language="en-IN",
    
    )

    vad = SileroVAD(
    threshold=0.5,
    min_speech_duration=0.1,
    min_silence_duration=0.75
    )

    turn_detector = NamoTurnDetectorV1(
    language="en",
    threshold=0.7
    )

    
    # model = GeminiRealtime(
    #     model="gemini-2.5-flash-native-audio-preview-12-2025",
    #     api_key=os.getenv("GOOGLE_API_KEY"),
    #     config=GeminiLiveConfig(
    #         voice="Kore",
    #         response_modalities=["AUDIO"],
    #         input_audio_transcription={}
    #     ),
    # )
    # pipeline = Pipeline(llm=model)
    logging.info(f"Context metadata: {context.metadata}")
    pre_download_namo_turn_v1_model(language="en")
    pipeline = Pipeline(
        llm=llm, stt=stt, tts=tts,
        vad=vad,
        turn_detector=turn_detector,
        eou_config=EOUConfig(
            mode='ADAPTIVE',
            min_max_speech_wait_timeout=[0.3, 0.6]
        )
        )
    agent = MyVoiceAgent(doctor_id=doctor_id, doctor_data=doctor_data, caller_number=caller_number)
    session = AgentSession(agent=agent, pipeline=pipeline)

    try:
        await context.run_until_shutdown(session=session, wait_for_participant=True)
    finally:
        call_transcript.save()
    
    


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