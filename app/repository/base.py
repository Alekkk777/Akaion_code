from abc import ABC, abstractmethod

from app.models.schemas import Workflow


class WorkflowRepository(ABC):
    @abstractmethod
    async def save(self, workflow: Workflow) -> None:
        ...

    @abstractmethod
    async def get(self, workflow_id: str) -> Workflow | None:
        ...
