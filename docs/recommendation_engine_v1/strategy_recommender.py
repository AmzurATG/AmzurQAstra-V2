"""
Strategy Recommender - Agent 2
Recommends testing types based on identified domain
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass


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
class TestRecommendation:
    """Individual test recommendation"""
    type: str
    category: str  # 'standard' or 'recommended'
    reason: str
    priority: str = "MEDIUM"


@dataclass
class StrategyRecommendationResult:
    """Result of strategy recommendation"""
    domain: str
    standard_tests: List[TestRecommendation]
    recommended_tests: List[TestRecommendation]
    metadata: Dict


class StrategyRecommender:
    """
    Agent 2: Strategy Recommender
    
    Takes identified domain and returns appropriate testing types
    """
    
    def __init__(self, config_path: str = None):
        """Initialize strategy recommender"""
        
        # Load domain mappings
        if config_path is None:
            config_path = get_resource_path("config/domain_mapping.json")
        
        with open(config_path, 'r') as f:
            self.domain_mappings = json.load(f)
        
        logger.info(f"[StrategyRecommender] Loaded {len(self.domain_mappings)} domain mappings")
    
    def recommend(self, domain: str, user_stories: List[Dict] = None) -> StrategyRecommendationResult:
        """
        Generate test recommendations for a domain
        
        Args:
            domain: Identified domain name
            user_stories: Optional list of user stories for context
        
        Returns:
            StrategyRecommendationResult with test recommendations
        """
        logger.info(f"[StrategyRecommender] Generating recommendations for: {domain}")
        
        if domain not in self.domain_mappings:
            logger.warning(f"[StrategyRecommender] Unknown domain: {domain}, using General Web Application")
            domain = "General Web Application"
        
        domain_config = self.domain_mappings[domain]
        
        # Get standard and recommended testing types
        standard_tests_raw = domain_config.get('standard_testing', [])
        recommended_tests_raw = domain_config.get('recommended_testing', [])
        
        # Convert to TestRecommendation objects
        standard_tests = []
        for test_type in standard_tests_raw:
            standard_tests.append(TestRecommendation(
                type=test_type,
                category='standard',
                reason=f"Standard practice for {domain} domain",
                priority=self._determine_priority(test_type, domain)
            ))
        
        recommended_tests = []
        for test_type in recommended_tests_raw:
            recommended_tests.append(TestRecommendation(
                type=test_type,
                category='recommended',
                reason=f"Recommended for {domain} applications",
                priority=self._determine_priority(test_type, domain)
            ))
        
        logger.info(f"[StrategyRecommender] ✓ Standard tests: {len(standard_tests)}")
        logger.info(f"[StrategyRecommender] ✓ Recommended tests: {len(recommended_tests)}")
        
        return StrategyRecommendationResult(
            domain=domain,
            standard_tests=standard_tests,
            recommended_tests=recommended_tests,
            metadata={
                'total_tests': len(standard_tests) + len(recommended_tests),
                'standard_count': len(standard_tests),
                'recommended_count': len(recommended_tests)
            }
        )
    
    def _determine_priority(self, test_type: str, domain: str) -> str:
        """Determine priority level for a test type"""
        
        # High priority keywords
        high_priority_keywords = [
            'security', 'compliance', 'hipaa', 'data privacy',
            'payment', 'authentication', 'authorization'
        ]
        
        test_lower = test_type.lower()
        
        for keyword in high_priority_keywords:
            if keyword in test_lower:
                return "HIGH"
        
        # Medium priority for most tests
        return "MEDIUM"


# Singleton instance
_recommender_instance = None

def get_strategy_recommender() -> StrategyRecommender:
    """Get or create singleton instance of strategy recommender"""
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = StrategyRecommender()
    return _recommender_instance
