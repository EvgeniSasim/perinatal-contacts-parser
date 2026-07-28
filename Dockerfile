FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt

COPY apps/api /app/apps/api
COPY data /app/data

ENV PYTHONPATH=/app/apps/api
ENV DATABASE_URL=postgresql+psycopg2://pnc:pnc@db:5432/pnc
ENV SEED_CSV_PATH=/app/data/seed/institutions.csv
ENV STORAGE_DIR=/app/storage
ENV ADMIN_API_KEY=dev-admin-key-change-me

RUN mkdir -p /app/storage/exports

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
