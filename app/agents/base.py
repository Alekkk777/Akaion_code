from abc import ABC, abstractmethod

from app.models.schemas import Workflow


class Agent(ABC):
    @abstractmethod
    async def run(self, workflow: Workflow) -> Workflow:
        ...
