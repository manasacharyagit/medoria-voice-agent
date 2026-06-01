import os
import logging
from datetime import datetime


def create_transcript(caller_number: str = "unknown") -> str:
    """Creates a new transcript file and returns the file path."""
    os.makedirs("transcripts", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    transcript_path = f"transcripts/{timestamp}_{caller_number}.txt"

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write("CALL TRANSCRIPT\n")
        f.write("===============\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Caller: {caller_number}\n\n")
        f.write("CONVERSATION\n")
        f.write("------------\n")

    logging.info(f"Transcript file created: {transcript_path}")
    return transcript_path


def write_transcript_line(transcript_path: str, role: str, text: str) -> None:
    """Appends a single line to the transcript file."""
    if not text.strip():
        return
    label = "Patient" if role == "user" else "Aria"
    line = f"{label}: {text}\n"
    logging.info(f"[TRANSCRIPT] {line.strip()}")
    with open(transcript_path, "a", encoding="utf-8") as f:
        f.write(line)


def close_transcript(transcript_path: str, summary: dict = None) -> None:
    """Writes a summary at the end of the transcript."""
    with open(transcript_path, "a", encoding="utf-8") as f:
        f.write("\n")
        f.write("CALL SUMMARY\n")
        f.write("------------\n")
        if summary:
            for key, value in summary.items():
                f.write(f"{key}: {value}\n")
        else:
            f.write("No appointment booked.\n")
    logging.info(f"Transcript closed: {transcript_path}")