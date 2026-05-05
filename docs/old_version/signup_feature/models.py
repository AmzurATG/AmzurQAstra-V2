from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any ,TypedDict
from datetime import datetime
import re


class SecurityQuestion(BaseModel):
    id: Optional[str] = None
    question: str
    answer: str


class JiraConfigModel(BaseModel):
    """Model for storing Jira configuration"""
    jira_url: str
    email: str
    api_token: str
    project_key: str
    default_issue_type: str = "Bug"
    default_priority: str = "Medium"

class JiraConfigResponse(BaseModel):
    """Response model for Jira config"""
    config_id: Optional[int] = None
    user_id: int
    jira_url: str
    email: str
    project_key: str
    default_issue_type: str = "Bug"
    default_priority: str = "Medium"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class CreateBugRequest(BaseModel):
    """Model for creating a bug in Jira"""
    test_name: str
    test_description: Optional[str] = None
    error_message: Optional[str] = None
    build_id: Optional[str] = None
    build_url: Optional[str] = None
    environment: Optional[str] = None
    priority: Optional[str] = "Medium"
    issue_type: Optional[str] = "Bug"
    # Optional: Override user's default Jira config
    jira_url: Optional[str] = None
    email: Optional[str] = None
    api_token: Optional[str] = None
    project_key: Optional[str] = None

    
class UserCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    email: EmailStr
    country_code: Optional[str] = None  # New field for country code
    phone_number: Optional[str] = None
    password: str
    confirm_password: str
    security_questions: Optional[List[SecurityQuestion]] = []  # Make security_questions optional with default empty list
    
    @validator('email')
    def validate_business_email(cls, v):
        # Check if it's a business email (not from common free email providers)
        free_email_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'mail.com', 'protonmail.com',
            'zoho.com', 'yandex.com', 'gmx.com', 'live.com'
        ]
        
        domain = v.split('@')[1].lower() if '@' in v else ''
        
        if domain in free_email_domains:
            raise ValueError('Please use a business email address (you@company.com)')
        
        return v
    
    @validator('phone_number')
    def validate_phone_number(cls, v, values):
        if not v:
            return None
            
        # Strip non-digit characters
        v_clean = ''.join(filter(str.isdigit, v or ''))
        
        # Phone number validation should consider country code
        country_code = values.get('country_code', '')
        
        # Simple validation - adjust as needed for your requirements
        if country_code and v_clean:
            # Don't include country code in the phone number if it's already provided separately
            if v_clean.startswith(country_code.replace('+', '')):
                v_clean = v_clean[len(country_code.replace('+', '')):]
        
        # Ensure reasonable length for phone number
        if v_clean and not (7 <= len(v_clean) <= 15):
            raise ValueError("Phone number must be between 7 and 15 digits")
            
        return v_clean
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class User(BaseModel):
    id: int  # Changed from str to int to match BIGSERIAL
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    email: EmailStr
    country_code: Optional[str] = None  # New field for country code
    phone_number: Optional[str] = None
    is_verified: bool = False


class OTPVerify(BaseModel):
    email: EmailStr
    otp: str
    
    @validator('otp')
    def validate_otp(cls, v):
        # Remove any whitespace
        v = v.strip()
        
        # Check if it's exactly 6 digits
        if not v.isdigit() or len(v) != 6:
            raise ValueError('OTP must be exactly 6 digits')
        
        return v


class OTPResponse(BaseModel):
    detail: str
    success: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    id: int  # Changed from str to int to match BIGSERIAL
    first_name: str
    last_name: str
    email: EmailStr
    token: str
    detail: str
    company_name: str


# Password reset models
class PasswordResetRequest(BaseModel):
    email: EmailStr


class SecurityAnswerVerify(BaseModel):
    email: EmailStr
    security_answers: List[SecurityQuestion]


class PasswordReset(BaseModel):
    email: EmailStr
    reset_token: str
    new_password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v


