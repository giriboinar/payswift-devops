# PaySwift — Payment Gateway (SIMULATION / PORTFOLIO PROJECT)
# ---------------------------------------------------------------------------
# This is a PORTFOLIO SIMULATION, not company employment and not a real
# production payment system. Nothing here ever moves real money.
# See README.md ("What is real vs what is simulated") before reusing it.
# ---------------------------------------------------------------------------

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.kafka_client import publish_payment_event
from app.store import Payment, get_store, reset_store

AUDIT_LOG_PATH = os.environ.get("AUDIT_LOG_PATH", "")
KAFKA_TOPIC = os.environ.get("PAYSWIFT_KAFKA_TOPIC", "payswift.payments")

logger = logging.getLogger("payswift.audit")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
    if AUDIT_LOG_PATH:
        logger.addHandler(logging.FileHandler(AUDIT_LOG_PATH))


def audit(action: str, payment_id: str, detail: dict | None = None) -> None:
    """Write one JSON audit line (stdout, plus audit.log when configured).

    Audit logs are the record this project is designed to ship to
    Elasticsearch/Kibana. No card numbers, secrets, or personal data are
    ever logged — only payment ids, amounts, currencies, and statuses.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "payswift-api",
        "action": action,
        "payment_id": payment_id,
        **(detail or {}),
    }
    logger.info(json.dumps(record))


class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Payment amount, must be > 0")
    currency: str = Field(..., pattern=r"^[A-Z]{3}$", description="ISO code, e.g. INR")
    payer: str = Field(..., min_length=1)
    payee: str = Field(..., min_length=1)
    description: str = ""


app = FastAPI(
    title="PaySwift Payment API (Simulation)",
    description="Portfolio simulation of a payment gateway. No real money moves here.",
    version="0.1.0",
)


def _payload_hash(body: PaymentCreate) -> str:
    canonical = json.dumps(body.model_dump(), sort_keys=True)
    return str(abs(hash(canonical)))


@app.get("/health")
def health():
    return {"status": "ok", "service": "payswift-api (simulation)"}


@app.post("/payments", status_code=201)
def create_payment(
    body: PaymentCreate,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Create a payment.

    Idempotency (the exactly-once *effect* this project demonstrates):
    - Same Idempotency-Key + same payload  -> returns the ORIGINAL payment
      (HTTP 200, header X-Idempotent-Replay: true). No second transaction.
    - Same Idempotency-Key + different payload -> HTTP 409 (key reuse is a
      client bug; it must never silently create or overwrite a payment).
    - No key -> every request creates a new payment (callers that need
      exactly-once behaviour MUST send a key).
    """
    store = get_store()
    payload_hash = _payload_hash(body)

    if idempotency_key:
        existing = store.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            payment, stored_hash = existing
            if stored_hash != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency-Key already used with a different payload",
                )
            return JSONResponse(
                status_code=200,
                content=payment.model_dump(),
                headers={"X-Idempotent-Replay": "true"},
            )

    payment = Payment(
        id="pay_" + uuid.uuid4().hex[:12],
        amount=body.amount,
        currency=body.currency,
        payer=body.payer,
        payee=body.payee,
        description=body.description,
        status="created",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    store.save_payment(payment)
    if idempotency_key:
        store.save_idempotency_key(idempotency_key, payment.id, payload_hash)

    audit("payment.created", payment.id, {
        "amount": payment.amount,
        "currency": payment.currency,
        "status": payment.status,
    })
    # Kafka publish failure must NEVER fail the payment itself: the event
    # is a notification, not part of the transaction. Any publish error —
    # including an unexpected raise from the client — is logged and the
    # payment still returns 201.
    try:
        publish_payment_event(KAFKA_TOPIC, {
            "event": "payment.created",
            "payment_id": payment.id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
        })
    except Exception as exc:  # noqa: BLE001 — publish must never break payments
        logger.warning("Kafka publish raised (payment unaffected): %s", exc)
    return JSONResponse(status_code=201, content=payment.model_dump())


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str):
    payment = get_store().get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@app.get("/payments")
def list_payments():
    return get_store().list_payments()


def _transition(payment_id: str, expected: str, target: str, action: str):
    store = get_store()
    payment = store.get_payment(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != expected:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot {action} a payment in status '{payment.status}' "
                   f"(expected '{expected}')",
        )
    payment.status = target
    store.save_payment(payment)
    audit(f"payment.{action}", payment.id, {"status": target})
    return payment


@app.post("/payments/{payment_id}/authorize")
def authorize_payment(payment_id: str):
    return _transition(payment_id, "created", "authorized", "authorized")


@app.post("/payments/{payment_id}/capture")
def capture_payment(payment_id: str):
    return _transition(payment_id, "authorized", "captured", "captured")
