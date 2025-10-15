"""
Real-Data TERVYX System Architecture
===================================

A comprehensive system for automated evidence evaluation using real scientific literature.
Replaces synthetic data generation with actual paper search, analysis, and gate evaluation.

Architecture Components:
1. Paper Discovery & Metadata Collection
2. AI-Powered Content Analysis  
3. Journal Quality Assessment
4. Automated Gate Evaluation
5. Real Meta-Analysis Pipeline
6. TEL-5 Classification & Entry Generation
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import json
import requests
import asyncio
from datetime import datetime
import hashlib

# ============================================================================
# Core Data Models
# ============================================================================

@dataclass
class PaperMetadata:
    """Complete metadata for a scientific paper"""
    pmid: str
    doi: Optional[str] 
    title: str
    abstract: str
    authors: List[str]
    journal: str
    journal_issn: str
    impact_factor: Optional[float]
    publication_year: int
    study_type: str  # RCT, observational, review, etc.
    mesh_terms: List[str]
    citation_count: Optional[int]
    retraction_status: bool
    full_text_available: bool

@dataclass 
class StudyData:
    """Extracted quantitative data from a study"""
    paper: PaperMetadata
    intervention: str
    control: str
    outcome_measure: str
    sample_size_treatment: int
    sample_size_control: int
    effect_size: Optional[float]
    effect_type: str  # SMD, MD, OR, RR
    confidence_interval: Tuple[float, float]
    p_value: Optional[float]
    study_duration_weeks: Optional[int]
    population: str
    risk_of_bias: str  # low, some, high
    
@dataclass
class JournalQuality:
    """Journal quality assessment data"""
    issn: str
    name: str
    impact_factor_2023: Optional[float]
    impact_factor_5year: Optional[float]
    predatory_status: bool
    retraction_rate: float
    publisher: str
    open_access: bool
    peer_review_type: str
    indexing_databases: List[str]

class GateResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL" 
    LOW = "LOW"
    HIGH = "HIGH"

# ============================================================================
# Paper Discovery System
# ============================================================================

class PubMedSearchEngine:
    """
    Real-time paper search and metadata extraction from PubMed/PMC
    """
    
    def __init__(self, email: str):
        self.email = email
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        
    async def search_papers(self, 
                          substance: str, 
                          outcome: str,
                          max_results: int = 100) -> List[str]:
        """
        Search PubMed for papers matching substance + outcome
        
        Returns list of PMIDs for relevant papers
        """
        # Construct sophisticated search query
        query_parts = []
        
        # Substance terms
        substance_terms = self._generate_substance_synonyms(substance)
        substance_query = " OR ".join([f'"{term}"[Title/Abstract]' for term in substance_terms])
        query_parts.append(f"({substance_query})")
        
        # Outcome terms  
        outcome_terms = self._generate_outcome_synonyms(outcome)
        outcome_query = " OR ".join([f'"{term}"[Title/Abstract]' for term in outcome_terms])
        query_parts.append(f"({outcome_query})")
        
        # Study type filters
        study_filters = [
            '"randomized controlled trial"[Publication Type]',
            '"clinical trial"[Publication Type]',
            '"meta-analysis"[Publication Type]',
            '"systematic review"[Publication Type]'
        ]
        query_parts.append(f"({' OR '.join(study_filters)})")
        
        # Language and date filters
        query_parts.append('English[Language]')
        query_parts.append('("2000/01/01"[Date - Publication] : "2025/12/31"[Date - Publication])')
        
        final_query = " AND ".join(query_parts)
        
        # Execute search via E-utilities API
        search_url = f"{self.base_url}esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': final_query,
            'retmax': max_results,
            'retmode': 'json',
            'email': self.email,
            'tool': 'tervyx'
        }
        
        response = requests.get(search_url, params=params)
        data = response.json()
        
        if 'esearchresult' in data and 'idlist' in data['esearchresult']:
            return data['esearchresult']['idlist']
        return []
    
    def _generate_substance_synonyms(self, substance: str) -> List[str]:
        """Generate substance name variants and synonyms"""
        # This would integrate with chemical databases like ChEBI, PubChem
        synonyms = [substance]
        
        # Basic transformations
        synonyms.append(substance.replace('-', ' '))
        synonyms.append(substance.replace(' ', '-'))
        
        # Chemical name variations would be looked up from databases
        return list(set(synonyms))
    
    def _generate_outcome_synonyms(self, outcome: str) -> List[str]:
        """Generate outcome measure synonyms"""
        outcome_map = {
            'sleep': ['sleep quality', 'insomnia', 'sleep latency', 'sleep efficiency', 'PSQI'],
            'cognition': ['cognitive function', 'memory', 'attention', 'executive function'],
            'mental_health': ['depression', 'anxiety', 'mood', 'psychological wellbeing'],
            'cardiovascular': ['blood pressure', 'cholesterol', 'heart rate', 'cardiovascular'],
            'renal_safety': ['kidney function', 'creatinine', 'nephrotoxicity', 'renal']
        }
        return outcome_map.get(outcome, [outcome])

    async def fetch_paper_metadata(self, pmids: List[str]) -> List[PaperMetadata]:
        """
        Fetch complete metadata for papers given PMIDs
        """
        if not pmids:
            return []
            
        # Fetch via efetch API
        fetch_url = f"{self.base_url}efetch.fcgi"
        params = {
            'db': 'pubmed',
            'id': ','.join(pmids[:50]),  # Batch process max 50
            'retmode': 'xml',
            'email': self.email
        }
        
        response = requests.get(fetch_url, params=params)
        
        # Parse XML response and extract metadata
        # This would use xml.etree.ElementTree or lxml
        papers = self._parse_pubmed_xml(response.content)
        
        # Enrich with additional data
        for paper in papers:
            paper.impact_factor = await self._get_impact_factor(paper.journal_issn)
            paper.citation_count = await self._get_citation_count(paper.doi)
            paper.retraction_status = await self._check_retraction(paper.pmid)
            
        return papers
    
    def _parse_pubmed_xml(self, xml_content: bytes) -> List[PaperMetadata]:
        """Parse PubMed XML response into PaperMetadata objects"""
        # XML parsing implementation would go here
        # This is a placeholder - real implementation would parse the XML
        return []
    
    async def _get_impact_factor(self, issn: str) -> Optional[float]:
        """Get journal impact factor from JCR or similar database"""
        # Would integrate with Journal Citation Reports API
        return None
    
    async def _get_citation_count(self, doi: str) -> Optional[int]:
        """Get citation count from CrossRef or similar"""
        if not doi:
            return None
        # Would use CrossRef API or similar
        return None
    
    async def _check_retraction(self, pmid: str) -> bool:
        """Check if paper has been retracted"""
        # Would check against Retraction Watch database
        return False

# ============================================================================
# AI-Powered Content Analysis
# ============================================================================

class AIAbstractAnalyzer:
    """
    AI-powered analysis of abstracts for gate evaluation and data extraction
    """
    
    def __init__(self, api_provider: str = "gemini"):
        self.api_provider = api_provider
        self.setup_api()
    
    def setup_api(self):
        """Setup AI API client (Gemini/GPT/Claude)"""
        if self.api_provider == "gemini":
            # Setup Gemini API
            pass
        elif self.api_provider == "gpt":
            # Setup OpenAI API
            pass
    
    async def analyze_abstract(self, paper: PaperMetadata, substance: str, outcome: str) -> Dict[str, Any]:
        """
        Comprehensive AI analysis of abstract for TERVYX gates
        
        Returns structured analysis including:
        - Study design assessment
        - Population characteristics  
        - Intervention details
        - Outcome measures
        - Risk of bias indicators
        - Gate-specific evaluations
        """
        
        analysis_prompt = f"""
        Analyze this scientific abstract for TERVYX Protocol evaluation:
        
        **Paper Details:**
        Title: {paper.title}
        Journal: {paper.journal} ({paper.publication_year})
        Abstract: {paper.abstract}
        
        **Research Question:**
        Substance: {substance}
        Outcome: {outcome}
        
        **Required Analysis:**
        
        1. **Φ Gate (Physiological Plausibility):**
           - Is the claimed effect biologically plausible?
           - Any obvious physiological impossibilities?
           - Category-outcome alignment appropriate?
           
        2. **R Gate (Relevance):**
           - Does study population match general use case?
           - Is dosage/intervention clinically relevant?
           - Outcome measures appropriate?
           
        3. **J Gate (Journal Quality):**
           - Study design quality (RCT vs observational)
           - Sample size adequacy
           - Methodology rigor indicators
           
        4. **K Gate (Safety):**
           - Any safety signals or adverse events mentioned?
           - Contraindications noted?
           - Risk populations identified?
           
        5. **L Gate (Language):**
           - Any exaggerated claims or marketing language?
           - Appropriate scientific tone?
           - Overstatement of results?
           
        6. **Data Extraction:**
           - Sample sizes (treatment/control)
           - Effect size estimates if available
           - Statistical significance
           - Study duration
           - Population characteristics
        
        Provide structured JSON output with specific scores and reasoning.
        """
        
        # Call AI API with prompt
        if self.api_provider == "gemini":
            result = await self._call_gemini_api(analysis_prompt)
        else:
            result = await self._call_other_api(analysis_prompt)
            
        return self._parse_analysis_result(result)
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API for abstract analysis"""
        # Implement actual Gemini API call
        # Use gemini-1.5-flash for cost efficiency
        return ""
    
    async def _call_other_api(self, prompt: str) -> str:
        """Call other AI API (GPT/Claude)"""
        return ""
    
    def _parse_analysis_result(self, result: str) -> Dict[str, Any]:
        """Parse AI analysis result into structured format"""
        try:
            return json.loads(result)
        except:
            # Fallback parsing or error handling
            return {}

