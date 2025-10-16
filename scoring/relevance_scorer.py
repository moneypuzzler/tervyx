"""
TERVYX Protocol - BERT-based Relevance Scoring
Implements abstract-based relevance scoring using transformer models
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import json
import logging
from datetime import datetime
import re
import pickle
from dataclasses import dataclass
import warnings

# Try to import transformer libraries (with fallbacks)
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    warnings.warn("SentenceTransformers not available. Install with: pip install sentence-transformers")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    warnings.warn("Scikit-learn not available. Install with: pip install scikit-learn")

@dataclass
class RelevanceScore:
    """Relevance scoring result"""
    study_id: str
    semantic_score: float      # BERT-based semantic similarity
    keyword_score: float       # Keyword-based scoring
    combined_score: float      # Weighted combination
    confidence: float          # Confidence in the score
    matched_concepts: List[str]  # Key concepts that matched
    scoring_model: str         # Model used for scoring
    computed_at: str

class RelevanceScorer:
    """BERT-based relevance scoring for study abstracts"""
    
    def __init__(self, model_path: str = "scoring", cache_embeddings: bool = True):
        self.model_path = Path(model_path)
        self.model_path.mkdir(exist_ok=True)
        
        self.cache_embeddings = cache_embeddings
        self.embeddings_cache = {}
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Load or initialize models
        self._initialize_models()
        
        # Load category-specific concepts
        self._load_category_concepts()
    
    def _initialize_models(self):
        """Initialize BERT and fallback models"""
        
        # Try to load BERT model
        self.bert_model = None
        if TRANSFORMERS_AVAILABLE:
            try:
                # Use a model optimized for biomedical text
                model_name = "sentence-transformers/all-MiniLM-L6-v2"  # Fast and good quality
                self.bert_model = SentenceTransformer(model_name)
                self.logger.info(f"Loaded BERT model: {model_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load BERT model: {e}")
        
        # Initialize TF-IDF fallback
        self.tfidf_model = None
        if SKLEARN_AVAILABLE:
            self.tfidf_model = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2
            )
            self.logger.info("Initialized TF-IDF fallback model")
        
        if not self.bert_model and not self.tfidf_model:
            raise RuntimeError("No scoring models available. Install sentence-transformers or scikit-learn.")
    
    def _load_category_concepts(self):
        """Load category-specific biomedical concepts"""
        
        self.category_concepts = {
            'sleep': {
                'primary': [
                    'sleep quality', 'sleep duration', 'sleep onset', 'sleep maintenance',
                    'insomnia', 'sleep efficiency', 'rem sleep', 'deep sleep', 'nrem sleep',
                    'sleep latency', 'wake after sleep onset', 'sleep fragmentation'
                ],
                'secondary': [
                    'circadian rhythm', 'melatonin', 'sleep disorders', 'sleepiness',
                    'fatigue', 'alertness', 'sleep architecture', 'polysomnography'
                ],
                'measures': [
                    'pittsburgh sleep quality index', 'epworth sleepiness scale',
                    'sleep diary', 'actigraphy', 'polysomnography', 'psg'
                ]
            },
            'cognition': {
                'primary': [
                    'cognitive function', 'memory', 'attention', 'executive function',
                    'working memory', 'processing speed', 'cognitive performance',
                    'learning', 'recall', 'recognition', 'cognitive flexibility'
                ],
                'secondary': [
                    'neuroplasticity', 'neuroprotection', 'brain function',
                    'cognitive decline', 'cognitive enhancement', 'nootropic'
                ],
                'measures': [
                    'mini mental state examination', 'mmse', 'montreal cognitive assessment',
                    'moca', 'trail making test', 'stroop test', 'digit span'
                ]
            },
            'mental_health': {
                'primary': [
                    'depression', 'anxiety', 'mood', 'stress', 'wellbeing',
                    'psychological distress', 'emotional regulation', 'resilience',
                    'mental health', 'psychological health'
                ],
                'secondary': [
                    'serotonin', 'dopamine', 'neurotransmitter', 'mood disorder',
                    'major depressive disorder', 'generalized anxiety', 'cortisol'
                ],
                'measures': [
                    'beck depression inventory', 'bdi', 'hamilton rating scale',
                    'dass-21', 'gad-7', 'phq-9', 'perceived stress scale'
                ]
            },
            'cardiovascular': {
                'primary': [
                    'blood pressure', 'hypertension', 'cholesterol', 'triglycerides',
                    'cardiovascular disease', 'heart rate', 'endothelial function',
                    'arterial stiffness', 'cardiovascular risk'
                ],
                'secondary': [
                    'atherosclerosis', 'coronary artery disease', 'myocardial infarction',
                    'stroke', 'peripheral arterial disease', 'cardiac output'
                ],
                'measures': [
                    'systolic blood pressure', 'diastolic blood pressure',
                    'ldl cholesterol', 'hdl cholesterol', 'framingham risk score'
                ]
            },
            'renal_safety': {
                'primary': [
                    'kidney function', 'renal function', 'creatinine', 'egfr',
                    'glomerular filtration rate', 'proteinuria', 'albuminuria',
                    'acute kidney injury', 'chronic kidney disease'
                ],
                'secondary': [
                    'nephrotoxicity', 'renal clearance', 'kidney damage',
                    'renal impairment', 'kidney biomarkers', 'urinalysis'
                ],
                'measures': [
                    'serum creatinine', 'blood urea nitrogen', 'bun',
                    'urine albumin', 'cystatin c', 'kidney injury molecule'
                ]
            }
        }
        
        # Create combined concept lists for each category
        self.combined_concepts = {}
        for category, concepts in self.category_concepts.items():
            all_concepts = []
            for concept_type, concept_list in concepts.items():
                all_concepts.extend(concept_list)
            self.combined_concepts[category] = all_concepts
    
    def compute_relevance_score(self, study_abstract: str, target_category: str,
                              target_substance: str, target_indication: str) -> RelevanceScore:
        """Compute comprehensive relevance score for a study abstract"""
        
        if not study_abstract or not study_abstract.strip():
            return RelevanceScore(
                study_id="unknown",
                semantic_score=0.0,
                keyword_score=0.0,
                combined_score=0.0,
                confidence=0.0,
                matched_concepts=[],
                scoring_model="none",
                computed_at=datetime.now().isoformat()
            )
        
        # Prepare target query
        target_query = self._create_target_query(target_category, target_substance, target_indication)
        
        # Compute semantic similarity
        semantic_score = self._compute_semantic_similarity(study_abstract, target_query)
        
        # Compute keyword-based score
        keyword_score, matched_concepts = self._compute_keyword_score(
            study_abstract, target_category, target_substance, target_indication
        )
        
        # Combine scores with weights
        combined_score = self._combine_scores(semantic_score, keyword_score)
        
        # Compute confidence
        confidence = self._compute_confidence(semantic_score, keyword_score, matched_concepts)
        
        # Determine scoring model used
        scoring_model = "bert" if self.bert_model else "tfidf"
        
        return RelevanceScore(
            study_id="computed",
            semantic_score=semantic_score,
            keyword_score=keyword_score,
            combined_score=combined_score,
            confidence=confidence,
            matched_concepts=matched_concepts,
            scoring_model=scoring_model,
            computed_at=datetime.now().isoformat()
        )
    
    def batch_score_studies(self, studies_data: List[Dict], target_category: str,
                           target_substance: str, target_indication: str) -> List[RelevanceScore]:
        """Batch score multiple studies for efficiency"""
        
        scores = []
        abstracts = []
        study_ids = []
        
        # Collect abstracts and IDs
        for study in studies_data:
            abstract = study.get('abstract', '')
            study_id = study.get('study_id', f"study_{len(study_ids)}")
            
            abstracts.append(abstract)
            study_ids.append(study_id)
        
        # Create target query
        target_query = self._create_target_query(target_category, target_substance, target_indication)
        
        # Batch compute semantic similarities if using BERT
        if self.bert_model and abstracts:
            try:
                # Encode all abstracts and target query
                all_texts = abstracts + [target_query]
                embeddings = self.bert_model.encode(all_texts)
                
                # Compute similarities
                target_embedding = embeddings[-1:] 
                abstract_embeddings = embeddings[:-1]
                
                similarities = cosine_similarity(abstract_embeddings, target_embedding).flatten()
                
            except Exception as e:
                self.logger.warning(f"Batch BERT encoding failed: {e}")
                similarities = [0.5] * len(abstracts)  # Fallback
        else:
            similarities = [0.5] * len(abstracts)  # Fallback for TF-IDF or no abstracts
        
        # Compute individual scores
        for i, (study_id, abstract) in enumerate(zip(study_ids, abstracts)):
            
            semantic_score = similarities[i] if i < len(similarities) else 0.5
            
            keyword_score, matched_concepts = self._compute_keyword_score(
                abstract, target_category, target_substance, target_indication
            )
            
            combined_score = self._combine_scores(semantic_score, keyword_score)
            confidence = self._compute_confidence(semantic_score, keyword_score, matched_concepts)
            
            score = RelevanceScore(
                study_id=study_id,
                semantic_score=semantic_score,
                keyword_score=keyword_score,
                combined_score=combined_score,
                confidence=confidence,
                matched_concepts=matched_concepts,
                scoring_model="bert" if self.bert_model else "tfidf",
                computed_at=datetime.now().isoformat()
            )
            
            scores.append(score)
        
        return scores
    
    def _create_target_query(self, category: str, substance: str, indication: str) -> str:
        """Create target query text for similarity computation"""
        
        # Start with substance and indication
        query_parts = [
            substance.replace('_', ' '),
            indication.replace('_', ' ')
        ]
        
        # Add category-specific concepts
        if category in self.category_concepts:
            primary_concepts = self.category_concepts[category]['primary'][:5]  # Top 5 concepts
            query_parts.extend(primary_concepts)
        
        # Join into coherent query
        target_query = '. '.join(query_parts)
        
        return target_query
    
    def _compute_semantic_similarity(self, abstract: str, target_query: str) -> float:
        """Compute semantic similarity using BERT or TF-IDF"""
        
        if not abstract.strip() or not target_query.strip():
            return 0.0
        
        # Try BERT first
        if self.bert_model:
            try:
                embeddings = self.bert_model.encode([abstract, target_query])
                similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
                return float(similarity)
            
            except Exception as e:
                self.logger.warning(f"BERT similarity computation failed: {e}")
        
        # Fallback to TF-IDF
        if self.tfidf_model:
            try:
                # Fit TF-IDF on both texts
                tfidf_matrix = self.tfidf_model.fit_transform([abstract, target_query])
                similarity = sklearn_cosine(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                return float(similarity)
            
            except Exception as e:
                self.logger.warning(f"TF-IDF similarity computation failed: {e}")
        
        # Final fallback: simple keyword overlap
        return self._simple_text_similarity(abstract, target_query)
    
    def _compute_keyword_score(self, abstract: str, category: str, 
                              substance: str, indication: str) -> Tuple[float, List[str]]:
        """Compute keyword-based relevance score"""
        
        if not abstract.strip():
            return 0.0, []
        
        abstract_lower = abstract.lower()
        matched_concepts = []
        score_components = []
        
        # Check substance mentions
        substance_clean = substance.replace('_', ' ').lower()
        if substance_clean in abstract_lower:
            score_components.append(0.3)  # High weight for exact substance match
            matched_concepts.append(f"substance: {substance}")
        
        # Check indication mentions
        indication_clean = indication.replace('_', ' ').lower()
        if indication_clean in abstract_lower:
            score_components.append(0.25)  # High weight for exact indication match
            matched_concepts.append(f"indication: {indication}")
        
        # Check category-specific concepts
        if category in self.combined_concepts:
            concept_matches = 0
            total_concepts = len(self.combined_concepts[category])
            
            for concept in self.combined_concepts[category]:
                if concept.lower() in abstract_lower:
                    concept_matches += 1
                    matched_concepts.append(f"concept: {concept}")
            
            # Concept coverage score
            concept_score = min(concept_matches / max(total_concepts * 0.1, 1), 1.0)
            score_components.append(concept_score * 0.4)  # Moderate weight for concept coverage
        
        # Check for study quality indicators
        quality_terms = [
            'randomized', 'controlled trial', 'double-blind', 'placebo',
            'meta-analysis', 'systematic review', 'clinical trial'
        ]
        
        quality_matches = sum(1 for term in quality_terms if term in abstract_lower)
        if quality_matches > 0:
            quality_score = min(quality_matches / len(quality_terms), 0.2)
            score_components.append(quality_score)
            matched_concepts.append(f"quality indicators: {quality_matches}")
        
        # Check for outcome measures
        if category in self.category_concepts and 'measures' in self.category_concepts[category]:
            measures = self.category_concepts[category]['measures']
            measure_matches = sum(1 for measure in measures if measure.lower() in abstract_lower)
            
            if measure_matches > 0:
                measure_score = min(measure_matches / len(measures), 0.15)
                score_components.append(measure_score)
                matched_concepts.append(f"outcome measures: {measure_matches}")
        
        # Combine score components
        final_score = sum(score_components)
        final_score = min(final_score, 1.0)  # Cap at 1.0
        
        return final_score, matched_concepts
    
    def _combine_scores(self, semantic_score: float, keyword_score: float) -> float:
        """Combine semantic and keyword scores with optimal weights"""
        
        # Weighted combination favoring semantic similarity but boosted by keywords
        combined = 0.6 * semantic_score + 0.4 * keyword_score
        
        # Bonus for high agreement between methods
        agreement_bonus = 0.0
        if abs(semantic_score - keyword_score) < 0.2:  # High agreement
            agreement_bonus = 0.05 * min(semantic_score, keyword_score)
        
        combined += agreement_bonus
        
        return min(combined, 1.0)  # Cap at 1.0
    
    def _compute_confidence(self, semantic_score: float, keyword_score: float, 
                          matched_concepts: List[str]) -> float:
        """Compute confidence in the relevance score"""
        
        # Base confidence from score agreement
        score_diff = abs(semantic_score - keyword_score)
        agreement_confidence = 1.0 - score_diff
        
        # Boost confidence with more matched concepts
        concept_confidence = min(len(matched_concepts) / 10.0, 0.3)
        
        # Boost for high scores
        score_confidence = max(semantic_score, keyword_score) * 0.2
        
        # Model availability confidence
        model_confidence = 0.1 if self.bert_model else 0.05
        
        total_confidence = agreement_confidence + concept_confidence + score_confidence + model_confidence
        
        return min(total_confidence, 1.0)
    
    def _simple_text_similarity(self, text1: str, text2: str) -> float:
        """Simple fallback similarity based on word overlap"""
        
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def save_scoring_cache(self, cache_file: str):
        """Save embeddings cache to file"""
        
        if self.embeddings_cache:
            cache_path = self.model_path / cache_file
            
            try:
                with open(cache_path, 'wb') as f:
                    pickle.dump(self.embeddings_cache, f)
                
                self.logger.info(f"Saved embeddings cache to {cache_path}")
            
            except Exception as e:
                self.logger.warning(f"Failed to save embeddings cache: {e}")
    
    def load_scoring_cache(self, cache_file: str):
        """Load embeddings cache from file"""
        
        cache_path = self.model_path / cache_file
        
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    self.embeddings_cache = pickle.load(f)
                
                self.logger.info(f"Loaded embeddings cache from {cache_path}")
                
            except Exception as e:
                self.logger.warning(f"Failed to load embeddings cache: {e}")
    
    def get_category_relevance_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get category-specific relevance score thresholds"""
        
        return {
            'sleep': {
                'high_relevance': 0.75,
                'medium_relevance': 0.5,
                'low_relevance': 0.25
            },
            'cognition': {
                'high_relevance': 0.7,
                'medium_relevance': 0.45,
                'low_relevance': 0.2
            },
            'mental_health': {
                'high_relevance': 0.8,
                'medium_relevance': 0.55,
                'low_relevance': 0.3
            },
            'cardiovascular': {
                'high_relevance': 0.75,
                'medium_relevance': 0.5,
                'low_relevance': 0.25
            },
            'renal_safety': {
                'high_relevance': 0.8,   # Higher threshold for safety studies
                'medium_relevance': 0.6,
                'low_relevance': 0.35
            }
        }


