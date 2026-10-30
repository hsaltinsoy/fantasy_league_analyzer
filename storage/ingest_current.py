"""Ingest a current authenticated TFF player response into PostgreSQL."""
from data_sources.tff_official import fetch_players
from storage.db import engine_from_env
from storage.runtime_repository import RuntimeRepository
from analysis.live_benchmark import fetch_official_fixtures


def main():
    repository = RuntimeRepository(engine_from_env())
    print({'players': repository.ingest_current_players(fetch_players(include_evidence=True))})
    print({'fixtures': repository.ingest_current_fixtures(fetch_official_fixtures(include_evidence=True))})


if __name__ == '__main__':
    main()