# ============================================================================
# Journal Quality Database  
# ============================================================================

class JournalQualityDB:
    """
    Database of journal quality metrics and predatory journal detection
    """
    
    def __init__(self):
        self.predatory_journals = self._load_predatory_list()
        self.impact_factors = self._load_impact_factors()
        
    def assess_journal_quality(self, journal: str, issn: str) -> JournalQuality:
        """
        Comprehensive journal quality assessment
        """
        return JournalQuality(
            issn=issn,
            name=journal,
            impact_factor_2023=self._get_if_2023(issn),
            impact_factor_5year=self._get_if_5year(issn), 
            predatory_status=self._is_predatory(journal, issn),
            retraction_rate=self._get_retraction_rate(issn),
            publisher=self._get_publisher(issn),
            open_access=self._is_open_access(issn),
            peer_review_type=self._get_peer_review_type(issn),
            indexing_databases=self._get_indexing(issn)
        )
    
    def _load_predatory_list(self) -> set:
        """Load Beall's list and other predatory journal databases"""
        # Would load from updated predatory journal lists
        return set()
    
    def _load_impact_factors(self) -> dict:
        """Load Journal Citation Reports data"""
        return {}
    
    def _is_predatory(self, journal: str, issn: str) -> bool:
        """Check if journal is predatory"""
        return issn in self.predatory_journals or journal.lower() in self.predatory_journals
    
    def _get_if_2023(self, issn: str) -> Optional[float]:
        """Get 2023 impact factor"""
        return self.impact_factors.get(issn, {}).get('if_2023')
    
    def _get_if_5year(self, issn: str) -> Optional[float]:
        return self.impact_factors.get(issn, {}).get('if_5year')
    
    def _get_retraction_rate(self, issn: str) -> float:
        """Calculate retraction rate for journal"""
        return 0.0
    
    def _get_publisher(self, issn: str) -> str:
        return "Unknown"
    
    def _is_open_access(self, issn: str) -> bool:
        return False
    
    def _get_peer_review_type(self, issn: str) -> str:
        return "unknown"
    
    def _get_indexing(self, issn: str) -> List[str]:
        return []

