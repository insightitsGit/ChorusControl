# Mother — multi-stage
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY choruscontrol ./choruscontrol
COPY scripts ./scripts
RUN pip install --no-cache-dir --prefix=/install ".[server,agent,postgres,prism]"

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY choruscontrol ./choruscontrol
COPY scripts ./scripts
COPY pyproject.toml README.md ./
ENV CHORUSCONTROL_DEMO_MODE=1
ENV PYTHONPATH=/app
EXPOSE 8443
CMD ["choruscontrol", "serve", "--host", "0.0.0.0", "--port", "8443"]
