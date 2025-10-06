"""
VERA Protocol - Entry Catalog Management
Manages 1000+ entry seeds with CSV-based catalog system
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import csv
import json
import hashlib
import logging
from dataclasses import dataclass, asdict
import uuid

@dataclass
class EntrySeed:
    """Entry seed specification for catalog system"""
    entry_id: str
    category: str  # HBV category (sleep, cognition, etc.)
    substance: str
    formulation: str
    indication: str
    priority: str  # high, medium, low
    estimated_studies: int
    target_effect_size: float
    confidence_level: str  # preliminary, moderate, strong
    source_hint: str  # PubMed query or DOI hint
    created_at: str
    status: str  # pending, in_progress, completed, failed
    assignee: Optional[str] = None
    completion_date: Optional[str] = None
    final_tier: Optional[str] = None
    notes: str = ""

class EntryCatalog:
    """Catalog system for managing 1000+ entry seeds"""
    
    def __init__(self, catalog_path: str = "catalog"):
        self.catalog_path = Path(catalog_path)
        self.entries_file = self.catalog_path / "entries.csv"
        self.metadata_file = self.catalog_path / "catalog_metadata.json"
        self.progress_file = self.catalog_path / "progress_summary.json"
        
        # Create catalog directory
        self.catalog_path.mkdir(exist_ok=True)
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize catalog if it doesn't exist
        if not self.entries_file.exists():
            self._initialize_catalog()
    
    def _initialize_catalog(self):
        """Initialize catalog with predefined entry seeds"""
        self.logger.info("Initializing entry catalog with 1000+ seeds")
        
        # Generate comprehensive seed list
        seeds = self._generate_entry_seeds()
        
        # Save to CSV
        df = pd.DataFrame([asdict(seed) for seed in seeds])
        df.to_csv(self.entries_file, index=False)
        
        # Save metadata
        metadata = {
            'catalog_version': '1.0.0',
            'created_at': datetime.now().isoformat(),
            'total_seeds': len(seeds),
            'schema_version': '1.0.0',
            'categories': list(set(seed.category for seed in seeds)),
            'priority_distribution': {
                'high': len([s for s in seeds if s.priority == 'high']),
                'medium': len([s for s in seeds if s.priority == 'medium']),
                'low': len([s for s in seeds if s.priority == 'low'])
            }
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self._update_progress_summary()
        
        self.logger.info(f"Catalog initialized with {len(seeds)} entry seeds")
    
    def _generate_entry_seeds(self) -> List[EntrySeed]:
        """Generate comprehensive list of entry seeds"""
        seeds = []
        
        # Define substance categories with formulations and indications
        substance_matrix = {
            'sleep': {
                'magnesium': ['glycinate', 'oxide', 'citrate', 'bisglycinate'],
                'melatonin': ['immediate_release', 'extended_release', 'sublingual'],
                'valerian': ['root_extract', 'standardized_extract'],
                'ashwagandha': ['ksm66', 'root_extract', 'standardized'],
                'l_theanine': ['pure', 'with_gaba', 'with_melatonin'],
                'gaba': ['pure', 'pharmagaba', 'with_theanine'],
                'chamomile': ['extract', 'tea', 'standardized'],
                'passionflower': ['extract', 'standardized', 'combination'],
                'lemon_balm': ['extract', 'standardized', 'tea'],
                'glycine': ['pure', 'with_magnesium', 'timed_release'],
                'tryptophan': ['l_tryptophan', '5_htp', 'combination'],
                'cbd': ['isolate', 'full_spectrum', 'broad_spectrum'],
                'lavender': ['oil', 'extract', 'standardized'],
                'magnolia_bark': ['extract', 'standardized', 'honokiol'],
                'kava': ['extract', 'kavalactones', 'standardized']
            },
            'cognition': {
                'lion_mane': ['extract', 'fruiting_body', 'mycelium'],
                'bacopa_monnieri': ['standardized', 'bacosides', 'extract'],
                'rhodiola_rosea': ['standardized', 'rosavins', 'salidroside'],
                'ginkgo_biloba': ['egb761', 'standardized', 'extract'],
                'phosphatidylserine': ['soy_derived', 'sunflower_derived'],
                'alpha_gpc': ['pure', 'with_citicoline', 'liposomal'],
                'citicoline': ['cognizin', 'pure', 'with_alpha_gpc'],
                'acetyl_l_carnitine': ['pure', 'with_lipoic_acid'],
                'piracetam': ['pure', 'with_choline', 'aniracetam'],
                'modafinil': ['pure', 'armodafinil', 'combination'],
                'curcumin': ['standardized', 'with_piperine', 'liposomal'],
                'omega_3': ['epa_dha', 'high_dha', 'algae_derived'],
                'creatine': ['monohydrate', 'with_beta_alanine'],
                'caffeine': ['pure', 'with_l_theanine', 'timed_release'],
                'nicotinamide_riboside': ['pure', 'with_pterostilbene']
            },
            'mental_health': {
                'st_johns_wort': ['standardized', 'hypericin', 'extract'],
                'sam_e': ['pure', 'enteric_coated', 'with_b_vitamins'],
                'omega_3': ['high_epa', 'balanced', 'ethyl_ester'],
                'probiotics': ['multi_strain', 'lactobacillus', 'bifidobacterium'],
                'vitamin_d': ['d3', 'd2', 'with_k2'],
                'b_complex': ['methylated', 'standard', 'high_potency'],
                'folate': ['methylfolate', 'folic_acid', '5_mthf'],
                'inositol': ['myo_inositol', 'd_chiro', 'combination'],
                'taurine': ['pure', 'with_magnesium', 'sustained'],
                'tyrosine': ['n_acetyl', 'pure', 'with_b6'],
                'phenylethylamine': ['pure', 'with_hordenine'],
                'saffron': ['extract', 'standardized', 'crocin'],
                'curcumin': ['standardized', 'with_piperine', 'longvida'],
                'ashwagandha': ['ksm66', 'sensoril', 'root_extract'],
                'cordyceps': ['cs4', 'militaris', 'sinensis']
            },
            'renal_safety': {
                'creatine': ['monohydrate', 'hcl', 'buffered'],
                'protein_powder': ['whey', 'casein', 'plant_based'],
                'nsaids': ['ibuprofen', 'naproxen', 'aspirin'],
                'high_dose_vitamins': ['vitamin_c', 'vitamin_d', 'b_vitamins'],
                'herbal_extracts': ['kratom', 'aristolochia', 'ephedra'],
                'amino_acids': ['arginine', 'lysine', 'methionine'],
                'minerals': ['calcium', 'iron', 'zinc'],
                'diuretics': ['caffeine', 'dandelion', 'juniper'],
                'contrast_agents': ['gadolinium', 'iodine_based'],
                'antibiotics': ['aminoglycosides', 'vancomycin'],
                'antimalarials': ['chloroquine', 'quinine'],
                'chemotherapy': ['cisplatin', 'methotrexate'],
                'immunosuppressants': ['cyclosporine', 'tacrolimus'],
                'ace_inhibitors': ['lisinopril', 'enalapril'],
                'arb_medications': ['losartan', 'valsartan']
            },
            'cardiovascular': {
                'omega_3': ['fish_oil', 'krill_oil', 'algae'],
                'coq10': ['ubiquinol', 'ubiquinone', 'liposomal'],
                'garlic': ['extract', 'aged', 'allicin'],
                'hawthorn': ['extract', 'standardized', 'berries'],
                'red_yeast_rice': ['standardized', 'with_coq10'],
                'bergamot': ['extract', 'standardized', 'polyphenols'],
                'nattokinase': ['pure', 'with_serrapeptase'],
                'grape_seed': ['extract', 'proanthocyanidins'],
                'resveratrol': ['trans', 'with_pterostilbene'],
                'policosanol': ['sugar_cane', 'rice_bran'],
                'plant_sterols': ['beta_sitosterol', 'mixed'],
                'psyllium': ['husk', 'powder', 'capsules'],
                'beta_glucan': ['oat', 'mushroom', 'yeast'],
                'l_arginine': ['pure', 'with_citrulline'],
                'hibiscus': ['extract', 'tea', 'standardized']
            }
        }
        
        # Generate seeds for each category
        for category, substances in substance_matrix.items():
            for substance, formulations in substances.items():
                
                # Define indications per category
                indications = self._get_indications_for_category(category)
                
                for formulation in formulations:
                    for indication in indications:
                        # Generate multiple priority levels for comprehensive coverage
                        priorities = self._assign_priorities(substance, indication, category)
                        
                        for priority in priorities:
                            entry_id = self._generate_entry_id(category, substance, formulation, indication)
                            
                            seed = EntrySeed(
                                entry_id=entry_id,
                                category=category,
                                substance=substance,
                                formulation=formulation,
                                indication=indication,
                                priority=priority,
                                estimated_studies=self._estimate_study_count(substance, indication),
                                target_effect_size=self._estimate_effect_size(substance, indication, category),
                                confidence_level=self._estimate_confidence_level(substance, indication),
                                source_hint=self._generate_search_hint(substance, formulation, indication),
                                created_at=datetime.now().isoformat(),
                                status='pending'
                            )
                            
                            seeds.append(seed)
        
        # Add some high-impact combination studies
        combination_seeds = self._generate_combination_seeds()
        seeds.extend(combination_seeds)
        
        self.logger.info(f"Generated {len(seeds)} entry seeds across {len(substance_matrix)} categories")
        
        return seeds
    
    def _get_indications_for_category(self, category: str) -> List[str]:
        """Get relevant indications for each category"""
        indication_map = {
            'sleep': [
                'sleep_onset', 'sleep_maintenance', 'sleep_quality', 'sleep_duration',
                'rem_sleep', 'deep_sleep', 'sleep_efficiency', 'insomnia'
            ],
            'cognition': [
                'memory', 'attention', 'processing_speed', 'executive_function',
                'working_memory', 'verbal_fluency', 'cognitive_flexibility'
            ],
            'mental_health': [
                'depression', 'anxiety', 'mood', 'stress', 'wellbeing',
                'emotional_regulation', 'resilience'
            ],
            'renal_safety': [
                'kidney_function', 'creatinine_levels', 'gfr_impact', 'proteinuria',
                'acute_kidney_injury', 'chronic_kidney_disease'
            ],
            'cardiovascular': [
                'blood_pressure', 'cholesterol', 'triglycerides', 'heart_rate',
                'endothelial_function', 'arterial_stiffness', 'cardiovascular_events'
            ]
        }
        
        return indication_map.get(category, ['general_health'])
    
    def _assign_priorities(self, substance: str, indication: str, category: str) -> List[str]:
        """Assign priority levels based on evidence strength and clinical importance"""
        
        # High-priority combinations (strong evidence expected)
        high_priority_combinations = {
            ('magnesium', 'sleep_quality'),
            ('melatonin', 'sleep_onset'),
            ('omega_3', 'cardiovascular_events'),
            ('curcumin', 'cognition'),
            ('ashwagandha', 'stress'),
            ('bacopa_monnieri', 'memory'),
            ('creatine', 'kidney_function'),
            ('coq10', 'heart_rate')
        }
        
        # Medium-priority (moderate evidence expected)
        medium_priority_substances = {
            'ginkgo_biloba', 'rhodiola_rosea', 'garlic', 'hawthorn',
            'valerian', 'passionflower', 'sam_e', 'inositol'
        }
        
        priorities = []
        
        if (substance, indication) in high_priority_combinations:
            priorities.append('high')
        elif substance in medium_priority_substances:
            priorities.append('medium')
        else:
            priorities.append('low')
        
        # Add some medium priority variants for comprehensive coverage
        if 'high' in priorities:
            priorities.append('medium')
        
        return priorities
    
    def _estimate_study_count(self, substance: str, indication: str) -> int:
        """Estimate number of available studies"""
        
        # High-evidence substances
        high_evidence = {
            'melatonin': 50, 'omega_3': 100, 'creatine': 80, 'caffeine': 70,
            'curcumin': 60, 'magnesium': 45, 'vitamin_d': 90
        }
        
        # Medium-evidence substances  
        medium_evidence = {
            'ashwagandha': 25, 'bacopa_monnieri': 20, 'rhodiola_rosea': 18,
            'ginkgo_biloba': 35, 'coq10': 40, 'garlic': 30
        }
        
        base_count = high_evidence.get(substance, medium_evidence.get(substance, 10))
        
        # Adjust based on indication specificity
        indication_multipliers = {
            'sleep_onset': 0.8, 'memory': 0.9, 'depression': 0.7,
            'blood_pressure': 0.8, 'kidney_function': 0.6
        }
        
        multiplier = indication_multipliers.get(indication, 0.5)
        
        return max(3, int(base_count * multiplier))
    
    def _estimate_effect_size(self, substance: str, indication: str, category: str) -> float:
        """Estimate expected effect size"""
        
        # Category-based baseline effect sizes
        category_baselines = {
            'sleep': 0.4, 'cognition': 0.3, 'mental_health': 0.35,
            'cardiovascular': 0.25, 'renal_safety': -0.1  # Negative for safety outcomes
        }
        
        # Substance-specific modifiers
        substance_modifiers = {
            'melatonin': 0.2, 'omega_3': 0.15, 'curcumin': 0.1,
            'magnesium': 0.1, 'caffeine': 0.25, 'creatine': 0.15
        }
        
        baseline = category_baselines.get(category, 0.2)
        modifier = substance_modifiers.get(substance, 0.0)
        
        effect_size = baseline + modifier
        
        # Add some realistic variation
        variation = np.random.normal(0, 0.05)
        effect_size += variation
        
        return round(effect_size, 3)
    
    def _estimate_confidence_level(self, substance: str, indication: str) -> str:
        """Estimate confidence level based on research maturity"""
        
        mature_substances = {
            'melatonin', 'omega_3', 'creatine', 'caffeine', 'magnesium',
            'vitamin_d', 'curcumin', 'ginkgo_biloba'
        }
        
        emerging_substances = {
            'lion_mane', 'nicotinamide_riboside', 'cbd', 'nattokinase'
        }
        
        if substance in mature_substances:
            return 'strong'
        elif substance in emerging_substances:
            return 'preliminary'
        else:
            return 'moderate'
    
    def _generate_search_hint(self, substance: str, formulation: str, indication: str) -> str:
        """Generate PubMed search hint"""
        
        # Clean up names for search
        substance_clean = substance.replace('_', ' ')
        indication_clean = indication.replace('_', ' ')
        
        # Add formulation specificity if meaningful
        formulation_terms = {
            'standardized': 'standardized extract',
            'extract': 'extract',
            'glycinate': 'glycinate',
            'ksm66': 'KSM-66',
            'cognizin': 'Cognizin',
            'egb761': 'EGb 761'
        }
        
        formulation_term = formulation_terms.get(formulation, '')
        
        if formulation_term:
            search_hint = f'("{substance_clean}" OR "{substance_clean} {formulation_term}") AND "{indication_clean}"'
        else:
            search_hint = f'"{substance_clean}" AND "{indication_clean}"'
        
        # Add study type filters
        search_hint += ' AND (randomized controlled trial OR clinical trial OR meta-analysis)'
        
        return search_hint
    
    def _generate_combination_seeds(self) -> List[EntrySeed]:
        """Generate seeds for combination studies"""
        combinations = [
            ('sleep', 'magnesium_melatonin', 'combined', 'sleep_quality', 'high'),
            ('cognition', 'lion_mane_bacopa', 'combined', 'memory', 'medium'),
            ('mental_health', 'omega3_vitamin_d', 'combined', 'depression', 'high'),
            ('cardiovascular', 'coq10_omega3', 'combined', 'heart_rate', 'medium'),
            ('sleep', 'ashwagandha_gaba', 'combined', 'stress_sleep', 'medium')
        ]
        
        seeds = []
        for category, substance, formulation, indication, priority in combinations:
            entry_id = self._generate_entry_id(category, substance, formulation, indication)
            
            seed = EntrySeed(
                entry_id=entry_id,
                category=category,
                substance=substance,
                formulation=formulation,
                indication=indication,
                priority=priority,
                estimated_studies=15,  # Combinations typically have fewer studies
                target_effect_size=0.35,  # Synergistic effects
                confidence_level='moderate',
                source_hint=f'"{substance.replace("_", " ")}" AND "{indication.replace("_", " ")}" AND combination',
                created_at=datetime.now().isoformat(),
                status='pending',
                notes='Combination study - potential synergistic effects'
            )
            
            seeds.append(seed)
        
        return seeds
    
    def _generate_entry_id(self, category: str, substance: str, formulation: str, indication: str) -> str:
        """Generate unique entry ID"""
        # Create deterministic but unique ID
        id_string = f"{category}-{substance}-{formulation}-{indication}"
        hash_obj = hashlib.md5(id_string.encode())
        hash_hex = hash_obj.hexdigest()[:8]
        
        return f"vera_{category}_{hash_hex}"
    
    def load_catalog(self) -> pd.DataFrame:
        """Load entry catalog from CSV"""
        if self.entries_file.exists():
            return pd.read_csv(self.entries_file)
        else:
            return pd.DataFrame()
    
    def save_catalog(self, df: pd.DataFrame):
        """Save catalog to CSV"""
        df.to_csv(self.entries_file, index=False)
        self._update_progress_summary()
    
    def _update_progress_summary(self):
        """Update progress summary statistics"""
        df = self.load_catalog()
        
        if df.empty:
            return
        
        summary = {
            'last_updated': datetime.now().isoformat(),
            'total_entries': len(df),
            'status_breakdown': df['status'].value_counts().to_dict(),
            'category_breakdown': df['category'].value_counts().to_dict(),
            'priority_breakdown': df['priority'].value_counts().to_dict(),
            'completion_rate': len(df[df['status'] == 'completed']) / len(df) * 100,
            'high_priority_pending': len(df[(df['priority'] == 'high') & (df['status'] == 'pending')]),
            'estimated_total_studies': df['estimated_studies'].sum()
        }
        
        with open(self.progress_file, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def get_next_batch(self, batch_size: int = 10, priority: Optional[str] = None, 
                      category: Optional[str] = None) -> List[Dict]:
        """Get next batch of entries to process"""
        df = self.load_catalog()
        
        if df.empty:
            return []
        
        # Filter pending entries
        pending_df = df[df['status'] == 'pending'].copy()
        
        # Apply filters
        if priority:
            pending_df = pending_df[pending_df['priority'] == priority]
        
        if category:
            pending_df = pending_df[pending_df['category'] == category]
        
        # Sort by priority and estimated studies (high-impact first)
        priority_order = {'high': 3, 'medium': 2, 'low': 1}
        pending_df['priority_score'] = pending_df['priority'].map(priority_order)
        
        sorted_df = pending_df.sort_values([
            'priority_score', 'estimated_studies'
        ], ascending=[False, False])
        
        # Return batch
        batch = sorted_df.head(batch_size)
        return batch.to_dict('records')
    
    def update_entry_status(self, entry_id: str, status: str, 
                          assignee: Optional[str] = None, 
                          final_tier: Optional[str] = None,
                          notes: str = ""):
        """Update entry status in catalog"""
        df = self.load_catalog()
        
        mask = df['entry_id'] == entry_id
        
        if not mask.any():
            self.logger.warning(f"Entry {entry_id} not found in catalog")
            return False
        
        # Update fields
        df.loc[mask, 'status'] = status
        
        if assignee:
            df.loc[mask, 'assignee'] = assignee
        
        if final_tier:
            df.loc[mask, 'final_tier'] = final_tier
        
        if status == 'completed':
            df.loc[mask, 'completion_date'] = datetime.now().isoformat()
        
        if notes:
            existing_notes = df.loc[mask, 'notes'].iloc[0] or ""
            df.loc[mask, 'notes'] = f"{existing_notes}\n{notes}".strip()
        
        # Save updated catalog
        self.save_catalog(df)
        
        self.logger.info(f"Updated entry {entry_id} status to {status}")
        return True
    
    def search_entries(self, query: str, limit: int = 20) -> List[Dict]:
        """Search entries by substance, indication, or notes"""
        df = self.load_catalog()
        
        if df.empty:
            return []
        
        # Search across multiple fields
        mask = (
            df['substance'].str.contains(query, case=False, na=False) |
            df['indication'].str.contains(query, case=False, na=False) |
            df['notes'].str.contains(query, case=False, na=False) |
            df['entry_id'].str.contains(query, case=False, na=False)
        )
        
        results = df[mask].head(limit)
        return results.to_dict('records')
    
    def get_catalog_statistics(self) -> Dict:
        """Get comprehensive catalog statistics"""
        df = self.load_catalog()
        
        if df.empty:
            return {'total_entries': 0}
        
        stats = {
            'total_entries': len(df),
            'categories': {
                'breakdown': df['category'].value_counts().to_dict(),
                'completion_by_category': {}
            },
            'priorities': df['priority'].value_counts().to_dict(),
            'status': df['status'].value_counts().to_dict(),
            'progress': {
                'completion_rate': len(df[df['status'] == 'completed']) / len(df) * 100,
                'in_progress': len(df[df['status'] == 'in_progress']),
                'pending_high_priority': len(df[(df['priority'] == 'high') & (df['status'] == 'pending')])
            },
            'estimates': {
                'total_studies': df['estimated_studies'].sum(),
                'avg_effect_size': df['target_effect_size'].mean(),
                'confidence_distribution': df['confidence_level'].value_counts().to_dict()
            }
        }
        
        # Completion rate by category
        for category in df['category'].unique():
            cat_df = df[df['category'] == category]
            completed = len(cat_df[cat_df['status'] == 'completed'])
            total = len(cat_df)
            stats['categories']['completion_by_category'][category] = {
                'completed': completed,
                'total': total,
                'rate': completed / total * 100 if total > 0 else 0
            }
        
        return stats
    
    def export_batch_assignments(self, output_file: str, batch_size: int = 50):
        """Export batch assignments for distributed processing"""
        df = self.load_catalog()
        pending_df = df[df['status'] == 'pending'].copy()
        
        # Create batches
        batches = []
        for i in range(0, len(pending_df), batch_size):
            batch = pending_df.iloc[i:i+batch_size].copy()
            batch['batch_id'] = f"batch_{i//batch_size + 1:03d}"
            batches.append(batch)
        
        if batches:
            all_batches = pd.concat(batches, ignore_index=True)
            all_batches.to_csv(output_file, index=False)
            
            self.logger.info(f"Exported {len(batches)} batches to {output_file}")
        
        return len(batches)


if __name__ == "__main__":
    # Example usage
    catalog = EntryCatalog()
    
    print("Entry Catalog Statistics:")
    stats = catalog.get_catalog_statistics()
    
    print(f"Total entries: {stats['total_entries']}")
    print(f"Categories: {list(stats['categories']['breakdown'].keys())}")
    print(f"Priority distribution: {stats['priorities']}")
    print(f"Status distribution: {stats['status']}")
    print(f"Completion rate: {stats['progress']['completion_rate']:.1f}%")
    
    print("\nNext batch (high priority):")
    batch = catalog.get_next_batch(batch_size=5, priority='high')
    for entry in batch:
        print(f"  {entry['entry_id']}: {entry['substance']} -> {entry['indication']}")