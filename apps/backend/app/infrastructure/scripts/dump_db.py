import subprocess
from infrastructure.repositories.base import BaseDBRepo
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


def dump_database(engine, dump_file_path):
    url = engine.url

    command = [
        'pg_dump',
        '-U', url.username,
        '-h', url.host,

        '-p', str(url.port),
        url.database
    ]
    # Open the file at the specified path
    with open(dump_file_path, "w") as file:
        subprocess.run(command, stdout=file, check=True)
        logger.info(f"Database dumped successfully to {dump_file_path}")


# Usage
dump_database(engine=BaseDBRepo.get_engine(uri=settings.DATABASE.URI, echo=True),
              dump_file_path=settings.DATABASE.DUMP_PATH)
