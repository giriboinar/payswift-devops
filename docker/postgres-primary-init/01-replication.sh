# Postgres primary init: create the replication user used by the standby.
# Runs once, on first init of the primary data volume.
#!/bin/bash
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD '${POSTGRES_PASSWORD}';
EOSQL
