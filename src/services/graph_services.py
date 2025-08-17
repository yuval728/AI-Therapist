from src.therapy.graphs.therapy_flow import build_therapy_graph
from src.therapy.memory.memory_manager import get_memory
from src.config.constants import Limits
from functools import lru_cache
from typing import Dict, Any, Optional
import anyio
from loguru import logger

@lru_cache(maxsize=1)
def _get_compiled_graph():
    """Get cached compiled therapy graph."""
    return build_therapy_graph()

def _create_initial_state(user_id: str, user_input: str) -> Dict[str, Any]:
    """Create initial state for therapy flow."""
    history = get_memory({"user_id": user_id}, limit=Limits.MEMORY_HISTORY_LIMIT, from_db=True)
    return {
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

async def run_therapy_flow_async(user_id: str, user_input: str, thread_id: str = "default") -> Optional[Dict[str, Any]]:
    """Run the therapy flow asynchronously for a user."""
    try:
        graph = _get_compiled_graph()
        initial_state = _create_initial_state(user_id, user_input)
        config = {"configurable": {"thread_id": thread_id}}
        
        # Try async invoke first
        if hasattr(graph, "ainvoke"):
            return await graph.ainvoke(initial_state, config=config)
        
        # Fallback to sync in thread
        return await anyio.to_thread.run_sync(
            lambda: graph.invoke(initial_state, config=config),
            cancellable=True
        )
    except Exception as e:
        logger.error(f"Therapy flow failed for user {user_id}: {e}")
        return None

def run_therapy_flow_sync(user_id: str, user_input: str, thread_id: str = "default") -> Optional[Dict[str, Any]]:
    """Run the therapy flow synchronously for a user (for testing/debugging)."""
    try:
        graph = _get_compiled_graph()
        initial_state = _create_initial_state(user_id, user_input)
        config = {"configurable": {"thread_id": thread_id}}
        return graph.invoke(initial_state, config=config)
    except Exception as e:
        logger.error(f"Sync therapy flow failed for user {user_id}: {e}")
        return None