# ============================================================================
# Real Meta-Analysis Engine
# ============================================================================

class RealMetaAnalysis:
    """
    Automated meta-analysis using extracted real study data
    """
    
    def __init__(self):
        pass
    
    async def perform_meta_analysis(self, studies: List[StudyData], outcome_category: str) -> Dict[str, Any]:
        """
        Perform REML + Monte Carlo meta-analysis on real study data
        """
        if len(studies) < 2:
            return {"error": "Insufficient studies for meta-analysis"}
        
        # Convert studies to analysis format
        effect_sizes = []
        variances = []
        sample_sizes = []
        
        for study in studies:
            if study.effect_size is not None:
                effect_sizes.append(study.effect_size)
                # Calculate variance from CI or use estimated variance
                var = self._calculate_variance(study)
                variances.append(var)
                sample_sizes.append(study.sample_size_treatment + study.sample_size_control)
        
        # Perform REML estimation
        from engine.mc_meta import run_reml_mc_analysis
        
        result = run_reml_mc_analysis(
            effect_sizes=effect_sizes,
            variances=variances,
            sample_sizes=sample_sizes,
            delta=self._get_delta_threshold(outcome_category),
            n_draws=10000
        )
        
        return result
    
    def _calculate_variance(self, study: StudyData) -> float:
        """Calculate study variance from available data"""
        if study.confidence_interval:
            ci_lower, ci_upper = study.confidence_interval
            # Approximate variance from CI width
            se = (ci_upper - ci_lower) / (2 * 1.96)
            return se ** 2
        else:
            # Use sample size based approximation
            total_n = study.sample_size_treatment + study.sample_size_control
            return 4 / total_n  # Rough approximation
    
    def _get_delta_threshold(self, outcome_category: str) -> float:
        """Get clinical significance threshold for outcome category"""
        thresholds = {
            'sleep': 0.2,
            'cognition': 0.15, 
            'mental_health': 0.2,
            'cardiovascular': 0.1,
            'renal_safety': 5.0  # Different scale for safety
        }
        return thresholds.get(outcome_category, 0.2)

