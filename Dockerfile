FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt ./
RUN --mount=type=secret,id=pip_ca,required=false \
    if [ -f /run/secrets/pip_ca ]; then \
      cat /etc/ssl/certs/ca-certificates.crt /run/secrets/pip_ca > /tmp/pip-ca.pem && \
      PIP_CERT=/tmp/pip-ca.pem python -m pip install --no-cache-dir -r requirements.txt && \
      rm /tmp/pip-ca.pem; \
    else \
      python -m pip install --no-cache-dir -r requirements.txt; \
    fi

COPY app ./app
COPY data ./data
COPY scripts ./scripts
COPY examples ./examples

RUN useradd --create-home appuser && \
    mkdir -p /app/data/runtime && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
