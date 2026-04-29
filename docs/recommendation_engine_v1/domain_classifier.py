"""
Domain Classifier - Agent 1
Identifies application domain from BRD and user stories using keyword + context scoring
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Try to import sentence-transformers for context scoring
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

logger = logging.getLogger(__name__)


def get_resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # Running in normal Python environment
        base_path = Path(__file__).parent.parent
    return base_path / relative_path


@dataclass
class DomainClassificationResult:
    """Result of domain classification"""
    domain: str
    confidence_score: float
    keyword_score: float
    context_score: float
    evidence: List[str]
    all_scores: Dict[str, Dict[str, float]]


class DomainClassifier:
    """
    Agent 1: Domain Classifier
    
    Uses two-stage approach:
    1. Keyword matching (50% weight)
    2. Context understanding with embeddings (50% weight)
    """
    
    def __init__(self, config_path: str = None):
        """Initialize domain classifier"""
        
        # Load domain mappings
        if config_path is None:
            config_path = get_resource_path("config/domain_mapping.json")
        
        with open(config_path, 'r') as f:
            self.domain_mappings = json.load(f)
        
        logger.info(f"[DomainClassifier] Loaded {len(self.domain_mappings)} domain mappings")
        
        # Initialize embeddings model if available
        self.model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                logger.info("[DomainClassifier] Loading embedding model...")
                self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
                logger.info("[DomainClassifier] ✓ Embedding model loaded")
            except Exception as e:
                logger.warning(f"[DomainClassifier] Could not load embeddings: {e}")
                self.model = None
        
        logger.info(f"[DomainClassifier] Initialized (Embeddings: {'enabled' if self.model else 'disabled'})")
    
    def classify(self, brd_text: str, user_stories_text: str = "") -> DomainClassificationResult:
        """
        Classify domain from BRD and user stories
        
        Args:
            brd_text: Business Requirements Document content
            user_stories_text: Combined user stories text (optional)
        
        Returns:
            DomainClassificationResult with domain and confidence
        """
        logger.info("[DomainClassifier] Starting classification...")
        
        # Combine texts
        combined_text = f"{brd_text} {user_stories_text}".lower()
        
        # Stage 1: Keyword Scoring (50% weight)
        keyword_scores = self._calculate_keyword_scores(combined_text)
        
        # Stage 2: Context Scoring (50% weight)
        context_scores = self._calculate_context_scores(combined_text)
        
        # Combine scores with 50/50 weighting
        final_scores = {}
        for domain in self.domain_mappings.keys():
            keyword_score = keyword_scores.get(domain, 0.0)
            context_score = context_scores.get(domain, 0.0)
            
            # 50% keywords + 50% context
            final_score = (keyword_score * 0.5) + (context_score * 0.5)
            
            final_scores[domain] = {
                'final': final_score,
                'keyword': keyword_score,
                'context': context_score
            }
        
        # Find best domain
        best_domain = max(final_scores.keys(), key=lambda d: final_scores[d]['final'])
        best_score = final_scores[best_domain]
        
        # Generate evidence
        evidence = self._generate_evidence(combined_text, best_domain)
        
        logger.info(f"[DomainClassifier] ✓ Result: {best_domain}")
        logger.info(f"[DomainClassifier] ✓ Confidence: {best_score['final']:.1%}")
        logger.info(f"[DomainClassifier] ✓ Breakdown: Keywords={best_score['keyword']:.1%}, Context={best_score['context']:.1%}")
        
        return DomainClassificationResult(
            domain=best_domain,
            confidence_score=best_score['final'],
            keyword_score=best_score['keyword'],
            context_score=best_score['context'],
            evidence=evidence,
            all_scores=final_scores
        )
    
    def _calculate_keyword_scores(self, text: str) -> Dict[str, float]:
        """Calculate keyword match scores for each domain"""
        scores = {}
        
        for domain, config in self.domain_mappings.items():
            keywords = config.get('keywords', [])
            if not keywords:
                scores[domain] = 0.0
                continue
            
            # Count keyword matches
            matches = 0
            for keyword in keywords:
                # Use word boundaries for better matching
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, text):
                    matches += 1
            
            # Normalize by total keywords
            score = matches / len(keywords) if keywords else 0.0
            scores[domain] = score
        
        return scores
    
    def _calculate_context_scores(self, text: str) -> Dict[str, float]:
        """Calculate context similarity scores using embeddings"""
        
        if not self.model:
            # Fallback: return zero scores if embeddings not available
            return {domain: 0.0 for domain in self.domain_mappings.keys()}
        
        try:
            # Encode the input text
            text_embedding = self.model.encode([text])
            
            scores = {}
            for domain, config in self.domain_mappings.items():
                business_contexts = config.get('business_context', [])
                
                if not business_contexts:
                    scores[domain] = 0.0
                    continue
                
                # Encode all business context descriptions
                context_embeddings = self.model.encode(business_contexts)
                
                # Calculate cosine similarity with each context
                similarities = cosine_similarity(text_embedding, context_embeddings)[0]
                
                # Average similarity across all contexts
                avg_similarity = sum(similarities) / len(similarities)
                
                scores[domain] = max(0.0, avg_similarity)  # Ensure non-negative
            
            return scores
            
        except Exception as e:
            logger.warning(f"[DomainClassifier] Context scoring failed: {e}")
            return {domain: 0.0 for domain in self.domain_mappings.keys()}
    
    def _generate_evidence(self, text: str, domain: str, max_evidence: int = 5) -> List[str]:
        """Generate evidence for why this domain was selected"""
        
        evidence = []
        keywords = self.domain_mappings[domain].get('keywords', [])
        
        # Find matched keywords
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
            if re.search(pattern, text):
                evidence.append(keyword)
                if len(evidence) >= max_evidence:
                    break
        
        return evidence


# Singleton instance
_classifier_instance = None

def get_domain_classifier() -> DomainClassifier:
    """Get or create singleton instance of domain classifier"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = DomainClassifier()
    return _classifier_instance
