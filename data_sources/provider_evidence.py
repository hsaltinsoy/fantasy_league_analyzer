"""Provider-neutral evidence contracts; no provider feeds production scoring yet."""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol


class MissingReason(str, Enum):
    NOT_REPORTED = 'not_reported'
    NOT_COVERED = 'not_covered'
    NOT_YET_PUBLISHED = 'not_yet_published'
    NOT_APPLICABLE = 'not_applicable'
    INVALID = 'invalid'
    UNPOPULATED_FIELD = 'unpopulated_field'


def utc(value):
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Evidence timestamp must include timezone')
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class EntityMatch:
    provider_id: str
    canonical_id: str | None
    confidence: float
    method: str
    reviewed: bool = False

    def __post_init__(self):
        if not 0 <= self.confidence <= 1:
            raise ValueError('Match confidence must be between 0 and 1')
        if self.canonical_id is not None and (not self.reviewed or self.confidence < .9):
            raise ValueError('Canonical IDs require reviewed high-confidence matching')


@dataclass(frozen=True)
class EvidenceValue:
    field: str
    value: int | float | str | bool | None
    source_field: str
    missing_reason: MissingReason | None = None

    def __post_init__(self):
        if (self.value is None) != (self.missing_reason is not None):
            raise ValueError('Missing evidence requires an explicit reason; present evidence must not have one')


@dataclass(frozen=True)
class EvidenceRecord:
    kind: str
    provider_entity_id: str
    match: EntityMatch | None
    event_at: datetime
    published_at: datetime | None
    fields: tuple[EvidenceValue, ...]

    def __post_init__(self):
        if self.kind not in {'player_stat', 'team_stat', 'fixture', 'availability', 'expected_metric'}:
            raise ValueError('Unknown evidence kind')
        utc(self.event_at)
        if self.published_at is not None:
            utc(self.published_at)
        if len({v.field for v in self.fields}) != len(self.fields):
            raise ValueError('Duplicate evidence field')


@dataclass(frozen=True)
class EvidenceBatch:
    provider: str
    endpoint: str
    retrieved_at: datetime
    source_sha256: str
    competition_id: str
    season: str
    records: tuple[EvidenceRecord, ...]
    complete: bool
    missing_reason: MissingReason | None = None

    def __post_init__(self):
        utc(self.retrieved_at)
        if not self.provider or not self.endpoint or len(self.source_sha256) != 64 or \
                any(c not in '0123456789abcdef' for c in self.source_sha256.lower()):
            raise ValueError('Provider, endpoint and SHA-256 provenance required')
        if not self.complete and self.missing_reason is None:
            raise ValueError('Incomplete provider response requires a reason')
        if self.complete and self.missing_reason is not None:
            raise ValueError('Complete response cannot carry a missing reason')

    def before(self, cutoff, *, event_cutoff=None):
        """Reject late observations; never silently drop post-cutoff records."""
        cutoff = utc(cutoff)
        event_cutoff = utc(event_cutoff or cutoff)
        if utc(self.retrieved_at) > cutoff:
            raise ValueError('Provider response was retrieved after prediction cutoff')
        for record in self.records:
            if record.kind in {'player_stat', 'team_stat'} and utc(record.event_at) >= event_cutoff:
                raise ValueError('Observed statistic is not historical at prediction cutoff')
            if record.published_at is not None and utc(record.published_at) > cutoff:
                raise ValueError('Field was published after prediction cutoff')
        return self


class ProviderAdapter(Protocol):
    def player_stats(self, competition_id: str, season: str, *, cutoff: datetime) -> EvidenceBatch: ...
    def team_stats(self, competition_id: str, season: str, *, cutoff: datetime) -> EvidenceBatch: ...
    def fixtures(self, competition_id: str, season: str, *, cutoff: datetime) -> EvidenceBatch: ...
    def availability(self, competition_id: str, season: str, *, cutoff: datetime) -> EvidenceBatch: ...
    def expected_metrics(self, competition_id: str, season: str, *, cutoff: datetime) -> EvidenceBatch: ...


def require_complete(batch: EvidenceBatch, *, kind: str, cutoff: datetime):
    batch.before(cutoff)
    if not batch.complete or batch.missing_reason is not None:
        raise ValueError('Provider evidence incomplete')
    if not batch.records or any(r.kind != kind for r in batch.records):
        raise ValueError('Provider evidence missing required record kind')
    return batch
