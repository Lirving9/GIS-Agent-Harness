FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GDAL_CONFIG=/usr/bin/gdal-config \
    GIS_AGENT_HARNESS_RUN_ROOT=/workspace/.runs \
    GIS_AGENT_HARNESS_STATE_FILE=/workspace/AGENT_STATE.md

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --chown=appuser:appuser pyproject.toml requirements.txt README.md AGENTS.md .env.example litellm-config.yaml ./
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser goals ./goals
COPY --chown=appuser:appuser scripts ./scripts
COPY --chown=appuser:appuser docs ./docs
COPY --chown=appuser:appuser tests ./tests
COPY --chown=appuser:appuser .codex ./.codex

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install -r requirements.txt

RUN mkdir -p /workspace && chown appuser:appuser /workspace

USER appuser
WORKDIR /workspace

ENTRYPOINT ["python3", "-m", "gis_agent_harness.cli"]
CMD ["--help"]
