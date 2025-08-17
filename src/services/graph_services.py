from src.graphs.therapy_flow import build_therapy_graph
from src.memory.memory_manager import get_memory
from functools import lru_cache
import anyio

@lru_cache(maxsize=1)
def _graph():
    return build_therapy_graph()

def run_therapy_flow(user_id: str, user_input: str, thread_id: str = "default"):
    """Run the therapy flow for a user using a cached compiled graph."""
    history = get_memory({"user_id": user_id}, limit=6, from_db=True)
    initial_state = {
        "user_id": user_id,
        "input": user_input,
        "messages": history,
        "response": None,
        "relevant_memories": None,
        "emotion": None,
        "is_crisis": None,
        "mode": None,
        "journal_entry": None,
        "attack": None,
    }
    final_state = _graph().invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
    return final_state

async def run_therapy_flow_async(user_id: str, user_input: str, thread_id: str = "default"):
    graph = _graph()
    history = get_memory({"user_id": user_id}, limit=6, from_db=True)
    initial_state = {
        "user_id": user_id,
        "input": user_input,
        "messages": history,
        "response": None,
        "relevant_memories": None,
        "emotion": None,
        "is_crisis": None,
        "mode": None,
        "journal_entry": None,
        "attack": None,
    }
    try:
        ainvoke = getattr(graph, "ainvoke", None)
        if ainvoke:
            return await ainvoke(initial_state, config={"configurable": {"thread_id": thread_id}})
        # fallback
        return await anyio.to_thread.run_sync(lambda: graph.invoke(initial_state, config={"configurable": {"thread_id": thread_id}}))
    except Exception:
        # last resort fallback
        return run_therapy_flow(user_id, user_input, thread_id)