# ============================================================================
# Integrated TERVYX Pipeline
# ============================================================================

class RealTERVYXPipeline:
    """
    Complete pipeline from query to TERVYX entry using real data
    """
    
    def __init__(self, email: str):
        self.pubmed = PubMedSearchEngine(email)
        self.ai_analyzer = AIAbstractAnalyzer("gemini")  # Use Gemini for cost efficiency
        self.journal_db = JournalQualityDB()
        self.meta_analyzer = RealMetaAnalysis()
    
    async def generate_real_entry(self, substance: str, outcome_category: str) -> Dict[str, Any]:
        """
        Generate complete TERVYX entry using real scientific literature
        
        Steps:
        1. Search PubMed for relevant papers
        2. Extract and analyze abstracts with AI
        3. Assess journal quality
        4. Evaluate all gates
        5. Perform meta-analysis on extracted data
        6. Generate TEL-5 classification
        7. Create final TERVYX entry
        """
        
        print(f"🔍 Searching literature for {substance} + {outcome_category}...")
        
        # Step 1: Paper Discovery
        pmids = await self.pubmed.search_papers(substance, outcome_category, max_results=50)
        if not pmids:
            return {"error": "No relevant papers found"}
        
        print(f"📄 Found {len(pmids)} papers, fetching metadata...")
        
        # Step 2: Metadata Collection
        papers = await self.pubmed.fetch_paper_metadata(pmids)
        
        # Step 3: AI Analysis & Data Extraction
        print(f"🤖 Analyzing abstracts with AI...")
        analyzed_studies = []
        
        for paper in papers:
            analysis = await self.ai_analyzer.analyze_abstract(paper, substance, outcome_category)
            
            # Skip if analysis failed or study not relevant
            if not analysis or analysis.get('relevance_score', 0) < 0.5:
                continue
                
            # Convert AI analysis to StudyData
            study_data = self._convert_analysis_to_study_data(paper, analysis, substance, outcome_category)
            if study_data:
                analyzed_studies.append(study_data)
        
        if len(analyzed_studies) < 2:
            return {"error": "Insufficient high-quality studies for analysis"}
        
        print(f"✅ Extracted data from {len(analyzed_studies)} studies")
        
        # Step 4: Gate Evaluation
        gate_results = self._evaluate_gates(analyzed_studies)
        
        # Step 5: Meta-Analysis
        print(f"📊 Performing meta-analysis...")
        meta_results = await self.meta_analyzer.perform_meta_analysis(analyzed_studies, outcome_category)
        
        # Step 6: TEL-5 Classification
        from engine.tel5_rules import tel5_classify
        
        P_effect = meta_results.get('P_effect_gt_delta', 0.0)
        phi_violation = gate_results['phi'] == GateResult.FAIL
        k_violation = gate_results['k'] == GateResult.FAIL
        
        tier, label = tel5_classify(P_effect, phi_violation, k_violation)
        
        # Step 7: Generate Final Entry
        entry = {
            "@context": "https://schema.org/",
            "@type": "Dataset", 
            "id": f"nutrient:{substance}:{outcome_category}:v1",
            "title": f"{substance.title()} — {outcome_category.title()}",
            "category": outcome_category,
            "tier": tier,
            "label": label,
            "P_effect_gt_delta": P_effect,
            "gate_results": {
                "phi": gate_results['phi'].value,
                "r": gate_results['r'].value,
                "j": gate_results['j_score'],
                "k": gate_results['k'].value,
                "l": gate_results['l'].value
            },
            "evidence_summary": {
                "n_studies": len(analyzed_studies),
                "total_n": sum(s.sample_size_treatment + s.sample_size_control for s in analyzed_studies),
                "I2": meta_results.get('I2', 0),
                "tau2": meta_results.get('tau2', 0),
                "mu_hat": meta_results.get('mu_hat', 0),
                "mu_CI95": meta_results.get('mu_CI95', [0, 0])
            },
            "real_papers": [
                {
                    "pmid": study.paper.pmid,
                    "doi": study.paper.doi,
                    "title": study.paper.title,
                    "journal": study.paper.journal,
                    "year": study.paper.publication_year,
                    "effect_size": study.effect_size
                }
                for study in analyzed_studies
            ],
            "data_source": "real_literature",
            "created": datetime.now().isoformat(),
            "audit_hash": self._generate_audit_hash(analyzed_studies)
        }
        
        return entry
    
    def _convert_analysis_to_study_data(self, paper: PaperMetadata, analysis: Dict, substance: str, outcome: str) -> Optional[StudyData]:
        """Convert AI analysis results to StudyData object"""
        extracted_data = analysis.get('extracted_data', {})
        
        if not extracted_data.get('sample_size_treatment'):
            return None
            
        return StudyData(
            paper=paper,
            intervention=f"{substance} supplement",
            control=extracted_data.get('control', 'Placebo'),
            outcome_measure=extracted_data.get('outcome_measure', outcome),
            sample_size_treatment=extracted_data.get('sample_size_treatment', 0),
            sample_size_control=extracted_data.get('sample_size_control', 0),
            effect_size=extracted_data.get('effect_size'),
            effect_type=extracted_data.get('effect_type', 'SMD'),
            confidence_interval=extracted_data.get('confidence_interval', (0, 0)),
            p_value=extracted_data.get('p_value'),
            study_duration_weeks=extracted_data.get('duration_weeks'),
            population=extracted_data.get('population', 'Adults'),
            risk_of_bias=analysis.get('risk_of_bias', 'some')
        )
    
    def _evaluate_gates(self, studies: List[StudyData]) -> Dict[str, Any]:
        """Evaluate all TERVYX gates based on real study data"""
        
        # Φ Gate: Aggregate physiological plausibility
        phi_scores = [self._evaluate_phi_gate(study) for study in studies]
        phi_result = GateResult.FAIL if any(score == GateResult.FAIL for score in phi_scores) else GateResult.PASS
        
        # R Gate: Relevance assessment  
        r_scores = [self._evaluate_r_gate(study) for study in studies]
        avg_r_score = sum(1 if s == GateResult.PASS else 0 for s in r_scores) / len(r_scores)
        r_result = GateResult.PASS if avg_r_score > 0.6 else GateResult.FAIL
        
        # J Gate: Journal quality aggregate
        j_scores = [self._evaluate_j_gate(study) for study in studies]
        avg_j_score = sum(j_scores) / len(j_scores)
        
        # K Gate: Safety assessment
        k_scores = [self._evaluate_k_gate(study) for study in studies]  
        k_result = GateResult.FAIL if any(score == GateResult.FAIL for score in k_scores) else GateResult.PASS
        
        # L Gate: Language assessment
        l_scores = [self._evaluate_l_gate(study) for study in studies]
        l_result = GateResult.FAIL if any(score == GateResult.FAIL for score in l_scores) else GateResult.PASS
        
        return {
            'phi': phi_result,
            'r': r_result, 
            'j_score': avg_j_score,
            'k': k_result,
            'l': l_result
        }
    
    def _evaluate_phi_gate(self, study: StudyData) -> GateResult:
        """Evaluate Φ gate for single study"""
        # Would implement physiological plausibility checks
        return GateResult.PASS
    
    def _evaluate_r_gate(self, study: StudyData) -> GateResult:
        """Evaluate R gate for single study"""
        # Check population relevance, dosage appropriateness, etc.
        return GateResult.PASS
    
    def _evaluate_j_gate(self, study: StudyData) -> float:
        """Evaluate J gate for single study, return numeric score"""
        journal_quality = self.journal_db.assess_journal_quality(study.paper.journal, study.paper.journal_issn)
        
        score = 0.5  # Base score
        
        if journal_quality.impact_factor_2023:
            if journal_quality.impact_factor_2023 > 5.0:
                score += 0.3
            elif journal_quality.impact_factor_2023 > 2.0:
                score += 0.2
            else:
                score += 0.1
        
        if journal_quality.predatory_status:
            score = 0.0  # Zero out predatory journals
            
        return min(score, 1.0)
    
    def _evaluate_k_gate(self, study: StudyData) -> GateResult:
        """Evaluate K gate for single study"""
        # Check for safety signals in the study
        return GateResult.PASS
    
    def _evaluate_l_gate(self, study: StudyData) -> GateResult:
        """Evaluate L gate for single study"""
        # Check for exaggerated language in title/abstract
        return GateResult.PASS
    
    def _generate_audit_hash(self, studies: List[StudyData]) -> str:
        """Generate audit hash for reproducibility"""
        study_ids = [study.paper.pmid for study in studies]
        study_ids.sort()
        hash_input = "|".join(study_ids)
        return hashlib.sha256(hash_input.encode()).hexdigest()[:8]

# ============================================================================
# Usage Examples & Testing
# ============================================================================

async def test_real_system():
    """Test the real-data TERVYX system"""
    
    pipeline = RealTERVYXPipeline(email="your-email@domain.com")
    
    # Test substances with known literature
    test_cases = [
        ("melatonin", "sleep"),
        ("omega-3", "cognition"), 
        ("curcumin", "cognition"),
        ("magnesium", "sleep"),
        ("st-john-wort", "mental_health")
    ]
    
    results = []
    for substance, outcome in test_cases:
        print(f"\n🧪 Testing {substance} + {outcome}...")
        
        try:
            entry = await pipeline.generate_real_entry(substance, outcome)
            results.append(entry)
            
            if 'error' not in entry:
                print(f"✅ Generated TEL-{entry['tier']} entry with {entry['evidence_summary']['n_studies']} studies")
            else:
                print(f"❌ Failed: {entry['error']}")
                
        except Exception as e:
            print(f"💥 Error: {str(e)}")
    
    return results

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        results = await test_real_system()
        
        # Save results
        with open('/home/user/webapp/real_entries_test.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n🎉 Generated {len(results)} real-data TERVYX entries")
    
    asyncio.run(main())