#!/bin/bash
# Postgres standby entrypoint for the PaySwift failover demo (SIMULATION).
# First start: pg_basebackup from the primary, write standby.signal, then
# run Postgres in standby mode. Later starts: just run Postgres (data dir
# already populated). Promotion = `pg_ctl promote` (see scripts/failover_demo.sh).
set -e
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "Standby: first start, base backup from $PRIMARY_HOST ..."
  until pg_isready -h "$PRIMARY_HOST" -U payswift; do sleep 2; done
  PGPASSWORD="$REPLICA_PASSWORD" pg_basebackup -h "$PRIMARY_HOST" -D "$PGDATA" \
    -U replicator -v -P -W --wal-method=stream
  echo "primary_conninfo = 'host=$PRIMARY_HOST port=5432 user=replicator password=$REPLICA_PASSWORD'" >> "$PGDATA/postgresql.auto.conf"
  touch "$PGDATA/standby.signal"
  chown -R postgres:postgres "$PGDATA"
fi
exec gosu postgres postgres
