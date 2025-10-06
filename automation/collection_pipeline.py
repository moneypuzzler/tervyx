"""
VERA Protocol - Automated Collection Pipeline
Integrates OpenAlex, PubMed, and Crossref APIs for evidence collection
"""

import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json
import time
import logging
from dataclasses import dataclass, asdict
import xml.etree.ElementTree as ET
import re
from urllib.parse import quote_plus, urlencode
import hashlib

@dataclass
class StudyRecord:
    """Individual study record from collection pipeline"""
    study_id: str
    title: str
    authors: List[str]
    journal: str
    journal_issn: str
    publication_year: int
    doi: Optional[str]
    pmid: Optional[str]
    abstract: str
    study_type: str  # rct, meta_analysis, cohort, case_control, etc.
    sample_size: Optional[int]
    effect_size: Optional[float]
    confidence_interval: Optional[Tuple[float, float]]
    p_value: Optional[float]
    relevance_score: Optional[float]
    quality_score: Optional[float]
    data_source: str  # openalex, pubmed, crossref
    collection_date: str
    raw_metadata: Dict[str, Any]

class CollectionPipeline:
    """Automated evidence collection from multiple academic databases"""
    
    def __init__(self, cache_dir: str = "automation/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # API endpoints
        self.openalex_base = "https://api.openalex.org"
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.crossref_base = "https://api.crossref.org"
        
        # Rate limiting
        self.request_delays = {
            'openalex': 0.1,    # 10 requests/second
            'pubmed': 0.34,     # 3 requests/second for free users
            'crossref': 0.05    # 20 requests/second
        }
        
        self.last_request_time = {}
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Email for API requests (required by some APIs)
        self.email = "research@vera-protocol.org"
    
    def collect_evidence(self, search_query: str, max_results: int = 100,
                        databases: List[str] = None) -> List[StudyRecord]:
        """Collect evidence from multiple databases"""
        
        if databases is None:
            databases = ['openalex', 'pubmed', 'crossref']
        
        all_studies = []
        
        for database in databases:
            try:
                self.logger.info(f"Collecting from {database}: {search_query}")
                
                if database == 'openalex':
                    studies = self._collect_from_openalex(search_query, max_results // len(databases))
                elif database == 'pubmed':
                    studies = self._collect_from_pubmed(search_query, max_results // len(databases))
                elif database == 'crossref':
                    studies = self._collect_from_crossref(search_query, max_results // len(databases))
                else:
                    continue
                
                all_studies.extend(studies)
                self.logger.info(f"Collected {len(studies)} studies from {database}")
                
            except Exception as e:
                self.logger.error(f"Error collecting from {database}: {e}")
                continue
        
        # Deduplicate by DOI and title similarity
        deduplicated = self._deduplicate_studies(all_studies)
        
        self.logger.info(f"Total unique studies collected: {len(deduplicated)}")
        
        return deduplicated
    
    def _collect_from_openalex(self, query: str, max_results: int) -> List[StudyRecord]:
        """Collect studies from OpenAlex API"""
        studies = []
        
        # Convert search query for OpenAlex format
        openalex_query = self._convert_query_for_openalex(query)
        
        params = {
            'search': openalex_query,
            'filter': 'type:article,is_oa:true',  # Open access articles
            'per-page': min(200, max_results),
            'sort': 'cited_by_count:desc',
            'mailto': self.email
        }
        
        try:
            self._rate_limit('openalex')
            
            url = f"{self.openalex_base}/works"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            for work in data.get('results', []):
                try:
                    study = self._parse_openalex_work(work)
                    if study:
                        studies.append(study)
                        
                        if len(studies) >= max_results:
                            break
                            
                except Exception as e:
                    self.logger.warning(f"Error parsing OpenAlex work: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"OpenAlex API error: {e}")
        
        return studies
    
    def _collect_from_pubmed(self, query: str, max_results: int) -> List[StudyRecord]:
        """Collect studies from PubMed via NCBI E-utilities"""
        studies = []
        
        try:
            # Step 1: Search for PMIDs
            pmids = self._search_pubmed(query, max_results)
            
            if not pmids:
                return studies
            
            # Step 2: Fetch detailed records
            studies = self._fetch_pubmed_details(pmids)
            
        except Exception as e:
            self.logger.error(f"PubMed collection error: {e}")
        
        return studies
    
    def _search_pubmed(self, query: str, max_results: int) -> List[str]:
        """Search PubMed for PMIDs"""
        
        # Convert query for PubMed format
        pubmed_query = self._convert_query_for_pubmed(query)
        
        params = {
            'db': 'pubmed',
            'term': pubmed_query,
            'retmax': max_results,
            'retmode': 'json',
            'sort': 'relevance',
            'tool': 'vera-protocol',
            'email': self.email
        }
        
        self._rate_limit('pubmed')
        
        url = f"{self.pubmed_base}/esearch.fcgi"
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        pmids = data.get('esearchresult', {}).get('idlist', [])
        
        self.logger.info(f"Found {len(pmids)} PMIDs for query: {query}")
        
        return pmids
    
    def _fetch_pubmed_details(self, pmids: List[str]) -> List[StudyRecord]:
        """Fetch detailed records from PubMed"""
        studies = []
        
        # Process in batches of 200 (PubMed limit)
        batch_size = 200
        
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            
            params = {
                'db': 'pubmed',
                'id': ','.join(batch_pmids),
                'retmode': 'xml',
                'tool': 'vera-protocol',
                'email': self.email
            }
            
            try:
                self._rate_limit('pubmed')
                
                url = f"{self.pubmed_base}/efetch.fcgi"
                response = requests.get(url, params=params, timeout=60)
                response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(response.content)
                
                for article in root.findall('.//PubmedArticle'):
                    try:
                        study = self._parse_pubmed_article(article)
                        if study:
                            studies.append(study)
                    except Exception as e:
                        self.logger.warning(f"Error parsing PubMed article: {e}")
                        continue
            
            except Exception as e:
                self.logger.error(f"Error fetching PubMed batch: {e}")
                continue
        
        return studies
    
    def _collect_from_crossref(self, query: str, max_results: int) -> List[StudyRecord]:
        """Collect studies from Crossref API"""
        studies = []
        
        params = {
            'query': query,
            'rows': min(1000, max_results),
            'sort': 'score',
            'order': 'desc',
            'filter': 'type:journal-article',
            'mailto': self.email
        }
        
        try:
            self._rate_limit('crossref')
            
            url = f"{self.crossref_base}/works"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            for work in data.get('message', {}).get('items', []):
                try:
                    study = self._parse_crossref_work(work)
                    if study:
                        studies.append(study)
                        
                        if len(studies) >= max_results:
                            break
                            
                except Exception as e:
                    self.logger.warning(f"Error parsing Crossref work: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Crossref API error: {e}")
        
        return studies
    
    def _parse_openalex_work(self, work: Dict) -> Optional[StudyRecord]:
        """Parse OpenAlex work into StudyRecord"""
        
        try:
            # Extract basic information
            title = work.get('title', '').strip()
            if not title:
                return None
            
            # Authors
            authors = []
            for authorship in work.get('authorships', []):
                author = authorship.get('author', {})
                name = author.get('display_name', '')
                if name:
                    authors.append(name)
            
            # Journal information
            host_venue = work.get('host_venue') or {}
            journal = host_venue.get('display_name', '')
            journal_issn = None
            
            if host_venue.get('issn'):
                journal_issn = host_venue['issn'][0] if host_venue['issn'] else None
            
            # Publication year
            pub_year = work.get('publication_year')
            
            # DOI
            doi = work.get('doi')
            if doi and doi.startswith('https://doi.org/'):
                doi = doi[16:]  # Remove prefix
            
            # Abstract (often not available in OpenAlex)
            abstract = ''
            if work.get('abstract_inverted_index'):
                abstract = self._reconstruct_abstract(work['abstract_inverted_index'])
            
            # Study type (inferred from concepts and venue)
            study_type = self._infer_study_type_openalex(work)
            
            # Generate unique study ID
            study_id = self._generate_study_id('openalex', work.get('id', ''), doi, title)
            
            return StudyRecord(
                study_id=study_id,
                title=title,
                authors=authors,
                journal=journal,
                journal_issn=journal_issn,
                publication_year=pub_year or 0,
                doi=doi,
                pmid=None,  # Not available in OpenAlex
                abstract=abstract,
                study_type=study_type,
                sample_size=None,  # Would need full text analysis
                effect_size=None,   # Would need full text analysis
                confidence_interval=None,
                p_value=None,
                relevance_score=None,  # To be computed later
                quality_score=None,    # To be computed later
                data_source='openalex',
                collection_date=datetime.now().isoformat(),
                raw_metadata=work
            )
            
        except Exception as e:
            self.logger.warning(f"Error parsing OpenAlex work: {e}")
            return None
    
    def _parse_pubmed_article(self, article: ET.Element) -> Optional[StudyRecord]:
        """Parse PubMed XML article into StudyRecord"""
        
        try:
            # PMID
            pmid = article.find('.//PMID')
            pmid = pmid.text if pmid is not None else None
            
            # Title
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ''
            title = title.strip() if title else ''
            
            if not title:
                return None
            
            # Authors
            authors = []
            for author in article.findall('.//Author'):
                lastname = author.find('LastName')
                firstname = author.find('ForeName')
                
                if lastname is not None and firstname is not None:
                    authors.append(f"{firstname.text} {lastname.text}")
                elif lastname is not None:
                    authors.append(lastname.text)
            
            # Journal
            journal_elem = article.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ''
            
            # Journal ISSN
            issn_elem = article.find('.//Journal/ISSN')
            journal_issn = issn_elem.text if issn_elem is not None else None
            
            # Publication year
            year_elem = article.find('.//PubDate/Year')
            pub_year = int(year_elem.text) if year_elem is not None else 0
            
            # DOI
            doi = None
            for article_id in article.findall('.//ArticleId'):
                if article_id.get('IdType') == 'doi':
                    doi = article_id.text
                    break
            
            # Abstract
            abstract_elem = article.find('.//Abstract/AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else ''
            abstract = abstract.strip() if abstract else ''
            
            # Study type (inferred from publication types)
            study_type = self._infer_study_type_pubmed(article)
            
            # Generate study ID
            study_id = self._generate_study_id('pubmed', pmid, doi, title)
            
            return StudyRecord(
                study_id=study_id,
                title=title,
                authors=authors,
                journal=journal,
                journal_issn=journal_issn,
                publication_year=pub_year,
                doi=doi,
                pmid=pmid,
                abstract=abstract,
                study_type=study_type,
                sample_size=None,  # Would need full text analysis
                effect_size=None,   # Would need full text analysis
                confidence_interval=None,
                p_value=None,
                relevance_score=None,
                quality_score=None,
                data_source='pubmed',
                collection_date=datetime.now().isoformat(),
                raw_metadata={}  # Could store raw XML if needed
            )
            
        except Exception as e:
            self.logger.warning(f"Error parsing PubMed article: {e}")
            return None
    
    def _parse_crossref_work(self, work: Dict) -> Optional[StudyRecord]:
        """Parse Crossref work into StudyRecord"""
        
        try:
            # Title
            titles = work.get('title', [])
            title = titles[0] if titles else ''
            title = title.strip() if title else ''
            
            if not title:
                return None
            
            # Authors
            authors = []
            for author in work.get('author', []):
                given = author.get('given', '')
                family = author.get('family', '')
                if given and family:
                    authors.append(f"{given} {family}")
                elif family:
                    authors.append(family)
            
            # Journal
            journal_titles = work.get('container-title', [])
            journal = journal_titles[0] if journal_titles else ''
            
            # Journal ISSN
            issns = work.get('ISSN', [])
            journal_issn = issns[0] if issns else None
            
            # Publication year
            pub_date = work.get('published-print') or work.get('published-online')
            pub_year = 0
            if pub_date and pub_date.get('date-parts'):
                try:
                    pub_year = pub_date['date-parts'][0][0]
                except (IndexError, TypeError):
                    pub_year = 0
            
            # DOI
            doi = work.get('DOI')
            
            # Abstract (usually not available in Crossref)
            abstract = work.get('abstract', '')
            
            # Study type (inferred from type and subject)
            study_type = self._infer_study_type_crossref(work)
            
            # Generate study ID
            study_id = self._generate_study_id('crossref', work.get('URL', ''), doi, title)
            
            return StudyRecord(
                study_id=study_id,
                title=title,
                authors=authors,
                journal=journal,
                journal_issn=journal_issn,
                publication_year=pub_year,
                doi=doi,
                pmid=None,  # Not available in Crossref
                abstract=abstract,
                study_type=study_type,
                sample_size=None,
                effect_size=None,
                confidence_interval=None,
                p_value=None,
                relevance_score=None,
                quality_score=None,
                data_source='crossref',
                collection_date=datetime.now().isoformat(),
                raw_metadata=work
            )
            
        except Exception as e:
            self.logger.warning(f"Error parsing Crossref work: {e}")
            return None
    
    def _convert_query_for_openalex(self, query: str) -> str:
        """Convert VERA search query for OpenAlex format"""
        
        # Remove PubMed-specific operators
        query = re.sub(r'\[MeSH\]|\[tiab\]|\[tw\]', '', query)
        
        # Convert AND/OR operators
        query = query.replace(' AND ', ' ')
        query = query.replace(' OR ', ' | ')
        
        # Remove extra quotes and clean up
        query = re.sub(r'["\(\)]', '', query)
        query = re.sub(r'\s+', ' ', query).strip()
        
        return query
    
    def _convert_query_for_pubmed(self, query: str) -> str:
        """Convert VERA search query for PubMed format"""
        
        # Add MeSH terms and field tags for better precision
        
        # Common substance terms to enhance with MeSH
        mesh_terms = {
            'magnesium': 'magnesium[MeSH]',
            'melatonin': 'melatonin[MeSH]',
            'omega-3': 'fatty acids, omega-3[MeSH]',
            'curcumin': 'curcumin[MeSH]',
            'caffeine': 'caffeine[MeSH]',
            'creatine': 'creatine[MeSH]'
        }
        
        # Enhance query with MeSH terms
        enhanced_query = query
        for term, mesh in mesh_terms.items():
            if term in query.lower():
                enhanced_query = enhanced_query.replace(f'"{term}"', f'({mesh} OR "{term}")')
        
        # Add study type filters
        study_filters = (
            ' AND (randomized controlled trial[pt] OR '
            'controlled clinical trial[pt] OR '
            'meta-analysis[pt] OR '
            'systematic review[ti])'
        )
        
        enhanced_query += study_filters
        
        return enhanced_query
    
    def _reconstruct_abstract(self, inverted_index: Dict[str, List[int]]) -> str:
        """Reconstruct abstract from OpenAlex inverted index"""
        
        word_positions = []
        
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))
        
        # Sort by position and reconstruct
        word_positions.sort(key=lambda x: x[0])
        words = [word for pos, word in word_positions]
        
        return ' '.join(words)
    
    def _infer_study_type_openalex(self, work: Dict) -> str:
        """Infer study type from OpenAlex work"""
        
        title = work.get('title', '').lower()
        concepts = [c.get('display_name', '').lower() for c in work.get('concepts', [])]
        
        # Check for meta-analysis
        if any(term in title for term in ['meta-analysis', 'systematic review']):
            return 'meta_analysis'
        
        # Check for RCT
        if any(term in title for term in ['randomized', 'clinical trial', 'rct']):
            return 'rct'
        
        # Check concepts for study types
        if 'clinical trial' in concepts:
            return 'rct'
        elif 'meta-analysis' in concepts:
            return 'meta_analysis'
        elif 'cohort study' in concepts:
            return 'cohort'
        elif 'case-control study' in concepts:
            return 'case_control'
        
        return 'observational'
    
    def _infer_study_type_pubmed(self, article: ET.Element) -> str:
        """Infer study type from PubMed article"""
        
        # Check publication types
        pub_types = []
        for pub_type in article.findall('.//PublicationType'):
            if pub_type.text:
                pub_types.append(pub_type.text.lower())
        
        # Map publication types to study types
        if any(pt in pub_types for pt in ['randomized controlled trial', 'controlled clinical trial']):
            return 'rct'
        elif 'meta-analysis' in pub_types:
            return 'meta_analysis'
        elif 'systematic review' in pub_types:
            return 'systematic_review'
        elif 'cohort studies' in pub_types:
            return 'cohort'
        elif 'case-control studies' in pub_types:
            return 'case_control'
        
        return 'observational'
    
    def _infer_study_type_crossref(self, work: Dict) -> str:
        """Infer study type from Crossref work"""
        
        title = work.get('title', [''])[0].lower()
        
        # Simple title-based inference
        if any(term in title for term in ['meta-analysis', 'meta analysis']):
            return 'meta_analysis'
        elif any(term in title for term in ['systematic review']):
            return 'systematic_review'
        elif any(term in title for term in ['randomized', 'clinical trial', 'rct']):
            return 'rct'
        elif 'cohort' in title:
            return 'cohort'
        elif 'case-control' in title or 'case control' in title:
            return 'case_control'
        
        return 'observational'
    
    def _generate_study_id(self, source: str, source_id: str, doi: str, title: str) -> str:
        """Generate unique study ID"""
        
        # Use DOI if available, otherwise use source ID + title hash
        if doi:
            id_string = f"{source}_{doi}"
        else:
            title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
            id_string = f"{source}_{source_id}_{title_hash}"
        
        # Clean up for filename safety
        study_id = re.sub(r'[^a-zA-Z0-9_-]', '_', id_string)
        
        return study_id
    
    def _deduplicate_studies(self, studies: List[StudyRecord]) -> List[StudyRecord]:
        """Deduplicate studies by DOI and title similarity"""
        
        unique_studies = []
        seen_dois = set()
        seen_titles = set()
        
        for study in studies:
            
            # Skip if DOI already seen
            if study.doi and study.doi in seen_dois:
                continue
            
            # Skip if very similar title already seen
            title_normalized = re.sub(r'[^a-zA-Z0-9\s]', '', study.title.lower())
            title_normalized = re.sub(r'\s+', ' ', title_normalized).strip()
            
            if title_normalized in seen_titles:
                continue
            
            # Add to unique list
            unique_studies.append(study)
            
            if study.doi:
                seen_dois.add(study.doi)
            
            seen_titles.add(title_normalized)
        
        return unique_studies
    
    def _rate_limit(self, api: str):
        """Enforce rate limiting for API requests"""
        
        delay = self.request_delays.get(api, 0.1)
        last_time = self.last_request_time.get(api, 0)
        
        time_since_last = time.time() - last_time
        
        if time_since_last < delay:
            time.sleep(delay - time_since_last)
        
        self.last_request_time[api] = time.time()
    
    def save_collection_results(self, studies: List[StudyRecord], output_file: str):
        """Save collection results to file"""
        
        # Convert to DataFrame
        study_dicts = [asdict(study) for study in studies]
        df = pd.DataFrame(study_dicts)
        
        # Save based on file extension
        if output_file.endswith('.csv'):
            df.to_csv(output_file, index=False)
        elif output_file.endswith('.json'):
            df.to_json(output_file, orient='records', indent=2)
        elif output_file.endswith('.parquet'):
            df.to_parquet(output_file, index=False)
        else:
            # Default to JSON
            df.to_json(output_file, orient='records', indent=2)
        
        self.logger.info(f"Saved {len(studies)} studies to {output_file}")


if __name__ == "__main__":
    # Example usage
    pipeline = CollectionPipeline()
    
    # Test query
    test_query = '"magnesium glycinate" AND "sleep quality" AND (randomized controlled trial OR clinical trial)'
    
    print(f"Collecting evidence for: {test_query}")
    
    studies = pipeline.collect_evidence(test_query, max_results=50)
    
    print(f"\nCollected {len(studies)} unique studies")
    
    # Show sample results
    for i, study in enumerate(studies[:3]):
        print(f"\n{i+1}. {study.title}")
        print(f"   Authors: {', '.join(study.authors[:3])}{'...' if len(study.authors) > 3 else ''}")
        print(f"   Journal: {study.journal} ({study.publication_year})")
        print(f"   DOI: {study.doi}")
        print(f"   Source: {study.data_source}")
        print(f"   Type: {study.study_type}")
    
    # Save results
    pipeline.save_collection_results(studies, "automation/cache/sample_collection.json")