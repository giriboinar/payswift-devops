#!/usr/bin/env python3
"""Lightweight log shipper for the PaySwift simulation stack.

Tails the API audit log (shared volume /app/logs/audit.log) and indexes
each JSON line into Elasticsearch, so audit events are visible in Kibana.
This replaces a full Logstash deployment for local runs — same visible
result (searchable audit trail), far less memory. Not a production
log pipeline: no retries beyond one attempt, no backpressure handling.
"""
import json
import os
import time

import requests

LOG_PATH = "/app/logs/audit.log"
ES_URL = os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200")
INDEX = "payswift-audit"


def main() -> None:
    while not os.path.exists(LOG_PATH):
        time.sleep(2)
    with open(LOG_PATH) as fh:
        fh.seek(0, 2)  # tail only new lines
        while True:
            line = fh.readline()
            if not line:
                time.sleep(1)
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                requests.post(f"{ES_URL}/{INDEX}/_doc", json=doc, timeout=5)
            except requests.RequestException:
                pass  # local demo: drop on ES outage, do not crash


if __name__ == "__main__":
    main()
