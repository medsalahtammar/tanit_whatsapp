from flask import Flask, request, jsonify
from flask_cors import CORS as cors
from whatsapp_utils import  process_message_literal, find_user, find_inactive_numeric_users, notify_user
from whatsapp_metrics import get_global_metrics, analyze_thread

app = Flask(__name__)

cors(app)

@app.route("/literal", methods=['POST'])
def handle_prompt_literal():
    data = request.get_json()
    if 'prompt' not in data:
        return jsonify({"error": "Missing 'prompt' in request"}), 400
    if 'phone_number' not in data:
        return jsonify({"error": "Missing 'phone_number' in request"}), 400
    prompt = data['prompt']
    phone_number = data['phone_number']
    response = process_message_literal(prompt,phone_number)
    return jsonify({"response": response})

@app.route("/user", methods=['POST'])
def find_user_literal():
    data = request.get_json()
    if 'phone_number' not in data:
        return jsonify({"error": "Missing 'phone_number' in request"}), 400
    phone_number = data['phone_number']
    exists = find_user(phone_number)
    return jsonify({"response": exists})

@app.route("/inactive_users", methods=['GET'])
def get_inactive_users():
    inactive_users = find_inactive_numeric_users()
    return jsonify({"inactive_users": inactive_users})

@app.route("/notify_user", methods=['POST'])
def notify_user_endpoint():
    data = request.get_json()
    if not data or 'identifier' not in data:
        return jsonify({"error": "Missing 'identifier' in request"}), 400

    identifier = data['identifier']
    user = notify_user(identifier)
    if user:
        return jsonify({"message": f"User {identifier} has been notified."})
    else:
        return jsonify({"error": f"User {identifier} not found."}), 404
    
@app.route("/metrics/global", methods=["GET"])
def global_metrics_endpoint():
    global_summary = get_global_metrics()
    if not global_summary:
        return jsonify({"error": "No valid WhatsApp threads found"}), 404
    return jsonify(global_summary)

@app.route("/metrics/thread/<string:phone_number>", methods=["GET"])
def thread_metrics_endpoint(phone_number):
    thread_id = f"Thread_{phone_number}"
    metrics = analyze_thread(thread_id)
    if not metrics:
        return jsonify({"error": f"No data found for thread_id {thread_id}"}), 404
    return jsonify(metrics)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

    