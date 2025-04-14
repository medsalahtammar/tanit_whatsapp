from literalai import LiteralClient
import os
from dotenv import load_dotenv
from literalai import LiteralClient
from datetime import datetime, timedelta
import statistics
import os
load_dotenv()

literalai_client = LiteralClient(api_key=os.getenv("LITERAL_API_KEY"))

def safe_parse_datetime(dt_str):
    try:
        if '.' in dt_str:
            date_part, microsecond_part = dt_str.split('.')
            microsecond_part = microsecond_part.rstrip('Z') 

            microsecond_part = microsecond_part.ljust(6, '0')

            dt_str = f"{date_part}.{microsecond_part}"

        return datetime.fromisoformat(dt_str)
    except Exception as e:
        print(f"Error parsing datetime '{dt_str}': {e}")
        raise

def get_thread_ids_for_whatsapp_users():
    users = literalai_client.api.get_users()
    thread_ids = []

    for user in users.data:
        if user.metadata.get("Type") == "Whatsapp":
            identifier = user.identifier
            thread_ids.append(f"Thread_{identifier}")

    return thread_ids

def analyze_thread(thread_id: str):
    try:
        steps = literalai_client.api.get_thread(id=thread_id).steps
    except Exception:
        return None

    if not steps:
        return None

    total_steps = len(steps)
    start_times = [safe_parse_datetime(step.start_time) for step in steps]
    end_times = [safe_parse_datetime(step.end_time) for step in steps]

    total_duration = end_times[-1] - start_times[0]
    response_times = [end - start for start, end in zip(start_times, end_times)]
    total_response_time = sum(response_times, timedelta())
    average_response_time = total_response_time / total_steps if total_steps > 0 else timedelta()
    idle_time = total_duration - total_response_time
    engagement_density = total_response_time / total_duration if total_duration.total_seconds() > 0 else 0
    duration_minutes = total_duration.total_seconds() / 60 if total_duration.total_seconds() > 0 else 1
    messages_per_minute = total_steps / duration_minutes
    response_time_seconds = [rt.total_seconds() for rt in response_times]
    response_time_variance = statistics.variance(response_time_seconds) if len(response_time_seconds) > 1 else 0

    return {
        "thread_id": thread_id,
        "total_duration_sec": total_duration.total_seconds(),
        "total_response_time_sec": total_response_time.total_seconds(),
        "idle_time_sec": idle_time.total_seconds(),
        "average_response_time_sec": average_response_time.total_seconds(),
        "engagement_density": engagement_density,
        "messages_per_minute": messages_per_minute,
        "response_time_variance": response_time_variance,
        "message_count": total_steps
    }

def get_global_metrics():
    thread_ids = get_thread_ids_for_whatsapp_users()

    all_metrics = []
    for thread_id in thread_ids:
        metrics = analyze_thread(thread_id)
        if metrics:
            all_metrics.append(metrics)

    if not all_metrics:
        return None

    total_conversations = len(all_metrics)

    def avg(field):
        return round(sum(m[field] for m in all_metrics) / total_conversations, 3)

    global_summary = {
        "total_whatsapp_conversations": total_conversations,
        "average_conversation_duration_sec": avg("total_duration_sec"),
        "average_response_time_sec": avg("average_response_time_sec"),
        "average_idle_time_sec": avg("idle_time_sec"),
        "average_engagement_density": avg("engagement_density"),
        "average_messages_per_minute": avg("messages_per_minute"),
        "average_response_time_variance": avg("response_time_variance"),
        "average_message_count": avg("message_count")
    }

    return global_summary
