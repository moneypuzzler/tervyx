"""Utilities for exporting deterministic citation records."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

DOI_REGEX = re.compile(r"^10\.\S+$", re.IGNORECASE)


def _normalize_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_doi(doi: Optional[str]) -> Optional[str]:
    text = _normalize_string(doi)
    if not text:
        return None
    text = text.lower()
    if text.startswith("https://doi.org/"):
        text = text[len("https://doi.org/") :]
    elif text.startswith("http://doi.org/"):
        text = text[len("http://doi.org/") :]
    return text if DOI_REGEX.match(text) else text


def _doi_url(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    return f"https://doi.org/{doi}"


def _drop_none(data: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _format_citation_text(study: Dict[str, Any]) -> str:
    parts: List[str] = []

    study_id = study.get("study_id")
    year = study.get("year")
    if year:
        parts.append(f"{study_id} ({year})")
    else:
        parts.append(str(study_id))

    journal = study.get("journal")
    if journal:
        parts.append(f"Journal: {journal}")

    design = study.get("design")
    if design:
        parts.append(f"Design: {design}")

    population = study.get("population")
    if population:
        parts.append(f"Population: {population}")

    outcome = study.get("outcome")
    if outcome:
        parts.append(f"Outcome: {outcome}")

    doi = study.get("doi")
    if doi:
        parts.append(f"DOI: {doi}")

    pmid = study.get("pmid")
    if pmid:
        parts.append(f"PMID: {pmid}")

    adverse = study.get("adverse_events")
    if adverse:
        parts.append(f"Adverse Events: {adverse}")

    return "; ".join(parts) + "."


def build_citations_payload(
    evidence_rows: Iterable[Dict[str, Any]],
    *,
    policy_fingerprint: str,
    evidence_path: str,
    preferred_citation: str,
) -> Dict[str, Any]:
    """Create a deterministic citation manifest for an entry."""

    studies: List[Dict[str, Any]] = []
    references: List[Dict[str, Any]] = []

    for row in evidence_rows:
        study_id = _normalize_string(row.get("study_id"))
        if not study_id:
            raise ValueError("Evidence row missing study_id for citation export")

        year = row.get("year")
        try:
            year_int = int(year) if year is not None else None
        except (TypeError, ValueError):
            year_int = None

        doi = _normalize_doi(row.get("doi"))
        pmid = _normalize_string(row.get("pmid"))
        journal = _normalize_string(row.get("journal_id"))
        design = _normalize_string(row.get("design"))
        population = _normalize_string(row.get("population"))
        outcome = _normalize_string(row.get("outcome"))
        adverse_events = _normalize_string(row.get("adverse_events"))

        study_payload = {
            "study_id": study_id,
            "year": year_int,
            "design": design,
            "journal": journal,
            "outcome": outcome,
            "population": population,
            "adverse_events": adverse_events,
            "doi": doi,
            "pmid": pmid,
            "url": _doi_url(doi),
        }
        study_payload["citation"] = _format_citation_text(study_payload)
        studies.append(_drop_none(study_payload))

        if doi:
            references.append(
                {
                    "type": "doi",
                    "identifier": doi,
                    "study_id": study_id,
                    "url": _doi_url(doi),
                }
            )
        if pmid:
            references.append(
                {
                    "type": "pmid",
                    "identifier": pmid,
                    "study_id": study_id,
                }
            )

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "policy_fingerprint": policy_fingerprint,
        "source_evidence": evidence_path,
        "preferred_citation": preferred_citation,
        "studies": studies,
        "references": references,
    }

    return payload


def to_entry_references(citations_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Reduce citations payload to references embedded in entry.jsonld."""

    references: List[Dict[str, Any]] = []
    for study in citations_payload.get("studies", []):
        ref: Dict[str, Any] = {
            "study_id": study["study_id"],
            "citation": study["citation"],
        }
        doi = study.get("doi")
        url = study.get("url")
        if doi:
            ref["doi"] = doi
        if url:
            ref["url"] = url
        references.append(ref)
    return references

