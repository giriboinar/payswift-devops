# PaySwift API image (simulation). Pinned base, non-root user, no secrets.
FROM python:3.12.16-slim-bookworm

# Apply current Debian bookworm security updates: the base image snapshot alone
# still carries OS packages with later-published fixes.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN useradd -m appuser && mkdir -p /app/logs && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
