import asyncio
import base64
import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_publisher = None


def _get_publisher():
    global _publisher
    if _publisher is None:
        from google.cloud import pubsub_v1

        _publisher = pubsub_v1.PublisherClient()
    return _publisher


async def publish_workflow_created(workflow_id: str) -> None:
    """Notifica che un workflow è pronto per essere processato.

    In staging/prod pubblica su Pub/Sub (il worker consuma via push subscription).
    In locale, senza infrastruttura, esegue il processing in-process cosi'
    l'API resta utilizzabile senza dover avviare emulatori.
    """
    if settings.use_pubsub:
        data = json.dumps({"workflow_id": workflow_id}).encode("utf-8")
        publisher = _get_publisher()
        topic_path = publisher.topic_path(settings.gcp_project, settings.pubsub_topic)
        publisher.publish(topic_path, data)
        logger.info("Pubblicato workflow.created per %s su %s", workflow_id, topic_path)
    else:
        from app.workers.processor import process_workflow

        logger.info("[local mode] Processing in-process del workflow %s", workflow_id)
        asyncio.create_task(process_workflow(workflow_id))


def decode_push_envelope(envelope: dict) -> str:
    """Estrae il workflow_id da un envelope di push subscription Pub/Sub."""
    message = envelope.get("message", {})
    data = base64.b64decode(message.get("data", "")).decode("utf-8")
    return json.loads(data)["workflow_id"]
