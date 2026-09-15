import logging
import os
import subprocess

from config.settings import settings
from infrastructure.repositories.base import BaseDBRepo

logger = logging.getLogger(__name__)


def clean_database(engine):
    """ Drop all tables in the database to ensure it is clean before restoring a dump. """
    url = engine.url
    clean_command = [
        'psql',
        '-U', url.username,
        '-h', url.host,
        '-p', str(url.port),
        '-d', url.database,
        '-c', "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    ]

    try:
        subprocess.run(clean_command, check=True)
        logger.info("Database cleaned successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during database cleaning: {e}")


def restore_database(engine, dump_file_path):
    url = engine.url

    # Ensure the dump file exists
    if not os.path.exists(dump_file_path):
        logger.error("Dump file does not exist.")
        return

    command = [
        'psql',
        '-U', url.username,
        '-h', url.host,
        '-p', str(url.port),
        '-d', url.database,  # Specify the database into which to restore
        '-f', dump_file_path  # Specify the file path to the SQL dump
    ]

    try:
        subprocess.run(command, check=True)
        logger.info(f"Database restored successfully from {dump_file_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during database restoration: {e}")


# Usage
engine = BaseDBRepo.get_engine(uri=settings.DATABASE.URI, echo=True)
clean_database(engine)  # Clean the database first
restore_database(engine=engine, dump_file_path=settings.DATABASE.DUMP_PATH)