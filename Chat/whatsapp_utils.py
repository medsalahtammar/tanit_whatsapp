
from Chat_function_literal import chat_with_gpt4_no_streaming as chat_with_gpt4_literal
from literalai import LiteralClient
import os
from datetime import datetime, timezone, timedelta
from dateutil import parser
from dotenv import load_dotenv
load_dotenv()

def process_message_literal(message: str, phone_number):
    """
    Process a message using the GPT-4 chat function and return a generator of the response tokens.
    """
    literalai_client = LiteralClient(api_key=os.getenv("LITERAL_API_KEY"))
    
    with literalai_client.thread(name=f"Thread_{phone_number}",thread_id=f"Thread_{phone_number}", participant_id=phone_number) as thread:
        chat_history = find_chat_history(thread.id, literalai_client) 
        with literalai_client.step(thread_id=thread.id, name=message) as step:
            full_response =  chat_with_gpt4_literal(message, chat_history)
        user = literalai_client.api.get_user(identifier=phone_number)
        if user.metadata.get("Status") != "Active":
            literalai_client.api.update_user(id=user.id, identifier=user.identifier, metadata={"Status": "Active", "Type": "Whatsapp"})
    return full_response

def find_chat_history(thread_id, literalai_client):
    chat_history = []
    if literalai_client.api.get_thread(id=thread_id):
        if literalai_client.api.get_thread(id=thread_id).steps:
            for step in [literalai_client.api.get_thread(id=thread_id).steps[-1]]:
                if step.generation:
                    for message in step.generation.messages[-9:]:
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
        user = literalai_client.api.create_user(identifier=phone_number, metadata={"Type": "Whatsapp"})
        return False

def find_inactive_numeric_users():
    literalai_client = LiteralClient(api_key=os.getenv("LITERAL_API_KEY"))
    users = literalai_client.api.get_users()
    threshold_time = datetime.now(timezone.utc) - timedelta(days=0.9)
    inactive_users = []
    for user in users.data:
        if user.metadata.get("Type") == "Whatsapp":
            print(user.identifier)
            thread = literalai_client.api.get_thread(id=f"Thread_{user.identifier}")
            if thread:
                step = thread.steps[len(thread.steps)-1]
                print(step.end_time)
                last_step_time = parser.isoparse(step.end_time)
                if last_step_time.tzinfo is None:
                    last_step_time = last_step_time.replace(tzinfo=timezone.utc)
                if last_step_time < threshold_time:
                    if(user.metadata.get("Status") == "Notified"):
                        break
                    else:
                        literalai_client.api.update_user(id=user.id,identifier=user.identifier, metadata={"Status": "Inactive", "Type": "Whatsapp"})
                        inactive_users.append(user.identifier)
                        print(f"User {user.identifier} has been inactive for more than 2 days.")
    return inactive_users

def notify_user(identifier):
    literalai_client = LiteralClient(api_key=os.getenv("LITERAL_API_KEY"))
    user = literalai_client.api.get_user(identifier=identifier)
    if user != None:
        user= literalai_client.api.update_user(id=user.id,identifier=user.identifier, metadata={"Status": "Notified","Type": "Whatsapp"})
    return user
        