# Subscription and payment models
class LicenseType(BaseModel):
    id: str
    name: str
    description: str
    category: str  # e.g., "TEST_CREATION", "TEST_EXECUTION"
    price: float
    quantity: int = 1
    period: str = "year"  # "month", "year", etc.
    is_optional: bool = False


class TestExecutionOption(BaseModel):
    id: str
    name: str
    description: str
    is_cloud_hosted: bool
    price: float
    quantity: int = 0
    period: str = "year"
    is_selected: bool = False


class Discount(BaseModel):
    code: Optional[str] = None
    description: str
    percentage: Optional[float] = None
    fixed_amount: Optional[float] = None
    applies_to: Optional[str] = None  # Specific product ID or "total"
    minimum_purchase: Optional[float] = None
    is_applied: bool = False


class SubscriptionPlan(BaseModel):
    id: str
    name: str
    description: str
    licenses: List[LicenseType]
    execution_options: List[TestExecutionOption]
    available_discounts: List[Discount] = []
    stripe_price_id: Optional[str] = None
    stripe_annual_price_id: Optional[str] = None  # Add field for annual price ID


class OrderSummary(BaseModel):
    plan_id: str
    licenses: List[LicenseType]
    execution_options: List[TestExecutionOption]
    subtotal: float
    discount: float = 0
    tax: float = 0
    total: float

    @validator('total')
    def calculate_total(cls, v, values):
        if 'subtotal' in values and 'discount' in values and 'tax' in values:
            return values['subtotal'] - values['discount'] + values['tax']
        return v


class PaymentRequest(BaseModel):
    order_summary: OrderSummary
    payment_method: str = "card"  # card, apple_pay, google_pay, etc.
    coupon_code: Optional[str] = None
    currency: str = "USD"
    return_url: str
    cancel_url: str


class SocialLoginRequest(BaseModel):
    provider: str  # "google"
    token: str
    redirect_to: Optional[str] = None


class StripeCheckoutSessionRequest(BaseModel):
    plan_id: str
    licenses: List[Dict[str, int]]  # list of {license_id: quantity} pairs
    execution_options: List[str] = []  # list of selected execution option IDs
    success_url: str
    cancel_url: str
    coupon_code: Optional[str] = None
    billing_cycle: Optional[str] = "monthly"  # Add billing cycle field


class StripeCheckoutSessionResponse(BaseModel):
    url: str
    session_id: str


class SubscriptionStatus(BaseModel):
    id: str
    user_id: str
    plan_id: str
    status: str  # active, canceled, past_due, etc.
    current_period_end: str
    licenses: List[LicenseType]
    execution_options: List[TestExecutionOption]
    created_at: str
    updated_at: str


class UserUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    country_code: Optional[str] = None  # New field for country code
    phone_number: Optional[str] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None
    email: Optional[str] = None
    is_verified: Optional[bool] = None

    @validator('phone_number')
    def validate_phone_number(cls, v, values):
        # If phone number is None or empty, return it as is (optional field)
        if v is None or v == '':
            return None
            
        # Strip any non-digit characters (spaces, hyphens, etc.)
        v_clean = ''.join(filter(str.isdigit, v or ''))
        
        # Consider country code in validation
        country_code = values.get('country_code', '')
        if country_code and v_clean:
            # Don't include country code in the phone number if it's already provided separately
            if v_clean.startswith(country_code.replace('+', '')):
                v_clean = v_clean[len(country_code.replace('+', '')):]
                
        # Simple length validation
        if v_clean and not (7 <= len(v_clean) <= 15):
            raise ValueError("Phone number must be between 7 and 15 digits")
            
        return v_clean


class PublicUserProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    country_code: Optional[str] = None  # New field for country code
    phone_number: Optional[str] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None
    email: EmailStr
    is_verified: Optional[bool] = None



# ============================================================================
# AI Test Automation Models (from POC)
# ============================================================================

class UserStory(BaseModel):
    """User story model generated from BRD documents."""
    id: str = Field(..., description="Unique identifier for the user story")
    title: str = Field(..., description="Title of the user story")
    description: str = Field(..., description="Detailed description of the user story")
    acceptance_criteria: List[str] = Field(default_factory=list, description="List of acceptance criteria")
    jira_key: Optional[str] = Field(None, description="Jira issue key if story is from Jira")


