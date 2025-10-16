"""
Real-data meta-analysis orchestration for the TERVYX pipeline.

This module converts AI-extracted study summaries into the evidence schema used
by the core TEL-5 engine, executes REML + Monte Carlo meta-analysis, evaluates
Gate Governance Protocol criteria, and assembles a TEL-5 compliant entry
payload. The implementation is intentionally lightweight so it can run inside
continuous-integration environments while still reflecting the production data
flow (PubMed → Gemini → Journal Quality → Meta-analysis → TEL-5).
"""

from __future__ import annotations

import math
import pathlib
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import yaml

from engine.mc_meta import run_reml_mc_analysis
from engine.tel5_rules import apply_l_gate_penalty, tel5_classify
from engine.gates import evaluate_all_gates

from .ai_abstract_analyzer import AbstractAnalysis, ExtractedData
from .journal_quality_db import JournalAssessment

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy.yaml"


class StudyQuality(Enum):
    """Discrete quality buckets used for coarse filtering."""

    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


@dataclass
class StandardizedStudy:
    """Normalized study representation suitable for meta-analysis."""

    study_id: str
    effect_size: float
    standard_error: float
    variance: float
    n_treatment: int
    n_control: int
    total_n: int
    risk_of_bias: StudyQuality
    journal_quality: float
    confidence: float
    duration_weeks: Optional[int]
    population: Optional[str]
    intervention: Optional[str]
    outcome: Optional[str]
    doi: Optional[str]
    journal_id: Optional[str]

    def to_evidence_row(self) -> Dict[str, Any]:
        """Translate into the evidence schema expected by TEL-5 engine."""

        ci_low = self.effect_size - 1.96 * self.standard_error
        ci_high = self.effect_size + 1.96 * self.standard_error

        return {
            "study_id": self.study_id,
            "effect_point": self.effect_size,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "effect_type": "SMD",
            "n_treat": self.n_treatment,
            "n_ctrl": self.n_control,
            "risk_of_bias": self.risk_of_bias.value,
            "doi": self.doi,
            "journal_id": self.journal_id or "unknown",
            "design": "RCT",
            "year": None,
        }


