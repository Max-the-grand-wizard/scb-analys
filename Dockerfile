FROM python:3.9-slim

WORKDIR /app

# Installera systemberoenden
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Kopiera requirements.txt först
COPY requirements.txt .

# Uppgradera pip och installera numpy först (viktigt!)
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir numpy==1.24.3
RUN pip install --no-cache-dir -r requirements.txt

# Kopiera applikationen
COPY app.py .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Använd flask's inbyggda server istället för gunicorn (för att testa)
CMD ["python", "app.py"]