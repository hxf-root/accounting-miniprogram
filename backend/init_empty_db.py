"""Initialize a new, explicitly named SQLite database; never migrate existing data."""
import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from database import Base
import models  # noqa: F401 - register the schema


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, type=Path, help='absolute path to a NEW database')
    args = parser.parse_args()
    path = args.database
    if not path.is_absolute():
        parser.error('database path must be absolute')
    # Exclusive create makes accidental initialization of an existing database fail.
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        engine = create_engine(URL.create('sqlite', database=str(path)))
        try:
            Base.metadata.create_all(engine)
        finally:
            engine.dispose()
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    print('Created new empty database.')


if __name__ == '__main__':
    main()
