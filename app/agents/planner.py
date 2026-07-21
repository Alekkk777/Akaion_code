from app.agents.base import Agent
from app.core.exceptions import PlanningError
from app.models.schemas import TaskStep, Workflow


class PlannerAgent(Agent):
    """Scompone l'intent utente in una sequenza di TaskStep eseguibili.

    v1: pattern matching su keyword. Il contratto (intent -> list[TaskStep])
    e' lo stesso che userebbe un planner LLM-based, quindi lo swap e' un
    dettaglio implementativo isolato qui dentro.
    """

    async def run(self, workflow: Workflow) -> Workflow:
        workflow.steps = self._plan(workflow.intent, workflow.context)
        return workflow

    def _plan(self, intent: str, context: dict) -> list[TaskStep]:
        intent_lower = intent.lower()
        steps: list[TaskStep] = []

        if any(k in intent_lower for k in ("messaggio", "message", "invia", "manda")):
            steps.append(
                TaskStep(service="messaging", action="send_message", payload={"text": intent, **context})
            )

        if any(k in intent_lower for k in ("calendario", "calendar", "riunione", "evento", "blocca")):
            steps.append(TaskStep(service="calendar", action="create_event", payload=dict(context)))

        if not steps:
            raise PlanningError(f"Nessun agente in grado di gestire l'intent: '{intent}'")

        return steps
