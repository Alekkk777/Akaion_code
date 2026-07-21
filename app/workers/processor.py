import logging

from app.agents.executor import ExecutorAgent
from app.agents.planner import PlannerAgent
from app.core.exceptions import PlanningError
from app.models.schemas import WorkflowStatus
from app.repository import repo

logger = logging.getLogger(__name__)

planner = PlannerAgent()
executor = ExecutorAgent()


async def process_workflow(workflow_id: str) -> None:
    """Pipeline planner -> executor -> persistenza. Condivisa dal fallback
    in-process (locale) e dall'endpoint di push subscription (worker/Pub/Sub).
    """
    workflow = await repo.get(workflow_id)
    if workflow is None:
        logger.error("Workflow %s non trovato durante il processing", workflow_id)
        return

    try:
        workflow = await planner.run(workflow)
        workflow = await executor.run(workflow)
    except PlanningError as exc:
        logger.warning("Planning fallito per %s: %s", workflow_id, exc)
        workflow.status = WorkflowStatus.FAILED
    except Exception:
        logger.exception("Errore inatteso nel processing del workflow %s", workflow_id)
        workflow.status = WorkflowStatus.FAILED

    await repo.save(workflow)
