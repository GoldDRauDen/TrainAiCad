# Build context: repository root.
FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./requirements.txt
COPY services/trainaicad-mcp/requirements.txt ./services/trainaicad-mcp/requirements.txt
RUN python3 -m venv /opt/cad-python \
    && /opt/cad-python/bin/pip install --no-cache-dir -r services/trainaicad-mcp/requirements.txt
COPY services/trainaicad-mcp/package*.json ./services/trainaicad-mcp/
RUN cd services/trainaicad-mcp && npm ci
COPY AI_ENTRYPOINT.md ./AI_ENTRYPOINT.md
COPY skills/lispcad/router ./skills/lispcad/router
COPY skills/lispcad/core ./skills/lispcad/core
COPY skills/lispcad/modes ./skills/lispcad/modes
COPY skills/lispcad/features ./skills/lispcad/features
COPY references ./references
COPY regression/datum ./regression/datum
COPY tools/export_dxf.py ./tools/export_dxf.py
COPY services/trainaicad-mcp ./services/trainaicad-mcp
RUN mkdir -p /app/data && chown node:node /app/data
ENV TRAINAICAD_PYTHON=/opt/cad-python/bin/python \
    TRAINAICAD_REPO_ROOT=/app \
    TRAINAICAD_MCP_DATA=/app/data \
    TRAINAICAD_MCP_HOST=0.0.0.0
USER node
WORKDIR /app/services/trainaicad-mcp
EXPOSE 8787
CMD ["npm", "run", "dev"]
