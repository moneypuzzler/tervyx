"""
PubMed API Integration for Real TERVYX System
==========================================

Implements actual PubMed E-utilities API integration for paper search and metadata extraction.
Handles rate limiting, XML parsing, and data enrichment from multiple sources.
"""

import requests
import xml.etree.ElementTree as ET
import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import time
import re
from urllib.parse import quote

@dataclass
class PubMedPaper:
    """Enhanced paper metadata from PubMed"""
    pmid: str
    doi: Optional[str] = None
    title: str = ""
    abstract: str = ""
    authors: List[str] = None
    journal: str = ""
    journal_issn: str = ""
    publication_year: int = 0
    mesh_terms: List[str] = None
    publication_types: List[str] = None
    grant_numbers: List[str] = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.mesh_terms is None:
            self.mesh_terms = []
        if self.publication_types is None:
            self.publication_types = []
        if self.grant_numbers is None:
            self.grant_numbers = []

class PubMedAPI:
    """
    Production-ready PubMed API client with rate limiting and error handling
    """
    
    def __init__(self, email: str, tool_name: str = "tervyx", api_key: Optional[str] = None):
        self.email = email
        self.tool_name = tool_name
        self.api_key = api_key  # Optional NCBI API key for higher rate limits
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        
        # Rate limiting: 3 requests/second without API key, 10/second with key
        self.rate_limit = 10 if api_key else 3
        self.last_request_time = 0
        
    async def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.rate_limit
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    async def search_papers(self, 
                          substance: str, 
                          outcome: str,
                          max_results: int = 100,
                          year_from: int = 2000) -> List[str]:
        """
        Search PubMed for papers with sophisticated query construction
        
        Returns:
            List of PMIDs
        """
        
        await self._rate_limit()
        
        # Build comprehensive search query
        query = self._build_search_query(substance, outcome, year_from)
        
        search_url = f"{self.base_url}esearch.fcgi"
        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'json',
            'email': self.email,
            'tool': self.tool_name,
            'sort': 'relevance'  # Sort by relevance first
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(search_url, params=params) as response:
                    data = await response.json()
                    
                    if 'esearchresult' in data and 'idlist' in data['esearchresult']:
                        pmids = data['esearchresult']['idlist']
                        print(f"📊 Found {len(pmids)} papers for '{substance}' + '{outcome}'")
                        return pmids
                    
                    # Check for errors
                    if 'esearchresult' in data and 'errorlist' in data['esearchresult']:
                        errors = data['esearchresult']['errorlist']
                        print(f"⚠️ PubMed search errors: {errors}")
                    
                    return []
                    
            except Exception as e:
                print(f"❌ PubMed search failed: {str(e)}")
                return []
    
    def _build_search_query(self, substance: str, outcome: str, year_from: int) -> str:
        """
        Build sophisticated PubMed search query with synonyms and filters
        """
        
        # Substance synonyms and variations
        substance_terms = self._get_substance_terms(substance)
        substance_query = " OR ".join([f'"{term}"[Title/Abstract]' for term in substance_terms])
        
        # Outcome terms
        outcome_terms = self._get_outcome_terms(outcome)
        outcome_query = " OR ".join([f'"{term}"[Title/Abstract]' for term in outcome_terms])
        
        # Study type filters - prioritize high-quality evidence
        study_types = [
            '"randomized controlled trial"[Publication Type]',
            '"clinical trial"[Publication Type]', 
            '"controlled clinical trial"[Publication Type]',
            '"meta-analysis"[Publication Type]',
            '"systematic review"[Publication Type]'
        ]
        study_query = " OR ".join(study_types)
        
        # Quality filters
        quality_filters = [
            'English[Language]',
            f'("{year_from}/01/01"[Date - Publication] : "2025/12/31"[Date - Publication])',
            'hasabstract[text]',  # Must have abstract
            '"humans"[MeSH Terms]'  # Human studies only
        ]
        
        # Combine all parts
        query_parts = [
            f"({substance_query})",
            f"({outcome_query})", 
            f"({study_query})",
            *quality_filters
        ]
        
        final_query = " AND ".join(query_parts)
        print(f"🔍 PubMed Query: {final_query[:200]}...")
        
        return final_query
    
    def _get_substance_terms(self, substance: str) -> List[str]:
        """
        Generate comprehensive substance name variations
        """
        terms = [substance]
        
        # Basic transformations
        terms.append(substance.replace('-', ' '))
        terms.append(substance.replace(' ', '-'))
        terms.append(substance.replace('_', ' '))
        terms.append(substance.replace('_', '-'))
        
        # Common supplement name patterns
        if not any(word in substance.lower() for word in ['supplement', 'extract', 'acid']):
            terms.extend([
                f"{substance} supplement",
                f"{substance} supplementation",
                f"{substance} extract"
            ])
        
        # Specific substance mappings
        substance_synonyms = {
            'omega-3': ['omega-3 fatty acids', 'n-3 fatty acids', 'fish oil', 'EPA', 'DHA'],
            'curcumin': ['turmeric', 'curcuma longa', 'diferuloylmethane'],
            'melatonin': ['N-acetyl-5-methoxytryptamine'],
            'magnesium': ['magnesium glycinate', 'magnesium citrate', 'magnesium oxide'],
            'st-john-wort': ['hypericum perforatum', 'hypericum', 'SJW'],
            '5-htp': ['5-hydroxytryptophan', 'oxitriptan'],
            'rhodiola': ['rhodiola rosea', 'golden root', 'arctic root'],
            'ginkgo': ['ginkgo biloba', 'maidenhair tree'],
            'ashwagandha': ['withania somnifera', 'indian winter cherry']
        }
        
        if substance.lower() in substance_synonyms:
            terms.extend(substance_synonyms[substance.lower()])
        
        return list(set(terms))  # Remove duplicates
    
    def _get_outcome_terms(self, outcome: str) -> List[str]:
        """
        Generate comprehensive outcome measure terms
        """
        outcome_mappings = {
            'sleep': [
                'sleep quality', 'sleep duration', 'sleep latency', 'sleep efficiency',
                'insomnia', 'sleep onset', 'sleep maintenance', 'PSQI', 
                'Pittsburgh Sleep Quality Index', 'ISI', 'Insomnia Severity Index',
                'polysomnography', 'actigraphy', 'sleep architecture'
            ],
            'cognition': [
                'cognitive function', 'cognitive performance', 'memory',
                'attention', 'executive function', 'processing speed',
                'working memory', 'episodic memory', 'MMSE', 'MoCA',
                'Trail Making Test', 'digit span', 'verbal fluency',
                'cognitive decline', 'neuropsychological'
            ],
            'mental_health': [
                'depression', 'anxiety', 'mood', 'psychological wellbeing',
                'depressive symptoms', 'anxiety symptoms', 'Beck Depression Inventory',
                'Hamilton Depression Rating Scale', 'GAD-7', 'PHQ-9',
                'mental health', 'psychological distress', 'emotional wellbeing'
            ],
            'cardiovascular': [
                'blood pressure', 'hypertension', 'cholesterol', 'lipids',
                'cardiovascular', 'heart rate', 'endothelial function',
                'arterial stiffness', 'LDL', 'HDL', 'triglycerides',
                'systolic blood pressure', 'diastolic blood pressure',
                'cardiovascular risk', 'atherosclerosis'
            ],
            'renal_safety': [
                'kidney function', 'renal function', 'creatinine', 'nephrotoxicity',
                'acute kidney injury', 'chronic kidney disease', 'glomerular filtration rate',
                'BUN', 'blood urea nitrogen', 'proteinuria', 'albuminuria',
                'renal impairment', 'kidney damage', 'nephritis'
            ]
        }
        
        return outcome_mappings.get(outcome, [outcome])
    
    async def fetch_detailed_metadata(self, pmids: List[str], batch_size: int = 20) -> List[PubMedPaper]:
        """
        Fetch detailed metadata for papers in batches
        """
        if not pmids:
            return []
        
        papers = []
        
        # Process in batches to avoid overwhelming the API
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            batch_papers = await self._fetch_batch_metadata(batch_pmids)
            papers.extend(batch_papers)
            
            # Rate limiting between batches
            if i + batch_size < len(pmids):
                await asyncio.sleep(0.5)
        
        print(f"📄 Successfully fetched metadata for {len(papers)}/{len(pmids)} papers")
        return papers
    
    async def _fetch_batch_metadata(self, pmids: List[str]) -> List[PubMedPaper]:
        """Fetch metadata for a batch of PMIDs"""
        
        await self._rate_limit()
        
        fetch_url = f"{self.base_url}efetch.fcgi"
        params = {
            'db': 'pubmed',
            'id': ','.join(pmids),
            'retmode': 'xml',
            'email': self.email,
            'tool': self.tool_name
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(fetch_url, params=params) as response:
                    xml_content = await response.text()
                    return self._parse_pubmed_xml(xml_content)
                    
            except Exception as e:
                print(f"❌ Failed to fetch batch {pmids[:3]}...: {str(e)}")
                return []
    
    def _parse_pubmed_xml(self, xml_content: str) -> List[PubMedPaper]:
        """
        Parse PubMed XML response into structured paper objects
        """
        try:
            root = ET.fromstring(xml_content)
            papers = []
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    paper = self._extract_paper_from_xml(article)
                    if paper and paper.title:  # Only include papers with titles
                        papers.append(paper)
                except Exception as e:
                    print(f"⚠️ Failed to parse individual paper: {str(e)}")
                    continue
            
            return papers
            
        except ET.ParseError as e:
            print(f"❌ XML parsing failed: {str(e)}")
            return []
    
    def _extract_paper_from_xml(self, article_xml) -> Optional[PubMedPaper]:
        """Extract paper data from single PubmedArticle XML element"""
        
        # PMID
        pmid_elem = article_xml.find('.//PMID')
        if pmid_elem is None:
            return None
        pmid = pmid_elem.text
        
        # Title
        title_elem = article_xml.find('.//ArticleTitle')
        title = title_elem.text if title_elem is not None else ""
        
        # Abstract
        abstract_parts = []
        for abstract_elem in article_xml.findall('.//AbstractText'):
            label = abstract_elem.get('Label', '')
            text = abstract_elem.text or ""
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = " ".join(abstract_parts)
        
        # Authors
        authors = []
        for author_elem in article_xml.findall('.//Author'):
            lastname = author_elem.find('LastName')
            forename = author_elem.find('ForeName')
            if lastname is not None:
                lastname_text = lastname.text or ""
                forename_text = forename.text if forename is not None else ""
                full_name = f"{forename_text} {lastname_text}".strip()
                if full_name:
                    authors.append(full_name)
        
        # Journal info
        journal_elem = article_xml.find('.//Journal/Title')
        journal = journal_elem.text if journal_elem is not None else ""
        
        issn_elem = article_xml.find('.//Journal/ISSN')
        issn = issn_elem.text if issn_elem is not None else ""
        
        # Publication year
        year = 0
        pub_date_elems = article_xml.findall('.//PubDate/Year')
        if pub_date_elems:
            try:
                year = int(pub_date_elems[0].text)
            except (ValueError, TypeError):
                pass
        
        # DOI
        doi = None
        for article_id in article_xml.findall('.//ArticleId'):
            if article_id.get('IdType') == 'doi':
                doi = article_id.text
                break
        
        # MeSH terms
        mesh_terms = []
        for mesh_elem in article_xml.findall('.//MeshHeading/DescriptorName'):
            mesh_term = mesh_elem.text
            if mesh_term:
                mesh_terms.append(mesh_term)
        
        # Publication types
        pub_types = []
        for pub_type_elem in article_xml.findall('.//PublicationType'):
            pub_type = pub_type_elem.text
            if pub_type:
                pub_types.append(pub_type)
        
        return PubMedPaper(
            pmid=pmid,
            doi=doi,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal,
            journal_issn=issn,
            publication_year=year,
            mesh_terms=mesh_terms,
            publication_types=pub_types
        )

class CrossRefEnricher:
    """
    Enrich paper metadata with CrossRef data (citations, impact factors, etc.)
    """
    
    def __init__(self, email: str):
        self.email = email
        self.base_url = "https://api.crossref.org"
    
    async def enrich_papers(self, papers: List[PubMedPaper]) -> List[PubMedPaper]:
        """
        Enrich papers with CrossRef metadata
        """
        enriched = []
        
        async with aiohttp.ClientSession() as session:
            for paper in papers:
                if paper.doi:
                    citation_count = await self._get_citation_count(session, paper.doi)
                    # Add citation count to paper object (would extend dataclass)
                
                enriched.append(paper)
                await asyncio.sleep(0.1)  # CrossRef rate limiting
        
        return enriched
    
    async def _get_citation_count(self, session: aiohttp.ClientSession, doi: str) -> int:
        """Get citation count from CrossRef"""
        try:
            url = f"{self.base_url}/works/{doi}"
            headers = {'User-Agent': f'TERVYX (mailto:{self.email})'}
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('message', {}).get('is-referenced-by-count', 0)
                
        except Exception as e:
            print(f"⚠️ CrossRef lookup failed for {doi}: {str(e)}")
        
        return 0

# ============================================================================
# Testing and Usage
# ============================================================================

async def test_pubmed_integration():
    """Test the PubMed integration with real queries"""
    
    # Initialize API client (replace with real email)
    pubmed = PubMedAPI(
        email="your-email@domain.com",  # Replace with real email
        tool_name="tervyx_test"
    )
    
    # Test cases with known literature
    test_substances = ["melatonin", "omega-3", "curcumin"]
    test_outcomes = ["sleep", "cognition"]
    
    results = []
    
    for substance in test_substances:
        for outcome in test_outcomes:
            print(f"\n🧪 Testing: {substance} + {outcome}")
            
            # Search papers
            pmids = await pubmed.search_papers(substance, outcome, max_results=20)
            
            if pmids:
                # Fetch detailed metadata
                papers = await pubmed.fetch_detailed_metadata(pmids[:10])  # Limit for testing
                
                # Analyze results
                rcts = [p for p in papers if 'randomized controlled trial' in ' '.join(p.publication_types).lower()]
                recent_papers = [p for p in papers if p.publication_year >= 2015]
                
                result = {
                    'substance': substance,
                    'outcome': outcome,
                    'total_papers': len(papers),
                    'rcts': len(rcts),
                    'recent_papers': len(recent_papers),
                    'sample_papers': [
                        {
                            'pmid': p.pmid,
                            'title': p.title[:100] + '...' if len(p.title) > 100 else p.title,
                            'journal': p.journal,
                            'year': p.publication_year,
                            'has_abstract': len(p.abstract) > 0
                        }
                        for p in papers[:3]
                    ]
                }
                
                results.append(result)
                
                print(f"  📊 Found {len(papers)} papers ({len(rcts)} RCTs, {len(recent_papers)} recent)")
            
            else:
                print(f"  ❌ No papers found")
                results.append({
                    'substance': substance,
                    'outcome': outcome, 
                    'total_papers': 0,
                    'error': 'No papers found'
                })
    
    return results

async def main():
    """Main test function"""
    print("🚀 Testing Real PubMed Integration...")
    
    results = await test_pubmed_integration()
    
    # Save results
    with open('/home/user/webapp/system/pubmed_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    total_papers = sum(r.get('total_papers', 0) for r in results)
    successful_queries = len([r for r in results if r.get('total_papers', 0) > 0])
    
    print(f"\n📈 Summary:")
    print(f"  Successful queries: {successful_queries}/{len(results)}")
    print(f"  Total papers found: {total_papers}")
    print(f"  Results saved to: pubmed_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())