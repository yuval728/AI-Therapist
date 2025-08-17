from prometheus_client import Counter, Histogram

ws_messages_total = Counter(
    "ws_messages_total", "Total WebSocket messages processed", ["user_id", "thread_id"]
)
ws_errors_total = Counter(
    "ws_errors_total", "Total WebSocket errors", ["user_id", "thread_id"]
)
crisis_events_total = Counter(
    "crisis_events_total", "Total crisis detections", ["user_id", "thread_id"]
)
response_latency_seconds = Histogram(
    "response_latency_seconds", "Therapy response latency", ["user_id", "thread_id"]
)
