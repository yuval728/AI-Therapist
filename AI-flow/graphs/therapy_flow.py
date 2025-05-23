from langgraph.graph import StateGraph, END
from litellm import completion
from tools.emotions_analyzer import emotion_tool
from tools.crisis_detector import crisis_tool
from tools.journal_tool import journal_tool
from memory.state import TherapyState
from langchain_core.messages import HumanMessage, AIMessage
from memory.memory_manager import (
    append_to_memory,
    get_memory,
    save_to_long_term_memory,
    search_long_term_memory,
)
import os


def therapy_node(state: TherapyState) -> TherapyState:
    user_input = state["input"]
    history = get_memory(state)
    memory_msgs = [
        {
            "role": "user" if isinstance(m, HumanMessage) else "assistant",
            "content": m.content,
        }
        for m in history
    ]

    memory_msgs.insert(
        0,
        {
            "role": "system",
            "content": f"You are a compassionate therapist. The user currently feels {state['emotion']}.",
        },
    )
    memory_msgs.append({"role": "user", "content": user_input})

    relevant_docs = search_long_term_memory(state["user_id"], user_input)
    relevant_memories = [doc.page_content for doc in relevant_docs]

    prompt = [
        {
            "role": "system",
            "content": f"You are a compassionate therapist. The user currently feels {state['emotion']}.",
        }
    ]

    if relevant_memories:
        memory_str = "\n\n".join(relevant_memories)
        prompt.append(
            {
                "role": "system",
                "content": f"The user previously shared the following relevant context:\n{memory_str}",
            }
        )

    prompt += memory_msgs
    prompt.append({"role": "user", "content": user_input})

    # === 4. Generate response ===
    response = completion(model="gemini/gemini-2.0-flash", messages=prompt)
    ai_message = response["choices"][0]["message"]["content"]

    # === 5. Save to short-term memory ===
    state = append_to_memory(state, HumanMessage(content=user_input), role="user")
    state = append_to_memory(state, AIMessage(content=ai_message), role="assistant")

    return {
        **state,
        "response": ai_message,
        "relevant_memories": relevant_memories,
    }


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
    state = append_to_memory(state, HumanMessage(content=state["input"]), role="user")
    state = append_to_memory(state, AIMessage(content=message), role="assistant")
    return {**state, "response": message}


def journal_intent_node(state: TherapyState) -> str:
    user_input = state["input"]
    response = completion(
        model="gemini/gemini-2.0-flash-lite",
        messages=[
            {
                "role": "system",
                "content": "You classify if a user message is a journal entry or a request for therapy chat. Reply ONLY with 'journal' or 'chat'.",
            },
            {"role": "user", "content": f"Message: {user_input}"},
        ],
    )
    result = response["choices"][0]["message"]["content"].strip().lower()
    return {**state, "mode": result}


def is_journal_entry(state: TherapyState) -> bool:
    """
    Check if the user input is a journal entry.
    """
    return state["mode"] == "journal"


# 🪞 Journal Response Node
def journal_node(state: TherapyState) -> TherapyState:
    entry = state["input"]
    reflection = journal_tool(entry)

    save_to_long_term_memory(
        state["user_id"], content=entry, metadata={"type": "journal"}
    )

    # Store in short-term memory
    state = append_to_memory(state, HumanMessage(content=entry), role="user")
    state = append_to_memory(state, AIMessage(content=reflection), role="assistant")
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
    graph.add_conditional_edges(
        "analyze_emotion",
        crisis_check_node,
        {"safe": "check_journal", "crisis": "crisis"},
    )
    graph.add_conditional_edges(
        "check_journal", is_journal_entry, {True: "journal", False: "chat"}
    )

    graph.add_edge("journal", END)
    graph.add_edge("chat", END)
    graph.add_edge("crisis", END)

    return graph.compile(
        # checkpointer=checkpointer,
        # store=store,
        debug=True,
    )


# Example usage
if __name__ == "__main__":
    flow = build_therapy_graph()

    # 🔁 Try a journal example
    journal_input = "Here’s my journal for today. I felt drained most of the morning but lighter in the afternoon."

    # 🔁 Try a regular chat input
    # chat_input = "I’m feeling anxious before presentations. Can you help?"

    config = {"configurable": {"thread_id": "1"}}
    # result = flow.invoke({"input": journal_input, "user_id": "1", "messages": []}, config=config)
    # print("\nResponse:\n", result["response"])
    
    chat_input = "Do you remember what i talked last time?"
    # flow.stream
    result = flow.invoke({"input": chat_input, "user_id": "1", "messages": []}, config=config)
