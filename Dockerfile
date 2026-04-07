FROM python:3.11-slim

WORKDIR /app

COPY server/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY models.py .
COPY server/ ./server/

EXPOSE 7860

# Start the FastAPI server using UvicornEXPOSE 7860
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]