FROM python:3.12.1-slim-bullseye


WORKDIR    /sensors-guard-sandbox

# Installing packages (dedicated layer)
RUN        pip install pip==23.3.1

# Packages for using Taskfile
RUN        apt-get update && apt-get -y install openssh-client && apt-get -y  install build-essential curl file git \
           && apt-get -y install libpq-dev python3-dev
RUN        sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin




# Install requirements
COPY       requirements/ /tmp/requirements/
RUN        pip install -r /tmp/requirements/dev.txt
RUN        rm -rf /tmp/requirements/

# Project files
COPY       app/ app/
COPY       docker/streamer/entrypoint.sh docker/streamer/entrypoint.sh
COPY       docker/sensor_mocker/entrypoint.sh docker/sensor_mocker/entrypoint.sh
RUN        chmod +x docker/streamer/entrypoint.sh
RUN        chmod +x docker/sensor_mocker/entrypoint.sh

COPY       Taskfile.yaml/ Taskfile.yaml


COPY       .env .env

ENV        PYTHONPATH=/sensors-guard-sandbox/app/