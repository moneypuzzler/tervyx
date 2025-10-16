"""
AI-Powered Abstract Analysis for TERVYX Gate Evaluation
======================================================

Uses the Gemini API to analyse paper abstracts and extract structured evidence:
1. Gate evaluation scores (Φ, R, J, K, L)
2. Quantitative study data (effect sizes, sample sizes, CIs)
3. Study quality indicators and risk of bias
4. Inclusion recommendations with confidence scores

Designed for production use with retry logic, cost tracking and batch processing.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

from .pubmed_integration import PubMedPaper


class GateScore(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    AMBER = "AMBER"
    LOW = "LOW"
    HIGH = "HIGH"


@dataclass
class ExtractedData:
    """Quantitative data extracted from a study abstract."""

    sample_size_treatment: Optional[int] = None
    sample_size_control: Optional[int] = None
    effect_size: Optional[float] = None
    effect_type: Optional[str] = None  # SMD, MD, OR, RR, etc.
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    p_value: Optional[float] = None
    study_duration_weeks: Optional[int] = None
    population: Optional[str] = None
    intervention_details: Optional[str] = None
    control_type: Optional[str] = None
    outcome_measure: Optional[str] = None
    statistical_significance: Optional[bool] = None


@dataclass
class GateEvaluation:
    """Structured TEL-5 gate evaluation."""

    phi_gate: GateScore
    phi_reasoning: str
    r_gate: GateScore
    r_reasoning: str
    j_score: float  # 0.0 to 1.0
    j_reasoning: str
    k_gate: GateScore
    k_reasoning: str
    l_gate: GateScore
    l_reasoning: str
    overall_quality_score: float
    risk_of_bias: str  # low, some, high


@dataclass
class AbstractAnalysis:
    """Complete analysis result for a paper abstract."""

    paper_pmid: str
    extracted_data: ExtractedData
    gate_evaluation: GateEvaluation
    relevance_score: float
    inclusion_recommendation: bool
    analysis_confidence: float
    ai_reasoning: str
    processing_time: float


class GeminiAbstractAnalyzer:
    """Tiered Gemini-based abstract analyser used by the TERVYX pipeline."""

    def __init__(
        self,
        api_key: str,
        screening_model: str = "gemini-2.5-flash-lite",
        analysis_model: str = "gemini-2.5-flash",
        fallback_model: str = "gemini-2.5-pro",
    ) -> None:
        self.api_key = api_key
        self.screening_model = screening_model
        self.analysis_model = analysis_model
        self.fallback_model = fallback_model

        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.rate_limit_delay = 1.0
        self.max_retries = 3
        self.retry_delay = 2.0

        # Token accounting per tier (used by cost-optimised subclass)
        self.token_usage: Dict[str, Dict[str, float]] = {
            "screening": {"input": 0.0, "output": 0.0},
            "analysis": {"input": 0.0, "output": 0.0},
            "fallback": {"input": 0.0, "output": 0.0},
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def analyze_batch(
        self,
        papers: List[PubMedPaper],
        substance: str,
        outcome_category: str,
        use_tiered_approach: bool = True,
    ) -> List[AbstractAnalysis]:
        """Analyse a batch of papers using the tiered model strategy."""

        results: List[AbstractAnalysis] = []
        cost_savings = 0.0

        print(
            f"🤖 Starting {'tiered ' if use_tiered_approach else ''}AI analysis of {len(papers)} abstracts..."
        )

        if use_tiered_approach and papers:
            print(f"🔍 Phase 1: Relevance screening with {self.screening_model}...")
            relevant_papers = await self._screen_relevance(papers, substance, outcome_category)
            screened_out = len(papers) - len(relevant_papers)

            if screened_out > 0:
                # Rough savings estimate (same heuristic used in cost-optimised subclass)
                cost_savings = screened_out * 0.15
                print(
                    f"  💰 Filtered out {screened_out} irrelevant papers, saving ~${cost_savings:.2f}"
                )

            papers_to_analyze = relevant_papers
        else:
            papers_to_analyze = papers

        print(f"🔬 Phase 2: Detailed analysis of {len(papers_to_analyze)} papers...")

        for index, paper in enumerate(papers_to_analyze, start=1):
            print(f"  📄 Analyzing paper {index}/{len(papers_to_analyze)}: {paper.title[:60]}...")
            started = time.time()

            try:
                analysis = await self._analyze_single_abstract(paper, substance, outcome_category)
            except Exception as exc:  # pragma: no cover - defensive logging path
                print(f"    💥 Error: {exc}")
                await asyncio.sleep(self.rate_limit_delay)
                continue

            if analysis:
                analysis.processing_time = time.time() - started
                results.append(analysis)
                print(f"    ✅ Complete (relevance: {analysis.relevance_score:.2f})")
            else:
                print("    ❌ Failed to analyse")

            await asyncio.sleep(self.rate_limit_delay)

        print(f"🎯 Analysis complete: {len(results)}/{len(papers)} papers successfully analysed")
        if cost_savings > 0:
            print(f"💰 Estimated cost savings: ${cost_savings:.2f}")

        self._print_cost_summary()
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _screen_relevance(
        self,
        papers: List[PubMedPaper],
        substance: str,
        outcome_category: str,
    ) -> List[PubMedPaper]:
        """Perform a quick relevance screening using the cheapest tier."""

        relevant: List[PubMedPaper] = []

        for index, paper in enumerate(papers, start=1):
            print(f"  📋 Screening {index}/{len(papers)}: {paper.title[:50]}...")

            try:
                score = await self._quick_relevance_check(paper, substance, outcome_category)
            except Exception as exc:  # pragma: no cover - defensive logging path
                print(f"    ⚠️ Screening error: {exc}")
                # Default to keeping the paper if screening fails
                relevant.append(paper)
            else:
                if score >= 0.5:
                    relevant.append(paper)
                    print(f"    ✅ Relevant ({score:.2f})")
                else:
                    print(f"    ❌ Filtered ({score:.2f})")

            await asyncio.sleep(self.rate_limit_delay)

        return relevant

    async def _analyze_single_abstract(
        self,
        paper: PubMedPaper,
        substance: str,
        outcome_category: str,
    ) -> Optional[AbstractAnalysis]:
        """Analyse a single paper with retry logic."""

        for attempt in range(self.max_retries):
            try:
                result = await self._call_gemini_api(paper, substance, outcome_category)
            except Exception as exc:  # pragma: no cover - defensive logging path
                print(f"    ⚠️ Attempt {attempt + 1} failed: {exc}")
            else:
                if result is not None:
                    return result

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        return None

    async def _call_gemini_api(
        self,
        paper: PubMedPaper,
        substance: str,
        outcome_category: str,
    ) -> Optional[AbstractAnalysis]:
        """Call the Gemini API using the analysis tier."""

        prompt = self._build_analysis_prompt(paper, substance, outcome_category)
        url = f"{self.base_url}/models/{self.analysis_model}:generateContent?key={self.api_key}"

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("candidates"):
                        text_response = (
                            data["candidates"][0]["content"]["parts"][0]["text"]
                        )
                        return self._parse_gemini_response(text_response, paper.pmid)

                elif response.status == 429:
                    print("    ⏳ Rate limited, waiting...")
                    await asyncio.sleep(5.0)
                    raise RuntimeError("Rate limited")

                else:
                    error_text = await response.text()
                    raise RuntimeError(f"API error {response.status}: {error_text}")

        return None

    async def _quick_relevance_check(
        self,
        paper: PubMedPaper,
        substance: str,
        outcome_category: str,
    ) -> float:
        """Use the screening tier to get a quick relevance score (0.0-1.0)."""

        prompt = (
            f"Rate relevance to '{substance}' for '{outcome_category}' outcomes.\n\n"
            f"Title: {paper.title}\n"
            f"Abstract: {paper.abstract[:500]}...\n\n"
            "Respond with only a decimal from 0.0 to 1.0."
        )

        url = f"{self.base_url}/models/{self.screening_model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 20},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("candidates"):
                        raw = data["candidates"][0]["content"]["parts"][0]["text"]
                        match = re.search(r"(\d+\.\d+|\d+)", raw.strip())
                        if match:
                            return max(0.0, min(1.0, float(match.group(1))))

                elif response.status == 429:
                    await asyncio.sleep(3.0)

        return 0.7  # Conservative default if screening fails

    def _build_analysis_prompt(
        self,
        paper: PubMedPaper,
        substance: str,
        outcome_category: str,
    ) -> str:
        """Create the comprehensive Gemini prompt for detailed analysis."""

        publication_types = ", ".join(paper.publication_types)
        doi = paper.doi or "Not available"

        return (
            "You are an expert systematic reviewer analysing a scientific paper for "
            "the TERVYX Protocol evidence evaluation system.\n\n"
            "**PAPER TO ANALYSE:**\n"
            f"Title: {paper.title}\n"
            f"Journal: {paper.journal} ({paper.publication_year})\n"
            f"PMID: {paper.pmid}\n"
            f"DOI: {doi}\n"
            f"Publication Types: {publication_types}\n"
            f"Abstract: {paper.abstract}\n\n"
            "**RESEARCH QUESTION:**\n"
            f"Substance: {substance}\n"
            f"Outcome Category: {outcome_category}\n\n"
            "**REQUIRED ANALYSIS:**\n"
            "Provide a JSON object with the following keys:\n"
            "- relevance_score (0.0-1.0)\n"
            "- inclusion_recommendation (true/false)\n"
            "- analysis_confidence (0.0-1.0)\n"
            "- extracted_data { sample sizes, effect size, effect type, confidence interval, p-value, duration, population, intervention, control, outcome, statistical_significance }\n"
            "- gate_evaluation { phi_gate, phi_reasoning, r_gate, r_reasoning, j_score, j_reasoning, k_gate, k_reasoning, l_gate, l_reasoning, overall_quality_score, risk_of_bias }\n"
            "- ai_reasoning (string explanation)\n\n"
            "Return strictly valid JSON with double quotes and no markdown or commentary."
        )

    def _parse_gemini_response(self, response_text: str, pmid: str) -> Optional[AbstractAnalysis]:
        """Convert Gemini JSON output into the AbstractAnalysis dataclass."""

        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive logging path
            print(f"    ⚠️ Failed to parse AI response: {exc}")
            print(f"    Raw response: {response_text[:200]}...")
            return None

        extracted = ExtractedData(**data.get("extracted_data", {}))
        gate_data = data.get("gate_evaluation", {})

        gate_eval = GateEvaluation(
            phi_gate=GateScore(gate_data.get("phi_gate", "AMBER")),
            phi_reasoning=gate_data.get("phi_reasoning", ""),
            r_gate=GateScore(gate_data.get("r_gate", "AMBER")),
            r_reasoning=gate_data.get("r_reasoning", ""),
            j_score=float(gate_data.get("j_score", 0.5)),
            j_reasoning=gate_data.get("j_reasoning", ""),
            k_gate=GateScore(gate_data.get("k_gate", "AMBER")),
            k_reasoning=gate_data.get("k_reasoning", ""),
            l_gate=GateScore(gate_data.get("l_gate", "AMBER")),
            l_reasoning=gate_data.get("l_reasoning", ""),
            overall_quality_score=float(gate_data.get("overall_quality_score", 0.5)),
            risk_of_bias=gate_data.get("risk_of_bias", "some"),
        )

        return AbstractAnalysis(
            paper_pmid=pmid,
            extracted_data=extracted,
            gate_evaluation=gate_eval,
            relevance_score=float(data.get("relevance_score", 0.5)),
            inclusion_recommendation=bool(data.get("inclusion_recommendation", False)),
            analysis_confidence=float(data.get("analysis_confidence", 0.5)),
            ai_reasoning=data.get("ai_reasoning", ""),
            processing_time=0.0,
        )

    def _print_cost_summary(self) -> None:
        """Print cumulative token usage (used for diagnostic output)."""

        screening = self.token_usage.get("screening", {"input": 0.0, "output": 0.0})
        analysis = self.token_usage.get("analysis", {"input": 0.0, "output": 0.0})
        fallback = self.token_usage.get("fallback", {"input": 0.0, "output": 0.0})

        print("\n==============================")
        print("📊 TOKEN USAGE SUMMARY")
        print("==============================")
        print(
            f"Screening tokens: in={screening['input']:.0f}, out={screening['output']:.0f}"
        )
        print(f"Analysis tokens:  in={analysis['input']:.0f}, out={analysis['output']:.0f}")
        print(f"Fallback tokens:  in={fallback['input']:.0f}, out={fallback['output']:.0f}")
        print("==============================\n")


class AnalysisAggregator:
    """Aggregate multiple paper analyses into consensus results."""

    def aggregate_analyses(
        self,
        analyses: List[AbstractAnalysis],
        min_relevance: float = 0.5,
        min_confidence: float = 0.6,
    ) -> Dict[str, Any]:
        """Aggregate per-paper analyses into a consensus view."""

        high_quality = [
            analysis
            for analysis in analyses
            if (
                analysis.relevance_score >= min_relevance
                and analysis.analysis_confidence >= min_confidence
                and analysis.inclusion_recommendation
            )
        ]

        if len(high_quality) < 2:
            return {
                "error": "Insufficient high-quality analyses for aggregation",
                "total_papers": len(analyses),
                "quality_papers": len(high_quality),
            }

        print(f"📊 Aggregating {len(high_quality)} high-quality analyses...")

        gate_scores = self._aggregate_gate_scores(high_quality)
        meta_data = self._extract_meta_analysis_data(high_quality)
        quality_metrics = self._calculate_quality_metrics(high_quality)

        return {
            "n_papers_analyzed": len(analyses),
            "n_papers_included": len(high_quality),
            "inclusion_rate": len(high_quality) / len(analyses),
            "gate_scores": gate_scores,
            "meta_analysis_data": meta_data,
            "quality_metrics": quality_metrics,
        }

    def _aggregate_gate_scores(self, analyses: List[AbstractAnalysis]) -> Dict[str, Any]:
        phi_passes = sum(1 for a in analyses if a.gate_evaluation.phi_gate == GateScore.PASS)
        r_passes = sum(1 for a in analyses if a.gate_evaluation.r_gate == GateScore.PASS)
        k_passes = sum(1 for a in analyses if a.gate_evaluation.k_gate == GateScore.PASS)
        l_passes = sum(1 for a in analyses if a.gate_evaluation.l_gate == GateScore.PASS)

        phi_fails = sum(1 for a in analyses if a.gate_evaluation.phi_gate == GateScore.FAIL)
        k_fails = sum(1 for a in analyses if a.gate_evaluation.k_gate == GateScore.FAIL)

        j_scores = [a.gate_evaluation.j_score for a in analyses]
        avg_j = sum(j_scores) / len(j_scores) if j_scores else 0.5

        return {
            "phi_gate": GateScore.FAIL.value if phi_fails > 0 else GateScore.PASS.value,
            "r_gate": GateScore.PASS.value if r_passes / len(analyses) > 0.6 else GateScore.FAIL.value,
            "j_score": avg_j,
            "k_gate": GateScore.FAIL.value if k_fails > 0 else GateScore.PASS.value,
            "l_gate": GateScore.PASS.value if l_passes / len(analyses) > 0.8 else GateScore.FAIL.value,
            "gate_details": {
                "phi_pass_rate": phi_passes / len(analyses),
                "r_pass_rate": r_passes / len(analyses),
                "j_score_range": [min(j_scores), max(j_scores)] if j_scores else [0.0, 0.0],
                "k_pass_rate": k_passes / len(analyses),
                "l_pass_rate": l_passes / len(analyses),
            },
        }

    def _extract_meta_analysis_data(
        self, analyses: List[AbstractAnalysis]
    ) -> List[Dict[str, Any]]:
        studies: List[Dict[str, Any]] = []

        for analysis in analyses:
            data = analysis.extracted_data
            if (
                data.sample_size_treatment
                and data.sample_size_control
                and data.effect_size is not None
            ):
                studies.append(
                    {
                        "pmid": analysis.paper_pmid,
                        "effect_size": data.effect_size,
                        "effect_type": data.effect_type or "SMD",
                        "n_treatment": data.sample_size_treatment,
                        "n_control": data.sample_size_control,
                        "ci_lower": data.confidence_interval_lower,
                        "ci_upper": data.confidence_interval_upper,
                        "p_value": data.p_value,
                        "duration_weeks": data.study_duration_weeks,
                        "population": data.population,
                        "risk_of_bias": analysis.gate_evaluation.risk_of_bias,
                        "quality_score": analysis.gate_evaluation.overall_quality_score,
                    }
                )

        return studies

    def _calculate_quality_metrics(self, analyses: List[AbstractAnalysis]) -> Dict[str, float]:
        confidences = [a.analysis_confidence for a in analyses]
        relevances = [a.relevance_score for a in analyses]
        qualities = [a.gate_evaluation.overall_quality_score for a in analyses]

        return {
            "mean_confidence": sum(confidences) / len(confidences),
            "mean_relevance": sum(relevances) / len(relevances),
            "mean_quality_score": sum(qualities) / len(qualities),
            "high_quality_rate": len([q for q in qualities if q >= 0.7]) / len(qualities),
        }


# ============================================================================
# Testing helpers
# ============================================================================

async def test_ai_analyzer() -> None:
    """Minimal integration test for manual verification."""

    api_key = os.getenv("GEMINI_API_KEY", "your-api-key-here")
    if api_key == "your-api-key-here":
        print("⚠️ Set GEMINI_API_KEY environment variable to run this test.")
        return

    analyzer = GeminiAbstractAnalyzer(api_key)
    aggregator = AnalysisAggregator()

    sample_papers = [
        PubMedPaper(
            pmid="12345678",
            title="Melatonin supplementation improves sleep quality in adults with insomnia",
            abstract=(
                "Background: Insomnia affects 30% of adults. Objective: Evaluate melatonin supplementation. "
                "Methods: Randomised double-blind placebo-controlled trial. 120 adults received 3 mg melatonin or "
                "placebo for 4 weeks. Primary outcome: Pittsburgh Sleep Quality Index. Results: Significant improvement "
                "in PSQI scores (mean difference -2.3, 95% CI -3.1 to -1.5, p<0.001). Conclusion: Melatonin improves sleep "
                "quality in adults with insomnia."
            ),
            journal="Sleep Medicine",
            journal_issn="1389-9457",
            publication_year=2023,
            publication_types=["Journal Article", "Randomized Controlled Trial"],
        )
    ]

    print("🧪 Testing AI abstract analysis...")
    analyses = await analyzer.analyze_batch(sample_papers, "melatonin", "sleep")

    if not analyses:
        print("❌ Analysis failed")
        return

    for analysis in analyses:
        print(f"\n📄 Paper {analysis.paper_pmid}:")
        print(f"  Relevance: {analysis.relevance_score:.2f}")
        print(f"  Include: {analysis.inclusion_recommendation}")
        print(f"  Φ Gate: {analysis.gate_evaluation.phi_gate.value}")
        print(f"  R Gate: {analysis.gate_evaluation.r_gate.value}")
        print(f"  J Score: {analysis.gate_evaluation.j_score:.2f}")
        print(f"  K Gate: {analysis.gate_evaluation.k_gate.value}")
        print(f"  L Gate: {analysis.gate_evaluation.l_gate.value}")

    consensus = aggregator.aggregate_analyses(analyses)
    if "error" not in consensus:
        print("\n📊 Consensus Results:")
        print(f"  Papers included: {consensus['n_papers_included']}")
        print(f"  Gate scores: {consensus['gate_scores']}")


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    asyncio.run(test_ai_analyzer())
