FROM python:3-slim-buster

COPY . /app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc git && \
    pip install -r /app/requirements.txt && \
    git submodule init && \
    git submodule update && \
    rm -rf saveData/logs saveData/decks && \
    ln -s /decks /app/saveData/decks && \
    ln -s /logs /app/saveData/logs

VOLUME /decks
VOLUME /logs

ENTRYPOINT ["python3", "./main.py"]
