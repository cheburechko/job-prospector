FROM python:3.13-slim

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install-deps chromium

RUN groupadd -r scraper && useradd --no-log-init -r -g scraper scraper --home-dir /app
USER scraper

WORKDIR /app

RUN playwright install chromium

COPY src/ src/

ENV PYTHONPATH=/app/src
ENTRYPOINT ["python", "-m", "main"]
CMD ["worker"]
