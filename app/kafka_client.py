# Kafka client for PaySwift (SIMULATION).
# Publishes a `payment.created` event after a payment is stored. Delivery is
# best-effort: if Kafka is down or the library is missing, this returns
# False and the payment itself is unaffected. "Exactly-once" in this
# project comes from the idempotency key in app/main.py, NOT from Kafka —
# Kafka gives at-least-once delivery, and the consumer must be idempotent
# too (see app/consumer.py).

import json
import logging
import os

logger = logging.getLogger("payswift.kafka")


def publish_payment_event(topic: str, event: dict) -> bool:
    try:
        from kafka import KafkaProducer
    except ImportError:
        logger.warning("kafka-python not installed; skipping publish")
        return False
    try:
        producer = KafkaProducer(
            bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            request_timeout_ms=3000,
            max_block_ms=3000,
        )
        future = producer.send(topic, value=event, key=event["payment_id"].encode())
        future.get(timeout=5)
        producer.flush()
        producer.close()
        return True
    except Exception as exc:  # broker down, DNS failure, timeout, ...
        logger.warning("Kafka publish failed (payment unaffected): %s", exc)
        return False
