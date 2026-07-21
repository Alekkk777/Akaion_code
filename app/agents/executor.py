import logging

from app.agents.base import Agent
from app.models.schemas import Workflow, WorkflowStatus
from app.services.registry import registry

logger = logging.getLogger(__name__)


class ExecutorAgent(Agent):
    """Esegue gli step del workflow in sequenza, delegando ai service registrati."""

    async def run(self, workflow: Workflow) -> Workflow:
        workflow.status = WorkflowStatus.IN_PROGRESS

        for step in workflow.steps:
            try:
                handler = registry.get(step.service)
                step.result = await handler.execute(step.action, step.payload)
                step.status = WorkflowStatus.COMPLETED
            except Exception as exc:  # noqa: BLE001 - isolamento fallimento per-step
                logger.exception("Step %s (%s.%s) fallito", step.id, step.service, step.action)
                step.status = WorkflowStatus.FAILED
                step.error = str(exc)
                workflow.status = WorkflowStatus.FAILED
                return workflow

        workflow.status = WorkflowStatus.COMPLETED
        return workflow
