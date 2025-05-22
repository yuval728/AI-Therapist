# memory/short_term_memory.py

from langchain.memory import ConversationBufferMemory
from langchain.schema.messages import BaseMessage
from langchain.chat_models import ChatLiteLLM


def create_short_term_memory() -> ConversationBufferMemory:
    """
    Initializes short-term memory to track recent exchanges.
    Returns LangChain-compatible memory object.
    """
    llm = ChatLiteLLM(model="gpt-4")  # Uses LiteLLM under the hood

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        llm=llm
    )
    return memory


def load_history(memory: ConversationBufferMemory) -> list[BaseMessage]:
    """
    Returns the message history as a list (for use in prompts).
    """
    return memory.chat_memory.messages


def save_to_memory(memory: ConversationBufferMemory, user_input: str, ai_response: str):
    """
    Saves one turn of user → assistant interaction.
    """
    memory.chat_memory.add_user_message(user_input)
    memory.chat_memory.add_ai_message(ai_response)