class RealMetaAnalyzer:
    """Bridge AI-extracted study data with TEL-5 engine."""

    def __init__(self, min_studies: int = 2) -> None:
        self.min_studies = min_studies

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def perform_full_analysis(
        self,
        analyses: Iterable[AbstractAnalysis],
        journal_assessments: Dict[str, JournalAssessment],
        substance: str,
        outcome_category: str,
    ) -> Dict[str, Any]:
        studies = self._convert_to_standardized_studies(analyses, journal_assessments)
        if len(studies) < self.min_studies:
            return {
                "error": f"Insufficient studies after extraction ({len(studies)} found)",
                "studies": len(studies),
            }

        studies = self._filter_by_quality(studies)
        if len(studies) < self.min_studies:
            return {
                "error": f"Insufficient studies after quality filtering ({len(studies)})",
                "studies": len(studies),
            }

        policy = load_policy()
        category_cfg = policy["categories"].get(outcome_category)
        if category_cfg is None:
            return {"error": f"Unknown outcome category '{outcome_category}' in policy"}

        studies = self._harmonize_effect_direction(studies, category_cfg.get("benefit_direction", 1))
        evidence_rows = [study.to_evidence_row() for study in studies]

        simulation = run_reml_mc_analysis(
            evidence_rows=evidence_rows,
            delta=category_cfg["delta"],
            benefit_direction=category_cfg.get("benefit_direction", 1),
            seed=policy["monte_carlo"]["seed"],
            n_draws=policy["monte_carlo"]["n_draws"],
            tau2_method=policy["monte_carlo"].get("tau2_method", "REML"),
        )

        gate_results = self._evaluate_gates(evidence_rows, policy, substance, outcome_category)
        phi_fail = gate_results["phi"]["violation"]
        k_fail = gate_results["k"]["violation"]
        P_effect = simulation.get("P_effect_gt_delta", 0.0)
        label, tier = tel5_classify(P_effect, phi_fail, k_fail)
        label, tier = apply_l_gate_penalty(label, tier, gate_results["l"]["violation"])

        return {
            "simulation": simulation,
            "studies": studies,
            "evidence_rows": evidence_rows,
            "gate_results": gate_results,
            "tier": tier,
            "label": label,
            "policy": policy,
        }

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------
    def _convert_to_standardized_studies(
        self,
        analyses: Iterable[AbstractAnalysis],
        journal_assessments: Dict[str, JournalAssessment],
    ) -> List[StandardizedStudy]:
        studies: List[StandardizedStudy] = []

        for analysis in analyses:
            data = analysis.extracted_data
            if not self._has_sufficient_data(data):
                continue

            se, variance = self._estimate_uncertainty(data)
            if se is None or variance is None:
                continue

            risk = self._map_risk_of_bias(analysis.gate_evaluation.risk_of_bias)
            journal_assessment = journal_assessments.get(analysis.paper_pmid)
            j_score = journal_assessment.j_gate_score if journal_assessment else 0.5

            studies.append(
                StandardizedStudy(
                    study_id=analysis.paper_pmid,
                    effect_size=float(data.effect_size),
                    standard_error=se,
                    variance=variance,
                    n_treatment=int(data.sample_size_treatment),
                    n_control=int(data.sample_size_control),
                    total_n=int(data.sample_size_treatment + data.sample_size_control),
                    risk_of_bias=risk,
                    journal_quality=j_score,
                    confidence=analysis.analysis_confidence,
                    duration_weeks=data.study_duration_weeks,
                    population=data.population,
                    intervention=data.intervention_details,
                    outcome=data.outcome_measure,
                    doi=getattr(analysis, "doi", None),
                    journal_id=journal_assessment.issn if journal_assessment else None,
                )
            )

        return studies

    def _has_sufficient_data(self, data: ExtractedData) -> bool:
        return (
            data.effect_size is not None
            and data.sample_size_treatment is not None
            and data.sample_size_control is not None
            and data.sample_size_treatment > 0
            and data.sample_size_control > 0
        )

    def _estimate_uncertainty(self, data: ExtractedData) -> Tuple[Optional[float], Optional[float]]:
        if data.confidence_interval_lower is not None and data.confidence_interval_upper is not None:
            half_width = (data.confidence_interval_upper - data.confidence_interval_lower) / 2.0
            se = half_width / 1.96
        else:
            # Fallback: approximate using standard formula for SMD
            n_t = float(data.sample_size_treatment)
            n_c = float(data.sample_size_control)
            n_total = n_t + n_c
            if n_t <= 0 or n_c <= 0:
                return None, None
            se = math.sqrt((n_total / (n_t * n_c)) + (data.effect_size**2 / (2.0 * n_total)))

        variance = se**2
        return se, variance

    def _map_risk_of_bias(self, risk: str) -> StudyQuality:
        mapping = {
            "low": StudyQuality.HIGH,
            "some": StudyQuality.MODERATE,
            "moderate": StudyQuality.MODERATE,
            "high": StudyQuality.LOW,
        }
        return mapping.get(risk.lower(), StudyQuality.MODERATE)

    # ------------------------------------------------------------------
    # Quality filtering
    # ------------------------------------------------------------------
    def _filter_by_quality(self, studies: List[StandardizedStudy]) -> List[StandardizedStudy]:
        filtered: List[StandardizedStudy] = []
        for study in studies:
            if study.total_n < 20:
                continue
            if abs(study.effect_size) > 5:
                continue
            if study.confidence < 0.4:
                continue
            filtered.append(study)
        return filtered

    # ------------------------------------------------------------------
    # Harmonisation
    # ------------------------------------------------------------------
    def _harmonize_effect_direction(
        self, studies: List[StandardizedStudy], benefit_direction: int
    ) -> List[StandardizedStudy]:
        adjusted: List[StandardizedStudy] = []
        for study in studies:
            effect = study.effect_size * benefit_direction
            adjusted.append(
                StandardizedStudy(
                    study_id=study.study_id,
                    effect_size=effect,
                    standard_error=study.standard_error,
                    variance=study.variance,
                    n_treatment=study.n_treatment,
                    n_control=study.n_control,
                    total_n=study.total_n,
                    risk_of_bias=study.risk_of_bias,
                    journal_quality=study.journal_quality,
                    confidence=study.confidence,
                    duration_weeks=study.duration_weeks,
                    population=study.population,
                    intervention=study.intervention,
                    outcome=study.outcome,
                    doi=study.doi,
                    journal_id=study.journal_id,
                )
            )
        return adjusted

    # ------------------------------------------------------------------
    # Gate evaluation
    # ------------------------------------------------------------------
    def _evaluate_gates(
        self,
        evidence_rows: List[Dict[str, Any]],
        policy: Dict[str, Any],
        substance: str,
        outcome_category: str,
    ) -> Dict[str, Any]:
        snapshot_path = ROOT / policy["gates"]["j"]["use_snapshot"]
        snapshot = {}
        if snapshot_path.exists():
            snapshot = json_load(snapshot_path)
        text_hint = f"{substance} {outcome_category}"
        return evaluate_all_gates(evidence_rows, outcome_category, snapshot, policy, text_hint)


