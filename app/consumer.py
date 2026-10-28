# PaySwift Kafka consumer (SIMULATION).
# Reads `payment.created` events and logs an acknowledgement for each one.
# It is idempotent by design: it tracks payment ids it has already
# acknowledged, so a redelivered (at-least-once) Kafka message is logged
# as a duplicate, never processed twice.
#
# Run locally (needs the compose stack up):
#   docker compose exec api python -m app.consumer

import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("payswift.consumer")

TOPIC = os.environ.get("PAYSWIFT_KAFKA_TOPIC", "payswift.payments")
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")


def main() -> None:
    from kafka import KafkaConsumer

    seen: set[str] = set()
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        group_id="payswift-audit",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    logger.info("Consumer listening on topic %s", TOPIC)
    for message in consumer:
        event = message.value
        payment_id = event.get("payment_id", "?")
        if payment_id in seen:
            logger.info("DUPLICATE event ignored (at-least-once redelivery): %s", payment_id)
            continue
        seen.add(payment_id)
        logger.info("ACK payment.created payment_id=%s amount=%s %s",
                    payment_id, event.get("amount"), event.get("currency"))


if __name__ == "__main__":
    main()
