FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["gunicorn", "-k", "eventlet", "-w", "1", "-b", "0.0.0.0:8000", "app:app"]
