FROM python:3.11-slim

WORKDIR /app

# Install system deps needed by reportlab/psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x startup.sh

ENV PORT=8080
EXPOSE 8080

CMD ["./startup.sh"]
