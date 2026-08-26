"""ShopAI's memory layer.

`memory` is the process-wide manager. Ask it for a store by name:

    from shopai.memory import memory

    profile = memory.user_info.read(access_token=token)
    memory.user_info.write(values={"body_type": "curvy"}, access_token=token)

Further memory types (conversation, task, wardrobe) register themselves here
as they are built.
"""

from shopai.memory.base import Memory, MemoryManager
from shopai.memory.user_memory import UserInfoMemory, user_id_from_token

memory = MemoryManager()
memory.register(UserInfoMemory())

__all__ = ["Memory", "MemoryManager", "UserInfoMemory", "memory", "user_id_from_token"]
