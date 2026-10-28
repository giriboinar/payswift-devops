# Tiny image for the log shipper: Python + requests only.
FROM python:3.12.16-slim-bookworm
WORKDIR /shipper
RUN pip install --no-cache-dir requests==2.32.3
COPY scripts/log_shipper.py .
CMD ["python", "log_shipper.py"]
