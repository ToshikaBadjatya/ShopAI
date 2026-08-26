"""The memory layer's shared shape.

Every kind of memory ShopAI keeps - user info now, conversation, task and
wardrobe memory later - answers the same three questions: what do we know,
remember this, forget it. `MemoryManager` holds them by name so an agent or an
endpoint asks for `manager.user_info` without knowing where it is stored.
"""

from abc import ABC, abstractmethod
from typing import Any


class Memory(ABC):
    """One store of one kind of memory.

    Implementations decide where the data lives; callers only see read/write/
    delete. `name` is how the store is addressed on the manager.
    """

    name: str = ""

    @abstractmethod
    def read(self, key: str, **kwargs: Any) -> dict:
        """Return what is remembered for `key`, or an empty dict if nothing is."""

    @abstractmethod
    def write(self, key: str, values: dict, **kwargs: Any) -> dict:
        """Remember `values` for `key` and return the stored record."""

    @abstractmethod
    def delete(self, key: str, **kwargs: Any) -> bool:
        """Forget everything stored for `key`. True when a record was removed."""

    def exists(self, key: str, **kwargs: Any) -> bool:
        """Whether anything is remembered for `key`."""
        return bool(self.read(key, **kwargs))


class MemoryManager:
    """The registry of memory stores.

    Stores register themselves by name and are reached either through
    `manager.get("user_info")` or as an attribute, `manager.user_info`. The
    manager owns no storage of its own - it is the front door, so the rest of
    the system has one place to ask.
    """

    def __init__(self) -> None:
        self._stores: dict[str, Memory] = {}

    def register(self, store: Memory) -> Memory:
        """Add a store, replacing any earlier one of the same name."""
        if not store.name:
            raise ValueError(f"{type(store).__name__} needs a name to be registered")
        self._stores[store.name] = store
        return store

    def get(self, name: str) -> Memory:
        try:
            return self._stores[name]
        except KeyError:
            known = ", ".join(sorted(self._stores)) or "none registered"
            raise KeyError(f"No memory named '{name}'. Known: {known}") from None

    def __getattr__(self, name: str) -> Memory:
        # Only reached for attributes that do not exist; keeps manager.user_info working.
        try:
            return self.__dict__["_stores"][name]
        except KeyError:
            raise AttributeError(f"No memory named '{name}'") from None

    def __contains__(self, name: str) -> bool:
        return name in self._stores

    @property
    def names(self) -> list[str]:
        return sorted(self._stores)

    # ------------------------------------------------------------------
    # Convenience pass-throughs, so a caller with a name need not fetch first
    # ------------------------------------------------------------------

    def read(self, store: str, key: str, **kwargs: Any) -> dict:
        return self.get(store).read(key, **kwargs)

    def write(self, store: str, key: str, values: dict, **kwargs: Any) -> dict:
        return self.get(store).write(key, values, **kwargs)

    def delete(self, store: str, key: str, **kwargs: Any) -> bool:
        return self.get(store).delete(key, **kwargs)
