from typing import Protocol


class ServiceHandler(Protocol):
    async def execute(self, action: str, payload: dict) -> dict:
        ...


class ServiceRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, ServiceHandler] = {}

    def register(self, name: str, handler: ServiceHandler) -> None:
        self._handlers[name] = handler

    def get(self, name: str) -> ServiceHandler:
        if name not in self._handlers:
            raise KeyError(f"Nessun service registrato per '{name}'")
        return self._handlers[name]


registry = ServiceRegistry()
