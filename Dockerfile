FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Vlož soubor s Google credentials, pokud testuješ lokálně!
# ADD credentials.json /app/credentials.json

CMD ["python", "main.py"]