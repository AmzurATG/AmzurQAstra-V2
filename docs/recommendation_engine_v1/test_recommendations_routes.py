from typing import Dict, Any, List, Optional, Union
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator, validator
import traceback
from utils.shared_storage import user_stories_storage, processing_results
from services.recommendation_engine import TestingRecommendationEngine,  TEST_TEMPLATES
from services.domain_test_orchestrator import get_orchestrator


# Initialize engine with LLM filtering enabled for edge case detection
# Set use_llm_filtering=True to catch informal out-of-scope phrases that regex might miss
testing_recommendation_engine = TestingRecommendationEngine(use_llm_filtering=True)


router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic models for new domain-based endpoint
class UserStoryInput(BaseModel):
    """User story input model"""
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[Union[str, List[str]]] = None
    
    @field_validator('acceptance_criteria', mode='before')
    @classmethod
    def convert_acceptance_criteria(cls, v):
        """Convert acceptance_criteria to string if it's a list or other type"""
        if v is None:
            return None
        if isinstance(v, list):
            # Join list items with newlines, filter out empty strings
            return '\n'.join(str(item) for item in v if item)
        if isinstance(v, str):
            return v
        # Convert any other type to string
        return str(v)


class DomainAnalysisRequest(BaseModel):
    """Request model for domain-based analysis"""
    brd_content: str = Field(..., description="BRD content")
    user_stories: Optional[List[UserStoryInput]] = Field(default_factory=list, description="Optional user stories")
    
    @validator('brd_content')
    def validate_brd_content(cls, v):
        """Validate BRD content has sufficient text (not just whitespace)"""
        if not v or not v.strip():
            raise ValueError("BRD content cannot be empty")
        
        # Check if content has meaningful text (more than just whitespace/newlines)
        cleaned_content = v.strip()
        if len(cleaned_content) < 50:
            raise ValueError(
                "The uploaded BRD document does not contain sufficient text content. "
                "It appears to only have images/screenshots. "
                "Please upload a BRD document with at least 50 characters of text content for domain classification."
            )
        return v

