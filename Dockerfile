FROM python:3-slim-buster

ENV BOT_DIR /superdeckbreacker

# GCC is required to build some deps
RUN apt-get update && \
    apt-get install -y gcc

# Move requiremts in alone + install first to allow better docker caching
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy the whole bot in
COPY . $BOT_DIR

# Generate default config and place in our preferred config location
WORKDIR $BOT_DIR
RUN python3 ./makeDefaultConfig.py && \
    mv ./defaultCfg.toml /config.toml && \
    sed -i 's/saveData\/decks/\/decks/' /config.toml && \
    sed -i 's/saveData\/logs/\/logs/' /config.toml && \
    sed -i 's/bot\/cfg\/google_client_secret.json/\/google_client_secret.json/' /config.toml && \
    sed -i 's/saveData/\/saveData/' /config.toml && \
    sed -i 's/botToken_envVarName = ""/botToken_envVarName = "DISCORD_TOKEN"/' /config.toml && \
    mkdir -p /logs

# I/O
VOLUME /decks
VOLUME /saveData
ENTRYPOINT ["python3", "-u", "./main.py", "/config.toml"]
