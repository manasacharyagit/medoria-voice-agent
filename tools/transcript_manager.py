import os
import logging
from datetime import datetime

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

    def save(self):
        try:
            os.makedirs("transcripts", exist_ok=True)
            date_str = self.start_time.strftime("%Y-%m-%d")
            filename = f"transcripts/{date_str}_{self.phone_number}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Call Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Phone: {self.phone_number}\n")
                f.write("-" * 40 + "\n")
                f.write("\n".join(self.transcript))
            logging.info(f"Transcript saved: {filename}")
        except Exception as e:
            logging.error(f"Failed to save transcript: {e}")