# ----------------------------------------------------------------------
# Public helper for pipeline
# ----------------------------------------------------------------------

def load_policy() -> Dict[str, Any]:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def json_load(path: pathlib.Path) -> Dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def compute_policy_fingerprint(policy: Dict[str, Any], snapshot: Dict[str, Any]) -> str:
    import hashlib
    import json

    minimal = {
        "version": policy.get("version"),
        "protocol": policy.get("protocol"),
        "tel5_tiers": policy.get("tel5_tiers"),
        "categories": policy.get("categories"),
        "monte_carlo": policy.get("monte_carlo"),
    }

    policy_hash = hashlib.sha256(json.dumps(minimal, sort_keys=True).encode("utf-8")).hexdigest()
    snapshot_hash = hashlib.sha256(json.dumps(snapshot.get("journals", {}), sort_keys=True).encode("utf-8")).hexdigest()
    combined = hashlib.sha256(f"{policy_hash}{snapshot_hash}".encode("utf-8")).hexdigest()
    return f"sha256:{combined}"


async def generate_real_tervyx_entry(
    substance: str,
    outcome_category: str,
    analyses: Iterable[AbstractAnalysis],
    journal_assessments: Dict[str, JournalAssessment],
) -> Dict[str, Any]:
    analyzer = RealMetaAnalyzer()
    analysis_result = analyzer.perform_full_analysis(analyses, journal_assessments, substance, outcome_category)

    if "error" in analysis_result:
        return analysis_result

    policy: Dict[str, Any] = analysis_result["policy"]
    snapshot_path = ROOT / policy["gates"]["j"]["use_snapshot"]
    snapshot = json_load(snapshot_path) if snapshot_path.exists() else {}
    fingerprint = compute_policy_fingerprint(policy, snapshot)

    studies: List[StandardizedStudy] = analysis_result["studies"]
    simulation: Dict[str, Any] = analysis_result["simulation"]
    gate_results = analysis_result["gate_results"]
    label = analysis_result["label"]
    tier = analysis_result["tier"]

    simulation["policy_fingerprint"] = fingerprint

    evidence_summary = {
        "n_studies": len(studies),
        "total_n": int(sum(study.total_n for study in studies)),
        "I2": simulation.get("I2"),
        "tau2": simulation.get("tau2"),
        "mu_hat": simulation.get("mu_hat"),
        "mu_CI95": simulation.get("mu_CI95"),
    }

    snapshot_hint = policy["gates"]["j"].get("use_snapshot", "")
    snapshot_date = snapshot.get("snapshot_date")
    if not snapshot_date and "@" in snapshot_hint:
        snapshot_date = snapshot_hint.split("@")[-1].split(".")[0]

    return {
        "@context": "https://schema.org/",
        "@type": "Dataset",
        "id": f"{substance}:{outcome_category}:v1",
        "title": f"{substance.title()} — {outcome_category.replace('_', ' ').title()}",
        "tier_label_system": "TEL-5",
        "tier": tier,
        "label": label,
        "P_effect_gt_delta": simulation.get("P_effect_gt_delta", 0.0),
        "gate_results": gate_results,
        "evidence_summary": evidence_summary,
        "policy_refs": {
            "tel5_levels": policy.get("metadata", {}).get("tel5_version", "unknown"),
            "monte_carlo": policy.get("monte_carlo", {}).get("version", "unknown"),
            "journal_trust": snapshot_date or "unknown",
        },
        "policy_fingerprint": fingerprint,
        "created": datetime.utcnow().isoformat() + "Z",
        "real_studies": [asdict(study) for study in studies],
        "meta_analysis": simulation,
    }
