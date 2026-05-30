import requests
import os
import schedule
import time
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

VIDEOSDK_TOKEN = os.getenv("VIDEOSDK_AUTH_TOKEN")
OUTBOUND_GATEWAY_ID = "46b7d33a-4cdd-48fe-a733-2869442f2b9e"
CALLER_ID = "+17432508570"
PHONE_TO_CALL = "+918709252948"  # ← replace with actual number

headers = {
    "Authorization": VIDEOSDK_TOKEN,
    "Content-Type": "application/json"
}

def make_outbound_call():
    logging.info(f"Initiating outbound call to {PHONE_TO_CALL}...")
    
    payload = {
        "gatewayId": OUTBOUND_GATEWAY_ID,
        "callerId": CALLER_ID,
        "sipCallTo": PHONE_TO_CALL,
        "agentId": "MyTelephonyAgent",
        "agentType": "self_hosted",
        "instructions": "You are Aria, a friendly AI assistant from Medoria. Start the conversation warmly by asking how the person is doing. Keep it short and friendly."
    }

    response = requests.post(
        "https://api.videosdk.live/v2/sip/call",
        headers=headers,
        json=payload
    )

    if response.status_code in [200, 201]:
        logging.info(f"Call initiated successfully: {response.json()}")
    else:
        logging.error(f"Failed to initiate call: {response.status_code} - {response.text}")

def schedule_call():
    schedule.every().day.at("16:43").do(make_outbound_call)
    logging.info("Call scheduled for 5:00 PM today")
    
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    schedule_call()