FROM python:3.11-slim

WORKDIR /app

# System deps needed by psycopg2 / xgboost / pyod at build time
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# NOTE: app.main:app is a placeholder target -- app/main.py currently has no
# routable FastAPI instance uncommented yet. Uncomment the CMD once real
# implementation begins.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
