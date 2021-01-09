FROM python:3-slim-buster

# Move requiremts in alone + install first to allow better docker caching
COPY requirements.txt /tmp/requirements.txt
RUN apt-get update && \
    apt-get install -y gcc && \
    pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

COPY . /app
RUN rm -rf /app/saveData && \
    ln -s /saveData /app/saveData

VOLUME /saveData
WORKDIR /app
ENTRYPOINT ["python3", "./main.py"]
