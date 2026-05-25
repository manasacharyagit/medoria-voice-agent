import asyncio
import traceback
import json
from videosdk.agents import Agent, AgentSession, Pipeline, JobContext, RoomOptions, WorkerJob, Options, function_tool
from videosdk.plugins.google import GeminiRealtime, GeminiLiveConfig
from dotenv import load_dotenv
import os
import logging
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
            tools=[self.get_doctor_info]
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

