FROM python:3.12-slim AS dependencies
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
# Populate the embedding cache during build, before runtime memory limits apply.
RUN mkdir -p /opt/chroma-cache/onnx_models/all-MiniLM-L6-v2 \
    && curl --fail --location --retry 3 \
       https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz \
       -o /tmp/onnx.tar.gz \
    && tar -xzf /tmp/onnx.tar.gz -C /opt/chroma-cache/onnx_models/all-MiniLM-L6-v2 \
    && rm /tmp/onnx.tar.gz

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    ANONYMIZED_TELEMETRY=False CHROMA_HOST=127.0.0.1 CHROMA_PORT=8001 \
    CHROMA_PERSIST_DIRECTORY=/tmp/serviceflow/chroma \
    EVAL_BASELINE_PATH=/tmp/serviceflow/eval/baseline.json PROMETHEUS_PORT=0
RUN useradd --create-home --uid 1000 serviceflow
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=dependencies /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin
COPY --from=dependencies --chown=serviceflow:serviceflow /opt/chroma-cache /home/serviceflow/.cache/chroma
COPY --chown=serviceflow:serviceflow . .
RUN mkdir -p /tmp/serviceflow/chroma /tmp/serviceflow/eval /app/logs \
    && chown -R serviceflow:serviceflow /tmp/serviceflow /app/logs
USER serviceflow
EXPOSE 10000
CMD ["python", "-m", "deploy.serve"]
