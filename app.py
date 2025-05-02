from typing import Any, Dict, List
import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import snowflake.connector
import requests
import pandas as pd
from dotenv import load_dotenv
import matplotlib
import time
import matplotlib.pyplot as plt 
from cortex_chat import CortexChat
import certifi
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
os.environ['SSL_CERT_FILE'] = certifi.where()
matplotlib.use('Agg')
load_dotenv()

# Environment Variables
#USER = os.getenv("USER")
#ACCOUNT = os.getenv("ACCOUNT")
#ANALYST_ENDPOINT = os.getenv("ANALYST_ENDPOINT")
#RSA_PRIVATE_KEY_PATH = os.getenv("RSA_PRIVATE_KEY_PATH")
#SUPPORT_TICKETS_SEMANTIC_MODEL = os.getenv("SUPPORT_TICKETS_SEMANTIC_MODEL")
#SUPPLY_CHAIN_SEMANTIC_MODEL = os.getenv("SUPPLY_CHAIN_SEMANTIC_MODEL")
#SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
#SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

USER='ADEOKAR93'
ACCOUNT='XTTWWCT-MBB93540'
RSA_PRIVATE_KEY_PATH='rsa_key.pem'
SUPPORT_TICKETS_SEMANTIC_MODEL='@CORTEX_DEMO.CORTEX_SAMPLE_DATA.semantic_models/support_tickets_semantic_model.yaml'
SUPPLY_CHAIN_SEMANTIC_MODEL='@CORTEX_DEMO.CORTEX_SAMPLE_DATA.semantic_models/supply_chain_semantic_model.yaml'
ANALYST_ENDPOINT='https://XTTWWCT-MBB93540.snowflakecomputing.com/api/v2/cortex/analyst/message'
SLACK_APP_TOKEN='xapp-1-A08NXSU3L3C-8760915626999-0f0b659b57157d24935e5edc6fef6c48c6bc96b5a8adfc139cb3d24b6bf7ff80'
SLACK_BOT_TOKEN='xoxb-8773223986661-8779796738068-8VyclQXhLogqo3G7kfKUgPGr'

with open("rsa_key.p8", "rb") as key_file:
    p_key = serialization.load_der_private_key(
        key_file.read(),
        password=None,
        backend=default_backend()
    )

private_key = p_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)



ENABLE_CHARTS = False
DEBUG = False

# Initialize Slack App
app = App(token=SLACK_BOT_TOKEN)

# Initialize Snowflake and CortexChat
conn = snowflake.connector.connect(
    user=USER,
    authenticator="SNOWFLAKE_JWT",
    private_key=private_key,
    account=ACCOUNT
)
cortex_chat = CortexChat(ACCOUNT, USER, RSA_PRIVATE_KEY_PATH, ANALYST_ENDPOINT, SUPPORT_TICKETS_SEMANTIC_MODEL, SUPPLY_CHAIN_SEMANTIC_MODEL)

@app.message("hello")
def message_hello(message, say):
    say(f"Hey there <@{message['user']}>!")
    say(text="Let's BUILD", blocks=[
        {"type": "header", "text": {"type": "plain_text", "text": ":snowflake: Let's BUILD!"}}
    ])

@app.event("message")
def handle_message_events(ack, body, say):
    ack()
    process_analyst_message(body['event']['text'], say)

@app.command("/asksnowflake")
def ask_cortex(ack, body, say):
    ack()
    process_analyst_message(body['text'], say)


#def process_analyst_message(prompt, say) -> Any:
    #say_question(prompt, say)
    #print("Calling save_question_to_snowflake")
    #save_question_to_snowflake(prompt) 
    #try:
        # Send the query to Cortex and capture the response
        #response = cortex_chat.query_cortex_analyst(prompt)
        
        # Print the raw message payload for debugging
        #print("[DEBUG] Cortex Message Payload:", response)
        
        # Optionally, you can log this to a file or save it in a database
        # Example: Save it to a file
       # with open("cortex_payload_log.json", "a") as f:
            #import json
            #json.dump(response, f)
            #f.write("\n")
        
       # return response
  #  except Exception as e:
       # print(f"Error while capturing Cortex message payload: {e}")
       # return None
    #display_analyst_content(response["message"]["content"], say)