class TestCase(BaseModel):
    """Test case model for automated testing."""
    id: str = Field(..., description="Unique identifier for the test case")
    title: str = Field(..., description="Title of the test case")
    description: str = Field(..., description="Detailed description of what the test validates")
    steps: List[str] = Field(..., description="List of test steps to execute")
    expected_results: List[str] = Field(..., description="Expected results for each step")
    preconditions: Optional[List[str]] = Field(default_factory=list, description="Preconditions required before test execution")
    user_story_id: Optional[str] = Field(None, description="Reference to the source user story")
    jira_key: Optional[str] = Field(None, description="Jira issue key if test case is from Jira story")
    config: Optional[dict] = Field(default_factory=dict, description="Test configuration including credentials and browser settings", alias="_config")
    
    class Config:
        populate_by_name = True  # Allow both field name and alias


class ExecutionStep(BaseModel):
    """Individual step execution details."""
    step_index: int = Field(..., description="Index of the step in the plan")
    action: str = Field(..., description="Action performed (tool name)")
    parameters: dict = Field(default_factory=dict, description="Parameters passed to the tool")
    success: bool = Field(..., description="Whether the action succeeded")
    result: Optional[dict] = Field(None, description="Result returned from the tool")
    error: Optional[str] = Field(None, description="Error message if action failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the step was executed")


class ExecutionResult(BaseModel):
    """Complete test execution result."""
    test_case_id: str = Field(..., description="ID of the test case that was executed")
    status: str = Field(..., description="Overall status: passed, failed, or error")
    executed_steps: List[ExecutionStep] = Field(default_factory=list, description="List of all executed steps")
    screenshots: List[str] = Field(default_factory=list, description="List of screenshot paths or base64 data")
    duration: float = Field(..., description="Total execution duration in seconds")
    error_message: Optional[str] = Field(None, description="Error message if test failed")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="When execution started")
    completed_at: Optional[datetime] = Field(None, description="When execution completed")


# ============================================================================
# Test Execution Request/Response Models
# ============================================================================

class TestExecutionRequest(BaseModel):
    """Request for test execution."""
    session_id: str
    test_case_id: Optional[str] = None
    test_case: Dict[str, Any]
    deployment_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    environment: Optional[str] = None
    build_number: Optional[str] = None


class TestCaseUpdateRequest(BaseModel):
    """Request for updating a test case."""
    session_id: str
    test_case: Dict[str, Any]


class TestCaseDeleteRequest(BaseModel):
    """Request for deleting a test case."""
    session_id: str


class TestExecutionResult(BaseModel):
    """Result of test execution."""
    success: bool
    message: str
    logs: Optional[List[Dict[str, str]]] = None
    screenshot_paths: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    plan: Optional[List[Dict[str, Any]]] = None
    original_plan: Optional[List[Dict[str, Any]]] = None  # Original plan before adaptive replanning
    executed_actions: Optional[List[Dict[str, Any]]] = None
    execution_logs: Optional[List[Dict[str, Any]]] = None
    feedback: Optional[str] = None
    error: Optional[str] = None
    failing_step: Optional[int] = None
    duration: Optional[float] = None


class WorkflowExecutionRequest(BaseModel):
    """Request for workflow-based test execution."""
    session_id: str
    test_case_id: Optional[str] = None
    test_case: Dict[str, Any]
    deployment_url: str
    username: Optional[str] = None
    password: Optional[str] = None
    sso_provider: Optional[str] = None
    environment: Optional[str] = None
    build_number: Optional[str] = None
    headless: bool = True
    use_workflow: bool = True  # Flag to use multi-agent workflow
    viewport_resolution: Optional[str] = "1920x1080"  # Browser resolution (e.g., "1920x1080", "1366x768", "2560x1440")


# ============================================================================
# Build and Test Request/Response Models
# ============================================================================

