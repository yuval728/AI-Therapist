from langgraph.graph import StateGraph, END
from litellm import completion
from tools.emotion_analyzer import emotion_tool
from tools.crisis_detector import crisis_tool

# Define the state type
class TherapyState(dict):
    pass

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


# Define the graph
def build_therapy_graph():
    graph = StateGraph(TherapyState)

    graph.add_node("analyze_emotion", emotion_node)
    graph.add_node("check_crisis", crisis_check_node)
    graph.add_node("chat", therapy_node)
    graph.add_node("crisis", crisis_node)

    graph.set_entry_point("analyze_emotion")
    graph.add_edge("analyze_emotion", "check_crisis")
    graph.add_conditional_edges("check_crisis", {
        "safe": "chat",
        "crisis": "crisis"
    })
    graph.add_edge("chat", END)
    graph.add_edge("crisis", END)

    return graph.compile()


# Example usage
if __name__ == "__main__":
    flow = build_therapy_graph()
    result = flow.invoke({"input": "I don't think I can handle this anymore..."})
    print("\nResponse:\n", result["response"])
