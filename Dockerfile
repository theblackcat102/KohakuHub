FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安裝 uv 與 httpx
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY ./pyproject.toml .
COPY ./src/kohakuhub ./src/kohakuhub
COPY ./docker/startup.py /app/startup.py
RUN chmod +x /app/startup.py

RUN uv pip install --system httpx
RUN uv pip install --system -e .

EXPOSE 48888
CMD ["/app/startup.py"]
