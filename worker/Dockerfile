# syntax=docker/dockerfile:1
#
# Başak bulut tarayıcı işçisi.
# Karar vermez; yalnız onaylı tek eylemi uygular. Dışarıya port açmaz.
#
# Neden resmî Playwright imajı değil: sürüm etiketi ile pip paketi
# arasında kayma olmasın diye Chromium, kurulu Playwright'ın kendi
# `install` komutuyla indirilir.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    BASAK_STATE_DIR=/home/basak/state \
    BASAK_ISCI_SAGLIK_PORT=8787

COPY worker/requirements-worker.txt /tmp/requirements-worker.txt
RUN python -m pip install --upgrade pip \
 && python -m pip install -r /tmp/requirements-worker.txt \
 && python -m playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/* /tmp/requirements-worker.txt \
 && useradd --create-home --uid 10001 --shell /usr/sbin/nologin basak \
 && mkdir -p /app /home/basak/state \
 && chown -R basak:basak /app /home/basak

COPY --chown=basak:basak worker /app/worker

USER basak
WORKDIR /app

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/saglik', timeout=3)"

CMD ["python", "-m", "worker"]
