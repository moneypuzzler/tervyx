"""
Journal Quality Assessment Database for the TERVYX system.

Provides lightweight, cache-aware journal assessments that feed the TEL-5 J-gate.
The implementation intentionally keeps a small curated knowledge base and uses
heuristics so the real-data pipeline remains functional without requiring large
external datasets during local development or CI runs.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


class JournalStatus(Enum):
    LEGITIMATE = "legitimate"
    PREDATORY = "predatory"
    QUESTIONABLE = "questionable"
    UNKNOWN = "unknown"


class PeerReviewType(Enum):
    SINGLE_BLIND = "single_blind"
    DOUBLE_BLIND = "double_blind"
    OPEN = "open"
    POST_PUBLICATION = "post_publication"
    UNKNOWN = "unknown"


@dataclass
class JournalMetrics:
    """Aggregated journal quality metrics."""

    issn: str
    eissn: Optional[str] = None
    title: str = ""
    publisher: str = ""

    impact_factor_2023: Optional[float] = None
    impact_factor_5year: Optional[float] = None
    citescore_2023: Optional[float] = None
    sjr_2023: Optional[float] = None
    h_index: Optional[int] = None

    predatory_status: JournalStatus = JournalStatus.UNKNOWN
    peer_review_type: PeerReviewType = PeerReviewType.UNKNOWN
    open_access: bool = False

    indexed_in_pubmed: bool = False
    indexed_in_scopus: bool = False
    indexed_in_wos: bool = False
    indexed_in_doaj: bool = False

    total_articles_published: Optional[int] = None
    total_retractions: Optional[int] = None
    retraction_rate: Optional[float] = None
    recent_retractions_2y: Optional[int] = None

    last_updated: Optional[str] = None
    data_sources: List[str] = field(default_factory=list)


@dataclass
class JournalAssessment:
    """Final journal quality assessment consumed by the pipeline."""

    issn: str
    title: str
    overall_score: float  # 0.0 – 1.0
    tervyx_category: str  # GOLD / SILVER / BRONZE / QUESTIONABLE / PREDATORY
    j_gate_score: float
    quality_factors: List[str]
    warning_flags: List[str]
    recommendation: str
    confidence: float
    metrics: JournalMetrics
    assessment_date: str


HIGH_TRUST_JOURNALS: Dict[str, Dict[str, float]] = {
    "1389-9457": {"impact_factor_2023": 3.7, "sjr_2023": 1.1, "h_index": 120},  # Sleep Medicine
    "0006-3223": {"impact_factor_2023": 12.0, "sjr_2023": 4.5, "h_index": 250},  # Biological Psychiatry
    "1365-2869": {"impact_factor_2023": 5.2, "sjr_2023": 1.6, "h_index": 160},  # Journal of Sleep Research
    "0022-3476": {"impact_factor_2023": 5.8, "sjr_2023": 1.7, "h_index": 200},  # Journal of Pediatrics
}

PREDATORY_CUES: Tuple[str, ...] = (
    "international journal of complementary",
    "novel science publishing",
    "world academy of",
    "global publishing corporation",
)

CATEGORY_THRESHOLDS = {
    "GOLD": 0.8,
    "SILVER": 0.65,
    "BRONZE": 0.5,
    "QUESTIONABLE": 0.35,
}


class JournalQualityDatabase:
    """Async interface for journal quality assessment with caching."""

    def __init__(self, cache_ttl_days: int = 14) -> None:
        self.cache: Dict[str, Tuple[JournalAssessment, datetime]] = {}
        self.cache_ttl = timedelta(days=cache_ttl_days)

    async def assess_journal(self, issn: str, title: Optional[str] = None) -> JournalAssessment:
        """Return a journal assessment, using cached values when available."""

        cache_key = issn.strip().lower()
        now = datetime.utcnow()
        cached = self.cache.get(cache_key)
        if cached and now - cached[1] < self.cache_ttl:
            return cached[0]

        metrics = await self._gather_metrics(issn, title or "")
        overall_score, factors, flags = self._compute_scores(metrics)
        category = self._categorize(overall_score, flags)

        assessment = JournalAssessment(
            issn=metrics.issn,
            title=metrics.title or title or "Unknown Journal",
            overall_score=overall_score,
            tervyx_category=category,
            j_gate_score=self._j_gate_score(overall_score, flags),
            quality_factors=factors,
            warning_flags=flags,
            recommendation=self._recommendation(category, flags),
            confidence=0.85 if metrics.last_updated else 0.6,
            metrics=metrics,
            assessment_date=now.isoformat(),
        )

        self.cache[cache_key] = (assessment, now)
        return assessment

    # ------------------------------------------------------------------
    # Metric collection and scoring helpers
    # ------------------------------------------------------------------
    async def _gather_metrics(self, issn: str, title: str) -> JournalMetrics:
        # Simulate potential network latency to keep async signature meaningful
        await asyncio.sleep(0)

        record = HIGH_TRUST_JOURNALS.get(issn)
        metrics = JournalMetrics(
            issn=issn,
            title=title or (record and title) or "",
            publisher="",
            impact_factor_2023=record.get("impact_factor_2023") if record else None,
            impact_factor_5year=record.get("impact_factor_2023") if record else None,
            citescore_2023=None,
            sjr_2023=record.get("sjr_2023") if record else None,
            h_index=record.get("h_index") if record else None,
            predatory_status=JournalStatus.LEGITIMATE if record else JournalStatus.UNKNOWN,
            peer_review_type=PeerReviewType.DOUBLE_BLIND if record else PeerReviewType.UNKNOWN,
            open_access=False,
            indexed_in_pubmed=bool(record),
            indexed_in_scopus=bool(record),
            indexed_in_wos=bool(record),
            indexed_in_doaj=False,
            total_articles_published=None,
            total_retractions=None,
            retraction_rate=None,
            recent_retractions_2y=None,
            last_updated=datetime.utcnow().isoformat() if record else None,
            data_sources=["curated_registry"] if record else ["heuristic"],
        )

        # Apply heuristic penalties for suspicious titles
        lower_title = title.lower()
        if any(cue in lower_title for cue in PREDATORY_CUES):
            metrics.predatory_status = JournalStatus.PREDATORY
            metrics.peer_review_type = PeerReviewType.UNKNOWN
            metrics.indexed_in_pubmed = False
            metrics.indexed_in_scopus = False
            metrics.indexed_in_wos = False
            metrics.sjr_2023 = None
            metrics.impact_factor_2023 = None

        return metrics

    def _compute_scores(self, metrics: JournalMetrics) -> Tuple[float, List[str], List[str]]:
        factors: List[str] = []
        flags: List[str] = []
        score = 0.5  # neutral baseline

        if metrics.predatory_status == JournalStatus.PREDATORY:
            flags.append("Listed in predatory heuristics")
            return 0.05, factors, flags

        if metrics.impact_factor_2023:
            factors.append(f"Impact Factor 2023: {metrics.impact_factor_2023}")
            score += min(metrics.impact_factor_2023 / 20.0, 0.25)

        if metrics.sjr_2023:
            factors.append(f"SJR 2023: {metrics.sjr_2023}")
            score += min(metrics.sjr_2023 / 4.0, 0.15)

        if metrics.h_index:
            factors.append(f"H-Index: {metrics.h_index}")
            score += min(metrics.h_index / 500.0, 0.1)

        if metrics.indexed_in_pubmed:
            factors.append("Indexed in PubMed")
            score += 0.1

        if metrics.indexed_in_scopus:
            factors.append("Indexed in Scopus")
            score += 0.05

        if metrics.indexed_in_wos:
            factors.append("Indexed in Web of Science")
            score += 0.05

        if metrics.open_access:
            factors.append("Open access policy verified")
            score += 0.02

        score = max(0.0, min(1.0, score))
        return score, factors, flags

    def _categorize(self, score: float, flags: List[str]) -> str:
        if flags:
            return "PREDATORY"
        for label, threshold in CATEGORY_THRESHOLDS.items():
            if score >= threshold:
                return label
        return "PREDATORY"

    def _j_gate_score(self, score: float, flags: List[str]) -> float:
        if flags:
            return 0.0
        if score >= 0.85:
            return 0.95
        if score >= 0.7:
            return 0.85
        if score >= 0.55:
            return 0.7
        if score >= 0.35:
            return 0.5
        return 0.1

    def _recommendation(self, category: str, flags: List[str]) -> str:
        if flags:
            return "Reject journal – predatory signals detected"
        if category == "GOLD":
            return "High-trust journal; use without restriction"
        if category == "SILVER":
            return "Trustworthy; verify study design quality"
        if category == "BRONZE":
            return "Accept with caution; verify methodology"
        if category == "QUESTIONABLE":
            return "Manual review required before inclusion"
        return "Do not use for evidence synthesis"


__all__ = [
    "JournalQualityDatabase",
    "JournalAssessment",
    "JournalMetrics",
    "JournalStatus",
    "PeerReviewType",
]
