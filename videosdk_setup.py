# videosdk_setup.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

VIDEOSDK_TOKEN = os.getenv("VIDEOSDK_AUTH_TOKEN")
OUTBOUND_USERNAME = os.getenv("OUTBOUND_GATEWAY_AUTH_USERNAME")
OUTBOUND_PASSWORD = os.getenv("OUTBOUND_GATEWAY_AUTH_PASSWORD") 

API_URL = "https://api.videosdk.live/v2/sip/inbound-gateways"

OUTBOUND_URL = "https://api.videosdk.live/v2/sip/outbound-gateways"

ROUTING_RULES_URL = "https://api.videosdk.live/v2/sip/routing-rules"

headers = {
    "Authorization": VIDEOSDK_TOKEN,
    "Content-Type": "application/json"
}

#Checks if 'My Inbound Gateway' exists. If missing, creates it using the exact specifications.
def initialize_inbound_gateway():
    
    try:
        print("Checking existing VideoSDK gateways...")
        response = requests.get(API_URL, headers=headers)
        response.raise_for_status()
        
        existing_gateways = response.json().get("data", [])
        
        my_gateway = next((g for g in existing_gateways if g.get("name") == "My Inbound Gateway"), None)
        
        if my_gateway:
            gateway_id = my_gateway.get("id")
            sip_uri = f"sip:{gateway_id}@sip.videosdk.live"

            print(f"Gateway already exists. Use this URI: {sip_uri}")
            return sip_uri

        print("Gateway not found. Provisioning 'My Inbound Gateway'...")
        payload = {
            "name": "My Inbound Gateway",
            "numbers": ["+17432508570"]
        }
        
        create_response = requests.post(API_URL, headers=headers, json=payload)
        create_response.raise_for_status()
        
        
        response_json = create_response.json() # Parse the JSON payload once safely

        new_sip_uri = (
            response_json.get("sipUri") or 
            response_json.get("data", {}).get("sipUri")
        )
        
        if new_sip_uri:
            print(f"Gateway created successfully! URI: {new_sip_uri}")
            return new_sip_uri
        else:
            print("API call succeeded, but no 'sipUri' key was found in response payload.")
            return None

    except Exception as err:
        print(f"Failed to initialize VideoSDK Gateway: {err}")
        return None


# if __name__ == "__main__":
#     print("--- STARTING TELEPHONY API GATEWAY TEST ---")
#     uri = initialize_inbound_gateway()
#     print(f"--- TEST FINISHED. Resulting URI: {uri} ---")

#----- Outbound ----

def initialize_outbound_gateway():
    try:
        print("Checking existing Outbound VideoSDK gateways...")
        response = requests.get(OUTBOUND_URL, headers=headers)
        
        # 1. Inspect raw response details before trying to parse JSON
        if response.status_code != 200:
            print(f"Server Error {response.status_code}: {response.text or '[Empty Response Body]'}")
            return None
            
        existing_gateways = response.json().get("data", [])
        my_gateway = next((g for g in existing_gateways if g.get("name") == "My Outbound Gateway"), None)
        
        if my_gateway:
            gateway_id = my_gateway.get("id")
            print(f"Outbound Gateway already exists. ID: {gateway_id}")
            return gateway_id

        print("Gateway not found. Provisioning 'My Outbound Gateway'...")
        payload = {
            "name": "My Outbound Gateway",
            "numbers": ["+17432508570"],                    
            "address": "medoria.pstn.twilio.com",       
            "transport": "udp",
            "auth": {
                "username": OUTBOUND_USERNAME,     
                "password": OUTBOUND_PASSWORD      
            }
        }
        
        create_response = requests.post(OUTBOUND_URL, headers=headers, json=payload)
        
        if create_response.status_code not in [200, 201]:
            print(f"Creation Error {create_response.status_code}: {create_response.text or '[Empty Response Body]'}")
            return None

        response_json = create_response.json()
        gateway_data = response_json.get("data", response_json)
        gateway_id = gateway_data.get("id")
        
        print(f"Outbound Gateway created successfully! ID: {gateway_id}")
        return gateway_id
        
    except Exception as err:
        print(f"Failed to initialize Outbound Gateway: {err}")
        return None



# if __name__ == "__main__":
#     print("--- STARTING OUTBOUND GATEWAY TEST ---")
#     initialize_outbound_gateway()
#     print("--- TEST FINISHED ---")

