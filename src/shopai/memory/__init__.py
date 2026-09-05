"""ShopAI's memory layer.

`memory` is the process-wide manager. Ask it for a store by name:

    from shopai.memory import memory

    profile = memory.user_info.read(access_token=token)
    memory.user_info.write(values={"body_type": "curvy"}, access_token=token)

    memory.conversation.add_to_conversation(user_id, run_id, "loved the velvet mini")
    memory.conversation.compact(user_id, run_id)

    memory.task.plan_task(run_id, agent="recommendation_agent", task="curate looks")
    memory.task.get_status(run_id)

Further memory types (wardrobe) register themselves here as they are built.
"""

from shopai.memory.base import Memory, MemoryManager
from shopai.memory.conversation_memory import ConversationMemory
from shopai.memory.task_memory import TaskMemory
from shopai.memory.tool_memory import ToolMemory
from shopai.memory.user_memory import UserInfoMemory, user_id_from_token

memory = MemoryManager()
memory.register(UserInfoMemory())
memory.register(ConversationMemory())
memory.register(TaskMemory())
memory.register(ToolMemory())

__all__ = [
    "Memory",
    "MemoryManager",
    "UserInfoMemory",
    "ConversationMemory",
    "TaskMemory",
    "ToolMemory",
    "memory",
    "user_id_from_token",
]
