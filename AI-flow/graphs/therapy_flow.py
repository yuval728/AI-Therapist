from langgraph.graph import StateGraph, END
from litellm import completion
from tools.emotions_analyzer import emotion_tool
from tools.crisis_detector import crisis_tool
from tools.journal_tool import journal_tool
from langchain.chat_models import init_chat_model
from memory.state import TherapyState
from memory.memory_manager import store, checkpointer
import os


# llm = init_chat_model("google_genai:gemini-2.0-flash")


# Therapist LLM response using LiteLLM
def therapy_node(state: TherapyState) -> TherapyState:
    user_input = state["input"]

    response = completion(
        model="gemini/gemini-2.0-flash",
        messages=[
            {"role": "system", "content": "You are a compassionate AI therapist."},
            {"role": "user", "content": user_input}
        ]
    )
    return {**state, "response": response["choices"][0]["message"]["content"]}


# Emotion detection node
def emotion_node(state: TherapyState) -> TherapyState:
    emotion = emotion_tool(state["input"])
    return {**state, "emotion": emotion}


# Crisis detection logic
def crisis_check_node(state: TherapyState) -> str:
    is_crisis = crisis_tool(state["input"])
    return "crisis" if is_crisis else "safe"


# Emergency response
def crisis_node(state: TherapyState) -> TherapyState:
    message = (
        "I'm here for you. It sounds like you're going through something very difficult. "
        "Please know you're not alone. If you're in immediate danger or need urgent help, "
        "contact a mental health professional or crisis helpline in your area."
    )
    return {**state, "response": message}


def journal_intent_node(state: TherapyState) -> str:
    user_input = state["input"]
    response = completion(
        model="gemini/gemini-2.0-flash-lite",
        messages=[
            {"role": "system", "content": "You classify if a user message is a journal entry or a request for therapy chat. Reply ONLY with 'journal' or 'chat'."},
            {"role": "user", "content": f"Message: {user_input}"}
        ]
    )
    result = response["choices"][0]["message"]["content"].strip().lower()
    return "journal" if result == "journal" else "chat"


# 🪞 Journal Response Node
def journal_node(state: TherapyState) -> TherapyState:
    entry = state["input"]
    reflection = journal_tool(entry)
    return {**state, "response": reflection}

# Define the graph
def build_therapy_graph():
    graph = StateGraph(TherapyState)

    # Define Nodes
    graph.add_node("analyze_emotion", emotion_node)
    graph.add_node("check_crisis", crisis_check_node)
    graph.add_node("check_journal", journal_intent_node)
    graph.add_node("journal", journal_node)
    graph.add_node("chat", therapy_node)
    graph.add_node("crisis", crisis_node)

    # Flow Edges
    graph.set_entry_point("analyze_emotion")
    # graph.add_edge("analyze_emotion", "check_crisis")
    graph.add_conditional_edges("analyze_emotion", crisis_check_node, {
        "safe": "check_journal",
        "crisis": "crisis"
    })
    graph.add_conditional_edges("check_journal", journal_intent_node, {
        "journal": "journal",
        "chat": "chat"
    })

    graph.add_edge("journal", END)
    graph.add_edge("chat", END)
    graph.add_edge("crisis", END)

    return graph.compile(
        checkpointer=checkpointer,
        store=store,
        debug=True,
    )
    



# Example usage
if __name__ == "__main__":
    flow = build_therapy_graph()

    # 🔁 Try a journal example
    journal_input = "Here’s my journal for today. I felt drained most of the morning but lighter in the afternoon."

    # 🔁 Try a regular chat input
    chat_input = "I’m feeling anxious before presentations. Can you help?"

    config = {"configurable": {"thread_id": "1"}}
    result = flow.invoke({"input": journal_input}, config=config)
    print("\nResponse:\n", result["response"])
