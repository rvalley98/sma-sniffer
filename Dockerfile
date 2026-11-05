FROM python:3.12-slim

# Without this, print() output reaches the log only in delayed blocks.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/ /app/

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
