FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV ACCIONES_DRY_RUN=true

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
