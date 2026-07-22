import os
import time

from google.api_core.exceptions import AlreadyExists
from google.cloud import pubsub_v1

PROJECT = os.environ.get("GCP_PROJECT", "akaion-dev")
TOPIC_ID = os.environ.get("PUBSUB_TOPIC", "workflow-created")
SUBSCRIPTION_ID = os.environ.get("PUBSUB_SUBSCRIPTION", "workflow-created-sub")
PUSH_ENDPOINT = os.environ["PUSH_ENDPOINT"]


def _wait_for_emulator(publisher: pubsub_v1.PublisherClient, project: str, attempts: int = 15) -> None:
    for attempt in range(1, attempts + 1):
        try:
            next(publisher.list_topics(request={"project": f"projects/{project}"}).__iter__(), None)
            return
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(2)


def main() -> None:
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()

    _wait_for_emulator(publisher, PROJECT)

    topic_path = publisher.topic_path(PROJECT, TOPIC_ID)
    sub_path = subscriber.subscription_path(PROJECT, SUBSCRIPTION_ID)

    try:
        publisher.create_topic(request={"name": topic_path})
        print(f"created topic {topic_path}")
    except AlreadyExists:
        print(f"topic {topic_path} already exists")

    try:
        subscriber.create_subscription(
            request={
                "name": sub_path,
                "topic": topic_path,
                "push_config": {"push_endpoint": PUSH_ENDPOINT},
            }
        )
        print(f"created subscription {sub_path} -> {PUSH_ENDPOINT}")
    except AlreadyExists:
        print(f"subscription {sub_path} already exists")


if __name__ == "__main__":
    main()
