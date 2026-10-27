# syntax=docker/dockerfile:1
# Separate, unprivileged agent daemon; no API port or host Docker socket.
# Dockerfile.dockerignore selectively includes source code, not state/secrets.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    BASAK_STATE_DIR=/home/basak/state \
    BASAK_URETIM=1 \
    BASAK_BROWSER_ISOLATED=1

COPY requirements.txt worker/requirements-worker.txt /tmp/
RUN python -m pip install -r /tmp/requirements.txt \
    -r /tmp/requirements-worker.txt \
 && python -m playwright install --with-deps chromium \
 && useradd --create-home --uid 10001 --shell /usr/sbin/nologin basak \
 && mkdir -p /app /home/basak/state \
 && chown -R basak:basak /app /home/basak/state \
 && chmod -R a+rX /ms-playwright \
 && rm -rf /var/lib/apt/lists/* /tmp/requirements.txt /tmp/requirements-worker.txt

WORKDIR /app
COPY --chown=basak:basak . /app

USER basak

# No web port. The worker polls the SAME PostgreSQL task ledger as the web.
# Code execution stays unavailable until a separate gVisor runner is approved.
ENTRYPOINT ["python", "-m", "worker.platform"]
