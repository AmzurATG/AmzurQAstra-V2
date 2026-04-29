"""
LLM-Based Domain Classifier
Fallback classifier using GPT/Gemini for low-confidence cases
"""

import json
import logging
import sys
from typing import Dict, List, Any
from pathlib import Path

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


class LLMDomainClassifier:
    """
    LLM-based domain classifier for low-confidence fallback
    Uses GPT-4/Gemini to analyze BRD and classify domain
    """
    
    def __init__(self):
        """Initialize LLM classifier"""
        self.llm_client = None
        self._load_domain_definitions()
        self._init_llm_client()
    
    def _load_domain_definitions(self):
        """Load domain definitions from config"""
        config_path = get_resource_path("config/domain_mapping.json")
        with open(config_path, 'r') as f:
            self.domain_mappings = json.load(f)
        
        # Build domain descriptions for prompt
        self.domain_descriptions = {}
        for domain, config in self.domain_mappings.items():
            std_tests = ", ".join(config.get('standard_testing', [])[:3])
            contexts = "; ".join(config.get('business_context', [])[:2])
            self.domain_descriptions[domain] = f"{std_tests} | {contexts}"
    
    def _init_llm_client(self):
        """Initialize LiteLLM client"""
        try:
            from services.litellm_client import get_litellm_client
            self.llm_client = get_litellm_client()
            logger.info("[LLM Classifier] ✓ LiteLLM client initialized")
        except Exception as e:
            logger.warning(f"[LLM Classifier] Could not initialize LLM client: {e}")
            self.llm_client = None
    
    async def classify(self, brd_text: str, user_stories_text: str = "") -> Dict[str, Any]:
        """
        Classify domain using LLM
        
        Args:
            brd_text: BRD content
            user_stories_text: User stories text
        
        Returns:
            Dict with domain, confidence_score, evidence, reasoning
        """
        if not self.llm_client:
            logger.error("[LLM Classifier] LLM client not available")
            return self._fallback_response()
        
        try:
            prompt = self._build_classification_prompt(brd_text, user_stories_text)
            
            messages = [
                {"role": "system", "content": "You are an expert software QA analyst specializing in domain classification."},
                {"role": "user", "content": prompt}
            ]
            
            logger.info("[LLM Classifier] Sending classification request to LLM...")
            response = await self.llm_client.chat_completion_with_json(
                messages=messages,
                temperature=0.1,  # Low temperature for consistency
                max_tokens=800
            )
            
            # Parse JSON response
            result = json.loads(response)
            logger.info(f"[LLM Classifier] ✓ Domain identified: {result.get('domain')} ({result.get('confidence_score', 0):.1%})")
            
            return result
            
        except Exception as e:
            logger.error(f"[LLM Classifier] Classification failed: {e}", exc_info=True)
            return self._fallback_response()
    
    def _build_classification_prompt(self, brd_text: str, user_stories_text: str) -> str:
        """Build LLM prompt for domain classification"""
        
        # Build domain list with descriptions
        domain_list = []
        for i, (domain, desc) in enumerate(self.domain_descriptions.items(), 1):
            domain_list.append(f"{i}. **{domain}**\n   - {desc}")
        
        domains_text = "\n".join(domain_list)
        
        # Truncate content if too long
        max_brd_length = 3000
        max_stories_length = 1500
        
        brd_content = brd_text[:max_brd_length] + ("..." if len(brd_text) > max_brd_length else "")
        stories_content = user_stories_text[:max_stories_length] + ("..." if len(user_stories_text) > max_stories_length else "")
        
        prompt = f"""You are an expert software QA analyst specializing in domain classification for test strategy planning.

**Task**: Analyze the BRD and user stories below to identify the PRIMARY application domain.

**Available Domains**:
{domains_text}

**BRD Content**:
{brd_content}

**User Stories**:
{stories_content}

**Instructions**:
1. Identify the PRIMARY domain from the list above
2. Provide confidence score (0.0 to 1.0) - be realistic, not overly confident
3. List 3-5 key evidence phrases from the BRD that support your classification
4. Provide brief reasoning (2-3 sentences)
5. If confidence < 0.7, provide top 3 candidate domains with scores

**Response Format** (JSON only, no markdown):
{{
  "domain": "Exact domain name from list above",
  "confidence_score": 0.85,
  "evidence": ["specific phrase from BRD", "another phrase", "third phrase"],
  "reasoning": "Brief explanation of why this domain was selected",
  "top_candidates": [
    {{"domain": "Domain Name", "confidence": 0.85}},
    {{"domain": "Another Domain", "confidence": 0.45}},
    {{"domain": "Third Domain", "confidence": 0.30}}
  ]
}}

Respond with ONLY the JSON object, no additional text."""
        
        return prompt
    
    def _fallback_response(self) -> Dict[str, Any]:
        """Return fallback response when LLM fails"""
        return {
            "domain": "General Web Application",
            "confidence_score": 0.3,
            "evidence": [],
            "reasoning": "LLM classifier unavailable, defaulting to General Web Application",
            "top_candidates": [
                {"domain": "General Web Application", "confidence": 0.3}
            ]
        }


# Singleton instance
_llm_classifier_instance = None

def get_llm_domain_classifier() -> LLMDomainClassifier:
    """Get or create singleton instance of LLM domain classifier"""
    global _llm_classifier_instance
    if _llm_classifier_instance is None:
        _llm_classifier_instance = LLMDomainClassifier()
    return _llm_classifier_instance
