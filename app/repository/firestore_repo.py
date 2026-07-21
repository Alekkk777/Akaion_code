from google.cloud import firestore

from app.core.config import settings
from app.models.schemas import Workflow
from app.repository.base import WorkflowRepository


class FirestoreWorkflowRepo(WorkflowRepository):
    def __init__(self) -> None:
        self._client = firestore.AsyncClient(project=settings.gcp_project)
        self._collection = self._client.collection(settings.firestore_collection)

    async def save(self, workflow: Workflow) -> None:
        await self._collection.document(workflow.id).set(workflow.model_dump(mode="json"))

    async def get(self, workflow_id: str) -> Workflow | None:
        doc = await self._collection.document(workflow_id).get()
        if not doc.exists:
            return None
        return Workflow(**doc.to_dict())
