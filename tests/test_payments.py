# Tests for the PaySwift simulation API.
# Run:  pytest -v
# No database, Kafka broker, or Docker is needed: tests use the in-memory
# store and stub out Kafka publishing (except the test that proves a Kafka
# failure does not fail a payment).

import pytest
from fastapi.testclient import TestClient

from app import main
from app.store import reset_store


@pytest.fixture(autouse=True)
def clean_store(monkeypatch):
    reset_store()
    # Kafka is not running under test; stub publishing to instant success
    # (one test below overrides this with a raising stub instead).
    monkeypatch.setattr(main, "publish_payment_event", lambda *a, **k: True)
    yield
    reset_store()


@pytest.fixture
def client():
    return TestClient(main.app)


def _payload(**overrides):
    body = {
        "amount": 499.0,
        "currency": "INR",
        "payer": "demo-customer",
        "payee": "demo-merchant",
        "description": "test order",
    }
    body.update(overrides)
    return body


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_create_payment(client):
    r = client.post("/payments", json=_payload())
    assert r.status_code == 201
    data = r.json()
    assert data["id"].startswith("pay_")
    assert data["status"] == "created"
    assert data["amount"] == 499.0


def test_duplicate_idempotency_key_creates_one_transaction(client):
    headers = {"Idempotency-Key": "key-abc-123"}
    first = client.post("/payments", json=_payload(), headers=headers)
    second = client.post("/payments", json=_payload(), headers=headers)
    assert first.status_code == 201
    assert second.status_code == 200  # replay, not a new payment
    assert second.headers["X-Idempotent-Replay"] == "true"
    assert second.json()["id"] == first.json()["id"]
    # The store really holds exactly one payment.
    assert len(client.get("/payments").json()) == 1


def test_same_key_different_payload_is_conflict(client):
    headers = {"Idempotency-Key": "key-reuse"}
    assert client.post("/payments", json=_payload(), headers=headers).status_code == 201
    r = client.post("/payments", json=_payload(amount=999.0), headers=headers)
    assert r.status_code == 409


def test_invalid_amount_rejected(client):
    r = client.post("/payments", json=_payload(amount=0))
    assert r.status_code == 422
    r = client.post("/payments", json=_payload(amount=-5))
    assert r.status_code == 422


def test_invalid_currency_rejected(client):
    assert client.post("/payments", json=_payload(currency="inr")).status_code == 422
    assert client.post("/payments", json=_payload(currency="RUPEE")).status_code == 422


def test_status_flow_authorize_then_capture(client):
    pid = client.post("/payments", json=_payload()).json()["id"]
    assert client.post(f"/payments/{pid}/authorize").json()["status"] == "authorized"
    assert client.post(f"/payments/{pid}/capture").json()["status"] == "captured"
    assert client.get(f"/payments/{pid}").json()["status"] == "captured"


def test_capture_before_authorize_rejected(client):
    pid = client.post("/payments", json=_payload()).json()["id"]
    assert client.post(f"/payments/{pid}/capture").status_code == 409


def test_unknown_payment_404(client):
    assert client.get("/payments/pay_doesnotexist").status_code == 404


def test_kafka_failure_does_not_fail_payment(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("broker down")

    monkeypatch.setattr(main, "publish_payment_event", boom)
    r = client.post("/payments", json=_payload())
    assert r.status_code == 201  # event loss is logged, payment survives
