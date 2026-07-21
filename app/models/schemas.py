import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service: str  # es. "messaging", "calendar"
    action: str  # es. "send_message", "create_event"
    payload: dict = Field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: dict | None = None
    error: str | None = None


class WorkflowCreate(BaseModel):
    intent: str
    context: dict = Field(default_factory=dict)


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    intent: str
    context: dict = Field(default_factory=dict)
    steps: list[TaskStep] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
