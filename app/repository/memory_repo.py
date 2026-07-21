import asyncio

from app.models.schemas import Workflow
from app.repository.base import WorkflowRepository


class InMemoryWorkflowRepo(WorkflowRepository):
    """Repo di default per sviluppo locale/test: nessuna dipendenza esterna."""

    def __init__(self) -> None:
        self._store: dict[str, Workflow] = {}
        self._lock = asyncio.Lock()

    async def save(self, workflow: Workflow) -> None:
        async with self._lock:
            self._store[workflow.id] = workflow

    async def get(self, workflow_id: str) -> Workflow | None:
        return self._store.get(workflow_id)
