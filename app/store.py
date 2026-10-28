# PaySwift storage layer (SIMULATION).
# Default: in-memory store, used by tests and by `docker compose` without
# extra setup. If PAYSWIFT_DATABASE_URL is set and psycopg is installed,
# a Postgres-backed store is used instead (this is the persistence target
# for the failover demo). No real credentials are stored in this repo.

import os

from pydantic import BaseModel


class Payment(BaseModel):
    id: str
    amount: float
    currency: str
    payer: str
    payee: str
    description: str = ""
    status: str
    created_at: str


class InMemoryStore:
    def __init__(self):
        self.payments: dict[str, Payment] = {}
        self.idempotency: dict[str, tuple[str, str]] = {}  # key -> (pay_id, hash)

    def save_payment(self, payment: Payment) -> None:
        self.payments[payment.id] = payment

    def get_payment(self, payment_id: str) -> Payment | None:
        return self.payments.get(payment_id)

    def list_payments(self) -> list[Payment]:
        return list(self.payments.values())

    def save_idempotency_key(self, key: str, payment_id: str, payload_hash: str) -> None:
        self.idempotency[key] = (payment_id, payload_hash)

    def get_by_idempotency_key(self, key: str):
        entry = self.idempotency.get(key)
        if entry is None:
            return None
        payment = self.payments.get(entry[0])
        if payment is None:
            return None
        return payment, entry[1]


class PostgresStore:
    """Postgres-backed store. Used only when PAYSWIFT_DATABASE_URL is set.

    Schema is created on first use. The idempotency table has a UNIQUE
    constraint on the key, so even a race between two identical requests
    cannot create a second transaction for the same key.
    """

    def __init__(self, dsn: str):
        import psycopg

        self._psycopg = psycopg
        self._dsn = dsn
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS payments (
                        id TEXT PRIMARY KEY, amount DOUBLE PRECISION NOT NULL,
                        currency TEXT NOT NULL, payer TEXT NOT NULL,
                        payee TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL, created_at TEXT NOT NULL)"""
                )
                cur.execute(
                    """CREATE TABLE IF NOT EXISTS idempotency_keys (
                        key TEXT PRIMARY KEY, payment_id TEXT NOT NULL,
                        payload_hash TEXT NOT NULL)"""
                )

    def save_payment(self, payment: Payment) -> None:
        with self._psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO payments
                       (id, amount, currency, payer, payee, description, status, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (id) DO UPDATE SET status = EXCLUDED.status""",
                    (payment.id, payment.amount, payment.currency, payment.payer,
                     payment.payee, payment.description, payment.status,
                     payment.created_at),
                )

    def get_payment(self, payment_id: str) -> Payment | None:
        with self._psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM payments WHERE id = %s", (payment_id,))
                row = cur.fetchone()
        if row is None:
            return None
        return Payment(id=row[0], amount=row[1], currency=row[2], payer=row[3],
                       payee=row[4], description=row[5], status=row[6],
                       created_at=row[7])

    def list_payments(self) -> list[Payment]:
        with self._psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM payments ORDER BY created_at")
                rows = cur.fetchall()
        return [Payment(id=r[0], amount=r[1], currency=r[2], payer=r[3],
                        payee=r[4], description=r[5], status=r[6],
                        created_at=r[7]) for r in rows]

    def save_idempotency_key(self, key: str, payment_id: str, payload_hash: str) -> None:
        with self._psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO idempotency_keys VALUES (%s, %s, %s) "
                    "ON CONFLICT (key) DO NOTHING",
                    (key, payment_id, payload_hash),
                )

    def get_by_idempotency_key(self, key: str):
        with self._psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payment_id, payload_hash FROM idempotency_keys WHERE key = %s",
                    (key,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        payment = self.get_payment(row[0])
        if payment is None:
            return None
        return payment, row[1]


_STORE = None


def get_store():
    global _STORE
    if _STORE is None:
        dsn = os.environ.get("PAYSWIFT_DATABASE_URL", "")
        if dsn:
            try:
                _STORE = PostgresStore(dsn)
            except Exception:
                # Never crash the API because the database is unavailable
                # in a local demo; fall back to memory and log via stdout.
                print("WARNING: Postgres unavailable, falling back to in-memory store")
                _STORE = InMemoryStore()
        else:
            _STORE = InMemoryStore()
    return _STORE


def reset_store() -> None:
    """Test helper: drop the cached store so each test starts clean."""
    global _STORE
    _STORE = None
