from typing import Dict

from langchain.memory import ConversationBufferMemory


_global_memories: Dict[str, ConversationBufferMemory] = {}


def get_memory(session_id: str = "default") -> ConversationBufferMemory:
    """
    Return a ConversationBufferMemory instance for the given session id.
    """
    if session_id not in _global_memories:
        _global_memories[session_id] = ConversationBufferMemory(
            memory_key="history",
            input_key="question",
            return_messages=True,
        )
    return _global_memories[session_id]

