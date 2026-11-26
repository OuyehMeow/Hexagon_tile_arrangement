FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8765 \
    HEX_DATA_DIR=/data

WORKDIR /app

COPY hex-path-composer.html hex-path-tiles.html make_hex_tiles.py server.py ./

RUN mkdir -p /data/exports && useradd --create-home appuser && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/status', timeout=2)" || exit 1

CMD ["python3", "server.py", "--host", "0.0.0.0", "--port", "8765", "--data-dir", "/data"]
