FROM python:3-slim-buster

COPY . /app

RUN apt-get update && \
    apt-get install -y gcc git && \
    pip install -r /app/requirements.txt

WORKDIR /app
ENTRYPOINT ["python3", "./main.py"]
