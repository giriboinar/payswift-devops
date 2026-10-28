# PaySwift audit logging (SIMULATION)
#
# ## What is logged
# Every payment lifecycle event, one JSON line per event:
# `payment.created`, `payment.authorized`, `payment.captured`.
# Fields: timestamp, service, action, payment_id, amount, currency, status.
#
# ## What is NEVER logged
# Card numbers, bank details, passwords, tokens, emails, phone numbers.
# Payer/payee in this demo are opaque demo identifiers, not real people.
#
# ## Where it goes
# 1. API stdout (always) — visible with `docker compose logs api`.
# 2. `/app/logs/audit.log` inside the api container (shared volume
#    `audit-logs`) when `AUDIT_LOG_PATH` is set (compose sets it).
# 3. Elasticsearch index `payswift-audit` via the log-shipper service
#    (scripts/log_shipper.py), viewable in Kibana at http://localhost:5601
#    (Discover -> index pattern `payswift-audit*`).
# This is a lightweight ELK-compatible pipeline: Elasticsearch + Kibana +
# a small shipper, instead of a full Logstash deployment, to keep the
# local stack light. The audit trail itself (the JSON lines) is identical.
#
# ## Sample log lines
# ```json
# {"timestamp": "2026-10-28T12:00:00+00:00", "service": "payswift-api", "action": "payment.created", "payment_id": "pay_a1b2c3d4e5f6", "amount": 499.0, "currency": "INR", "status": "created"}
# {"timestamp": "2026-10-28T12:01:00+00:00", "service": "payswift-api", "action": "payment.authorized", "payment_id": "pay_a1b2c3d4e5f6", "status": "authorized"}
# {"timestamp": "2026-10-28T12:02:00+00:00", "service": "payswift-api", "action": "payment.captured", "payment_id": "pay_a1b2c3d4e5f6", "status": "captured"}
# ```
#
# ## Retention (design)
# Local demo: logs live as long as the `audit-logs` volume does.
# Real deployment: hot index 30 days in Elasticsearch, then archive to
# object storage for 1 year for audit/compliance — a design goal, not
# something this local stack implements.
