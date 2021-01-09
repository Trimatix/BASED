FROM python:3-slim-buster

# GCC is required to build some deps
RUN apt-get update && \
    apt-get install -y gcc

# Move requiremts in alone + install first to allow better docker caching
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

COPY . /superdeckbreacker
RUN mkdir -p /superdeckbreacker/saveData && \
    ln -s /decks /superdeckbreacker/saveData/decks

# Generate default config and place in our preferred config location
WORKDIR /superdeckbreacker
RUN python3 ./makeDefaultConfig.py && \
    mv ./defaultCfg.toml /config.toml

# I/O
VOLUME /decks
ENTRYPOINT ["python3", "./main.py", "/config.toml"]
