import logging
from flask import current_app, jsonify
import json
import requests
from Chat_function import chat_with_gpt4
from Chat_function_literal import chat_with_gpt4_no_streaming as chat_with_gpt4_literal
from literalai import LiteralClient
import re
import os

async def process_message(message: str, phone_number, chat_history=None):
    """
    Process a message using the GPT-4 chat function and return a generator of the response tokens.
    """
    full_response = ""
    async for token in chat_with_gpt4(message, phone_number, chat_history):
        if type(token) == str:
            full_response += token
    return full_response

def process_message_literal(message: str, phone_number):
    """
    Process a message using the GPT-4 chat function and return a generator of the response tokens.
    """
    literalai_client = LiteralClient(api_key=os.getenv("LITERAL_API_KEY"))
    
    with literalai_client.thread(name=f"Thread_{phone_number}",thread_id=f"Thread_{phone_number}", participant_id=phone_number) as thread:
        chat_history = find_chat_history(thread.id, literalai_client) 
        with literalai_client.step(thread_id=thread.id, name=message) as step:
            full_response =  chat_with_gpt4_literal(message, chat_history)
    
    return full_response

def find_chat_history(thread_id, literalai_client):
    chat_history = []
    if literalai_client.api.get_thread(id=thread_id):
        for step in [literalai_client.api.get_thread(id=thread_id).steps[-1]]:
            if step.generation:
                for message in step.generation.messages:
                    if message["role"] != "system" and message["role"] != "function":
                        chat_history.append(message)                      
            if step.output:
                chat_history.append({"role": "assistant", "content": step.output["content"]})
        return chat_history
    else:
        return None

def find_user(phone_number):
    literalai_client = LiteralClient(api_key=os.getenv("LITERAL_API_KEY"))
    user= literalai_client.api.get_user(identifier=phone_number)
    if user != None:
        return True
    else:
        user = literalai_client.api.create_user(identifier=phone_number)
        return False

def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


async def generate_response(user_message):
    response = await process_message(user_message)
    return response
"""
def generate_response(response):
    return response.upper()
"""
def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }
    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


async def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

    response =await  generate_response(message_body)

    data = get_text_message_input(current_app.config["RECIPIENT_WAID"], response)
    send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )