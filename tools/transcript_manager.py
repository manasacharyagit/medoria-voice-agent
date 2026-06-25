import os
import logging
from datetime import datetime
import json
import requests
from google import genai
from dotenv import load_dotenv

load_dotenv()

class TranscriptManager:
    def __init__(self):
        self.transcript = []
        self.phone_number = "unknown"
        self.start_time = datetime.now()

    def set_phone_number(self, phone_number: str):
        self.phone_number = phone_number.replace("+", "").replace(" ", "")

    def add_user(self, text: str):
        self.transcript.append(f"User: {text}")

    def add_agent(self, text: str):
        self.transcript.append(f"Aria: {text}")
    

    def get_transcript_text(self) -> str:
        return "\n".join(self.transcript)

    def save(self):
        try:
            os.makedirs("transcripts", exist_ok=True)
            date_str = self.start_time.strftime("%Y-%m-%d")
            filename = f"transcripts/{date_str}_{self.phone_number}_{self.start_time.strftime('%H%M%S')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Call Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Phone: {self.phone_number}\n")
                f.write("-" * 40 + "\n")
                f.write(self.get_transcript_text())
            logging.info(f"Transcript saved: {filename}")

            self.analyze_sentiment()

        except Exception as e:
            logging.error(f"Failed to save transcript: {e}")
    
    def analyze_sentiment(self):
        try:
            transcript_text = self.get_transcript_text()
            if not transcript_text.strip():
                return

            client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
            
            prompt = f"""You are analyzing a customer service call transcript for Medoria, a healthcare platform.

    Analyze the following call transcript and write a detailed behavioural and sentiment report covering:

    1. Customer Mood — Was the caller anxious, calm, frustrated, confused, happy, or impatient? How did their mood change during the call?
    2. Comfort Level — Was the caller comfortable talking to the AI agent or did they seem hesitant or unsure?
    3. Query Resolution — Were the caller's questions and needs addressed properly? Did they get what they called for?
    4. Confusion Points — Were there any moments where the caller seemed confused or had to repeat themselves?
    5. Overall Experience — How would you rate the overall call experience and why?
    6. Recommendations — What could be improved to make the experience better for this type of caller?

    Keep the report conversational and insightful, not robotic.

    TRANSCRIPT:
    {transcript_text}

    Write the sentiment report now:"""

            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt
            )
            self._save_sentiment(response.text)

        except Exception as e:
            logging.error(f"Failed to analyze sentiment: {e}")

    def _save_sentiment(self, analysis: str):
        try:
            os.makedirs("sentiment", exist_ok=True)
            date_str = self.start_time.strftime("%Y-%m-%d")
            filename = f"sentiment/{date_str}_{self.phone_number}_{self.start_time.strftime('%H%M%S')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Sentiment Analysis Report\n")
                f.write(f"Call Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Phone: {self.phone_number}\n")
                f.write("=" * 40 + "\n\n")
                f.write(analysis)
            logging.info(f"Sentiment report saved: {filename}")
        except Exception as e:
            logging.error(f"Failed to save sentiment report: {e}")