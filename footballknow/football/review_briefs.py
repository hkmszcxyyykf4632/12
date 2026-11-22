"""Small, source-linked excerpts of completed audits for past-performance rows."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, ValidationError

from .files import STATE
from .statistics_models import Frozen


class Source(Frozen):
    id: str
    title: str = ''
    url: str = ''


class Fact(Frozen):
    id: str
    sourceIds: list[str] = Field(default_factory=list)


class Finding(Frozen):
    title: str = ''
    explanation: str = ''
    evidenceIds: list[str] = Field(default_factory=list)
    nextCheck: str = ''
    category: str = ''


class Original(Frozen):
    stage: str = ''
    pick: str | None = None
    shortlist: list[str] = Field(default_factory=list)


class Dossier(Frozen):
    domain: str
    identity: str
    original: Original | None = None
    facts: list[Fact] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


class SavedReview(Frozen):
    generatedAt: datetime
    summary: list[str]
    drivers: list[Finding] = Field(default_factory=list)
    lessons: list[Finding] = Field(default_factory=list)
    evidenceSnapshot: Dossier


class Brief(Frozen):
    identity: str
    generatedAt: datetime
    summary: str
    finding: str
    nextCheck: str
    category: str
    stage: str
    pick: str | None
    shortlist: list[str]
    sources: list[Source]


class BriefIndex(Frozen):
    updatedAt: datetime
    records: list[Brief]


def read_briefs(domain: Literal['football', 'racing']) -> BriefIndex:
    """Read saved audits only; a history table must not trigger model calls."""
    latest = {}
    for path in (STATE / 'evidence-reviews' / domain).glob('*/*.json'):
        try:
            review = SavedReview.model_validate_json(path.read_text('utf-8'))
        except (OSError, ValidationError):
            continue
        dossier = review.evidenceSnapshot
        if dossier.domain != domain or not review.summary:
            continue
        previous = latest.get(dossier.identity)
        rank = (bool(dossier.original and dossier.original.stage == 'final'), review.generatedAt)
        if previous and previous[0] >= rank:
            continue
        driver = next((v for v in review.drivers if v.explanation and v.evidenceIds), None)
        lesson = next((v for v in review.lessons if v.nextCheck and v.evidenceIds), None)
        evidence = set((driver.evidenceIds if driver else []) + (lesson.evidenceIds if lesson else []))
        source_ids = {s for f in dossier.facts if f.id in evidence for s in f.sourceIds}
        original = dossier.original or Original()
        brief = Brief(identity=dossier.identity, generatedAt=review.generatedAt,
            summary=review.summary[0], finding=driver.explanation if driver else '',
            nextCheck=lesson.nextCheck if lesson else '', category=lesson.category if lesson else '',
            stage=original.stage, pick=original.pick, shortlist=original.shortlist,
            sources=[s for s in dossier.sources if s.id in source_ids and s.url.startswith(('https://', 'http://'))])
        latest[dossier.identity] = (rank, brief)
    return BriefIndex(updatedAt=datetime.now(timezone.utc), records=[v[1] for v in latest.values()])
