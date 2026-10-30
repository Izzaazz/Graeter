FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --uid 10001 --create-home dispatch && chown -R dispatch:dispatch /app
USER dispatch
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
