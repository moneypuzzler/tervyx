"""
AI-Powered Abstract Analysis for TERVYX Gate Evaluation
=====================================================

Uses Gemini API (cost-effective) to analyze paper abstracts and extract:
1. Gate evaluation scores (Φ, R, J, K, L)
2. Quantitative data (effect sizes, sample sizes, CIs)  
3. Study quality indicators
4. Risk of bias assessment

Designed for production use with error handling, retry logic, and batch processing.
"""

import asyncio
import aiohttp
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import time
from enum import Enum
import os

# Import paper types from PubMed integration
from .pubmed_integration import PubMedPaper

class GateScore(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    AMBER = "AMBER"
    LOW = "LOW"
    HIGH = "HIGH"

@dataclass
class ExtractedData:
    """Quantitative data extracted from abstract"""
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
    """TERVYX gate evaluation results"""
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
    """Complete analysis result for a paper abstract"""
    paper_pmid: str
    extracted_data: ExtractedData
    gate_evaluation: GateEvaluation
    relevance_score: float  # 0.0 to 1.0
    inclusion_recommendation: bool
    analysis_confidence: float
    ai_reasoning: str
    processing_time: float

class GeminiAbstractAnalyzer:
    """
    Production AI analyzer with cost-optimized tiered model approach
    - Uses Flash-Lite for initial screening (cheapest)
    - Uses Flash for detailed analysis (best cost/quality balance)
    - Falls back to Pro for complex cases
    """
    
    def __init__(self, api_key: str, 
                 screening_model: str = "gemini-2.5-flash-lite",
                 analysis_model: str = "gemini-2.5-flash", 
                 fallback_model: str = "gemini-2.5-pro"):
        self.api_key = api_key
        self.screening_model = screening_model  # $0.10/$0.40 per 1M tokens
        self.analysis_model = analysis_model    # $0.15/$0.60 per 1M tokens  
        self.fallback_model = fallback_model    # $2.50/$10.00 per 1M tokens
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.rate_limit_delay = 1.0  # 1 second between requests
        self.last_request_time = 0
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2.0
        
        # Cost tracking
        self.token_usage = {
            'screening': {'input': 0, 'output': 0},
            'analysis': {'input': 0, 'output': 0}, 
            'fallback': {'input': 0, 'output': 0}
        }
        
    async def analyze_batch(self, 
                          papers: List[PubMedPaper], 
                          substance: str, 
                          outcome_category: str,
                          use_tiered_approach: bool = True) -> List[AbstractAnalysis]:
        """
        Analyze a batch of papers with cost-optimized tiered approach:
        1. Fast screening with Flash-Lite ($0.10/$0.40)
        2. Detailed analysis with Flash ($0.15/$0.60) 
        3. Complex cases with Pro ($2.50/$10.00)
        """
        results = []
        cost_savings = 0.0
        
        print(f"🤖 Starting {'tiered ' if use_tiered_approach else ''}AI analysis of {len(papers)} abstracts...")
        
        if use_tiered_approach:
            # PHASE 1: Quick relevance screening with cheapest model
            print(f"🔍 Phase 1: Relevance screening with {self.screening_model}...")
            relevant_papers = await self._screen_relevance(papers, substance, outcome_category)
            
            screened_out = len(papers) - len(relevant_papers)
            if screened_out > 0:
                cost_savings = screened_out * 0.15  # Estimated savings per paper
                print(f"  💰 Filtered out {screened_out} irrelevant papers, saving ~${cost_savings:.2f}")
            
            papers_to_analyze = relevant_papers
        else:
            papers_to_analyze = papers
        
        # PHASE 2: Detailed analysis of relevant papers
        print(f"🔬 Phase 2: Detailed analysis of {len(papers_to_analyze)} papers...")
        
        for i, paper in enumerate(papers_to_analyze):
            print(f"  📄 Analyzing paper {i+1}/{len(papers_to_analyze)}: {paper.title[:60]}...")
            
            try:
                start_time = time.time()
                analysis = await self._analyze_single_abstract(paper, substance, outcome_category)
                processing_time = time.time() - start_time
                
                if analysis:
                    analysis.processing_time = processing_time
                    results.append(analysis)
                    print(f"    ✅ Complete (relevance: {analysis.relevance_score:.2f})")
                else:
                    print(f"    ❌ Failed to analyze")
                
            except Exception as e:
                print(f"    💥 Error: {str(e)}")
                continue
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
        
        successful = len(results)
        print(f"🎯 Analysis complete: {successful}/{len(papers)} papers successfully analyzed")
        if cost_savings > 0:
            print(f"💰 Estimated cost savings: ${cost_savings:.2f}")
        
        # Print cost summary
        self._print_cost_summary()
        
        return results
    
    async def _analyze_single_abstract(self, 
                                     paper: PubMedPaper, 
                                     substance: str, 
                                     outcome_category: str) -> Optional[AbstractAnalysis]:
        """
        Analyze a single abstract with retry logic
        """
        
        for attempt in range(self.max_retries):
            try:
                result = await self._call_gemini_api(paper, substance, outcome_category)
                if result:
                    return result
                    
            except Exception as e:
                print(f"    ⚠️ Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return None
    
    async def _call_gemini_api(self, 
                             paper: PubMedPaper, 
                             substance: str, 
                             outcome_category: str) -> Optional[AbstractAnalysis]:
        """
        Call Gemini API with structured analysis prompt
        """
        
        # Construct comprehensive analysis prompt
        prompt = self._build_analysis_prompt(paper, substance, outcome_category)
        
        # API request - use analysis model for detailed analysis
        url = f"{self.base_url}/models/{self.analysis_model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for consistent analysis
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
        }\n        \n        async with aiohttp.ClientSession() as session:\n            async with session.post(url, json=payload) as response:\n                if response.status == 200:\n                    data = await response.json()\n                    \n                    if 'candidates' in data and len(data['candidates']) > 0:\n                        text_response = data['candidates'][0]['content']['parts'][0]['text']\n                        return self._parse_gemini_response(text_response, paper.pmid)\n                    \n                elif response.status == 429:  # Rate limit\n                    print(f"    ⏳ Rate limited, waiting...")\n                    await asyncio.sleep(5.0)\n                    raise Exception("Rate limited")\n                    \n                else:\n                    error_text = await response.text()\n                    raise Exception(f"API error {response.status}: {error_text}")\n        \n        return None\n    \n    def _build_analysis_prompt(self, paper: PubMedPaper, substance: str, outcome_category: str) -> str:\n        """\n        Build comprehensive analysis prompt for Gemini\n        """\n        \n        return f"""\nYou are an expert systematic reviewer analyzing a scientific paper for the TERVYX Protocol evidence evaluation system.\n\n**PAPER TO ANALYZE:**\nTitle: {paper.title}\nJournal: {paper.journal} ({paper.publication_year})\nPMID: {paper.pmid}\nDOI: {paper.doi or 'Not available'}\nPublication Types: {', '.join(paper.publication_types)}\nAbstract: {paper.abstract}\n\n**RESEARCH QUESTION:**\nSubstance: {substance}\nOutcome Category: {outcome_category}\n\n**REQUIRED ANALYSIS:**\nPlease provide a comprehensive analysis in JSON format with the following structure:\n\n```json\n{{\n  "relevance_score": 0.0-1.0,\n  "inclusion_recommendation": true/false,\n  "analysis_confidence": 0.0-1.0,\n  "extracted_data": {{\n    "sample_size_treatment": integer or null,\n    "sample_size_control": integer or null,\n    "effect_size": float or null,\n    "effect_type": "SMD/MD/OR/RR/etc" or null,\n    "confidence_interval_lower": float or null,\n    "confidence_interval_upper": float or null,\n    "p_value": float or null,\n    "study_duration_weeks": integer or null,\n    "population": "string description",\n    "intervention_details": "string description",\n    "control_type": "placebo/active/etc",\n    "outcome_measure": "specific measure used",\n    "statistical_significance": true/false/null\n  }},\n  "gate_evaluation": {{\n    "phi_gate": "PASS/FAIL/AMBER",\n    "phi_reasoning": "Physiological plausibility assessment",\n    "r_gate": "PASS/FAIL/AMBER", \n    "r_reasoning": "Relevance to general population assessment",\n    "j_score": 0.0-1.0,\n    "j_reasoning": "Study design and methodology quality",\n    "k_gate": "PASS/FAIL/AMBER",\n    "k_reasoning": "Safety signals and contraindications",\n    "l_gate": "PASS/FAIL/AMBER",\n    "l_reasoning": "Language appropriateness and claims",\n    "overall_quality_score": 0.0-1.0,\n    "risk_of_bias": "low/some/high"\n  }},\n  "ai_reasoning": "Detailed explanation of analysis and decisions"\n}}\n```\n\n**GATE EVALUATION CRITERIA:**\n\n**Φ Gate (Physiological Plausibility):**\n- PASS: Biologically plausible mechanism, appropriate dose/timing\n- FAIL: Physiologically impossible claims, obvious pseudoscience\n- AMBER: Unclear or speculative mechanisms\n\n**R Gate (Relevance):**\n- PASS: Population, dose, duration relevant to typical use\n- FAIL: Highly specific population, extreme doses, irrelevant context\n- AMBER: Some relevance concerns but acceptable\n\n**J Gate (Journal/Study Quality):** (0.0-1.0 score)\n- Consider: Study design (RCT=higher), sample size, methodology rigor\n- Randomized controlled trials: 0.7-1.0\n- Well-designed observational: 0.4-0.7\n- Case studies, poor methodology: 0.0-0.4\n\n**K Gate (Safety):**\n- PASS: No safety concerns mentioned, or safety appropriately assessed\n- FAIL: Serious adverse events, safety signals, contraindications\n- AMBER: Minor safety concerns or insufficient safety data\n\n**L Gate (Language):**\n- PASS: Appropriate scientific language, measured conclusions\n- FAIL: Exaggerated claims, marketing language, overstatement\n- AMBER: Slightly enthusiastic but not problematic\n\n**DATA EXTRACTION NOTES:**\n- Extract numerical data exactly as reported\n- For effect sizes, prefer standardized measures (Cohen's d, SMD)\n- Note statistical significance based on p-values or confidence intervals\n- Population should describe key characteristics (age, health status, etc.)\n\n**RELEVANCE SCORING:**\n- 0.9-1.0: Highly relevant, perfect match to research question\n- 0.7-0.8: Good relevance, minor concerns\n- 0.5-0.6: Moderate relevance, some concerns\n- 0.3-0.4: Low relevance, significant concerns\n- 0.0-0.2: Not relevant or off-topic\n\nProvide ONLY the JSON response, no additional text.\n"""\n    \n    def _parse_gemini_response(self, response_text: str, pmid: str) -> Optional[AbstractAnalysis]:\n        """\n        Parse Gemini API response into AbstractAnalysis object\n        """\n        try:\n            # Clean response text (remove markdown formatting if present)\n            json_text = response_text.strip()\n            if json_text.startswith('```json'):\n                json_text = json_text.split('```json')[1].split('```')[0]\n            elif json_text.startswith('```'):\n                json_text = json_text.split('```')[1].split('```')[0]\n            \n            # Parse JSON\n            data = json.loads(json_text)\n            \n            # Extract data\n            extracted_data = ExtractedData(**data.get('extracted_data', {}))\n            \n            gate_eval_data = data.get('gate_evaluation', {})\n            gate_evaluation = GateEvaluation(\n                phi_gate=GateScore(gate_eval_data.get('phi_gate', 'AMBER')),\n                phi_reasoning=gate_eval_data.get('phi_reasoning', ''),\n                r_gate=GateScore(gate_eval_data.get('r_gate', 'AMBER')),\n                r_reasoning=gate_eval_data.get('r_reasoning', ''),\n                j_score=float(gate_eval_data.get('j_score', 0.5)),\n                j_reasoning=gate_eval_data.get('j_reasoning', ''),\n                k_gate=GateScore(gate_eval_data.get('k_gate', 'AMBER')),\n                k_reasoning=gate_eval_data.get('k_reasoning', ''),\n                l_gate=GateScore(gate_eval_data.get('l_gate', 'AMBER')),\n                l_reasoning=gate_eval_data.get('l_reasoning', ''),\n                overall_quality_score=float(gate_eval_data.get('overall_quality_score', 0.5)),\n                risk_of_bias=gate_eval_data.get('risk_of_bias', 'some')\n            )\n            \n            return AbstractAnalysis(\n                paper_pmid=pmid,\n                extracted_data=extracted_data,\n                gate_evaluation=gate_evaluation,\n                relevance_score=float(data.get('relevance_score', 0.5)),\n                inclusion_recommendation=bool(data.get('inclusion_recommendation', False)),\n                analysis_confidence=float(data.get('analysis_confidence', 0.5)),\n                ai_reasoning=data.get('ai_reasoning', ''),\n                processing_time=0.0  # Will be set by caller\n            )\n            \n        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:\n            print(f"    ⚠️ Failed to parse AI response: {str(e)}")\n            print(f"    Raw response: {response_text[:200]}...")\n            return None\n\nclass AnalysisAggregator:\n    """\n    Aggregate multiple paper analyses into consensus results\n    """\n    \n    def __init__(self):\n        pass\n    \n    def aggregate_analyses(self, \n                         analyses: List[AbstractAnalysis], \n                         min_relevance: float = 0.5,\n                         min_confidence: float = 0.6) -> Dict[str, Any]:\n        """\n        Aggregate multiple paper analyses into consensus gate scores and meta-analysis data\n        """\n        \n        # Filter by quality thresholds\n        quality_analyses = [\n            analysis for analysis in analyses \n            if (analysis.relevance_score >= min_relevance and \n                analysis.analysis_confidence >= min_confidence and\n                analysis.inclusion_recommendation)\n        ]\n        \n        if len(quality_analyses) < 2:\n            return {\n                'error': 'Insufficient high-quality analyses for aggregation',\n                'total_papers': len(analyses),\n                'quality_papers': len(quality_analyses)\n            }\n        \n        print(f"📊 Aggregating {len(quality_analyses)} high-quality analyses...")\n        \n        # Aggregate gate scores\n        gate_scores = self._aggregate_gate_scores(quality_analyses)\n        \n        # Extract quantitative data for meta-analysis\n        meta_data = self._extract_meta_analysis_data(quality_analyses)\n        \n        # Calculate consensus scores\n        consensus = {\n            'n_papers_analyzed': len(analyses),\n            'n_papers_included': len(quality_analyses),\n            'inclusion_rate': len(quality_analyses) / len(analyses),\n            'gate_scores': gate_scores,\n            'meta_analysis_data': meta_data,\n            'quality_metrics': self._calculate_quality_metrics(quality_analyses)\n        }\n        \n        return consensus\n    \n    def _aggregate_gate_scores(self, analyses: List[AbstractAnalysis]) -> Dict[str, Any]:\n        """\n        Aggregate gate scores across papers\n        """\n        phi_passes = sum(1 for a in analyses if a.gate_evaluation.phi_gate == GateScore.PASS)\n        r_passes = sum(1 for a in analyses if a.gate_evaluation.r_gate == GateScore.PASS)\n        k_passes = sum(1 for a in analyses if a.gate_evaluation.k_gate == GateScore.PASS)\n        l_passes = sum(1 for a in analyses if a.gate_evaluation.l_gate == GateScore.PASS)\n        \n        # K and Φ gates: ANY failure means overall failure (safety-first)\n        phi_fails = sum(1 for a in analyses if a.gate_evaluation.phi_gate == GateScore.FAIL)\n        k_fails = sum(1 for a in analyses if a.gate_evaluation.k_gate == GateScore.FAIL)\n        \n        # J gate: average score\n        j_scores = [a.gate_evaluation.j_score for a in analyses]\n        avg_j_score = sum(j_scores) / len(j_scores) if j_scores else 0.5\n        \n        return {\n            'phi_gate': GateScore.FAIL.value if phi_fails > 0 else GateScore.PASS.value,\n            'r_gate': GateScore.PASS.value if r_passes / len(analyses) > 0.6 else GateScore.FAIL.value,\n            'j_score': avg_j_score,\n            'k_gate': GateScore.FAIL.value if k_fails > 0 else GateScore.PASS.value,\n            'l_gate': GateScore.PASS.value if l_passes / len(analyses) > 0.8 else GateScore.FAIL.value,\n            'gate_details': {\n                'phi_pass_rate': phi_passes / len(analyses),\n                'r_pass_rate': r_passes / len(analyses),\n                'j_score_range': [min(j_scores), max(j_scores)],\n                'k_pass_rate': k_passes / len(analyses),\n                'l_pass_rate': l_passes / len(analyses)\n            }\n        }\n    \n    def _extract_meta_analysis_data(self, analyses: List[AbstractAnalysis]) -> List[Dict[str, Any]]:\n        """\n        Extract quantitative data for meta-analysis\n        """\n        meta_studies = []\n        \n        for analysis in analyses:\n            data = analysis.extracted_data\n            \n            # Only include studies with extractable quantitative data\n            if (data.sample_size_treatment and data.sample_size_control and \n                data.effect_size is not None):\n                \n                study_data = {\n                    'pmid': analysis.paper_pmid,\n                    'effect_size': data.effect_size,\n                    'effect_type': data.effect_type or 'SMD',\n                    'n_treatment': data.sample_size_treatment,\n                    'n_control': data.sample_size_control,\n                    'ci_lower': data.confidence_interval_lower,\n                    'ci_upper': data.confidence_interval_upper,\n                    'p_value': data.p_value,\n                    'duration_weeks': data.study_duration_weeks,\n                    'population': data.population,\n                    'risk_of_bias': analysis.gate_evaluation.risk_of_bias,\n                    'quality_score': analysis.gate_evaluation.overall_quality_score\n                }\n                \n                meta_studies.append(study_data)\n        \n        return meta_studies\n    \n    def _calculate_quality_metrics(self, analyses: List[AbstractAnalysis]) -> Dict[str, float]:\n        """\n        Calculate overall quality metrics for the evidence base\n        """\n        confidences = [a.analysis_confidence for a in analyses]\n        relevances = [a.relevance_score for a in analyses]\n        quality_scores = [a.gate_evaluation.overall_quality_score for a in analyses]\n        \n        return {\n            'mean_confidence': sum(confidences) / len(confidences),\n            'mean_relevance': sum(relevances) / len(relevances),\n            'mean_quality_score': sum(quality_scores) / len(quality_scores),\n            'high_quality_rate': len([q for q in quality_scores if q >= 0.7]) / len(quality_scores)\n        }\n\n# ============================================================================\n# Testing and Usage\n# ============================================================================\n\nasync def test_ai_analyzer():\n    """\n    Test the AI abstract analyzer with sample data\n    """\n    \n    # Mock Gemini API key (replace with real key)\n    api_key = os.getenv('GEMINI_API_KEY', 'your-api-key-here')\n    \n    if api_key == 'your-api-key-here':\n        print("⚠️ No Gemini API key found. Set GEMINI_API_KEY environment variable.")\n        return\n    \n    # Initialize analyzer\n    analyzer = GeminiAbstractAnalyzer(api_key)\n    aggregator = AnalysisAggregator()\n    \n    # Create sample papers (in real use, these would come from PubMed)\n    sample_papers = [\n        PubMedPaper(\n            pmid="12345678",\n            title="Melatonin supplementation improves sleep quality in adults with insomnia",\n            abstract="Background: Insomnia affects 30% of adults. Objective: To evaluate melatonin supplementation for sleep quality. Methods: Randomized, double-blind, placebo-controlled trial. 120 adults with insomnia randomized to 3mg melatonin or placebo for 4 weeks. Primary outcome: Pittsburgh Sleep Quality Index (PSQI). Results: Melatonin group showed significant improvement in PSQI scores (mean difference -2.3, 95% CI -3.1 to -1.5, p<0.001) compared to placebo. No serious adverse events. Conclusion: Melatonin supplementation significantly improves sleep quality in adults with insomnia.",\n            journal="Sleep Medicine",\n            journal_issn="1389-9457",\n            publication_year=2023,\n            publication_types=["Journal Article", "Randomized Controlled Trial"]\n        )\n    ]\n    \n    # Test analysis\n    print("🧪 Testing AI Abstract Analysis...")\n    \n    analyses = await analyzer.analyze_batch(sample_papers, "melatonin", "sleep")\n    \n    if analyses:\n        print(f"✅ Analysis successful!")\n        \n        # Print results\n        for analysis in analyses:\n            print(f"\\n📄 Paper {analysis.paper_pmid}:")\n            print(f"  Relevance: {analysis.relevance_score:.2f}")\n            print(f"  Include: {analysis.inclusion_recommendation}")\n            print(f"  Φ Gate: {analysis.gate_evaluation.phi_gate.value}")\n            print(f"  R Gate: {analysis.gate_evaluation.r_gate.value}") \n            print(f"  J Score: {analysis.gate_evaluation.j_score:.2f}")\n            print(f"  K Gate: {analysis.gate_evaluation.k_gate.value}")\n            print(f"  L Gate: {analysis.gate_evaluation.l_gate.value}")\n            \n            if analysis.extracted_data.sample_size_treatment:\n                print(f"  Sample: {analysis.extracted_data.sample_size_treatment} + {analysis.extracted_data.sample_size_control}")\n            if analysis.extracted_data.effect_size:\n                print(f"  Effect: {analysis.extracted_data.effect_size:.3f}")\n        \n        # Test aggregation\n        consensus = aggregator.aggregate_analyses(analyses)\n        print(f"\\n📊 Consensus Results:")\n        print(f"  Papers included: {consensus.get('n_papers_included', 0)}")\n        print(f"  Gate scores: {consensus.get('gate_scores', {})}")\n        \n    else:\n        print("❌ Analysis failed")\n\nif __name__ == "__main__":\n    asyncio.run(test_ai_analyzer())