class BuildTestRequest(BaseModel):
    """Request for build testing."""
    buildUrl: str
    features: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# DIFF CHECKER MODELS
# Models for user story and test case diff checking and incremental generation
# ============================================================================

class UserStoryDiffRequest(BaseModel):
    """Request to compare user stories against existing database records."""
    identifier_id: Optional[str] = None  # Optional identifier for grouping/filtering
    user_stories: List[Dict[str, Any]]
    match_strategy: str = "exact"  # "exact" (hash) or "fuzzy" (similarity)
    similarity_threshold: Optional[float] = 0.85  # For fuzzy matching
    
    @validator('match_strategy')
    def validate_match_strategy(cls, v):
        """Validate match strategy is either exact or fuzzy."""
        if v not in ['exact', 'fuzzy']:
            raise ValueError('match_strategy must be either "exact" or "fuzzy"')
        return v
    
    @validator('similarity_threshold')
    def validate_similarity_threshold(cls, v):
        """Validate similarity threshold is between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError('similarity_threshold must be between 0 and 1')
        return v


class UserStoryMatch(BaseModel):
    """Represents a matched user story."""
    incoming_story: Dict[str, Any]
    existing_story: Optional[Dict[str, Any]] = None
    match_type: str  # "exact", "similar", "new"
    similarity_score: Optional[float] = None
    content_hash: str
    
    @validator('match_type')
    def validate_match_type(cls, v):
        """Validate match type is valid."""
        if v not in ['exact', 'similar', 'new', 'modified']:
            raise ValueError('match_type must be one of: exact, similar, new, modified')
        return v


class UserStoryDiffResult(BaseModel):
    """Result of user story diff operation."""
    new_stories: List[Dict[str, Any]] = Field(default_factory=list, description="Stories not found in database")
    existing_stories: List[UserStoryMatch] = Field(default_factory=list, description="Stories found with exact match")
    modified_stories: List[UserStoryMatch] = Field(default_factory=list, description="Stories with same ID but different content")
    total_incoming: int = Field(..., description="Total number of incoming stories")
    total_new: int = Field(..., description="Count of new stories")
    total_existing: int = Field(..., description="Count of existing stories")
    total_modified: int = Field(..., description="Count of modified stories")
    existing_test_cases: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        default_factory=dict, 
        description="Test cases retrieved for existing matched stories (user_story_id -> list of test cases)"
    )
    
    @validator('total_incoming')
    def validate_total_incoming(cls, v, values):
        """Ensure total_incoming matches sum of categories."""
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "new_stories": [{"id": "US001", "story_title": "New Story"}],
                "existing_stories": [],
                "modified_stories": [],
                "total_incoming": 1,
                "total_new": 1,
                "total_existing": 0,
                "total_modified": 0,
                "existing_test_cases": {}
            }
        }


class TestCaseRetrievalRequest(BaseModel):
    """Request to retrieve test cases for specific user stories."""
    identifier_id: Optional[str] = None  # Optional identifier for filtering
    user_story_ids: List[str]
    
    @validator('user_story_ids')
    def validate_user_story_ids(cls, v):
        """Ensure at least one user story ID is provided."""
        if not v:
            raise ValueError('user_story_ids cannot be empty')
        return v


class TestCaseRetrievalResult(BaseModel):
    """Result of test case retrieval."""
    test_cases: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict, 
        description="Map of user_story_id to list of test cases"
    )
    found_count: int = Field(..., description="Total number of test cases found")
    missing_story_ids: List[str] = Field(
        default_factory=list, 
        description="User story IDs with no test cases"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "test_cases": {
                    "US001": [
                        {"id": "TC001", "name": "Test Login", "steps": ["Navigate", "Enter credentials"]}
                    ]
                },
                "found_count": 1,
                "missing_story_ids": []
            }
        }


class IncrementalTestGenerationRequest(BaseModel):
    """Request for incremental test case generation."""
    identifier_id: Optional[str] = None  # Optional identifier for grouping
    user_stories: List[Dict[str, Any]]
    deployment_url: Optional[str] = None
    generate_for_modified: bool = True  # Regenerate for modified stories
    
    @validator('user_stories')
    def validate_user_stories(cls, v):
        """Ensure at least one user story is provided."""
        if not v:
            raise ValueError('user_stories cannot be empty')
        return v
    
    @validator('deployment_url')
    def validate_deployment_url(cls, v):
        """Validate deployment URL if provided."""
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('deployment_url must start with http:// or https://')
        return v


class IncrementalTestGenerationResult(BaseModel):
    """Result of incremental test case generation."""
    diff_summary: UserStoryDiffResult
    retrieved_test_cases: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Test cases retrieved from database for existing stories"
    )
    newly_generated_test_cases: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Test cases generated for new/modified stories"
    )
    total_test_cases: int = Field(..., description="Total test cases (retrieved + generated)")
    generation_skipped_count: int = Field(..., description="Number of stories that skipped generation")
    time_saved_seconds: Optional[float] = Field(None, description="Estimated time saved by skipping generation")
    cost_saved_usd: Optional[float] = Field(None, description="Estimated cost saved by skipping LLM calls")
    
    class Config:
        schema_extra = {
            "example": {
                "diff_summary": {
                    "new_stories": [],
                    "existing_stories": [],
                    "modified_stories": [],
                    "total_incoming": 5,
                    "total_new": 2,
                    "total_existing": 3,
                    "total_modified": 0
                },
                "retrieved_test_cases": {"US001": [{"id": "TC001"}]},
                "newly_generated_test_cases": [{"id": "TC002"}],
                "total_test_cases": 2,
                "generation_skipped_count": 3,
                "time_saved_seconds": 45.2,
                "cost_saved_usd": 0.15
            }
        }


class ContentHashUpdate(BaseModel):
    """Request to update content hash for a story or test case."""
    entity_type: str  # "user_story" or "test_case"
    entity_id: str
    content_hash: str
    
    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Validate entity type."""
        if v not in ['user_story', 'test_case']:
            raise ValueError('entity_type must be either "user_story" or "test_case"')
        return v
    
    @validator('content_hash')
    def validate_content_hash(cls, v):
        """Validate content hash format (SHA-256 hex string)."""
        if len(v) != 64 or not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError('content_hash must be a valid 64-character SHA-256 hex string')
        return v


