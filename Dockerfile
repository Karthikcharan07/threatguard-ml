FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt pyproject.toml ./
COPY threatguard ./threatguard
COPY ml ./ml
RUN pip install --no-cache-dir --upgrade pip setuptools && pip install --no-cache-dir .
USER 10001:10001
EXPOSE 8000
ENV TG_MODEL_DIR=/models
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).close()"]
CMD ["uvicorn", "threatguard.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
