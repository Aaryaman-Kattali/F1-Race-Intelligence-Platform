"""
Pub/Sub topic and subscription configuration helper.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TOPIC = "f1-lap-telemetry"
DEFAULT_SUBSCRIPTION = "f1-lap-telemetry-sub"


def ensure_topic_exists(
    project_id: Optional[str] = None, topic_name: str = DEFAULT_TOPIC
) -> bool:
    """Create Pub/Sub topic if it doesn't exist."""
    project_id = project_id or os.getenv("GCP_PROJECT_ID")
    if not project_id:
        logger.warning("No GCP_PROJECT_ID — skipping topic creation")
        return False

    try:
        from google.cloud import pubsub_v1

        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, topic_name)

        try:
            publisher.get_topic(request={"topic": topic_path})
            logger.info(f"✅ Topic exists: {topic_path}")
        except Exception:
            publisher.create_topic(request={"name": topic_path})
            logger.info(f"📦 Created topic: {topic_path}")

        return True
    except Exception as e:
        logger.error(f"❌ Topic setup failed: {e}")
        return False


def ensure_subscription_exists(
    project_id: Optional[str] = None,
    topic_name: str = DEFAULT_TOPIC,
    subscription_name: str = DEFAULT_SUBSCRIPTION,
) -> bool:
    """Create Pub/Sub subscription if it doesn't exist."""
    project_id = project_id or os.getenv("GCP_PROJECT_ID")
    if not project_id:
        logger.warning("No GCP_PROJECT_ID — skipping subscription creation")
        return False

    try:
        from google.cloud import pubsub_v1

        subscriber = pubsub_v1.SubscriberClient()
        publisher = pubsub_v1.PublisherClient()

        topic_path = publisher.topic_path(project_id, topic_name)
        sub_path = subscriber.subscription_path(project_id, subscription_name)

        try:
            subscriber.get_subscription(request={"subscription": sub_path})
            logger.info(f"✅ Subscription exists: {sub_path}")
        except Exception:
            subscriber.create_subscription(
                request={"name": sub_path, "topic": topic_path}
            )
            logger.info(f"📦 Created subscription: {sub_path}")

        return True
    except Exception as e:
        logger.error(f"❌ Subscription setup failed: {e}")
        return False


def setup_pubsub(project_id: Optional[str] = None) -> bool:
    """Set up both topic and subscription."""
    t = ensure_topic_exists(project_id)
    s = ensure_subscription_exists(project_id)
    return t and s