if __name__ == "__main__":
    # Example usage
    scorer = RelevanceScorer()
    
    # Test abstract
    test_abstract = """
    Background: Magnesium glycinate supplementation has been proposed to improve sleep quality.
    Methods: We conducted a randomized, double-blind, placebo-controlled trial with 120 adults
    with mild insomnia. Participants received either 400mg magnesium glycinate or placebo daily
    for 8 weeks. Sleep quality was assessed using the Pittsburgh Sleep Quality Index (PSQI).
    Results: Magnesium glycinate significantly improved PSQI scores compared to placebo
    (p=0.003). Sleep onset latency decreased by 15 minutes on average.
    Conclusions: Magnesium glycinate supplementation may be effective for improving sleep quality.
    """
    
    # Compute relevance score
    score = scorer.compute_relevance_score(
        test_abstract,
        target_category="sleep",
        target_substance="magnesium_glycinate", 
        target_indication="sleep_quality"
    )
    
    print("Relevance Scoring Results:")
    print(f"Semantic Score: {score.semantic_score:.3f}")
    print(f"Keyword Score: {score.keyword_score:.3f}")
    print(f"Combined Score: {score.combined_score:.3f}")
    print(f"Confidence: {score.confidence:.3f}")
    print(f"Matched Concepts: {score.matched_concepts}")
    print(f"Scoring Model: {score.scoring_model}")
    
    # Get thresholds
    thresholds = scorer.get_category_relevance_thresholds()
    sleep_thresholds = thresholds['sleep']
    
    if score.combined_score >= sleep_thresholds['high_relevance']:
        relevance_level = "High"
    elif score.combined_score >= sleep_thresholds['medium_relevance']:
        relevance_level = "Medium"
    elif score.combined_score >= sleep_thresholds['low_relevance']:
        relevance_level = "Low"
    else:
        relevance_level = "Very Low"
    
    print(f"Relevance Level: {relevance_level}")