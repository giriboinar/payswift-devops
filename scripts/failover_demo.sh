#!/bin/bash
# PaySwift Postgres failover DEMO (SIMULATION — local compose stack only).
# ---------------------------------------------------------------------------
# What this proves, honestly: with a primary + streaming-replica pair, you
# can stop the primary, promote the replica, and count rows before/after
# to show no committed demo transaction was lost in THIS demo run.
# What it does NOT prove: a real RDS Multi-AZ failover time, a production
# SLA, or "under 2 minutes" as a measured production result. The "under
# 2 minutes" claim in the project description is a DESIGN GOAL for the
# runbook (docs/dr-runbook.md), and this script prints its own measured
# wall-clock time so the demo result is visible, not asserted.
#
# Prereqs: docker compose stack up (see README.md), psql available inside
# the postgres containers. Run from the repo root.
# ---------------------------------------------------------------------------
set -e
cd "$(dirname "$0")/.."

echo "== 1. Row count on PRIMARY before failover =="
BEFORE=$(docker compose exec -T postgres-primary psql -U payswift -d payswift -tAc \
  "SELECT count(*) FROM payments;" 2>/dev/null || echo "0")
echo "Primary payments rows: $BEFORE"

echo "== 2. Stop primary, promote replica =="
START=$(date +%s)
docker compose stop postgres-primary
docker compose exec -T postgres-replica pg_ctl promote -D /var/lib/postgresql/data || true
# Wait until the replica accepts writes (no longer in recovery).
for i in $(seq 1 30); do
  if docker compose exec -T postgres-replica psql -U payswift -d payswift -tAc \
       "SELECT NOT pg_is_in_recovery();" 2>/dev/null | grep -q t; then
    break
  fi
  sleep 2
done
END=$(date +%s)

echo "== 3. Row count on PROMOTED replica after failover =="
AFTER=$(docker compose exec -T postgres-replica psql -U payswift -d payswift -tAc \
  "SELECT count(*) FROM payments;" 2>/dev/null || echo "0")
echo "Replica payments rows: $AFTER"
echo "Failover wall-clock: $((END - START)) seconds"
if [ "$BEFORE" = "$AFTER" ]; then
  echo "RESULT: no demo rows lost in this run (before=$BEFORE after=$AFTER)."
else
  echo "RESULT: row counts differ (before=$BEFORE after=$AFTER) — investigate replication lag."
fi
echo "NOTE: restart the stack (docker compose down -v && docker compose up) to reset the demo."
