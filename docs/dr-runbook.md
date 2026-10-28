# PaySwift DR runbook (SIMULATION — design + local demo, not a production SLA)
#
# RPO / RTO below are DESIGN GOALS for a real deployment, not measured
# results. The only measured result in this project is the local failover
# demo (scripts/failover_demo.sh), which prints its own wall-clock time.
#
# ## Design goals (real deployment, if this were built for real)
# - RPO (max data loss): 5 minutes — from continuous WAL shipping /
#   RDS automated backups + transaction logs.
# - RTO (time to restore service): 30 minutes — promote standby, repoint
#   the API, verify health, resume traffic.
# - Backup: nightly full snapshot + continuous WAL (RDS: automated backups,
#   7-day retention in the design; local demo: pg_dump, see below).
#
# ## What "cross-region DR" means here — HONESTLY
# The Terraform design (terraform/) provisions a single region. Cross-region
# restore is a DOCUMENTED PROCEDURE, not a provisioned second region:
# 1. Restore the latest snapshot into the DR region.
# 2. Replay WAL / transaction logs up to the last checkpoint.
# 3. Repoint DNS / API configuration to the DR endpoint.
# 4. Run the smoke checks in "Verification" below.
# No second region exists for this portfolio project, and none is claimed.
#
# ## Local backup / restore (works with the compose stack)
# ```bash
# # Backup (primary up):
# docker compose exec -T postgres-primary pg_dump -U payswift payswift > backup.sql
# # Restore (into a fresh database):
# docker compose exec -T postgres-primary psql -U payswift -d payswift < backup.sql
# ```
#
# ## Local failover demo (the simulated "RDS failover")
# ```bash
# bash scripts/failover_demo.sh
# ```
# The script counts rows on the primary, stops it, promotes the replica,
# counts rows again, and prints the wall-clock time. If the counts match,
# no demo transaction was lost IN THAT RUN. This simulates the shape of
# an RDS Multi-AZ failover; it is not an RDS failover and its timing is
# not an RDS SLA.
#
# ## Verification after any failover (real or demo)
# 1. `GET /health` returns ok.
# 2. A previously created payment id is still readable (`GET /payments/{id}`).
# 3. A new payment can be created (writes succeed on the promoted node).
# 4. Kafka consumer shows no duplicate processing (idempotent consumer).
# 5. Audit logs continue flowing to Kibana.
#
# ## What I would do differently in real production
# - Run the API against RDS with Multi-AZ + automated failover tests in
#   staging, and measure failover time over many runs before quoting it.
# - Use managed Kafka with exactly-once producer settings AND idempotent
#   consumers (both sides), never Kafka alone.
# - Store secrets in Vault with AppRole + short-lived tokens, never dev mode.
# - Test restores quarterly — an untested backup is not a backup.
