from flask import Flask, request, jsonify, current_app
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS as cors
import logging
from security import signature_required
import asyncio
from whatsapp_utils import process_message, send_message
import json
from config import load_configurations, configure_logging
from whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)
from Utils import retrieve_info
app = Flask(__name__)

cors(app)
load_configurations(app)
configure_logging()

@app.route("/botpress", methods=['POST'])
async def handle_prompt():
    data = request.get_json()
    if 'prompt' not in data:
        return jsonify({"error": "Missing 'prompt' in request"}), 400

    prompt = data['prompt']
    response = await process_message(prompt)
    return jsonify({"response": response})

@app.route("/similaritysearch", methods=['POST'])
def search():
    data = request.get_json()
    if 'question' not in data:
        return jsonify({"error": "Missing 'question' in request"}), 400

    question = data['question']
    response = retrieve_info(question)
    return jsonify({"response": response})

@app.route("/", methods=['POST'])
async def tanit():
    user_msg = request.values.get('Body', '').lower()
    response = MessagingResponse()
    tanit_response =  await process_message(user_msg)
    response.message(tanit_response)
    return str(response)

def handle_message():
    """
    Handle incoming webhook events from the WhatsApp API.

    This function processes incoming WhatsApp messages and other events,
    such as delivery statuses. If the event is a valid message, it gets
    processed. If the incoming payload is not a recognized WhatsApp event,
    an error is returned.

    Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

    Returns:
        response: A tuple containing a JSON response and an HTTP status code.
    """
    body = request.get_json()
    # logging.info(f"request body: {body}")

    # Check if it's a WhatsApp status update
    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        logging.info("Received a WhatsApp status update.")
        return jsonify({"status": "ok"}), 200

    try:
        if is_valid_whatsapp_message(body):
            asyncio.run(process_whatsapp_message(body))
           
            return jsonify({"status": "ok"}), 200
        else:
            # if the request is not a WhatsApp API event, return an error
            return (
                jsonify({"status": "error", "message": "Not a WhatsApp API event"}),
                404,
            )
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400


# Required webhook verifictaion for WhatsApp
def verify():
    # Parse params from the webhook verification request
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    # Check if a token and mode were sent
    if mode and token:
        # Check the mode and token sent are correct
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            # Respond with 200 OK and challenge token from the request
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            logging.info("VERIFICATION_FAILED")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        # Responds with '400 Bad Request' if verify tokens do not match
        logging.info("MISSING_PARAMETER")
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


@app.route("/webhook", methods=["GET"])
def webhook_get():
    return verify()

@app.route("/webhook", methods=["POST"])
@signature_required
def webhook_post():
  
    return  handle_message()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

    