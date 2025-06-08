import sys
sys.path.append("..")  # Adjust the path as necessary to import AIFlow modules
from AIFlow.graphs.therapy_flow import build_therapy_graph
from AIFlow.memory.memory_manager import get_memory

def run_therapy_flow(user_id: str, user_input: str, thread_id: str = "default"):
    """Run the therapy flow for a user."""
    # Initialize the therapy graph
    therapy_graph = build_therapy_graph()
    
    history = get_memory({"user_id": user_id}, limit=6, from_db=True)

    # Create initial state
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

    # Run the graph with the initial state
    final_state =  therapy_graph.invoke(initial_state, config={"configurable": {"thread_id": "1"}})

    return final_state
