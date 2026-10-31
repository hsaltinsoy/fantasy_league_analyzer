"""Import a local Football-Data CSV without changing the source file."""
import argparse
import json

from storage.db import engine_from_env
from storage.football_data_repository import FootballDataRepository


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True)
    parser.add_argument('--season', default='2026-27')
    args = parser.parse_args()
    engine = engine_from_env()
    try:
        result = FootballDataRepository(engine).import_file(args.file, season=args.season)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