class BulkUserStorySaveRequest(BaseModel):
    """Request to save multiple user stories with computed hashes."""
    identifier_id: Optional[str] = None  # Optional identifier for grouping
    user_stories: List[Dict[str, Any]]
    compute_hashes: bool = True  # Auto-compute content hashes
    
    @validator('user_stories')
    def validate_user_stories(cls, v):
        """Ensure at least one user story is provided."""
        if not v:
            raise ValueError('user_stories cannot be empty')
        return v


class BulkUserStorySaveResult(BaseModel):
    """Result of bulk user story save operation."""
    saved_count: int
    failed_count: int
    saved_ids: List[str] = Field(default_factory=list)
    failed_stories: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class VersionHistoryRequest(BaseModel):
    """Request to get version history of a user story or test case."""
    entity_type: str  # "user_story" or "test_case"
    original_id: str
    
    @validator('entity_type')
    def validate_entity_type(cls, v):
        """Validate entity type."""
        if v not in ['user_story', 'test_case']:
            raise ValueError('entity_type must be either "user_story" or "test_case"')
        return v


class VersionHistoryResult(BaseModel):
    """Result containing version history."""
    entity_type: str
    original_id: str
    versions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of versions ordered by version number descending"
    )
    total_versions: int
    current_version: Optional[Dict[str, Any]] = None


# Build and Test Request/Response Models
class BuildTestRequest(BaseModel):
    """Request for build testing."""
    buildUrl: str
    features: Optional[List[Dict[str, Any]]] = None



