# Use the offical python image
FROM python:3.12-slim

# 1- Setup the work dir
WORKDIR /fwc

# Install PostgreSQL client
RUN apt-get update && \
    apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*


# Packages for using psycopg2 and Taskfile
RUN        apt-get update && apt-get -y install openssh-client && apt-get -y  install build-essential curl file git \
           && apt-get -y install libpq-dev python3-dev
RUN        sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin



# Installing packages (dedicated layer)
RUN        pip install pip==24.0


# Copy requirements file and install Python dependencies
COPY requirements/base.txt /fwc/requirements/base.txt
RUN pip install -r /fwc/requirements/base.txt

# 2- Copy The project files

COPY        app/ app/
COPY        docker/ docker/
RUN        chmod +x docker/streamer/entrypoint.sh
RUN        chmod +x docker/api/entrypoint.sh
COPY        Taskfile.yaml Taskfile.yaml
COPY        alembic/ alembic/
COPY        alembic.ini alembic.ini



ENV         PYTHONPATH=/fwc/app/