# Enhanced Test Recommendations Endpoint 
@router.post("/generate-test-recommendations")
async def generate_test_recommendations(request: Dict[str, Any]):
    """
    Generate test recommendations using the new simplified recommendation engine.
    Prioritizes direct content from the request body (brd_content, user_stories)
    and falls back to ID-based lookup if direct content is not provided.
    """
    try:
        logger.info("Generating test recommendations with simplified engine")
        
        # --- START CHANGES ---
        
        # Extract direct content and IDs from the request
        document_id = request.get('document_id')
        session_id = request.get('session_id')
        direct_brd_content = request.get('brd_content')
        direct_user_stories = request.get('user_stories') # Can be list of dicts or a single string
        
        # DEBUG: Log what we received
        logger.info(f"DEBUG: Received request data: document_id={document_id}, session_id={session_id}")
        logger.info(f"DEBUG: direct_brd_content type={type(direct_brd_content)}, length={len(direct_brd_content) if direct_brd_content else 0}")
        logger.info(f"DEBUG: direct_user_stories type={type(direct_user_stories)}, count={len(direct_user_stories) if direct_user_stories else 0}")
        
        brd_content = ""
        user_stories_content = ""
        user_stories_list = [] # Keep track of the list format if provided

        # Priority 1: Use direct content if available
        if direct_brd_content:
            brd_content = direct_brd_content
            logger.info("Using BRD content directly from request body.")
        # Priority 2: Fallback to ID lookup for BRD content
        elif document_id:
            logger.info(f"Attempting to retrieve BRD content using document_id: {document_id}")
            if document_id in processing_results:
                brd_content = processing_results[document_id].get('content', '')
                logger.info(f"Retrieved BRD content from processing_results (length: {len(brd_content)})")
            else:
                 logger.warning(f"BRD document_id {document_id} not found in storage.")

        # Priority 1: Use direct user stories if available
        if direct_user_stories:
            logger.info("Using user stories directly from request body.")
            if isinstance(direct_user_stories, list):
                user_stories_list = direct_user_stories
                # Convert list of user story objects/dicts to a single text block
                user_stories_texts = []
                for story in user_stories_list:
                     # Handle potential dict or object format
                    title = ""
                    description = ""
                    key = "N/A"
                    if isinstance(story, dict):
                        title = story.get('title', story.get('summary', ''))
                        description = story.get('description', '')
                        key = story.get('jira_key', story.get('key', 'N/A'))
                    elif hasattr(story, 'title') and hasattr(story, 'description'): # Basic object check
                         title = getattr(story, 'title', '')
                         description = getattr(story, 'description', '')
                         key = getattr(story, 'jira_key', getattr(story, 'key', 'N/A'))
                    else:
                        # Fallback if it's just a string or unexpected format
                         story_text = str(story)
                         user_stories_texts.append(story_text)
                         continue # Skip detailed formatting for this item

                    story_text = f"Story {key}: {title}. {description}"
                    user_stories_texts.append(story_text.strip())
                user_stories_content = "\n\n".join(user_stories_texts) # Use double newline for better separation
            elif isinstance(direct_user_stories, str):
                # If it's already a string, use it directly
                user_stories_content = direct_user_stories
                # Attempt to parse into list structure if needed later (simple split)
                user_stories_list = [{"id": f"story_{i+1}", "description": s} for i, s in enumerate(user_stories_content.split('\n\n'))]
            else:
                 logger.warning("Received user_stories in unexpected format, attempting to convert to string.")
                 user_stories_content = str(direct_user_stories)

        # Priority 2: Fallback to ID lookup for user stories
        elif session_id:
            logger.info(f"Attempting to retrieve user stories using session_id: {session_id}")
            if session_id in user_stories_storage:
                stories_data = user_stories_storage[session_id]
                # Adjust key based on actual storage structure ('stories' or 'user_stories')
                user_stories_list = stories_data.get('user_stories', stories_data.get('stories', []))
                logger.info(f"Retrieved {len(user_stories_list)} user stories from user_stories_storage.")

                # Convert user stories list to a single text block
                user_stories_texts = []
                for story in user_stories_list:
                     if isinstance(story, dict):
                         title = story.get('title', story.get('summary', ''))
                         description = story.get('description', '')
                         key = story.get('jira_key', story.get('key', 'N/A'))
                         story_text = f"Story {key}: {title}. {description}"
                         user_stories_texts.append(story_text.strip())
                     else:
                         user_stories_texts.append(str(story))
                user_stories_content = "\n\n".join(user_stories_texts)
            else:
                 logger.warning(f"User stories session_id {session_id} not found in storage.")

        # --- END CHANGES ---

        # Check if we have *any* content to analyze
        if not brd_content and not user_stories_content:
            logger.error("No content available for analysis from either direct input or storage lookup.")
            raise HTTPException(status_code=404, detail="No content found for analysis. Please provide BRD/user stories directly or ensure they were processed correctly with IDs.")

        logger.info(f"Analyzing BRD content: {len(brd_content)} chars, User stories: {len(user_stories_content)} chars")

        # Generate recommendations using the new engine
        # Convert user stories text back to list format for engine
        user_stories_list = []
        if user_stories_content:
            for story_text in user_stories_content.split("\n\n"):
                if story_text.strip():
                    parts = story_text.split(": ", 1)
                    story_id = parts[0].replace("Story ", "") if len(parts) > 1 else "N/A"
                    content = parts[1] if len(parts) > 1 else story_text
                    user_stories_list.append({
                        "id": story_id,
                        "title": content.split(".")[0] if "." in content else content[:100],
                        "description": content
                    })
        
        # Call the async method
        import asyncio
        result = await testing_recommendation_engine.generate_recommendations(
            brd_content,
            user_stories_list if user_stories_list else None,
            confidence_threshold=0.08  # Lower threshold for better recall
        )
        recommendations = result.get("recommendations", [])
        filtered_content = result.get("filtered_content", {})

        # Transform recommendations to match frontend expectations
        standard_tests = []
        recommended_tests = []

        for rec in recommendations:
            # Get template data for fallback
            template_data = TEST_TEMPLATES.get(rec["test_type"], {})
            
            # NEW STRUCTURE: Use new fields (overview, why_recommended, triggering_requirements, llm_assessment)
            # Build blocks array for frontend from triggering_requirements
            blocks = []
            keywords = []
            story_ids = []
            
            # Extract data from new structure
            if "triggering_requirements" in rec and rec["triggering_requirements"]:
                for req in rec["triggering_requirements"][:5]:  # Top 5 triggers
                    req_type = req.get("type", "")
                    artifact = req.get("artifact", "")
                    
                    if req_type == "Keyword Match":
                        # Extract keyword from artifact like "Keyword: 'select'"
                        keyword = artifact.replace("Keyword: ", "").strip("'\"")
                        keywords.append(keyword)
                    elif req_type == "BRD Section":
                        blocks.append({
                            "evidence": artifact[:150] + "..." if len(artifact) > 150 else artifact,
                            "rationale": rec.get("why_recommended", f"BRD section shows relevance to {rec['test_type']}")[:200]
                        })
                    elif req_type == "User Story":
                        # Extract story ID from artifact like "US-001: Description"
                        story_id = artifact.split(":")[0].strip() if ":" in artifact else artifact[:20]
                        story_ids.append(story_id)
                        blocks.append({
                            "evidence": artifact[:150] + "..." if len(artifact) > 150 else artifact,
                            "rationale": rec.get("llm_assessment", f"This user story requires {rec['test_type']}")[:200]
                        })
            
            # Use new structure fields with fallbacks for backward compatibility
            description = rec.get("overview") or rec.get("description", template_data.get("description", ""))
            justification = rec.get("why_recommended") or rec.get("why_needed") or rec.get("llm_rationale") or description
            
            test_data = {
                "id": f"{rec['category']}_{rec['test_type'].lower().replace(' ', '_').replace('/', '_')}",
                "test_type": rec["test_type"],
                "category": rec["category"],
                "similarity": round(rec["confidence"] * 100, 1),  # Convert 0-1 to percentage
                "description": description,
                "display_description": rec.get("display_description", description[:100]),  # Short description for UI
                "justification": justification,
                "blocks": blocks,  # Evidence blocks with LLM rationale
                "brd_sections": rec.get("brd_sections", []),  # BRD paragraphs that triggered this test
                "user_stories": rec.get("user_stories", []),  # Matched user stories with similarity
                "sources": rec.get("sources", ["BRD"]),  # Use new sources field
                "keywords": keywords,  # Extracted from triggering_requirements
                "story_ids": story_ids,  # Extracted from triggering_requirements
                "priority": "HIGH" if rec["confidence"] >= 0.6 else "MEDIUM" if rec["confidence"] >= 0.4 else "LOW",
                "risk_factor": rec.get("risk_factor", "N/A"),
                "requirement_type": rec.get("requirement_type", "N/A"),
                "decision_logic": rec.get("llm_assessment", "AI-based recommendation")  # Use llm_assessment for decision logic
            }

            if rec["category"] == "standard":
                standard_tests.append(test_data)
            else:
                recommended_tests.append(test_data)

        # Format the response to match frontend expectations
        has_matches = len(standard_tests) > 0 or len(recommended_tests) > 0
        
        response_data = {
            "success": True,
            "message": f"Generated {len(standard_tests)} standard and {len(recommended_tests)} recommended test types",
            "standard_tests": standard_tests,
            "recommended_tests": recommended_tests,
            "filtered_content": filtered_content,
            "summary": result.get("summary", {}),
            "match_status": {
                "has_matches": has_matches,
                "total_matches": len(recommendations),
                "standard_count": len(standard_tests),
                "recommended_count": len(recommended_tests)
            },
            "metadata": {
                "total_recommendations": len(recommendations),
                "brd_content_length": len(brd_content),
                "user_stories_count": len(user_stories_list) if user_stories_list else 0,
                "engine": "ai_driven_multi_layer_engine_v2.0",
                "model_used": result.get("model_used", "sentence-transformers/all-mpnet-base-v2"),
                "timestamp": result.get("timestamp")
            }
        }

        logger.info(f"Successfully generated {len(standard_tests)} standard tests and {len(recommended_tests)} recommended tests")
        
        # DEBUG: Log the actual response being sent
        logger.info(f"DEBUG: Response keys: {list(response_data.keys())}")
        logger.info(f"DEBUG: Has match_status field: {'match_status' in response_data}")
        if 'match_status' in response_data:
            logger.info(f"DEBUG: match_status value: {response_data['match_status']}")
        logger.info(f"DEBUG: Sample standard test: {standard_tests[0] if standard_tests else 'None'}")
        logger.info(f"DEBUG: Sample recommended test: {recommended_tests[0] if recommended_tests else 'None'}")
        
        return response_data

    except HTTPException as e:
        # Re-raise HTTP exceptions directly
        raise
    except Exception as e:
        error_msg = f"Test recommendations generation failed: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/domain-based-recommendations")
