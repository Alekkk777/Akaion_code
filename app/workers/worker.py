from fastapi import FastAPI, Request

from app.core.logging import configure_logging
from app.core.pubsub import decode_push_envelope
from app.services.bootstrap import register_services
from app.workers.processor import process_workflow

configure_logging()
register_services()

app = FastAPI(title="Akaion LifeOS — Worker")


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok"}


@app.post("/pubsub/push", tags=["pubsub"])
async def handle_push(request: Request) -> dict:
    envelope = await request.json()
    workflow_id = decode_push_envelope(envelope)
    await process_workflow(workflow_id)
    return {"status": "ack"}
