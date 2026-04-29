"""
Domain-Based Test Recommendation Orchestrator
Coordinates domain classification and test recommendation
"""

import logging
import time
from typing import Dict, List, Any
from dataclasses import asdict

from services.domain_classifier import get_domain_classifier, DomainClassificationResult
from services.strategy_recommender import get_strategy_recommender, StrategyRecommendationResult
from services.llm_domain_classifier import get_llm_domain_classifier


logger = logging.getLogger(__name__)


class DomainTestOrchestrator:
    """
    Orchestrator for domain-based test recommendations
    
    Workflow:
    1. Classify domain from BRD + user stories
    2. Generate test recommendations for that domain
    3. Return combined results
    """
    
    def __init__(self):
        """Initialize orchestrator with agents"""
        logger.info("[Orchestrator] Initializing domain-based recommendation system...")
        
        self.domain_classifier = get_domain_classifier()
        self.strategy_recommender = get_strategy_recommender()
        self.llm_classifier = get_llm_domain_classifier()
        
        logger.info("[Orchestrator] ✓ Agents initialized (with LLM fallback)")
    
    async def analyze_requirements(
        self,
        brd_content: str,
        user_stories: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze BRD and user stories to generate domain-based test recommendations
        
        Args:
            brd_content: Business Requirements Document content
            user_stories: Optional list of user story dictionaries
        
        Returns:
            Dictionary with domain classification and test recommendations
        """
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info("[Orchestrator] STARTING DOMAIN-BASED RECOMMENDATION")
        logger.info(f"[Orchestrator] BRD length: {len(brd_content)} characters")
        logger.info(f"[Orchestrator] User stories: {len(user_stories) if user_stories else 0}")
        logger.info("=" * 80)
        
        try:
            # Step 1: Classify Domain
            logger.info("\n[Orchestrator] STEP 1: Classifying domain...")
            
            # Combine user stories into text
            user_stories_text = ""
            if user_stories:
                user_stories_text = "\n".join([
                    f"{story.get('title', '')} {story.get('description', '')} {story.get('acceptance_criteria', '')}"
                    for story in user_stories
                ])
            
            domain_result = self.domain_classifier.classify(brd_content, user_stories_text)
            
            logger.info(f"[Orchestrator] ✓ Domain identified: {domain_result.domain}")
            logger.info(f"[Orchestrator] ✓ Confidence: {domain_result.confidence_score:.1%}")
            
            # LLM Fallback: Trigger if confidence < 60%
            if domain_result.confidence_score < 0.60:
                logger.warning(f"[Orchestrator] ⚠ Low confidence ({domain_result.confidence_score:.1%}), triggering LLM fallback...")
                
                try:
                    # Call LLM classifier for better accuracy
                    llm_result = await self.llm_classifier.classify(brd_content, user_stories_text)
                    llm_domain = llm_result.get('domain', domain_result.domain)
                    llm_confidence = llm_result.get('confidence_score', 0.0)
                    
                    logger.info(f"[Orchestrator] ✓ LLM result: {llm_domain} ({llm_confidence:.1%})")
                    
                    # Use LLM result if more confident
                    if llm_confidence > domain_result.confidence_score:
                        logger.info(f"[Orchestrator] ✓ Using LLM result (better confidence: {llm_confidence:.1%} vs {domain_result.confidence_score:.1%})")
                        
                        # Create new domain result with LLM data
                        # Keep the original all_scores structure intact
                        domain_result = DomainClassificationResult(
                            domain=llm_domain,
                            confidence_score=llm_confidence,
                            keyword_score=domain_result.keyword_score,  # Keep original
                            context_score=domain_result.context_score,  # Keep original
                            evidence=llm_result.get('evidence', domain_result.evidence),
                            all_scores=domain_result.all_scores  # CRITICAL: Keep original structure
                        )
                    else:
                        logger.info(f"[Orchestrator] ⚠ LLM confidence ({llm_confidence:.1%}) not better than fast classifier ({domain_result.confidence_score:.1%}), keeping fast result")
                        
                except Exception as llm_error:
                    logger.error(f"[Orchestrator] ✗ LLM fallback failed: {str(llm_error)}")
                    logger.info(f"[Orchestrator] ℹ Using fast classifier result: {domain_result.domain} ({domain_result.confidence_score:.1%})")
            
            # Check confidence threshold (lowered to 0.35 for better acceptance)
            if domain_result.confidence_score < 0.35:
                logger.warning(f"[Orchestrator] ⚠ Low confidence ({domain_result.confidence_score:.1%})")
                return self._build_low_confidence_response(domain_result, user_stories)
            
            # Step 2: Generate Test Recommendations
            logger.info("\n[Orchestrator] STEP 2: Generating test recommendations...")
            
            recommendations = self.strategy_recommender.recommend(
                domain=domain_result.domain,
                user_stories=user_stories
            )
            
            logger.info(f"[Orchestrator] ✓ Standard tests: {len(recommendations.standard_tests)}")
            logger.info(f"[Orchestrator] ✓ Recommended tests: {len(recommendations.recommended_tests)}")
            
            # Step 3: Build Response
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            response = self._build_success_response(
                domain_result=domain_result,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
            logger.info("\n[Orchestrator] ✓ WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info(f"[Orchestrator] Processing time: {processing_time:.2f}ms")
            logger.info("=" * 80)
            
            return response
            
        except Exception as e:
            logger.error(f"[Orchestrator] ✗ Workflow failed: {str(e)}", exc_info=True)
            raise Exception(f"Domain-based recommendation failed: {str(e)}")
    
    def _build_success_response(
        self,
        domain_result: DomainClassificationResult,
        recommendations: StrategyRecommendationResult,
        processing_time: float
    ) -> Dict[str, Any]:
        """Build successful response"""
        
        # Convert all_scores to ensure JSON serializability
        all_scores_dict = {}
        for domain, scores in domain_result.all_scores.items():
            all_scores_dict[domain] = {
                "keyword": float(scores.get("keyword", 0)),
                "context": float(scores.get("context", 0)),
                "final": float(scores.get("final", 0))
            }
        
        return {
            "status": "SUCCESS",
            "processing_time_ms": float(processing_time),
            "domain_classification": {
                "domain": str(domain_result.domain),
                "confidence_score": float(domain_result.confidence_score),
                "keyword_score": float(domain_result.keyword_score),
                "context_score": float(domain_result.context_score),
                "evidence": list(domain_result.evidence),
                "all_scores": all_scores_dict
            },
            "test_recommendations": {
                "standard_tests": [
                    {
                        "type": str(test.type),
                        "category": str(test.category),
                        "reason": str(test.reason),
                        "priority": str(test.priority)
                    }
                    for test in recommendations.standard_tests
                ],
                "recommended_tests": [
                    {
                        "type": str(test.type),
                        "category": str(test.category),
                        "reason": str(test.reason),
                        "priority": str(test.priority)
                    }
                    for test in recommendations.recommended_tests
                ]
            },
            "metadata": {
                "domain": str(domain_result.domain),
                "total_tests": len(recommendations.standard_tests) + len(recommendations.recommended_tests),
                "confidence_level": self._get_confidence_level(domain_result.confidence_score),
                "processing_time_ms": float(processing_time)
            }
        }
    
    def _build_low_confidence_response(
        self,
        domain_result: DomainClassificationResult,
        user_stories: List[Dict]
    ) -> Dict[str, Any]:
        """Build response for low confidence scenarios"""
        
        # Get top 3 possible domains
        sorted_domains = sorted(
            domain_result.all_scores.items(),
            key=lambda x: x[1]['final'],
            reverse=True
        )[:3]
        
        return {
            "status": "LOW_CONFIDENCE",
            "message": "Unable to confidently identify domain. Please review and select manually.",
            "domain_classification": {
                "top_candidates": [
                    {
                        "domain": str(domain),
                        "confidence": float(scores['final']),
                        "keyword_score": float(scores['keyword']),
                        "context_score": float(scores['context'])
                    }
                    for domain, scores in sorted_domains
                ]
            },
            "suggestion": "Consider adding more domain-specific details to the BRD or user stories",
            "test_recommendations": {
                "standard_tests": [],
                "recommended_tests": []
            },
            "metadata": {
                "domain": str(domain_result.domain),
                "total_tests": 0,
                "confidence_level": "LOW",
                "processing_time_ms": 0.0
            }
        }
    
    def _get_confidence_level(self, score: float) -> str:
        """Convert confidence score to level"""
        if score >= 0.7:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"


# Singleton instance
_orchestrator_instance = None

def get_orchestrator() -> DomainTestOrchestrator:
    """Get or create singleton instance of orchestrator"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = DomainTestOrchestrator()
    return _orchestrator_instance
