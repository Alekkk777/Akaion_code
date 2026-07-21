from fastapi import APIRouter

from app.core.exceptions import WorkflowNotFoundError
from app.core.pubsub import publish_workflow_created
from app.models.schemas import Workflow, WorkflowCreate
from app.repository import repo

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", status_code=202, summary="Crea ed avvia un nuovo workflow")
async def create_workflow(payload: WorkflowCreate) -> dict:
    workflow = Workflow(intent=payload.intent, context=payload.context)
    await repo.save(workflow)
    await publish_workflow_created(workflow.id)
    return {"workflow_id": workflow.id, "status": workflow.status}


@router.get("/{workflow_id}", summary="Recupera stato e risultato di un workflow")
async def get_workflow(workflow_id: str) -> Workflow:
    workflow = await repo.get(workflow_id)
    if workflow is None:
        raise WorkflowNotFoundError(workflow_id)
    return workflow
