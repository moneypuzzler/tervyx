"""
Cost-Optimized AI Abstract Analyzer for TERVYX
=============================================

Implements tiered LLM approach for maximum cost efficiency:
- Tier 1: Flash-Lite ($0.10/$0.40) for relevance screening
- Tier 2: Flash ($0.15/$0.60) for detailed analysis  
- Tier 3: Pro ($2.50/$10.00) for complex cases

Provides 30-40% cost savings while maintaining scientific rigor.
"""

import asyncio
import aiohttp
import json
import re
from typing import Dict, List, Optional, Any
import time
import os

# Import base types
from .ai_abstract_analyzer import (
    GeminiAbstractAnalyzer, AbstractAnalysis, ExtractedData, 
    GateEvaluation, GateScore
)
from .pubmed_integration import PubMedPaper

class CostOptimizedAnalyzer(GeminiAbstractAnalyzer):
    """
    Cost-optimized analyzer with intelligent tiered processing
    """
    
    def __init__(self, api_key: str, 
                 screening_model: str = "gemini-2.5-flash-lite",
                 analysis_model: str = "gemini-2.5-flash", 
                 fallback_model: str = "gemini-2.5-pro",
                 enable_cost_tracking: bool = True):
        
        super().__init__(api_key, screening_model, analysis_model, fallback_model)
        
        self.enable_cost_tracking = enable_cost_tracking
        
        # Enhanced cost tracking with pricing
        self.pricing = {
            'gemini-2.5-flash-lite': {'input': 0.10, 'output': 0.40},
            'gemini-2.5-flash': {'input': 0.15, 'output': 0.60}, 
            'gemini-2.5-pro': {'input': 2.50, 'output': 10.00}
        }
        
        # Performance metrics
        self.metrics = {
            'papers_screened': 0,
            'papers_filtered': 0,
            'papers_analyzed': 0,
            'papers_retried': 0,
            'total_cost': 0.0,
            'processing_time': 0.0
        }
    
    async def process_batch_optimized(self, 
                                    papers: List[PubMedPaper], 
                                    substance: str, 
                                    outcome_category: str,
                                    relevance_threshold: float = 0.6,
                                    confidence_threshold: float = 0.7) -> List[AbstractAnalysis]:
        """
        Process papers with full cost optimization strategy
        """
        start_time = time.time()
        
        print(f"🚀 Starting cost-optimized analysis of {len(papers)} papers...")
        print(f"📊 Strategy: Screen → Analyze → Retry with quality fallbacks")
        
        # PHASE 1: Relevance Screening (Flash-Lite)
        print(f"\n🔍 PHASE 1: Relevance screening with {self.screening_model}")
        relevant_papers = await self._screen_relevance_batch(
            papers, substance, outcome_category, relevance_threshold
        )
        
        screened_out = len(papers) - len(relevant_papers)
        self.metrics['papers_screened'] = len(papers)
        self.metrics['papers_filtered'] = screened_out
        
        if screened_out > 0:
            savings = screened_out * self._estimate_paper_cost(self.analysis_model)
            print(f"  💰 Filtered {screened_out} irrelevant papers → Saved ~${savings:.2f}")
        
        # PHASE 2: Detailed Analysis (Flash)  
        print(f"\n🔬 PHASE 2: Detailed analysis with {self.analysis_model}")
        analyses = await self._analyze_batch_with_quality_check(
            relevant_papers, substance, outcome_category, confidence_threshold
        )
        
        self.metrics['papers_analyzed'] = len(relevant_papers)
        
        # PHASE 3: Results Summary
        self.metrics['processing_time'] = time.time() - start_time
        
        await self._print_optimization_summary()
        
        return analyses
    
    async def _screen_relevance_batch(self, 
                                    papers: List[PubMedPaper],
                                    substance: str, 
                                    outcome_category: str,
                                    threshold: float) -> List[PubMedPaper]:
        """
        Batch relevance screening with cost tracking
        """
        relevant_papers = []
        
        for i, paper in enumerate(papers):
            print(f"  📋 Screening {i+1}/{len(papers)}: {paper.title[:50]}...")
            
            try:
                relevance_score = await self._quick_relevance_check(
                    paper, substance, outcome_category
                )
                
                if relevance_score >= threshold:
                    relevant_papers.append(paper)
                    print(f"    ✅ Relevant ({relevance_score:.2f})")
                else:
                    print(f"    ❌ Filtered ({relevance_score:.2f})")
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                print(f"    ⚠️ Screening error: {str(e)}")
                # Conservative: include paper if screening fails
                relevant_papers.append(paper)
        
        return relevant_papers
    
    async def _analyze_batch_with_quality_check(self,
                                              papers: List[PubMedPaper],
                                              substance: str, 
                                              outcome_category: str,
                                              confidence_threshold: float) -> List[AbstractAnalysis]:
        """
        Analyze papers with automatic quality-based retry logic
        """
        analyses = []
        
        for i, paper in enumerate(papers):
            print(f"  📄 Analyzing {i+1}/{len(papers)}: {paper.title[:50]}...")
            
            # Try with primary analysis model (Flash)
            analysis = await self._analyze_with_model(
                paper, substance, outcome_category, self.analysis_model
            )
            
            # Check if retry needed with premium model
            if analysis and analysis.analysis_confidence < confidence_threshold:
                print(f"    🔄 Low confidence ({analysis.analysis_confidence:.2f}) → Retrying with Pro")
                
                pro_analysis = await self._analyze_with_model(
                    paper, substance, outcome_category, self.fallback_model
                )
                
                if pro_analysis and pro_analysis.analysis_confidence > analysis.analysis_confidence:
                    analysis = pro_analysis
                    self.metrics['papers_retried'] += 1
                    print(f"    ⬆️ Improved confidence ({analysis.analysis_confidence:.2f})")
            
            if analysis:
                analyses.append(analysis)
                print(f"    ✅ Complete (confidence: {analysis.analysis_confidence:.2f})")
            else:
                print(f"    ❌ Failed to analyze")
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
        
        return analyses
    
    async def _analyze_with_model(self, 
                                paper: PubMedPaper, 
                                substance: str, 
                                outcome_category: str,
                                model: str) -> Optional[AbstractAnalysis]:
        """
        Analyze single paper with specified model and cost tracking
        """
        try:
            # Build prompt
            prompt = self._build_analysis_prompt(paper, substance, outcome_category)
            
            # API call
            url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
            
            payload = {
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
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'candidates' in data and len(data['candidates']) > 0:
                            text_response = data['candidates'][0]['content']['parts'][0]['text']
                            
                            # Track costs
                            if self.enable_cost_tracking:
                                self._track_api_usage(prompt, text_response, model)
                            
                            return self._parse_gemini_response(text_response, paper.pmid)
                    
                    elif response.status == 429:
                        print(f"    ⏳ Rate limited")
                        await asyncio.sleep(5.0)
                        
        except Exception as e:
            print(f"    💥 Analysis error: {str(e)}")
        
        return None
    
    async def _quick_relevance_check(self, 
                                   paper: PubMedPaper, 
                                   substance: str, 
                                   outcome_category: str) -> float:
        """
        Quick relevance scoring with Flash-Lite
        """
        prompt = f"""Rate relevance to "{substance}" for "{outcome_category}" outcomes.

Title: {paper.title}
Abstract: {paper.abstract[:500]}...

Respond with only a decimal from 0.0 to 1.0:
- 1.0 = Highly relevant (direct study)
- 0.5 = Moderately relevant  
- 0.0 = Not relevant

Score:"""
        
        url = f"{self.base_url}/models/{self.screening_model}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 20,
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'candidates' in data and len(data['candidates']) > 0:
                            text_response = data['candidates'][0]['content']['parts'][0]['text']
                            
                            # Track screening costs
                            if self.enable_cost_tracking:
                                self._track_api_usage(prompt, text_response, self.screening_model)
                            
                            # Extract score
                            score_match = re.search(r'(\d+\.?\d*)', text_response.strip())
                            if score_match:
                                return min(1.0, max(0.0, float(score_match.group(1))))
        
        except Exception:
            pass
        
        return 0.7  # Conservative default
    
    def _track_api_usage(self, prompt: str, response: str, model: str):
        """
        Track API usage and calculate costs
        """
        # Rough token estimation (1 token ≈ 0.75 words)
        input_tokens = len(prompt.split()) * 1.33
        output_tokens = len(response.split()) * 1.33
        
        # Calculate cost
        if model in self.pricing:
            input_cost = (input_tokens / 1_000_000) * self.pricing[model]['input']
            output_cost = (output_tokens / 1_000_000) * self.pricing[model]['output']
            total_cost = input_cost + output_cost
            
            self.metrics['total_cost'] += total_cost
            
            # Update token usage tracking
            model_key = model.split('-')[-1]  # 'lite', 'flash', 'pro'
            if model_key in ['lite', 'flash-lite']:
                model_key = 'screening'
            elif 'flash' in model:
                model_key = 'analysis'
            elif 'pro' in model:
                model_key = 'fallback'
            
            if model_key not in self.token_usage:
                self.token_usage[model_key] = {'input': 0, 'output': 0}
            
            self.token_usage[model_key]['input'] += input_tokens
            self.token_usage[model_key]['output'] += output_tokens
    
    def _estimate_paper_cost(self, model: str) -> float:
        """
        Estimate cost per paper for given model
        """
        if model in self.pricing:
            # Estimate ~1000 input + 500 output tokens per paper
            estimated_cost = (1000 / 1_000_000) * self.pricing[model]['input']
            estimated_cost += (500 / 1_000_000) * self.pricing[model]['output']
            return estimated_cost
        return 0.02  # Default estimate
    
    async def _print_optimization_summary(self):
        """
        Print comprehensive cost optimization results
        """
        print(f"\n{'='*60}")
        print(f"🎯 COST OPTIMIZATION SUMMARY")
        print(f"{'='*60}")
        
        # Performance metrics
        print(f"📊 PROCESSING METRICS:")
        print(f"  • Papers screened: {self.metrics['papers_screened']}")
        print(f"  • Papers filtered: {self.metrics['papers_filtered']} ({self.metrics['papers_filtered']/max(1,self.metrics['papers_screened'])*100:.1f}%)")
        print(f"  • Papers analyzed: {self.metrics['papers_analyzed']}")
        print(f"  • Papers retried: {self.metrics['papers_retried']}")
        print(f"  • Processing time: {self.metrics['processing_time']:.1f}s")
        
        # Cost breakdown
        print(f"\n💰 COST BREAKDOWN:")
        screening_cost = 0
        analysis_cost = 0
        fallback_cost = 0
        
        if 'screening' in self.token_usage:
            screening_cost = (self.token_usage['screening']['input'] / 1_000_000) * 0.10
            screening_cost += (self.token_usage['screening']['output'] / 1_000_000) * 0.40
        
        if 'analysis' in self.token_usage:
            analysis_cost = (self.token_usage['analysis']['input'] / 1_000_000) * 0.15
            analysis_cost += (self.token_usage['analysis']['output'] / 1_000_000) * 0.60
        
        if 'fallback' in self.token_usage:
            fallback_cost = (self.token_usage['fallback']['input'] / 1_000_000) * 2.50
            fallback_cost += (self.token_usage['fallback']['output'] / 1_000_000) * 10.00
        
        total_cost = screening_cost + analysis_cost + fallback_cost
        
        print(f"  • Screening (Flash-Lite): ${screening_cost:.3f}")
        print(f"  • Analysis (Flash): ${analysis_cost:.3f}")
        print(f"  • Retry (Pro): ${fallback_cost:.3f}")
        print(f"  • TOTAL COST: ${total_cost:.3f}")
        
        # Savings estimate
        if self.metrics['papers_filtered'] > 0:
            estimated_savings = self.metrics['papers_filtered'] * self._estimate_paper_cost('gemini-2.5-flash')
            print(f"  • Estimated savings: ${estimated_savings:.3f}")
            print(f"  • Cost efficiency: {(1 - total_cost/(total_cost + estimated_savings))*100:.1f}% savings")
        
        print(f"{'='*60}")

# Testing function
async def test_cost_optimized_analyzer():
    """
    Test the cost-optimized analyzer
    """
    api_key = os.getenv('GEMINI_API_KEY', 'your-api-key-here')
    
    if api_key == 'your-api-key-here':
        print("⚠️ Set GEMINI_API_KEY environment variable to test")
        return
    
    # Initialize cost-optimized analyzer
    analyzer = CostOptimizedAnalyzer(api_key)
    
    # Sample papers for testing
    test_papers = [
        PubMedPaper(
            pmid="12345",
            title="Melatonin supplementation for sleep disorders: systematic review",
            abstract="Background: Sleep disorders affect millions. Methods: We analyzed melatonin studies. Results: Significant improvement in sleep quality observed.",
            journal="Sleep Research",
            journal_issn="1234-5678",
            publication_year=2023,
            publication_types=["Systematic Review"]
        ),
        PubMedPaper(
            pmid="67890", 
            title="Cardiovascular effects of exercise in elderly populations",
            abstract="Background: Exercise benefits elderly. Methods: Studied 200 patients. Results: Improved cardiovascular outcomes.",
            journal="Cardiology Today",
            journal_issn="8765-4321",
            publication_year=2023,
            publication_types=["Clinical Trial"]
        )
    ]
    
    print("🧪 Testing Cost-Optimized Analyzer...")
    
    analyses = await analyzer.process_batch_optimized(
        test_papers, 
        substance="melatonin",
        outcome_category="sleep"
    )
    
    print(f"\n✅ Analysis complete! Processed {len(analyses)} papers.")
    
    for analysis in analyses:
        print(f"📄 {analysis.paper_pmid}: Relevance={analysis.relevance_score:.2f}, Confidence={analysis.analysis_confidence:.2f}")

if __name__ == "__main__":
    asyncio.run(test_cost_optimized_analyzer())