async def domain_based_recommendations(request: DomainAnalysisRequest):
    """
    NEW: Domain-based test recommendations using multi-stage pipeline
    
    This endpoint:
    1. Classifies application domain (Healthcare, Retail, CRM, etc.) using keyword + context scoring
    2. Recommends domain-specific testing types (standard + recommended)
    3. Returns confidence scores and evidence
    
    Multi-stage approach:
    - 50% keyword matching (exact term frequency)
    - 50% context understanding (semantic embeddings via sentence-transformers)
    - Confidence threshold: <0.5 = manual review needed
    
    No LLM costs - uses local embeddings only
    """
    try:
        logger.info("=== Domain-Based Recommendation Request ===")
        logger.info(f"BRD content length: {len(request.brd_content)} characters")
        logger.info(f"User stories count: {len(request.user_stories)}")
        
        # Convert Pydantic models to dicts
        user_stories_dicts = [story.dict() for story in request.user_stories]
        
        # Get orchestrator singleton
        orchestrator = get_orchestrator()
        
        # Run domain analysis pipeline (async with LLM fallback support)
        result = await orchestrator.analyze_requirements(
            brd_content=request.brd_content,
            user_stories=user_stories_dicts
        )
        
        # DEBUG: Log full result structure
        logger.info(f"=== ORCHESTRATOR RESULT ===")
        logger.info(f"Result keys: {list(result.keys())}")
        logger.info(f"Status: {result.get('status', 'UNKNOWN')}")
        
        # Log classification results
        domain_classification = result.get('domain_classification', {})
        logger.info(f"Domain identified: {domain_classification.get('domain', 'unknown')}")
        logger.info(f"Confidence score: {domain_classification.get('confidence_score', 0.0):.2f}")
        
        # Get metadata and confidence level
        metadata = result.get('metadata', {})
        confidence_level = metadata.get('confidence_level', 'UNKNOWN')
        logger.info(f"Confidence level: {confidence_level}")
        
        # Log recommendations count - check both possible keys
        test_recommendations = result.get('test_recommendations', {})
        standard_tests = test_recommendations.get('standard_tests', [])
        recommended_tests = test_recommendations.get('recommended_tests', [])
        logger.info(f"Generated {len(standard_tests)} standard + {len(recommended_tests)} recommended tests")
        
        # Return success response
        return {
            "success": True,
            "message": "Domain analysis completed successfully",
            "data": result
        }
        
    except ValueError as ve:
        # Handle validation errors (e.g., missing config file)
        error_msg = f"Validation error: {str(ve)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=error_msg)
        
    except HTTPException as e:
        # Re-raise HTTP exceptions directly
        raise
        
    except Exception as e:
        error_msg = f"Domain-based recommendation failed: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

