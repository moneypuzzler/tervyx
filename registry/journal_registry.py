"""
VERA Protocol - Journal Registry Management
Handles journal scorecards with Parquet-based storage for scalability
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import requests
import json
import logging

class JournalRegistry:
    """Upper-layer journal registry with automated scorecard generation"""
    
    def __init__(self, registry_path: str = "registry"):
        self.registry_path = Path(registry_path)
        self.scorecards_file = self.registry_path / "scorecards.parquet"
        self.metadata_file = self.registry_path / "metadata.json"
        self.cache_duration = timedelta(hours=24)  # Cache journal data for 24 hours
        
        # Create registry directory if it doesn't exist
        self.registry_path.mkdir(exist_ok=True)
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def load_scorecards(self) -> pd.DataFrame:
        """Load journal scorecards from Parquet file"""
        if self.scorecards_file.exists():
            return pd.read_parquet(self.scorecards_file)
        else:
            # Return empty DataFrame with expected schema
            return pd.DataFrame(columns=[
                'issn', 'eissn', 'journal_name', 'publisher', 'category',
                'jcr_impact_factor', 'jcr_quartile', 'sjr_score', 'sjr_quartile',
                'doaj_member', 'cope_member', 'predatory_flag', 
                'if_z_score', 'sjr_z_score', 'trust_score',
                'last_updated', 'data_source'
            ])
    
    def save_scorecards(self, df: pd.DataFrame):
        """Save scorecards to Parquet file for efficient storage"""
        df.to_parquet(self.scorecards_file, index=False, compression='snappy')
        
        # Update metadata
        metadata = {
            'last_updated': datetime.now().isoformat(),
            'total_journals': len(df),
            'data_sources': df['data_source'].unique().tolist() if 'data_source' in df.columns else [],
            'schema_version': '1.0.0'
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def fetch_journal_metrics(self, issn: str) -> Dict:
        """Fetch journal metrics from multiple APIs"""
        metrics = {
            'issn': issn,
            'jcr_impact_factor': None,
            'jcr_quartile': None,
            'sjr_score': None,
            'sjr_quartile': None,
            'doaj_member': False,
            'cope_member': False,
            'predatory_flag': False,
            'journal_name': None,
            'publisher': None,
            'category': None,
            'data_source': 'api_fetch'
        }
        
        try:
            # Fetch from OpenAlex API (free alternative to JCR/SJR)
            openalex_data = self._fetch_openalex_data(issn)
            if openalex_data:
                metrics.update(openalex_data)
            
            # Check DOAJ membership
            doaj_status = self._check_doaj_membership(issn)
            metrics['doaj_member'] = doaj_status
            
            # Check COPE membership (simplified check)
            cope_status = self._check_cope_membership(metrics.get('publisher', ''))
            metrics['cope_member'] = cope_status
            
            # Check predatory journal lists (simplified)
            predatory_flag = self._check_predatory_lists(issn, metrics.get('journal_name', ''))
            metrics['predatory_flag'] = predatory_flag
            
        except Exception as e:
            self.logger.warning(f"Error fetching metrics for ISSN {issn}: {e}")
        
        return metrics
    
    def _fetch_openalex_data(self, issn: str) -> Optional[Dict]:
        """Fetch journal data from OpenAlex API"""
        try:
            url = f"https://api.openalex.org/sources/issn:{issn}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant metrics
                return {
                    'journal_name': data.get('display_name'),
                    'publisher': data.get('host_organization_name'),
                    'jcr_impact_factor': self._extract_impact_factor(data),
                    'sjr_score': self._extract_sjr_score(data),
                    'category': self._extract_primary_category(data)
                }
        except Exception as e:
            self.logger.warning(f"OpenAlex API error for {issn}: {e}")
        
        return None
    
    def _extract_impact_factor(self, openalex_data: Dict) -> Optional[float]:
        """Extract impact factor equivalent from OpenAlex data"""
        # Use h-index or citation metrics as proxy
        summary_stats = openalex_data.get('summary_stats', {})
        if summary_stats and summary_stats.get('h_index'):
            # Convert h-index to approximate impact factor
            h_index = summary_stats['h_index']
            # Rough approximation: IF ≈ h_index / 10
            return round(h_index / 10.0, 3)
        return None
    
    def _extract_sjr_score(self, openalex_data: Dict) -> Optional[float]:
        """Extract SJR equivalent from OpenAlex data"""
        # Use works count and citation metrics as proxy
        summary_stats = openalex_data.get('summary_stats', {})
        if summary_stats:
            works_count = summary_stats.get('works_count', 0)
            cited_by_count = summary_stats.get('cited_by_count', 0)
            
            if works_count > 0:
                # Rough SJR approximation
                return round(cited_by_count / (works_count * 1000), 3)
        return None
    
    def _extract_primary_category(self, openalex_data: Dict) -> Optional[str]:
        """Extract primary subject category"""
        x_concepts = openalex_data.get('x_concepts', [])
        if x_concepts:
            # Return highest scoring concept
            primary = max(x_concepts, key=lambda x: x.get('score', 0))
            return primary.get('display_name')
        return None
    
    def _check_doaj_membership(self, issn: str) -> bool:
        """Check if journal is in DOAJ (Directory of Open Access Journals)"""
        try:
            url = f"https://doaj.org/api/search/journals/issn%3A{issn}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('total', 0) > 0
        except Exception as e:
            self.logger.warning(f"DOAJ API error for {issn}: {e}")
        
        return False
    
    def _check_cope_membership(self, publisher: str) -> bool:
        """Check COPE membership (simplified - would need real COPE API)"""
        if not publisher:
            return False
        
        # Known COPE members (simplified list)
        cope_publishers = {
            'elsevier', 'springer', 'wiley', 'taylor & francis', 'sage',
            'oxford university press', 'cambridge university press', 'bmj',
            'nature', 'plos', 'frontiers', 'mdpi'
        }
        
        return any(member in publisher.lower() for member in cope_publishers)
    
    def _check_predatory_lists(self, issn: str, journal_name: str) -> bool:
        """Check against known predatory journal lists"""
        # This would integrate with real predatory journal databases
        # For now, return False (assume legitimate)
        return False
    
    def compute_trust_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute normalized trust scores for all journals"""
        # Compute z-scores for impact metrics
        if 'jcr_impact_factor' in df.columns:
            df['if_z_score'] = self._compute_z_score(df['jcr_impact_factor'])
        
        if 'sjr_score' in df.columns:
            df['sjr_z_score'] = self._compute_z_score(df['sjr_score'])
        
        # Compute composite trust score
        trust_components = []
        
        # Impact factor component (30% weight)
        if 'if_z_score' in df.columns:
            trust_components.append(0.3 * df['if_z_score'].fillna(0))
        
        # SJR component (30% weight)
        if 'sjr_z_score' in df.columns:
            trust_components.append(0.3 * df['sjr_z_score'].fillna(0))
        
        # DOAJ membership (20% weight)
        if 'doaj_member' in df.columns:
            trust_components.append(0.2 * df['doaj_member'].astype(int))
        
        # COPE membership (15% weight)
        if 'cope_member' in df.columns:
            trust_components.append(0.15 * df['cope_member'].astype(int))
        
        # Predatory flag penalty (-50% if flagged)
        if 'predatory_flag' in df.columns:
            trust_components.append(-0.5 * df['predatory_flag'].astype(int))
        
        # Sum components and normalize to 0-1 scale
        if trust_components:
            trust_raw = sum(trust_components)
            # Sigmoid normalization to 0-1 range
            df['trust_score'] = 1 / (1 + np.exp(-trust_raw))
        else:
            df['trust_score'] = 0.5  # Default neutral score
        
        return df
    
    def _compute_z_score(self, series: pd.Series) -> pd.Series:
        """Compute z-score for a metric series"""
        valid_values = series.dropna()
        if len(valid_values) > 1:
            mean_val = valid_values.mean()
            std_val = valid_values.std()
            if std_val > 0:
                return (series - mean_val) / std_val
        return pd.Series(0, index=series.index)
    
    def bulk_update_registry(self, issn_list: List[str], batch_size: int = 50):
        """Update registry for multiple journals in batches"""
        df = self.load_scorecards()
        existing_issns = set(df['issn'].tolist() if not df.empty else [])
        
        # Filter out already existing journals
        new_issns = [issn for issn in issn_list if issn not in existing_issns]
        
        self.logger.info(f"Updating registry for {len(new_issns)} new journals")
        
        new_records = []
        
        for i in range(0, len(new_issns), batch_size):
            batch = new_issns[i:i+batch_size]
            self.logger.info(f"Processing batch {i//batch_size + 1}/{(len(new_issns)-1)//batch_size + 1}")
            
            for issn in batch:
                try:
                    metrics = self.fetch_journal_metrics(issn)
                    metrics['last_updated'] = datetime.now().isoformat()
                    new_records.append(metrics)
                except Exception as e:
                    self.logger.error(f"Error processing {issn}: {e}")
        
        if new_records:
            new_df = pd.DataFrame(new_records)
            
            # Combine with existing data
            if not df.empty:
                combined_df = pd.concat([df, new_df], ignore_index=True)
            else:
                combined_df = new_df
            
            # Compute trust scores
            combined_df = self.compute_trust_scores(combined_df)
            
            # Save updated registry
            self.save_scorecards(combined_df)
            
            self.logger.info(f"Registry updated: {len(new_records)} new journals added")
    
    def get_journal_scorecard(self, issn: str) -> Optional[Dict]:
        """Get scorecard for a specific journal"""
        df = self.load_scorecards()
        
        if df.empty:
            return None
        
        matches = df[df['issn'] == issn]
        
        if matches.empty:
            # Try to fetch and add to registry
            self.bulk_update_registry([issn])
            df = self.load_scorecards()
            matches = df[df['issn'] == issn]
        
        if not matches.empty:
            return matches.iloc[0].to_dict()
        
        return None
    
    def search_journals(self, query: str, limit: int = 20) -> List[Dict]:
        """Search journals by name or ISSN"""
        df = self.load_scorecards()
        
        if df.empty:
            return []
        
        # Search in journal names and ISSNs
        mask = (
            df['journal_name'].str.contains(query, case=False, na=False) |
            df['issn'].str.contains(query, case=False, na=False)
        )
        
        results = df[mask].head(limit)
        return results.to_dict('records')
    
    def get_registry_stats(self) -> Dict:
        """Get registry statistics"""
        df = self.load_scorecards()
        
        if df.empty:
            return {'total_journals': 0}
        
        stats = {
            'total_journals': len(df),
            'doaj_members': df['doaj_member'].sum() if 'doaj_member' in df.columns else 0,
            'cope_members': df['cope_member'].sum() if 'cope_member' in df.columns else 0,
            'predatory_flagged': df['predatory_flag'].sum() if 'predatory_flag' in df.columns else 0,
            'avg_trust_score': df['trust_score'].mean() if 'trust_score' in df.columns else 0,
            'last_updated': self._get_last_update_time()
        }
        
        return stats
    
    def _get_last_update_time(self) -> Optional[str]:
        """Get last update timestamp from metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                return metadata.get('last_updated')
            except Exception:
                pass
        return None


if __name__ == "__main__":
    # Example usage
    registry = JournalRegistry()
    
    # Test with some sample ISSNs
    sample_issns = [
        "1389-9457",  # Sleep Medicine
        "1365-2869",  # Journal of Sleep Research
        "0006-3223",  # Biological Psychiatry
        "1529-9430"   # Sleep Medicine Reviews
    ]
    
    print("Updating journal registry...")
    registry.bulk_update_registry(sample_issns)
    
    print("\nRegistry statistics:")
    stats = registry.get_registry_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nSample journal scorecard:")
    scorecard = registry.get_journal_scorecard("1389-9457")
    if scorecard:
        for key, value in scorecard.items():
            print(f"  {key}: {value}")