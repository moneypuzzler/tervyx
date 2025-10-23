"""Utilities for exporting deterministic citation records."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

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


def _pmid_url(pmid: Optional[str]) -> Optional[str]:
    if not pmid:
        return None
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


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


def _dedupe_references(refs: Dict[Tuple[str, str], Dict[str, Any]],
                       ref_type: str,
                       identifier: str,
                       study_id: str,
                       url: Optional[str]) -> None:
    key = (ref_type, identifier)
    if key not in refs:
        refs[key] = {
            "type": ref_type,
            "identifier": identifier,
            "study_ids": {study_id},
        }
        if url:
            refs[key]["url"] = url
        return

    refs[key]["study_ids"].add(study_id)
    if url and not refs[key].get("url"):
        refs[key]["url"] = url


def _sort_studies(studies: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [studies[key] for key in sorted(studies.keys(), key=lambda value: value.lower())]


def _sort_references(refs: Dict[Tuple[str, str], Dict[str, Any]]) -> List[Dict[str, Any]]:
    sorted_refs: List[Dict[str, Any]] = []
    for ref_type, identifier in sorted(refs.keys(), key=lambda item: (item[0], item[1])):
        entry = refs[(ref_type, identifier)]
        study_ids = sorted(entry.pop("study_ids"))
        payload = {
            "type": ref_type,
            "identifier": identifier,
            "study_ids": study_ids,
            "primary_study_id": study_ids[0],
        }
        if "url" in entry:
            payload["url"] = entry["url"]
        sorted_refs.append(payload)
    return sorted_refs


def _canonical_bytes(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_manifest_hash(citations_payload: Dict[str, Any]) -> str:
    """Compute the deterministic manifest hash for a citations payload."""

    payload = dict(citations_payload)
    payload.pop("manifest_hash", None)
    digest = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return f"sha256:{digest}"


def build_citations_payload(
    evidence_rows: Iterable[Dict[str, Any]],
    *,
    policy_fingerprint: str,
    evidence_path: str,
    preferred_citation: str,
) -> Dict[str, Any]:
    """Create a deterministic citation manifest for an entry."""

    studies: Dict[str, Dict[str, Any]] = {}
    references: Dict[Tuple[str, str], Dict[str, Any]] = {}

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
            "url": _doi_url(doi) or _pmid_url(pmid),
        }
        study_payload["citation"] = _format_citation_text(study_payload)
        normalized = _drop_none(study_payload)

        existing = studies.get(study_id)
        if existing and existing != normalized:
            raise ValueError(f"Duplicate study_id '{study_id}' with conflicting citation metadata")
        studies[study_id] = normalized

        if doi:
            _dedupe_references(references, "doi", doi, study_id, _doi_url(doi))
        if pmid:
            _dedupe_references(references, "pmid", pmid, study_id, _pmid_url(pmid))

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "policy_fingerprint": policy_fingerprint,
        "source_evidence": evidence_path,
        "preferred_citation": preferred_citation,
        "studies": _sort_studies(studies),
        "references": _sort_references(references),
    }

    payload["manifest_hash"] = compute_manifest_hash(payload)
    return payload


def _reference_identifier(ref_type: str, identifier: str) -> str:
    if ref_type == "doi":
        return f"doi:{identifier}"
    return f"pmid:{identifier}"


def _reference_same_as(ref_type: str, identifier: str) -> Optional[str]:
    if ref_type == "doi":
        return _doi_url(identifier)
    if ref_type == "pmid":
        return _pmid_url(identifier)
    return None


def _first_available_study(study_ids: Sequence[str], study_lookup: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for study_id in study_ids:
        if study_id in study_lookup:
            return study_lookup[study_id]
    return None


def to_entry_references(citations_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Reduce citations payload to JSON-LD references embedded in entry.jsonld."""

    study_lookup = {study["study_id"]: study for study in citations_payload.get("studies", [])}
    references_ld: List[Dict[str, Any]] = []

    for reference in citations_payload.get("references", []):
        ref_type = reference.get("type")
        identifier = reference.get("identifier")
        if not ref_type or not identifier:
            continue

        study_ids = reference.get("study_ids") or []
        if not study_ids:
            primary = reference.get("primary_study_id")
            if primary:
                study_ids = [primary]

        study_ids = sorted(dict.fromkeys(study_ids))
        study = _first_available_study(study_ids, study_lookup)

        entry_ref: Dict[str, Any] = {
            "@id": _reference_identifier(ref_type, identifier),
            "@type": "ScholarlyArticle",
            "identifier": _reference_identifier(ref_type, identifier),
            "studyIds": study_ids,
        }

        if study and "citation" in study:
            entry_ref["citation"] = study["citation"]
        else:
            entry_ref["citation"] = ", ".join(study_ids)

        if ref_type == "doi":
            entry_ref["doi"] = identifier
        elif ref_type == "pmid":
            entry_ref["pmid"] = identifier

        same_as = _reference_same_as(ref_type, identifier)
        if same_as:
            entry_ref["sameAs"] = same_as

        if study:
            if study.get("year") is not None:
                entry_ref["datePublished"] = str(study["year"])
            if study.get("journal"):
                entry_ref["isPartOf"] = {
                    "@type": "Periodical",
                    "name": study["journal"],
                }

        references_ld.append(entry_ref)

    references_ld.sort(key=lambda item: item["@id"])
    return references_ld

