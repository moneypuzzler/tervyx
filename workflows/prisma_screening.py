"""
VERA Protocol - PRISMA-Compliant Screening Workflows
Implements systematic review screening following PRISMA 2020 guidelines
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import re

class ScreeningDecision(Enum):
    """Screening decision options following PRISMA guidelines"""
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"
    DEFER = "defer"  # For full-text review

class ExclusionReason(Enum):
    """Standardized exclusion reasons for PRISMA reporting"""
    WRONG_POPULATION = "wrong_population"
    WRONG_INTERVENTION = "wrong_intervention" 
    WRONG_COMPARATOR = "wrong_comparator"
    WRONG_OUTCOME = "wrong_outcome"
    WRONG_STUDY_DESIGN = "wrong_study_design"
    DUPLICATE = "duplicate"
    LANGUAGE = "language"
    ABSTRACT_ONLY = "abstract_only"
    INSUFFICIENT_DATA = "insufficient_data"
    FULL_TEXT_UNAVAILABLE = "full_text_unavailable"
    ONGOING_STUDY = "ongoing_study"
    RETRACTED = "retracted"
    PREDATORY_JOURNAL = "predatory_journal"
    QUALITY_CONCERNS = "quality_concerns"
    OTHER = "other"

@dataclass
class ScreeningRecord:
    """Individual screening record for PRISMA workflow"""
    study_id: str
    record_id: str  # Original database record ID
    title: str
    authors: List[str]
    journal: str
    publication_year: int
    abstract: str
    doi: Optional[str]
    pmid: Optional[str]
    
    # Screening results
    title_screening: Optional[ScreeningDecision] = None
    title_exclusion_reason: Optional[ExclusionReason] = None
    abstract_screening: Optional[ScreeningDecision] = None
    abstract_exclusion_reason: Optional[ExclusionReason] = None
    full_text_screening: Optional[ScreeningDecision] = None
    full_text_exclusion_reason: Optional[ExclusionReason] = None
    
    # Reviewer information
    title_reviewer: Optional[str] = None
    abstract_reviewer: Optional[str] = None
    full_text_reviewer: Optional[str] = None
    
    # Screening metadata
    screening_date: Optional[str] = None
    screening_notes: str = ""
    conflicts_resolved: bool = False
    final_decision: Optional[ScreeningDecision] = None
    
    # Relevance scores
    relevance_score: Optional[float] = None
    confidence_score: Optional[float] = None
    
    # PICO extraction
    population: str = ""
    intervention: str = ""
    comparator: str = ""
    outcomes: List[str] = None
    
    def __post_init__(self):
        if self.outcomes is None:
            self.outcomes = []

@dataclass
class PRISMAFlowDiagram:
    """PRISMA 2020 flow diagram data"""
    # Identification
    records_identified_database: int = 0
    records_identified_registers: int = 0
    records_removed_duplicate: int = 0
    records_screened: int = 0
    
    # Screening
    records_excluded: int = 0
    reports_sought_retrieval: int = 0
    reports_not_retrieved: int = 0
    reports_assessed_eligibility: int = 0
    reports_excluded_reasons: Dict[str, int] = None
    
    # Included
    studies_included_synthesis: int = 0
    reports_included_synthesis: int = 0
    
    # Exclusion reasons breakdown
    exclusion_breakdown: Dict[str, int] = None
    
    def __post_init__(self):
        if self.reports_excluded_reasons is None:
            self.reports_excluded_reasons = {}
        if self.exclusion_breakdown is None:
            self.exclusion_breakdown = {}

class PRISMAWorkflow:
    """PRISMA-compliant systematic review screening workflow"""
    
    def __init__(self, review_id: str, workflow_path: str = "workflows"):
        self.review_id = review_id
        self.workflow_path = Path(workflow_path)
        self.workflow_path.mkdir(exist_ok=True)
        
        # File paths
        self.records_file = self.workflow_path / f"{review_id}_screening_records.csv"
        self.flow_file = self.workflow_path / f"{review_id}_prisma_flow.json"
        self.metadata_file = self.workflow_path / f"{review_id}_metadata.json"
        self.conflicts_file = self.workflow_path / f"{review_id}_conflicts.json"
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load or initialize data
        self.records = self._load_records()
        self.flow_data = self._load_flow_data()
        self.metadata = self._load_metadata()
        
        # Screening criteria (PICO framework)
        self.inclusion_criteria = {}
        self.exclusion_criteria = {}
        
    def initialize_review(self, title: str, research_question: str, 
                         inclusion_criteria: Dict[str, List[str]],
                         exclusion_criteria: Dict[str, List[str]]):
        """Initialize systematic review with PICO criteria"""
        
        self.metadata = {
            'review_id': self.review_id,
            'title': title,
            'research_question': research_question,
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'inclusion_criteria': inclusion_criteria,
            'exclusion_criteria': exclusion_criteria,
            'reviewers': [],
            'screening_stage': 'title_abstract',  # title_abstract, full_text, completed
            'protocol_registered': False,
            'prospero_id': None
        }
        
        self.inclusion_criteria = inclusion_criteria
        self.exclusion_criteria = exclusion_criteria
        
        self._save_metadata()
        
        self.logger.info(f"Initialized PRISMA review: {title}")
    
    def import_search_results(self, search_results: List[Dict], database_name: str):
        """Import search results from database APIs"""
        
        imported_records = []
        
        for result in search_results:
            # Convert to screening record
            record = ScreeningRecord(
                study_id=self._generate_study_id(result),
                record_id=result.get('record_id', ''),
                title=result.get('title', '').strip(),
                authors=result.get('authors', []),
                journal=result.get('journal', ''),
                publication_year=result.get('publication_year', 0),
                abstract=result.get('abstract', '').strip(),
                doi=result.get('doi'),
                pmid=result.get('pmid'),
                relevance_score=result.get('relevance_score'),
                confidence_score=result.get('confidence_score')
            )
            
            imported_records.append(record)
        
        # Add to records list
        self.records.extend(imported_records)
        
        # Update flow data
        self.flow_data.records_identified_database += len(imported_records)
        
        # Save updates
        self._save_records()
        self._save_flow_data()
        
        self.logger.info(f"Imported {len(imported_records)} records from {database_name}")
    
    def remove_duplicates(self, similarity_threshold: float = 0.85) -> int:
        """Remove duplicate records using title and DOI similarity"""
        
        original_count = len(self.records)
        
        # Track duplicates
        seen_dois = set()
        seen_titles = set()
        duplicate_indices = set()
        
        for i, record in enumerate(self.records):
            
            # Check DOI duplicates
            if record.doi:
                normalized_doi = record.doi.lower().strip()
                if normalized_doi in seen_dois:
                    duplicate_indices.add(i)
                    continue
                seen_dois.add(normalized_doi)
            
            # Check title similarity
            normalized_title = self._normalize_title(record.title)
            
            if normalized_title:
                is_duplicate = False
                
                for seen_title in seen_titles:
                    similarity = self._title_similarity(normalized_title, seen_title)
                    if similarity >= similarity_threshold:
                        duplicate_indices.add(i)
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    seen_titles.add(normalized_title)
        
        # Remove duplicates
        self.records = [record for i, record in enumerate(self.records) 
                      if i not in duplicate_indices]
        
        duplicates_removed = original_count - len(self.records)
        
        # Update flow data
        self.flow_data.records_removed_duplicate = duplicates_removed
        self.flow_data.records_screened = len(self.records)
        
        self._save_records()
        self._save_flow_data()
        
        self.logger.info(f"Removed {duplicates_removed} duplicate records")
        
        return duplicates_removed
    
    def title_abstract_screening(self, batch_size: int = 50, 
                               reviewer_id: str = "auto") -> List[ScreeningRecord]:
        """Perform title and abstract screening"""
        
        # Get unscreened records
        unscreened = [r for r in self.records 
                     if r.title_screening is None and r.abstract_screening is None]
        
        if not unscreened:
            self.logger.info("No records pending title/abstract screening")
            return []
        
        # Get batch
        batch = unscreened[:batch_size]
        
        for record in batch:
            # Perform automated screening based on PICO criteria
            decision, reason = self._automated_title_abstract_screen(record)
            
            record.title_screening = decision
            record.abstract_screening = decision
            
            if decision == ScreeningDecision.EXCLUDE:
                record.title_exclusion_reason = reason
                record.abstract_exclusion_reason = reason
            
            record.title_reviewer = reviewer_id
            record.abstract_reviewer = reviewer_id
            record.screening_date = datetime.now().isoformat()
        
        # Update counts
        self._update_screening_counts()
        
        # Save updates
        self._save_records()
        self._save_flow_data()
        
        self.logger.info(f"Screened {len(batch)} records at title/abstract level")
        
        return batch
    
    def _automated_title_abstract_screen(self, record: ScreeningRecord) -> Tuple[ScreeningDecision, Optional[ExclusionReason]]:
        """Automated title/abstract screening using PICO criteria"""
        
        text_to_screen = f"{record.title} {record.abstract}".lower()
        
        # Check basic quality indicators first
        if not record.title.strip():
            return ScreeningDecision.EXCLUDE, ExclusionReason.INSUFFICIENT_DATA
        
        if record.publication_year < 1990:  # Very old studies
            return ScreeningDecision.EXCLUDE, ExclusionReason.OTHER
        
        # Check for retracted or predatory journals
        if 'retracted' in text_to_screen or 'retraction' in text_to_screen:
            return ScreeningDecision.EXCLUDE, ExclusionReason.RETRACTED
        
        # Check intervention criteria
        intervention_match = self._check_intervention_criteria(text_to_screen)
        if not intervention_match:
            return ScreeningDecision.EXCLUDE, ExclusionReason.WRONG_INTERVENTION
        
        # Check outcome criteria  
        outcome_match = self._check_outcome_criteria(text_to_screen)
        if not outcome_match:
            return ScreeningDecision.EXCLUDE, ExclusionReason.WRONG_OUTCOME
        
        # Check study design criteria
        design_match = self._check_study_design_criteria(text_to_screen)
        if not design_match:
            return ScreeningDecision.EXCLUDE, ExclusionReason.WRONG_STUDY_DESIGN
        
        # Check population criteria (less strict at title/abstract stage)
        population_match = self._check_population_criteria(text_to_screen)
        
        # If high relevance score, include
        if record.relevance_score and record.relevance_score > 0.7:
            return ScreeningDecision.INCLUDE, None
        
        # If medium relevance or uncertain criteria matches, defer to full text
        if (record.relevance_score and record.relevance_score > 0.4) or not population_match:
            return ScreeningDecision.DEFER, None
        
        # Default to inclusion for borderline cases (conservative approach)
        return ScreeningDecision.INCLUDE, None
    
    def _check_intervention_criteria(self, text: str) -> bool:
        """Check if text matches intervention criteria"""
        
        if 'intervention' not in self.inclusion_criteria:
            return True  # No specific criteria
        
        interventions = self.inclusion_criteria['intervention']
        
        return any(intervention.lower() in text for intervention in interventions)
    
    def _check_outcome_criteria(self, text: str) -> bool:
        """Check if text matches outcome criteria"""
        
        if 'outcome' not in self.inclusion_criteria:
            return True
        
        outcomes = self.inclusion_criteria['outcome']
        
        return any(outcome.lower() in text for outcome in outcomes)
    
    def _check_study_design_criteria(self, text: str) -> bool:
        """Check if text matches study design criteria"""
        
        if 'study_design' not in self.inclusion_criteria:
            return True
        
        designs = self.inclusion_criteria['study_design']
        
        # Check for excluded designs first
        if 'study_design' in self.exclusion_criteria:
            excluded_designs = self.exclusion_criteria['study_design']
            if any(design.lower() in text for design in excluded_designs):
                return False
        
        # Check for included designs
        return any(design.lower() in text for design in designs)
    
    def _check_population_criteria(self, text: str) -> bool:
        """Check if text matches population criteria"""
        
        if 'population' not in self.inclusion_criteria:
            return True
        
        populations = self.inclusion_criteria['population']
        
        return any(population.lower() in text for population in populations)
    
    def full_text_screening(self, study_ids: List[str], 
                           reviewer_id: str = "manual") -> List[ScreeningRecord]:
        """Perform full text screening for deferred records"""
        
        # Get records that need full text screening
        full_text_candidates = [
            r for r in self.records 
            if r.study_id in study_ids and 
            (r.abstract_screening == ScreeningDecision.DEFER or 
             r.abstract_screening == ScreeningDecision.UNCERTAIN)
        ]
        
        screened_records = []
        
        for record in full_text_candidates:
            # This would typically involve manual review
            # For now, we'll implement basic automated rules
            
            decision, reason = self._automated_full_text_screen(record)
            
            record.full_text_screening = decision
            if decision == ScreeningDecision.EXCLUDE:
                record.full_text_exclusion_reason = reason
            
            record.full_text_reviewer = reviewer_id
            record.final_decision = decision
            
            screened_records.append(record)
        
        self._update_screening_counts()
        self._save_records()
        self._save_flow_data()
        
        self.logger.info(f"Completed full-text screening for {len(screened_records)} records")
        
        return screened_records
    
    def _automated_full_text_screen(self, record: ScreeningRecord) -> Tuple[ScreeningDecision, Optional[ExclusionReason]]:
        """Automated full-text screening (simplified)"""
        
        # For demonstration - in reality this would involve full PDF analysis
        
        # High relevance scores pass
        if record.relevance_score and record.relevance_score > 0.6:
            return ScreeningDecision.INCLUDE, None
        
        # Check for specific exclusion criteria
        text = f"{record.title} {record.abstract}".lower()
        
        # Check for insufficient data
        if len(record.abstract) < 100:  # Very short abstract
            return ScreeningDecision.EXCLUDE, ExclusionReason.INSUFFICIENT_DATA
        
        # Check for wrong study design (more detailed at full text stage)
        if any(term in text for term in ['case report', 'editorial', 'letter', 'commentary']):
            return ScreeningDecision.EXCLUDE, ExclusionReason.WRONG_STUDY_DESIGN
        
        # Default to inclusion if criteria are met
        return ScreeningDecision.INCLUDE, None
    
    def _update_screening_counts(self):
        """Update PRISMA flow diagram counts"""
        
        # Title/abstract screening counts
        excluded_records = [r for r in self.records 
                          if r.abstract_screening == ScreeningDecision.EXCLUDE]
        
        self.flow_data.records_excluded = len(excluded_records)
        
        # Full text screening counts
        full_text_records = [r for r in self.records 
                           if r.full_text_screening is not None]
        
        self.flow_data.reports_assessed_eligibility = len(full_text_records)
        
        # Final inclusions
        included_records = [r for r in self.records 
                          if r.final_decision == ScreeningDecision.INCLUDE]
        
        self.flow_data.studies_included_synthesis = len(included_records)
        
        # Update exclusion reasons
        exclusion_counts = {}
        for record in self.records:
            if record.abstract_exclusion_reason:
                reason = record.abstract_exclusion_reason.value
                exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
            
            if record.full_text_exclusion_reason:
                reason = record.full_text_exclusion_reason.value
                exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
        
        self.flow_data.exclusion_breakdown = exclusion_counts
    
    def generate_prisma_flow_diagram(self) -> Dict[str, Any]:
        """Generate PRISMA 2020 flow diagram data"""
        
        self._update_screening_counts()
        
        flow_dict = asdict(self.flow_data)
        flow_dict['generated_at'] = datetime.now().isoformat()
        flow_dict['review_id'] = self.review_id
        
        return flow_dict
    
    def export_screening_results(self, output_format: str = 'csv') -> str:
        """Export screening results in various formats"""
        
        # Convert records to DataFrame
        records_data = []
        for record in self.records:
            record_dict = asdict(record)
            # Convert enums to strings
            for key, value in record_dict.items():
                if isinstance(value, Enum):
                    record_dict[key] = value.value
            records_data.append(record_dict)
        
        df = pd.DataFrame(records_data)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format.lower() == 'csv':
            output_file = self.workflow_path / f"{self.review_id}_screening_results_{timestamp}.csv"
            df.to_csv(output_file, index=False)
        
        elif output_format.lower() == 'excel':
            output_file = self.workflow_path / f"{self.review_id}_screening_results_{timestamp}.xlsx"
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Screening Results', index=False)
                
                # Add PRISMA flow data
                flow_df = pd.DataFrame([self.generate_prisma_flow_diagram()])
                flow_df.to_excel(writer, sheet_name='PRISMA Flow', index=False)
        
        else:  # JSON
            output_file = self.workflow_path / f"{self.review_id}_screening_results_{timestamp}.json"
            df.to_json(output_file, orient='records', indent=2)
        
        self.logger.info(f"Exported screening results to {output_file}")
        
        return str(output_file)
    
    def get_screening_statistics(self) -> Dict[str, Any]:
        """Get comprehensive screening statistics"""
        
        total_records = len(self.records)
        
        if total_records == 0:
            return {'total_records': 0}
        
        # Count by screening stage
        title_screened = len([r for r in self.records if r.title_screening is not None])
        abstract_screened = len([r for r in self.records if r.abstract_screening is not None])
        full_text_screened = len([r for r in self.records if r.full_text_screening is not None])
        
        # Count by decision
        included = len([r for r in self.records if r.final_decision == ScreeningDecision.INCLUDE])
        excluded = len([r for r in self.records if r.final_decision == ScreeningDecision.EXCLUDE])
        pending = total_records - included - excluded
        
        # Exclusion reasons
        exclusion_reasons = {}
        for record in self.records:
            if record.final_decision == ScreeningDecision.EXCLUDE:
                reason = (record.full_text_exclusion_reason or 
                         record.abstract_exclusion_reason or 
                         record.title_exclusion_reason)
                if reason:
                    exclusion_reasons[reason.value] = exclusion_reasons.get(reason.value, 0) + 1
        
        stats = {
            'total_records': total_records,
            'screening_progress': {
                'title_screened': title_screened,
                'abstract_screened': abstract_screened,
                'full_text_screened': full_text_screened
            },
            'decisions': {
                'included': included,
                'excluded': excluded,
                'pending': pending
            },
            'exclusion_reasons': exclusion_reasons,
            'completion_rate': {
                'title_abstract': abstract_screened / total_records * 100,
                'full_text': full_text_screened / total_records * 100,
                'overall': (included + excluded) / total_records * 100
            }
        }
        
        return stats
    
    def _generate_study_id(self, result: Dict) -> str:
        """Generate unique study ID"""
        
        title = result.get('title', '')
        doi = result.get('doi', '')
        pmid = result.get('pmid', '')
        
        if doi:
            id_string = f"doi_{doi}"
        elif pmid:
            id_string = f"pmid_{pmid}"
        else:
            # Use title hash
            title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
            id_string = f"title_{title_hash}"
        
        # Clean for filename safety
        study_id = re.sub(r'[^a-zA-Z0-9_-]', '_', id_string)
        
        return study_id
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for duplicate detection"""
        
        if not title:
            return ""
        
        # Convert to lowercase and remove special characters
        normalized = re.sub(r'[^a-zA-Z0-9\s]', ' ', title.lower())
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _title_similarity(self, title1: str, title2: str) -> float:
        """Compute similarity between two titles"""
        
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _load_records(self) -> List[ScreeningRecord]:
        """Load screening records from file"""
        
        if not self.records_file.exists():
            return []
        
        try:
            df = pd.read_csv(self.records_file)
            
            records = []
            for _, row in df.iterrows():
                # Convert enum strings back to enums
                record_dict = row.to_dict()
                
                # Handle enum fields
                enum_fields = {
                    'title_screening': ScreeningDecision,
                    'abstract_screening': ScreeningDecision,
                    'full_text_screening': ScreeningDecision,
                    'final_decision': ScreeningDecision,
                    'title_exclusion_reason': ExclusionReason,
                    'abstract_exclusion_reason': ExclusionReason,
                    'full_text_exclusion_reason': ExclusionReason
                }
                
                for field, enum_class in enum_fields.items():
                    if pd.notna(record_dict[field]):
                        try:
                            record_dict[field] = enum_class(record_dict[field])
                        except ValueError:
                            record_dict[field] = None
                
                # Handle list fields
                if pd.notna(record_dict.get('authors')):
                    record_dict['authors'] = json.loads(record_dict['authors'])
                else:
                    record_dict['authors'] = []
                
                if pd.notna(record_dict.get('outcomes')):
                    record_dict['outcomes'] = json.loads(record_dict['outcomes'])
                else:
                    record_dict['outcomes'] = []
                
                records.append(ScreeningRecord(**record_dict))
            
            return records
        
        except Exception as e:
            self.logger.warning(f"Error loading records: {e}")
            return []
    
    def _save_records(self):
        """Save screening records to file"""
        
        records_data = []
        for record in self.records:
            record_dict = asdict(record)
            
            # Convert enums to strings
            for key, value in record_dict.items():
                if isinstance(value, Enum):
                    record_dict[key] = value.value
            
            # Convert lists to JSON strings
            record_dict['authors'] = json.dumps(record_dict['authors'])
            record_dict['outcomes'] = json.dumps(record_dict['outcomes'])
            
            records_data.append(record_dict)
        
        df = pd.DataFrame(records_data)
        df.to_csv(self.records_file, index=False)
    
    def _load_flow_data(self) -> PRISMAFlowDiagram:
        """Load PRISMA flow data"""
        
        if self.flow_file.exists():
            try:
                with open(self.flow_file, 'r') as f:
                    data = json.load(f)
                return PRISMAFlowDiagram(**data)
            except Exception as e:
                self.logger.warning(f"Error loading flow data: {e}")
        
        return PRISMAFlowDiagram()
    
    def _save_flow_data(self):
        """Save PRISMA flow data"""
        
        with open(self.flow_file, 'w') as f:
            json.dump(asdict(self.flow_data), f, indent=2)
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load review metadata"""
        
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Error loading metadata: {e}")
        
        return {}
    
    def _save_metadata(self):
        """Save review metadata"""
        
        self.metadata['last_updated'] = datetime.now().isoformat()
        
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)


if __name__ == "__main__":
    # Example usage
    workflow = PRISMAWorkflow("magnesium_sleep_review")
    
    # Initialize review
    workflow.initialize_review(
        title="Magnesium Supplementation for Sleep Quality: A Systematic Review",
        research_question="Does magnesium supplementation improve sleep quality in adults?",
        inclusion_criteria={
            'population': ['adults', 'humans'],
            'intervention': ['magnesium', 'magnesium supplement', 'magnesium glycinate'],
            'outcome': ['sleep quality', 'sleep', 'insomnia', 'sleep duration'],
            'study_design': ['randomized controlled trial', 'clinical trial', 'rct']
        },
        exclusion_criteria={
            'population': ['children', 'adolescents', 'animals'],
            'study_design': ['case report', 'editorial', 'review']
        }
    )
    
    print("PRISMA Workflow initialized")
    print(f"Review ID: {workflow.review_id}")
    
    # Show statistics
    stats = workflow.get_screening_statistics()
    print(f"Current statistics: {stats}")
    
    # Generate flow diagram
    flow_diagram = workflow.generate_prisma_flow_diagram()
    print("PRISMA Flow Diagram generated")
    
    for key, value in flow_diagram.items():
        if isinstance(value, (int, str)):
            print(f"  {key}: {value}")