from app.core.config import settings
from app.repository.base import WorkflowRepository
from app.repository.memory_repo import InMemoryWorkflowRepo


def _build_repository() -> WorkflowRepository:
    if settings.use_firestore:
        from app.repository.firestore_repo import FirestoreWorkflowRepo

        return FirestoreWorkflowRepo()
    return InMemoryWorkflowRepo()


repo: WorkflowRepository = _build_repository()
