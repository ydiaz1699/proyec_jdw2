# JDownloader MCP Server — imagen de distribución.
# El servidor habla por stdio, así que el cliente MCP lo lanza con `docker run -i`.
FROM python:3.12-slim

# Metadatos para GHCR (enlaza la imagen con el repo).
LABEL org.opencontainers.image.source="https://github.com/ydiaz1699/proyec_jdw2" \
      org.opencontainers.image.description="MCP Server for full JDownloader remote control via My.JDownloader API" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1) Dependencias primero (mejor cache de capas).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) Código del paquete.
COPY src/ ./src/

# El paquete vive en /app/src; lo ponemos en el PYTHONPATH para poder
# ejecutar `python -m jdownloader_mcp.server` sin instalar nada más.
ENV PYTHONPATH=/app/src

# Ejecuta como usuario no-root por seguridad.
RUN useradd --create-home --uid 10001 mcp
USER mcp

# stdio MCP: el proceso es el servidor; el cliente se conecta por stdin/stdout.
ENTRYPOINT ["python", "-m", "jdownloader_mcp.server"]
