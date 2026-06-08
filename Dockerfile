FROM python:3.9-slim

WORKDIR /app

# Installera nödvändiga bibliotek
RUN pip install pandas requests

# Kopiera skriptet till containern
COPY scb_analys_final.py .

# Kör skriptet när containern startar
CMD ["python", "scb_analys_final.py"]