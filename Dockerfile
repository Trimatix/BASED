FROM python:3-slim-buster

COPY . /app
WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc && \
    pip install -r /app/requirements.txt && \
    rm -rf saveData/logs saveData/decks && \
    ln -s /saveData /app/saveData

VOLUME /saveData

ENTRYPOINT ["python3", "./main.py"]
