FROM python:3.12-slim

WORKDIR /webui

COPY webui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/models.py /app/models.py
COPY app/config_loader.py /app/config_loader.py
COPY webui/ .

ENV PYTHONPATH=/app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
