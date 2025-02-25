from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from flask_cors import CORS as cors
from Chat_function import chat_with_gpt4
app = Flask(__name__)

cors(app)
async def process_message(message: str):
    """
    Process a message using the GPT-4 chat function and return a generator of the response tokens.
    """
    full_response = ""
    async for token in chat_with_gpt4(message):
        full_response += token
    print(full_response)
    return full_response

@app.route("/", methods=['POST'])
async def tanit():
    print(request.values)
    user_msg = request.values.get('Body', '').lower()
    print("##################################")
    print(user_msg)
    response = MessagingResponse()
    tanit_response =  await process_message(user_msg)

    response.message(tanit_response)
    print(str(response))
    return str(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

    