#Checks if a routing rule for 'Support Line Rule' exists. If missing, creates it to route incoming calls to our self-hosted agent.
def initialize_routing_rule(gateway_id: str, agent_id: str = "MyTelephonyAgent"):
    
    if not gateway_id:
        print("Cannot initialize routing rule: Provided gateway_id is empty or None.")
        return None

    try:
        print("Checking existing VideoSDK routing rules...")
        response = requests.get(ROUTING_RULES_URL, headers=headers)
        
        if response.status_code != 200:
            print(f" Server Error {response.status_code}: {response.text or '[Empty Response Body]'}")
            return None
            
        existing_rules = response.json().get("data", [])
        my_rule = next((r for r in existing_rules if r.get("name") == "Support Line Rule"), None)
        
        if my_rule:
            rule_id = my_rule.get("id")
            print(f"Routing rule already exists. ID: {rule_id}")
            return rule_id

        print(f"Routing rule not found. Provisioning rule for Agent '{agent_id}'...")
        payload = {
            "gatewayId": gateway_id,
            "name": "Support Line Rule",
            "numbers": ["+17432508570"],
            "dispatch": "agent",
            "agentType": "self_hosted",
            "agentId": agent_id
        }
        
        create_response = requests.post(ROUTING_RULES_URL, headers=headers, json=payload)
        
        if create_response.status_code not in [200, 201]:
            print(f"Routing Rule Creation Error {create_response.status_code}: {create_response.text or '[Empty Response Body]'}")
            return None

        response_json = create_response.json()
        rule_data = response_json.get("data", response_json)
        rule_id = rule_data.get("id")
        
        print(f"Routing rule created successfully! ID: {rule_id}")
        return rule_id
        
    except Exception as err:
        print(f"Failed to initialize Routing Rule: {err}")
        return None
    


 
    #Creates a routing rule linked to the OUTBOUND gateway. VideoSDK Test the call UI uses this.

def initialize_outbound_routing_rule(outbound_gateway_id: str, agent_id: str = "MyTelephonyAgent"):
   
    if not outbound_gateway_id:
        print("Cannot initialize outbound routing rule: gateway_id is None.")
        return None

    try:
        print("Checking existing routing rules for outbound...")
        response = requests.get(ROUTING_RULES_URL, headers=headers)
        existing_rules = response.json().get("data", [])

        my_rule = next((r for r in existing_rules if r.get("name") == "Outbound Line Rule"), None)

        if my_rule:
            print(f"Outbound routing rule already exists. ID: {my_rule.get('id')}")
            return my_rule.get("id")

        print("Creating outbound routing rule...")
        payload = {
            "gatewayId": outbound_gateway_id,   # ← OUTBOUND gateway ID
            "name": "Outbound Line Rule",
            "numbers": ["+17432508570"],
            "dispatch": "agent",
            "agentType": "self_hosted",
            "agentId": agent_id
        }

        create_response = requests.post(ROUTING_RULES_URL, headers=headers, json=payload)

        if create_response.status_code not in [200, 201]:
            print(f"Error {create_response.status_code}: {create_response.text}")
            return None

        rule_data = create_response.json().get("data", create_response.json())
        rule_id = rule_data.get("id")
        print(f"Outbound routing rule created! ID: {rule_id}")
        return rule_id

    except Exception as err:
        print(f"Failed to create outbound routing rule: {err}")
        return None

# Final testing of bth gateway and routing setup 

if __name__ == "__main__":
    print("\n--- 🏁 STARTING FULL VIDEO_SDK TELEPHONY PROVISIONING 🏁 ---\n")
    
    #Setup Inbound Gateway
    
    print("Executing Phase 1: Inbound Gateway Setup...")
    inbound_response = requests.get(API_URL, headers=headers)
    
    if inbound_response.status_code == 200:
        gateways = inbound_response.json().get("data", [])
        my_inbound = next((g for g in gateways if g.get("name") == "My Inbound Gateway"), None)
        
        if not my_inbound:  
            initialize_inbound_gateway()
            inbound_response = requests.get(API_URL, headers=headers)
            gateways = inbound_response.json().get("data", [])
            my_inbound = next((g for g in gateways if g.get("name") == "My Inbound Gateway"), None)

        if my_inbound:
            g_id = my_inbound.get("id")
            print(f"Target Gateway ID Resolved: {g_id}")
            
            #Setup Routing Rule using the extracted Inbound Gateway ID
            print("\nExecuting Phase 2: Routing Rules Setup...")
            initialize_routing_rule(gateway_id=g_id, agent_id="MyTelephonyAgent")
        else:
            print("Setup halted: Could not retrieve a valid 'My Inbound Gateway' ID.")
    else:
        print(f"Setup halted: Unable to check inbound gateways. Status code: {inbound_response.status_code}")

    #Setup Outbound Gateway
    # Phase 3: Outbound Gateway + its routing rule
print("\nExecuting Phase 3: Outbound Gateway Setup...")
outbound_gw_id = initialize_outbound_gateway()

if outbound_gw_id:
    print("\nExecuting Phase 4: Outbound Routing Rule Setup...")
    initialize_outbound_routing_rule(outbound_gateway_id=outbound_gw_id, agent_id="MyTelephonyAgent")

import requests, os
from dotenv import load_dotenv
load_dotenv()

headers = {"Authorization": os.getenv("VIDEOSDK_AUTH_TOKEN"), "Content-Type": "application/json"}
r = requests.get("https://api.videosdk.live/v2/sip/inbound-gateways/9277af3f-98d5-4b23-92f6-c371ec958f88", headers=headers)
print(r.json())