# ============================================================================
# JIRA Integration Models
# ============================================================================
class JiraConfig(BaseModel):
    """Configuration for JIRA integration."""
    jiraUrl: str
    email: str
    apiToken: Optional[str] = None  # IMPORTANT: API token for JIRA authentication (optional for flexibility)
    project: str
    sprint: str
    epic: Optional[str] = None
    issueType: Optional[str] = None
    filterByAssignee: bool = False
	
	
class CheckProfileByEmailRequest(BaseModel):
    """Request model for checking profile by email"""
    email: EmailStr
class ComparisonState(TypedDict, total=False):
        brd_content: str
        user_stories: List[dict]
        brd_analysis: str
        comparison_result: str
        error: Optional[str]
        warning: Optional[str]
# Pydantic Models
class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    content_length: int
    status: str
	
	
class UserStoriesUploadResponse(BaseModel):
    filename: str
    content_length: int
    status: str
	
	
class ComparisonRequest(BaseModel):
    user_id: int  # Required user ID for tracking
    brd_content: str
    brd_file_path: Optional[str] = None  # Path to uploaded BRD file
    user_stories: Optional[List[dict]] = None
    jira_config: Optional[JiraConfig] = None
	
	
class JiraAuthRequest(BaseModel):
    user_id: Optional[int] = None  # Add user_id for tracking
    email: str
    apiToken: str
    jiraUrl: str
    project: str
    domain: Optional[str] = None
    filterByAssignee: Optional[bool] = True
    sprint: str  # Required
    epic: Optional[str] = None  # Optional
    issueType: Optional[str] = None  # New field for issue type filter


# Document info schema
class DocumentInfo(BaseModel):
    fileName: str
    fileType: Optional[str] = None
    fileSize: int
    uploadDate: str
    isCSV: bool = False

# ============================================================================
# COMPARISON STORAGE MODELS - For Gap Analysis File-Based Storage
# ============================================================================

class ComparisonCreate(BaseModel):
    """Model for creating a new comparison record in Supabase"""
    user_id: int
    brd_file_path: Optional[str] = None
    jira_config: Optional[str] = None  # JSON string of JIRA config
    brd_analysis_path: Optional[str] = None
    user_stories_path: Optional[str] = None
    comparison_result_path: Optional[str] = None

class ComparisonRecord(BaseModel):
    """Model for comparison record from Supabase"""
    comparison_id: int
    user_id: int
    brd_file_path: Optional[str] = None
    jira_config: Optional[str] = None
    brd_analysis_path: Optional[str] = None
    user_stories_path: Optional[str] = None
    comparison_result_path: Optional[str] = None
    created_at: datetime

class ComparisonListResponse(BaseModel):
    """Model for listing user's comparisons"""
    comparisons: List[ComparisonRecord]
    total: int
# BIC Check request schema
class BuildIntegrityCheckRequest(BaseModel):
    test_cases: Optional[List[dict]] = []
    deployed_url: str
    build_info: Optional[str] = None
    username: str
    password: str
    build_number: str
    environment: str
    test_framework: Optional[str] = None
    programming_language: Optional[str] = None
    test_objective: Optional[str] = None
    document_info: Optional[DocumentInfo] = None
    use_existing_document: bool = False
    headless: bool = True  # Run browser in headless mode by default
# BIC Check response schema
class BuildIntegrityCheckResponse(BaseModel):
    check_id: str
    status: str
    created_at: str
    chromedriver_available: bool = False
    chromedriver_status: str = ""

# ============================================================================
# FUNCTIONAL TEST RUNS MODELS
# Models for storing test execution results in functional_test_runs table
# ============================================================================

class FunctionalTestRunCreate(BaseModel):
    """Model for creating a new functional test run record."""
    user_id: int
    file_path: str
    status: str  # PASS / FAIL / ERROR / SKIPPED
    runtime_ms: int
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['PASS', 'FAIL', 'ERROR', 'SKIPPED']
        if v.upper() not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}")
        return v.upper()


class FunctionalTestRunResponse(BaseModel):
    """Model for functional test run response."""
    test_run_id: str
    user_id: int
    file_path: str
    status: str
    runtime_ms: int
    created_at: datetime