def save_text_to_snowflake(text: str):
    try:
        # Make sure the text isn't empty
        if text.strip():
            conn.cursor().execute("USE DATABASE CORTEX_DEMO")
            conn.cursor().execute("USE SCHEMA CORTEX_SAMPLE_DATA")
            # Insert the extracted 'text' into Snowflake table
            with conn.cursor() as cur:
                cur.execute("INSERT INTO cortex_responses (response_text) VALUES (%s)", (text,))
            print(f"[SUCCESS] Saved text to Snowflake: {text}")
        else:
            print("[ERROR] Skipped empty text response.")
    except Exception as e:
        print(f"❌ Failed to insert text into Snowflake: {e}")

def capture_and_store_cortex_message(prompt: str):
    try:
        # Send the query to Cortex and capture the response
        response = cortex_chat.query_cortex_analyst(prompt)

        # Print the entire response for debugging
        print("[DEBUG] Cortex Message Payload:", response)

        # Extract the 'text' key from 'content'
        if 'message' in response and 'content' in response['message']:
            content = response['message']['content']
            for item in content:
                if 'text' in item:  # Assuming the 'text' field is present in the content
                    text_response = item['text']
                    print(f"[DEBUG] Captured text: {text_response}")
                    
                    # Save this 'text' into Snowflake
                    save_text_to_snowflake(text_response)
                    return text_response
        else:
            print("[ERROR] No 'message' or 'content' found in the response.")
            return None
    except Exception as e:
        print(f"Error while capturing and storing Cortex message: {e}")
        return None


def process_analyst_message(prompt, say) -> Any:
    say_question(prompt, say)
    #print("Calling save_question_to_snowflake")
    #save_question_to_snowflake(prompt) 
    # Capture and store the Cortex message response
    captured_text = capture_and_store_cortex_message(prompt)
    
    if captured_text:
        say(f"Captured text from Cortex: {captured_text}")
    else:
        say("No valid response from Cortex.")
    # Send the query to Cortex and capture the response
    response = cortex_chat.query_cortex_analyst(prompt)

    display_analyst_content(response["message"]["content"], say)
    

def say_question(prompt, say):
    say(text=f"Question: {prompt}", blocks=[
        {"type": "header", "text": {"type": "plain_text", "text": f"Question: {prompt}"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "plain_text", "text": "Snowflake Cortex Analyst is generating a response. Please wait..."}},
        {"type": "divider"}
    ])

def display_analyst_content(content: List[Dict[str, str]], say):
    for item in content:
        if item["type"] == "sql":
            say(text="Generated SQL", blocks=[
                {"type": "rich_text", "elements": [{"type": "rich_text_preformatted", "elements": [{"type": "text", "text": item['statement']}]}]}
            ])
            df = pd.read_sql(item["statement"], conn)
            say(text="Answer:", blocks=[
                {"type": "rich_text", "elements": [{"type": "rich_text_preformatted", "elements": [{"type": "text", "text": df.to_string()}]}]}
            ])
            if ENABLE_CHARTS and len(df.columns) > 1:
                try:
                    chart_img_url = plot_chart(df)
                    if chart_img_url:
                        say(text="Chart", blocks=[
                            {"type": "image", "title": {"type": "plain_text", "text": "Chart"}, "block_id": "image", "slack_file": {"url": chart_img_url}, "alt_text": "Chart"}
                        ])
                except Exception as e:
                    print(f"Warning: Unable to generate chart - {e}")
        elif item["type"] == "suggestions":
            suggestions = "\n- ".join(item['suggestions'])
            say(text=f"You may try these suggested questions:\n- {suggestions}")

def plot_chart(df):
    plt.figure(figsize=(10, 6))
    plt.pie(df[df.columns[1]], labels=df[df.columns[0]], autopct='%1.1f%%', startangle=90)
    plt.axis('equal')
    file_path = 'chart.jpg'
    plt.savefig(file_path, format='jpg')
    file_upload_url = app.client.files_getUploadURLExternal(filename=file_path, length=os.path.getsize(file_path))
    file_id = file_upload_url['file_id']
    with open(file_path, 'rb') as f:
        requests.post(file_upload_url['upload_url'], files={'file': f})
    response = app.client.files_completeUploadExternal(files=[{"id": file_id, "title": "chart"}])
    time.sleep(2)
    return response['files'][0]['permalink'] if response.get('files') else None

if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()

