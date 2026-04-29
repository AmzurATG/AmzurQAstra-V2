"""
AI-Driven Testing Recommendation Engine
Role: Senior QA Architect + Applied ML Engineer

A multi-layered recommendation engine that maps BRD sections and User Stories
to 24 fixed testing types using deterministic, semantic, and granular scoring.

Architecture:
- Layer 1 (Deterministic): Keyword-based trigger matching (High precision)
- Layer 2 (Semantic): Section-level paragraph embeddings vs testing type descriptions
- Layer 3 (Granular): User Story ID-level embedding comparison
- Filtering: Pre-processing to remove "Out of Scope" and "Deferred" sections
- Negation Detection: Suppress recommendations for explicitly excluded requirements
- Domain Boosting: Apply confidence boost for domain-specific keywords
"""

from __future__ import annotations
import re
import os
import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Optional
import json
from datetime import datetime
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recommendation_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import sentence-transformers for semantic embeddings
try:
    from sentence_transformers import SentenceTransformer, util
    import numpy as np
    logger.info("✓ Successfully imported sentence-transformers and numpy")
except ImportError as e:
    logger.error(f"✗ Import Error: {e}")
    logger.error("Please run: pip install sentence-transformers numpy")
    raise

# Import LLM client for edge case detection
try:
    from .llm_client import LLMClient
    LLM_AVAILABLE = True
    logger.info("✓ LLM client available for edge case detection")
except ImportError:
    LLM_AVAILABLE = False
    logger.warning("⚠ LLM client not available - edge case detection disabled")

__all__ = [
    "TestingRecommendationEngine",
    "TESTING_TYPES_TAXONOMY",
    "format_recommendations_for_report"
]


# ============================================================================
# FIXED TAXONOMY: 24 Testing Types with Domain-Agnostic Descriptions
# ============================================================================

TESTING_TYPES_TAXONOMY: Dict[str, Dict[str, Any]] = {
    # ===== STANDARD (Critical/MVP) =====
    "Smoke Testing": {
        "category": "standard",
        "display_description": "Validates critical path functionality and core workflows after deployments",
        "description": (
            "Smoke Testing (Build Verification Testing) validates critical path functionality after deployments. "
            "QA Trigger: When build is deployed, before full regression. Tests must complete in <15 minutes. "
            "Includes: Can users login? Does homepage load? Are critical APIs responding? Can core transactions execute? "
            "Purpose: Catch showstopper defects early, decide if build is stable enough for detailed testing."
        ),
        "keywords": [
            "login", "logged", "logged in", "sign-in", "signed in", "authentication", 
            "dashboard", "core flow", "critical path", "registration", "session", 
            "main page", "homepage", "landing page", "product page", "product", 
            "load", "page load", "primary feature", "core feature", "basic functionality", 
            "sanity check", "build verification", "deployment", "critical workflow", 
            "happy path", "essential feature", "must work", "cannot fail", "blocking",
            "view profile", "view profiles", "view details", "display profiles"
        ],
        "risk_factor": "System Stability",
        "requirement_type": "Core User Workflows"
    },
    
    "Functional Testing": {
        "category": "standard",
        "display_description": "Validates business rules, workflows, and feature specifications against requirements",
        "description": (
            "Functional Testing validates business rules and logic against requirements. "
            "QA Trigger: Every user story, acceptance criterion, business rule, or functional requirement needs test cases. "
            "Test Scenarios: Input validation (boundary values, valid/invalid data), workflow state transitions, "
            "calculations (pricing, tax, discounts), CRUD operations, business rule enforcement, "
            "conditional logic (if user is admin, then show X), data transformations. "
            "Verification: Does feature behave EXACTLY as specified in AC? Do all paths work (success, failure, edge cases)?"
        ),
        "keywords": [
            "form", "validate", "submit", "workflow", "business logic", "business rule",
            "feature", "user story", "use case", "calculation", "processing",
            "selection", "choose", "select", "add to cart", "cart", "mandatory",
            "required", "option", "choice", "picker", "dropdown", "filter",
            "search", "allow", "display list", "match", "condition", "if then",
            "rule", "logic", "behavior", "action", "trigger", "perform",
            "execute", "process", "handle", "manage", "update", "save",
            "delete", "create", "edit", "modify", "change", "set",
            "calculate", "compute", "determine", "check", "verify",
            "acceptance criteria", "functional requirement", "FR", "AC",
            "shall", "must", "should", "will", "expects", "returns"
        ],
        "risk_factor": "Business Logic Correctness",
        "requirement_type": "Feature Specifications"
    },
    
    "Role-Based Access Testing": {
        "category": "standard",
        "display_description": "Validates user permissions, access control, and authorization boundaries",
        "description": (
            "Role-Based Access Testing validates authorization and permission boundaries. "
            "QA Trigger: Any mention of user roles, permissions, access levels, or 'only X can do Y'. "
            "Test Scenarios: Login as Admin → verify admin-only features visible. Login as User → verify admin features hidden/disabled. "
            "Attempt unauthorized actions (User tries to delete → blocked with 403). Role switching (user promoted to admin → new permissions). "
            "Data isolation (User A cannot see User B's data). Privilege escalation prevention. "
            "Critical for: Multi-tenant apps, healthcare (HIPAA patient data), financial systems, enterprise platforms."
        ),
        "keywords": [
            "role", "permission", "rbac", "admin", "privilege", "superuser",
            "access control", "authorization", "user role", "security",
            "user type", "manager", "viewer", "editor", "owner",
            "only admin", "only manager", "restricted", "authorized",
            "unauthorized", "forbidden", "403", "access denied",
            "who can", "allowed to", "not allowed", "restricted to",
            "based on role", "depending on user", "different users",
            "tenant", "organization", "workspace", "team",
            "patient", "practitioner", "doctor", "user", "users",
            "logged in", "access", "can view", "can access"
        ],
        "risk_factor": "Authorization Security",
        "requirement_type": "Permission Requirements"
    },
    
    "API Functional Testing": {
        "category": "standard",
        "display_description": "Validates backend endpoints, API contracts, and integration behavior",
        "description": (
            "API Functional Testing validates backend endpoints, request/response contracts, and integration behavior. "
            "QA Trigger: Any backend API, webhook, microservice, or integration mentioned. "
            "Test Scenarios: Request validation (required params, data types, auth headers). Response verification (status codes, payload schema, data accuracy). "
            "Error handling (400 bad request, 401 unauthorized, 404 not found, 500 server error). "
            "CRUD operations (POST create, GET retrieve, PUT/PATCH update, DELETE remove). "
            "Integration testing (call API A → triggers API B → verify end-to-end flow). "
            "Tools: Postman, REST Assured, curl, GraphQL queries."
        ),
        "keywords": [
            "api", "endpoint", "endpoints", "rest", "restful", "graphql", "json", "payload",
            "status code", "request", "response", "webhook", "backend", "server",
            "microservice", "service", "integration", "third-party",
            "get", "post", "put", "patch", "delete", "http",
            "200", "201", "400", "401", "403", "404", "500",
            "header", "parameter", "query", "body", "schema",
            "contract", "swagger", "openapi", "postman",
            "fetch", "call", "invoke", "trigger", "consume",
            "retrieve", "retrieval", "data source", "load data"
        ],
        "risk_factor": "Backend Service Correctness",
        "requirement_type": "Integration Requirements"
    },
    
    "UI Regression Testing": {
        "category": "standard",
        "display_description": "Ensures UI elements, layouts, and visual consistency after code changes",
        "description": (
            "UI Regression Testing ensures UI elements, layouts, and visual design remain consistent after changes. "
            "QA Trigger: UI changes, CSS updates, component library changes, framework upgrades, responsive design requirements. "
            "Test Scenarios: Component rendering (buttons, dropdowns, modals display correctly). "
            "Layout verification (spacing, alignment, grid structure). Color scheme consistency (theme colors match design). "
            "Visual comparison (screenshot baseline vs current). Cross-resolution testing (1920x1080, 1366x768, mobile). "
            "Before/After validation: Did code change break existing UI? Are all pages still visually correct? "
            "Tools: Selenium screenshots, Playwright visual comparison, Percy, Applitools."
        ),
        "keywords": [
            "ui", "user interface", "component", "visual", "regression", "layout",
            "css", "style", "styling", "front-end", "frontend", "theme", "design",
            "color", "swatch", "render", "rendering", "display", "appearance",
            "button", "selector", "widget", "interface", "element",
            "page", "screen", "view", "modal", "dialog", "popup",
            "dropdown", "menu", "navigation", "navbar", "sidebar",
            "icon", "image", "logo", "banner", "header", "footer",
            "spacing", "padding", "margin", "alignment", "position",
            "look and feel", "visual design", "mockup", "wireframe"
        ],
        "risk_factor": "Visual Consistency",
        "requirement_type": "Interface Changes"
    },
    
    "Payment Workflow Testing": {
        "category": "standard",
        "display_description": "Validates payment processing, billing, and financial transaction accuracy",
        "description": (
            "Payment Workflow Testing validates financial transactions with zero-error tolerance. "
            "QA Trigger: Any payment processing, billing, checkout, pricing, refunds, subscriptions mentioned. "
            "Test Scenarios: Checkout flow (add payment method → review order → confirm → verify charge). "
            "Payment methods (credit card, PayPal, Stripe, Apple Pay, bank transfer). "
            "Pricing calculations (subtotal, tax, shipping, discounts, total match exactly). "
            "Transaction states (pending, processing, completed, failed, refunded). "
            "Refund workflows (full refund, partial refund, verify credit issued). "
            "Subscription billing (recurring charges, proration, cancellation, renewal). "
            "Critical: Test with real payment gateways in sandbox/test mode, verify receipts, check audit logs."
        ),
        "keywords": [
            # Core payment terms (MUST be specific to financial transactions)
            "payment", "billing", "transaction", "checkout", "financial transaction",
            "refund", "subscription", "stripe", "paypal", "payment gateway",
            "credit card", "debit card", "charge customer", "invoice",
            "payment processing", "payment method",
            # Transaction-specific
            "purchase order", "receipt", "confirmation email",
            "recurring payment", "monthly billing", "annual subscription", "subscription plan",
            "cancel subscription", "upgrade plan", "downgrade plan",
            # Specific pricing terms (avoid generic "price", "cost", "total")
            "pricing calculation", "subtotal", "tax calculation", "shipping cost calculation",
            "discount code", "coupon code", "promo code", "apply coupon",
            # Payment flow terms
            "checkout flow", "payment flow", "billing cycle",
            "payment confirmation", "order confirmation",
            # Avoid overly generic terms that appear in non-payment contexts:
            # Removed: "pay" (too generic - appears in "display", "payload", etc.)
            # Removed: "price", "cost", "fee", "total", "amount" (too generic)
        ],
        "risk_factor": "Financial Transaction Accuracy",
        "requirement_type": "Commerce Requirements"
    },
    
    "Session Management Testing": {
        "category": "standard",
        "display_description": "Validates user authentication state, token lifecycle, and session security",
        "description": (
            "Session Management Testing validates user authentication state, token lifecycle, and session security. "
            "QA Trigger: Login/logout, session timeout, 'remember me', token expiry, multi-tab behavior. "
            "Test Scenarios: Login → verify session created (JWT token, cookie). "
            "Session timeout (idle 30 min → auto-logout → redirect to login). "
            "Token refresh (access token expires → refresh token renews session silently). "
            "Logout (user clicks logout → token invalidated, redirect to login, cannot use back button to access protected pages). "
            "Multi-tab (logout in tab 1 → tab 2 also logged out). Remember me (close browser → reopen → still logged in). "
            "Security: Session hijacking prevention, secure cookie flags (HttpOnly, Secure), CSRF protection."
        ),
        "keywords": [
            "session", "session management", "token", "jwt", "access token", "refresh token",
            "expiry", "expire", "timeout", "logout", "log out", "sign out",
            "cookie", "authentication", "auth", "multi-tab", "keep me logged in",
            "remember me", "stay logged in", "auto logout", "idle",
            "session timeout", "token expiry", "token refresh",
            "logged in", "logged out", "login state", "auth state",
            "persist", "persistence", "browser close", "reopen"
        ],
        "risk_factor": "Authentication Persistence",
        "requirement_type": "Security Policies"
    },
    
    "Connectivity Testing": {
        "category": "standard",
        "display_description": "Evaluates network resilience and graceful handling of connection issues",
        "description": (
            "Connectivity Testing evaluates network resilience triggered by distributed system requirements. "
            "Ensures graceful handling of network loss, reconnection, and real-time updates in IoT Healthcare devices, "
            "mobile Fintech apps, and cloud-based SaaS platforms."
        ),
        "keywords": [
            "connectivity", "network", "reconnect", "offline", "wifi",
            "bluetooth", "iot", "websocket", "real-time", "device"
        ],
        "risk_factor": "Network Resilience",
        "requirement_type": "Distributed System Requirements"
    },
    
    "Browser Compatibility": {
        "category": "standard",
        "display_description": "Ensures consistent functionality across Chrome, Firefox, Safari, and Edge",
        "description": (
            "Browser Compatibility evaluates cross-platform consistency triggered by web accessibility needs. "
            "Ensures uniform functionality and appearance across Chrome, Firefox, Safari, and Edge "
            "for Healthcare portals, Fintech dashboards, and SaaS web applications."
        ),
        "keywords": [
            "browser", "chrome", "firefox", "safari", "edge",
            "cross-browser", "compatibility", "webkit"
        ],
        "risk_factor": "Cross-Platform Consistency",
        "requirement_type": "Web Accessibility Needs"
    },
    
    "Error Handling Testing": {
        "category": "standard",
        "display_description": "Validates system behavior with invalid input, edge cases, and failure scenarios",
        "description": (
            "Error Handling Testing (Negative Testing) validates system behavior when things go wrong. "
            "QA Trigger: Validation rules, error messages, edge cases, boundary conditions, failure scenarios. "
            "Test Scenarios: Invalid input (empty required field, wrong format email, negative numbers where positive expected). "
            "Boundary testing (max length exceeded, date out of range). Missing data (null values, empty arrays). "
            "Error messages (clear, actionable, no stack traces shown to users). Recovery (can user retry? does form state persist?). "
            "Network failures (API timeout, 500 error → show user-friendly message). "
            "Validation feedback (red border on invalid field, inline error text, form cannot submit until fixed)."
        ),
        "keywords": [
            "error", "error handling", "404", "500", "exception", "failure",
            "timeout", "retry", "offline", "error message", "graceful",
            "prevent", "validation", "validate", "invalid", "warning", "alert",
            "cannot", "should not", "must not", "restrict", "block",
            "does not allow", "no results", "not found", "missing", "message",
            "required field", "mandatory field", "incorrect", "wrong",
            "negative testing", "edge case", "boundary", "limit",
            "fail", "failure", "reject", "denied", "forbidden",
            "empty", "null", "blank", "zero", "negative",
            "max length", "min length", "out of range", "exceeded",
            "shows error", "display error", "error text", "error banner"
        ],
        "risk_factor": "Graceful Failure Behavior",
        "requirement_type": "Exception Scenarios"
    },
    
    "Mobile Responsiveness": {
        "category": "standard",
        "display_description": "Ensures proper rendering and touch interactions on phones and tablets",
        "description": (
            "Mobile Responsiveness evaluates adaptive layout quality triggered by multi-device requirements. "
            "Ensures proper rendering, touch interactions, and functionality on phones and tablets "
            "for mobile Healthcare apps, Fintech services, and responsive SaaS platforms."
        ),
        "keywords": [
            "mobile", "tablet", "responsive", "viewport", "ios",
            "android", "touch", "device", "screen size"
        ],
        "risk_factor": "Adaptive Layout Quality",
        "requirement_type": "Multi-Device Requirements"
    },
    
    "Analytics Visibility Testing": {
        "category": "standard",
        "display_description": "Validates dashboards, reports, and data visualization accuracy",
        "description": (
            "Analytics Visibility Testing evaluates data presentation accuracy triggered by reporting requirements. "
            "Ensures dashboards, charts, metrics, and KPIs populate correctly and display meaningful insights "
            "for Healthcare analytics, Fintech dashboards, and SaaS business intelligence."
        ),
        "keywords": [
            "analytics", "dashboard", "metrics", "report", "chart",
            "graph", "kpi", "visualization", "data", "insights"
        ],
        "risk_factor": "Data Presentation Accuracy",
        "requirement_type": "Reporting Requirements"
    },
    
    # ===== RECOMMENDED (Advanced/Post-MVP) =====
    "Chaos Testing": {
        "category": "recommended",
        "display_description": "Evaluates system resilience with random failures and unpredictable conditions",
        "description": (
            "Chaos Testing evaluates system resilience triggered by fault tolerance requirements. "
            "Ensures systems withstand random service disruptions, failures, and unpredictable conditions "
            "in distributed Healthcare networks, Fintech microservices, and cloud-native SaaS architectures."
        ),
        "keywords": [
            "chaos", "fault", "failure injection", "resilience",
            "disruption", "random failure", "fault tolerance"
        ],
        "risk_factor": "System Resilience",
        "requirement_type": "Fault Tolerance Requirements"
    },
    
    "Interoperability Testing": {
        "category": "recommended",
        "display_description": "Ensures seamless communication with third-party systems and standard protocols",
        "description": (
            "Interoperability Testing evaluates cross-vendor compatibility triggered by integration standards. "
            "Ensures seamless communication with third-party systems using industry protocols like HL7 (Healthcare), "
            "OCPP (EV charging), or standard APIs across Healthcare, IoT, and enterprise integrations."
        ),
        "keywords": [
            "interoperability", "vendor", "third-party", "integration",
            "protocol", "hl7", "fhir", "ocpp", "standard", "compatibility"
        ],
        "risk_factor": "Cross-Vendor Compatibility",
        "requirement_type": "Integration Standards"
    },
    
    "Usability Testing": {
        "category": "recommended",
        "display_description": "Evaluates if users can accomplish tasks easily and efficiently",
        "description": (
            "Usability Testing evaluates if users can accomplish tasks easily, efficiently, and satisfactorily. "
            "QA Trigger: 'Easy to use', 'intuitive', 'user-friendly', 'clear', 'understandable' requirements. Visual indicators (disabled states, loading spinners, tooltips). "
            "Test Scenarios: Task completion (can user find and complete primary goal in <3 clicks?). "
            "Navigation clarity (is menu structure logical? can user find settings?). "
            "Feedback visibility (disabled button vs enabled, loading state, success confirmation). "
            "Error prevention (prevent user mistakes with tooltips, placeholders, confirmation dialogs). "
            "Cognitive load (is terminology clear? are labels self-explanatory?). "
            "Methods: User observation, task-based testing, Nielsen heuristics, A/B testing."
        ),
        "keywords": [
            "usability", "ux", "user experience", "intuitive", "ease of use",
            "user testing", "navigation", "user-friendly", "cognitive load",
            "understand", "comprehend", "clear", "clarity", "simple",
            "disabled", "enabled", "grayed out", "inactive", "active",
            "out of stock", "unavailable", "indicator", "feedback",
            "tooltip", "hint", "help text", "placeholder", "label",
            "easy to", "simple to", "quick to", "obvious",
            "confusing", "difficult", "complex", "unclear",
            "accessibility", "readable", "legible", "visible",
            "hover", "focus", "highlight", "emphasis",
            "confirmation", "success message", "progress indicator",
            "loading", "spinner", "skeleton", "placeholder"
        ],
        "risk_factor": "User Experience Quality",
        "requirement_type": "Human-Centered Design Goals"
    },
    
    "API Contract Testing": {
        "category": "recommended",
        "display_description": "Ensures API schema consistency and backward compatibility",
        "description": (
            "API Contract Testing evaluates interface consistency triggered by versioning requirements. "
            "Ensures backward compatibility, schema adherence, and breaking change prevention "
            "in microservice Healthcare systems, Fintech API ecosystems, and SaaS integration platforms."
        ),
        "keywords": [
            "contract", "schema", "api version", "backward compatibility",
            "openapi", "swagger", "pact", "breaking change", "microservice"
        ],
        "risk_factor": "Interface Consistency",
        "requirement_type": "Versioning Requirements"
    },
    
    "AI-based Visual Regression": {
        "category": "recommended",
        "display_description": "Detects pixel-perfect visual changes using computer vision",
        "description": (
            "AI-based Visual Regression evaluates pixel-perfect accuracy triggered by complex UI requirements. "
            "Ensures subtle visual changes are detected using computer vision in Healthcare dashboards, "
            "Fintech trading interfaces, and data-rich SaaS applications."
        ),
        "keywords": [
            "visual regression", "pixel", "ai-based", "computer vision",
            "applitools", "percy", "screenshot", "visual testing",
            "color change", "color swatch", "subtle", "detect change",
            "ui change", "appearance change"
        ],
        "risk_factor": "Pixel-Perfect Accuracy",
        "requirement_type": "Complex UI Requirements"
    },
    
    "Payment Security Testing": {
        "category": "recommended",
        "display_description": "Ensures PCI-DSS compliance, encryption, and fraud prevention",
        "description": (
            "Payment Security Testing evaluates financial data protection triggered by compliance mandates. "
            "Ensures PCI-DSS compliance, encryption standards, fraud prevention, and secure token handling "
            "in Fintech payment processors, e-commerce platforms, and subscription-based services."
        ),
        "keywords": [
            "pci", "pci-dss", "payment security", "encryption", "fraud",
            "cvv", "tokenization", "secure payment", "compliance"
        ],
        "risk_factor": "Financial Data Protection",
        "requirement_type": "Compliance Mandates"
    },
    
    "Concurrency Testing": {
        "category": "recommended",
        "display_description": "Validates multi-user scalability and prevents race conditions",
        "description": (
            "Concurrency Testing evaluates multi-user scalability triggered by load requirements. "
            "Ensures systems handle simultaneous operations without race conditions, deadlocks, or data corruption "
            "in high-traffic Healthcare portals, Fintech trading platforms, and collaborative SaaS applications."
        ),
        "keywords": [
            "concurrency", "simultaneous", "parallel", "race condition",
            "deadlock", "rate limit", "load", "stress", "multiple users"
        ],
        "risk_factor": "Multi-User Scalability",
        "requirement_type": "Load Requirements"
    },
    
    "Real-time Event Validation": {
        "category": "recommended",
        "display_description": "Ensures streaming data accuracy and minimal latency for live updates",
        "description": (
            "Real-time Event Validation evaluates streaming data accuracy triggered by live update requirements. "
            "Ensures WebSocket/MQTT events deliver with minimal latency and correct sequencing "
            "in Healthcare monitoring systems, Fintech live trading, and SaaS collaboration tools."
        ),
        "keywords": [
            "real-time", "websocket", "mqtt", "stream", "event",
            "live update", "push notification", "latency", "broker"
        ],
        "risk_factor": "Streaming Data Accuracy",
        "requirement_type": "Live Update Requirements"
    },
    
    "Accessibility Compliance": {
        "category": "recommended",
        "display_description": "Ensures WCAG/ADA compliance with screen readers and keyboard navigation",
        "description": (
            "Accessibility Compliance evaluates inclusive design standards triggered by regulatory requirements. "
            "Ensures WCAG 2.1/ADA compliance with screen readers, keyboard navigation, and proper contrast "
            "in Healthcare patient portals, government Fintech services, and public-facing SaaS platforms."
        ),
        "keywords": [
            "accessibility", "wcag", "ada", "a11y", "screen reader",
            "keyboard navigation", "contrast", "aria", "section 508"
        ],
        "risk_factor": "Inclusive Design Standards",
        "requirement_type": "Regulatory Requirements"
    },
    
    "Localization/Internationalization": {
        "category": "recommended",
        "display_description": "Validates translations, date/time formats, and cultural appropriateness",
        "description": (
            "Localization/Internationalization evaluates global adaptation quality triggered by multi-region deployment. "
            "Ensures accurate translations, date/time formats, currency handling, and cultural appropriateness "
            "across Healthcare international markets, global Fintech platforms, and worldwide SaaS offerings."
        ),
        "keywords": [
            "localization", "internationalization", "i18n", "l10n",
            "translation", "currency", "locale", "multi-language", "region"
        ],
        "risk_factor": "Global Adaptation Quality",
        "requirement_type": "Multi-Region Deployment"
    },
    
    "Progressive Web App (PWA) Testing": {
        "category": "recommended",
        "display_description": "Validates offline capability, service workers, and app-like behavior",
        "description": (
            "Progressive Web App Testing evaluates offline capability triggered by connectivity-independent requirements. "
            "Ensures service workers, background sync, push notifications, and app-like behavior function properly "
            "in mobile Healthcare apps, Fintech PWAs, and field-deployed SaaS solutions."
        ),
        "keywords": [
            "pwa", "progressive web app", "service worker", "offline",
            "background sync", "push notification", "app manifest"
        ],
        "risk_factor": "Offline Capability",
        "requirement_type": "Connectivity-Independent Requirements"
    },
    
    "Predictive Analytics Testing": {
        "category": "recommended",
        "display_description": "Validates machine learning accuracy and anomaly detection",
        "description": (
            "Predictive Analytics Testing evaluates machine learning accuracy triggered by AI-driven features. "
            "Ensures ML models produce reliable predictions, detect anomalies correctly, and handle edge cases "
            "in Healthcare diagnostics, Fintech fraud detection, and SaaS intelligent automation."
        ),
        "keywords": [
            "predictive", "machine learning", "ml model", "ai",
            "anomaly detection", "forecasting", "data science", "algorithm"
        ],
        "risk_factor": "Machine Learning Accuracy",
        "requirement_type": "AI-Driven Features"
    },
    
    "Data Migration Testing": {
        "category": "recommended",
        "display_description": "Ensures data integrity during system transitions and schema mapping",
        "description": (
            "Data Migration Testing evaluates data integrity preservation triggered by system transition requirements. "
            "Ensures accurate data transfer, schema mapping, and rollback procedures during legacy system migrations "
            "in Healthcare EHR transitions, Fintech platform upgrades, and SaaS database consolidations."
        ),
        "keywords": [
            "migration", "data transfer", "legacy", "etl",
            "import", "export", "data integrity", "schema mapping"
        ],
        "risk_factor": "Data Integrity Preservation",
        "requirement_type": "System Transition Requirements"
    }
}


# ============================================================================
# Core Recommendation Engine
# ============================================================================

class TestingRecommendationEngine:
    """
    Multi-layered AI-driven testing recommendation engine.
    
    Features:
    - Layer 1: Deterministic keyword matching
    - Layer 2: Semantic paragraph-level embeddings
    - Layer 3: Granular user story-level embeddings
    - Out-of-scope filtering with detailed logging
    - Negation detection to suppress inappropriate recommendations
    - Domain-specific confidence boosting
    - Comprehensive audit-ready JSON output
    """
    
    def __init__(
        self,
        taxonomy: Optional[Dict[str, Dict[str, Any]]] = None,
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
        use_llm_filtering: bool = True  # Enabled by default - works alongside regex to catch missed out-of-scope sections
    ):
        """
        Initialize the recommendation engine.
        
        Args:
            taxonomy: Testing types taxonomy (defaults to TESTING_TYPES_TAXONOMY)
            model_name: Sentence transformer model (must use all-mpnet-base-v2)
            use_llm_filtering: Enable LLM for edge case detection in out-of-scope filtering
        """
        logger.info("=" * 80)
        logger.info("INITIALIZING AI-DRIVEN TESTING RECOMMENDATION ENGINE")
        logger.info("=" * 80)
        
        # Validate model choice
        if "all-mpnet-base-v2" not in model_name:
            logger.warning(f"⚠ Model '{model_name}' is not all-mpnet-base-v2. Using required model.")
            model_name = "sentence-transformers/all-mpnet-base-v2"
        
        self.taxonomy = taxonomy or TESTING_TYPES_TAXONOMY
        self.model_name = model_name
        self.use_llm_filtering = use_llm_filtering and LLM_AVAILABLE
        
        # Initialize LLM client if available and enabled
        if self.use_llm_filtering:
            try:
                self.llm_client = LLMClient()
                logger.info("✓ LLM client initialized for edge case detection")
            except Exception as e:
                logger.warning(f"⚠ Failed to initialize LLM client: {e}")
                self.use_llm_filtering = False
                self.llm_client = None
        else:
            self.llm_client = None
        
        # Load semantic model
        logger.info(f"Loading semantic model: {model_name}")
        logger.info("(First-time download may take a moment)")
        try:
            self.model = SentenceTransformer(model_name)
            logger.info("✓ Model loaded successfully")
        except Exception as e:
            logger.error(f"✗ Failed to load model: {e}")
            raise
        
        # Pre-compute testing type embeddings
        logger.info("Pre-computing testing type description embeddings...")
        self.test_type_names = list(self.taxonomy.keys())
        self.test_type_descriptions = [
            self.taxonomy[name]["description"] for name in self.test_type_names
        ]
        
        try:
            self.test_type_embeddings = self.model.encode(
                self.test_type_descriptions,
                convert_to_tensor=True,
                show_progress_bar=False
            )
            logger.info(f"✓ Pre-computed embeddings for {len(self.test_type_names)} testing types")
        except Exception as e:
            logger.error(f"✗ Failed to encode testing types: {e}")
            raise
        
        # Initialize filtering metadata
        self.filtering_metadata = {
            "sections_removed": 0,
            "lines_removed": 0,
            "examples": []
        }
        
        logger.info("=" * 80)
        logger.info("ENGINE READY - Multi-layered scoring with comprehensive logging")
        logger.info("=" * 80)
    
    async def _filter_out_of_scope_with_llm(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Use LLM to detect and remove ALL out-of-scope content from BRD.
        
        Examples LLM can catch and remove:
        - "Out of Scope" sections (any format: with/without colons, headers, bullets)
        - "(Phase 2)" markers
        - "Deferred", "Excluded", "Future Release"
        - "We're not focusing on X right now"
        - "Mobile app will come later"
        - "Let's table the discussion on Y"
        - "This is a nice-to-have for future"
        
        Args:
            text: Raw BRD document text
            
        Returns:
            Tuple of (cleaned_text, metadata_dict)
        """
        if not self.llm_client:
            logger.warning("LLM client not available - returning original text without filtering")
            return text, {
                "sections_removed": 0,
                "lines_removed": 0,
                "examples": []
            }
        
        try:
            prompt = f"""You are a Business Analyst expert. Your task is to clean a Business Requirements Document (BRD) by removing ONLY out-of-scope content while preserving all in-scope content.

**CRITICAL RULES:**

1. **PRESERVE "In Scope" sections** - NEVER remove content under "In Scope" headers
   - If you see "In Scope" or "In-Scope", keep ALL content under it
   - Only remove content explicitly under "Out of Scope" headers

2. **REMOVE "Out of Scope" sections ONLY** - Be thorough and catch ANY indication that something is NOT included in current scope:

   **Explicit Markers:**
   - "Out of Scope", "Out-of-Scope", "Not in Scope"
   - "Deferred", "Future", "Later Phase", "Phase 2+", "V2", "Version 2"
   - "Excluded", "Not Required", "Not Needed"
   - "[OUT OF SCOPE]", "[DEFERRED]", "(Phase 2)", "(Future Release)"
   
   **Informal Phrases:**
   - "not focusing on", "will come later", "future consideration"
   - "nice to have", "lower priority", "if time permits", "if we have time"
   - "next iteration", "post-launch", "post-MVP", "after go-live"
   - "we're skipping", "let's table this", "parking lot item"
   - "optional feature", "stretch goal", "backlog item"
   
   **Temporal Indicators:**
   - "in a future release", "in the next version", "down the road"
   - "eventually", "someday", "at a later date"

3. **Removal boundaries:**
   - Start removing FROM the "Out of Scope" header or exclusion phrase
   - Stop removing BEFORE the next major section (like "4. Requirements" or "In Scope")
   - If a "Scope" section has BOTH "In Scope" and "Out of Scope", remove ONLY the "Out of Scope" part

4. **Extract** titles of removed out-of-scope features/items for logging

**EXAMPLE:**
BEFORE:
```
3. Scope
  In Scope
    - Feature A
    - Feature B
  Out of Scope
    - Feature C
    - Feature D
```

AFTER (keep "In Scope", remove "Out of Scope"):
```
3. Scope
  In Scope
    - Feature A
    - Feature B
```

**ORIGINAL BRD:**
```
{text}
```

**RESPOND WITH JSON ONLY:**
{{
  "cleaned_text": "<full cleaned BRD with In Scope preserved, Out of Scope removed>",
  "removed_sections": ["Feature C", "Feature D"]
}}

**IMPORTANT:**
- Return the FULL cleaned text (not a summary)
- NEVER remove "In Scope" content
- ONLY remove "Out of Scope" content
- Be conservative - if unsure whether something is in or out of scope, KEEP it
- Respond ONLY with valid JSON, no extra text"""
            
            response = await self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=4000  # Enough for full BRD text
            )
            
            # Parse JSON response
            try:
                result = json.loads(response)
                cleaned_text = result.get("cleaned_text", text)
                removed_sections = result.get("removed_sections", [])
                
                # Calculate metrics and find removed content
                original_lines_list = text.split('\n')
                cleaned_lines_list = cleaned_text.split('\n')
                original_lines = len(original_lines_list)
                cleaned_lines = len(cleaned_lines_list)
                lines_removed = original_lines - cleaned_lines
                
                # Find removed lines by comparing original and cleaned
                removed_lines = []
                if lines_removed > 0:
                    # Simple diff: find lines in original but not in cleaned
                    cleaned_set = set(cleaned_lines_list)
                    for line in original_lines_list:
                        if line.strip() and line not in cleaned_set:
                            removed_lines.append(line.strip())
                
                metadata = {
                    "sections_removed": len(removed_sections),
                    "lines_removed": lines_removed,
                    "examples": removed_sections,
                    "removed_lines": removed_lines[:20]  # Limit to first 20 lines
                }
                
                logger.info(f"LLM successfully filtered BRD")
                logger.info(f"  Sections removed: {len(removed_sections)}")
                if removed_sections:
                    for section in removed_sections:
                        logger.info(f"    - {section}")
                
                return cleaned_text, metadata
                
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse LLM response as JSON: {str(e)[:100]}")
                logger.warning(f"Response preview: {response[:200]}")
                # Return original text if parsing fails
                return text, {
                    "sections_removed": 0,
                    "lines_removed": 0,
                    "examples": []
                }
            
        except Exception as e:
            logger.error(f"LLM filtering error: {e}")
            logger.warning("Falling back to original text without filtering")
            return text, {
                "sections_removed": 0,
                "lines_removed": 0,
                "examples": []
            }
    
    async def _preprocess_filter_out_of_scope(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        PHASE 1: TEXT SANITIZATION
        
        Remove sections marked as out of scope using LLM-only approach.
        
        The LLM intelligently detects and removes:
        - Explicit markers (## Out of Scope, [DEFERRED], (Phase 2), etc.)
        - Informal exclusion phrases ("not focusing on", "will come later")
        - Any format variations (with/without colons, bullets, headers)
        
        Features:
        - Format-agnostic (handles any BRD structure)
        - Context-aware removal (understands section boundaries)
        - Log removed sections (titles, count)
        - In-memory only (original document unchanged in database)
        
        Returns in API response:
        {
          "filtered_content": {
            "sections_removed": 3,
            "examples": ["Mobile App (Phase 2)", "Legacy Integration"]
          }
        }
        
        Args:
            text: Raw BRD document text
            
        Returns:
            Tuple of (cleaned_text, filtered_content_metadata)
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("PHASE 1: TEXT SANITIZATION - LLM-Only Out-of-Scope Filtering")
        logger.info("=" * 80)
        
        if not text:
            logger.warning("Empty text provided, skipping filtering")
            return text, {
                "sections_removed": 0,
                "lines_removed": 0,
                "examples": []
            }
        
        original_line_count = len(text.split('\n'))
        logger.info(f"Original document: {len(text)} characters, {original_line_count} lines")
        
        # Use LLM-only filtering
        if self.use_llm_filtering and self.llm_client:
            logger.info("")
            logger.info(f"LLM scanning {len(text)} characters for ALL out-of-scope patterns...")
            
            cleaned_text, metadata = await self._filter_out_of_scope_with_llm(text)
            
            final_line_count = len(cleaned_text.split('\n'))
            
            # Log summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("FILTERING SUMMARY - LLM Only")
            logger.info("=" * 80)
            logger.info(f"TOTAL sections removed: {metadata['sections_removed']}")
            if metadata['examples']:
                for title in metadata['examples']:
                    logger.info(f"   - {title}")
            logger.info(f"Lines removed: {metadata['lines_removed']}")
            
            # Show removed line content if available
            if 'removed_lines' in metadata and metadata['removed_lines']:
                logger.info("")
                logger.info("Removed lines preview:")
                for i, line in enumerate(metadata['removed_lines'][:10], 1):
                    logger.info(f"  Line {i}: {line[:100]}{'...' if len(line) > 100 else ''}")
                if len(metadata['removed_lines']) > 10:
                    logger.info(f"  ... and {len(metadata['removed_lines']) - 10} more lines")
            
            logger.info(f"")
            logger.info(f"Original: {len(text)} chars, {original_line_count} lines")
            logger.info(f"Final: {len(cleaned_text)} chars, {final_line_count} lines")
            logger.info(f"Content reduction: {100 - (len(cleaned_text) / len(text) * 100 if len(text) > 0 else 0):.1f}%")
            logger.info("=" * 80)
            
            self.filtering_metadata = metadata
            return cleaned_text, metadata
        else:
            logger.warning("LLM filtering disabled or client unavailable - returning original text")
            return text, {
                "sections_removed": 0,
                "lines_removed": 0,
                "examples": []
            }
    
    def _detect_negation(self, text: str, test_type: str) -> bool:
        """
        Detect negation phrases that explicitly exclude a requirement.
        
        Patterns:
        - "[feature] not required"
        - "excluded from [feature]"
        - "[feature] is out of scope"
        
        Args:
            text: Text to check
            test_type: Testing type name
            
        Returns:
            True if negation detected (should suppress recommendation)
        """
        negation_patterns = [
            r'not\s+required',
            r'not\s+needed',
            r'excluded\s+from',
            r'is\s+out\s+of\s+scope',
            r'will\s+not\s+be',
            r'should\s+not\s+be',
            r'no\s+need\s+for'
        ]
        
        # Check if test type keywords appear near negation phrases
        test_keywords = self.taxonomy[test_type]["keywords"]
        
        for keyword in test_keywords:
            for pattern in negation_patterns:
                # Check within 50 characters before/after keyword
                regex = re.compile(
                    rf'(?:.{{0,50}}{pattern}.{{0,50}}{keyword})|(?:{keyword}.{{0,50}}{pattern})',
                    re.IGNORECASE
                )
                if regex.search(text):
                    logger.debug(f"  ⚠ Negation detected for '{test_type}': '{keyword}' near '{pattern}'")
                    return True
        
        return False
    
    def _apply_domain_boosting(self, text: str, confidence: float, test_type: str) -> float:
        """
        Apply domain-specific confidence boosting AND suppression.
        
        Boosting:
        - Healthcare keywords: "Patient", "EHR", "HIPAA"
        - Boosted types: Security, Accessibility, Interoperability (+15%)
        
        Suppression:
        - Prevent healthcare-specific tests from appearing in non-healthcare BRDs
        - Suppress generic tests that don't match the domain context
        
        Args:
            text: Document text
            confidence: Base confidence score
            test_type: Testing type name
            
        Returns:
            Boosted/suppressed confidence score
        """
        text_lower = text.lower()
        
        # Define domain indicators
        healthcare_keywords = ["patient", "ehr", "hipaa", "medical", "clinical", "practitioner", "healthcare"]
        ecommerce_keywords = ["cart", "product", "checkout", "payment", "order", "purchase", "inventory", "size", "color"]
        fintech_keywords = ["transaction", "payment", "billing", "subscription", "stripe", "paypal"]
        
        # Detect domain context
        is_healthcare = any(keyword in text_lower for keyword in healthcare_keywords)
        is_ecommerce = any(keyword in text_lower for keyword in ecommerce_keywords)
        is_fintech = any(keyword in text_lower for keyword in fintech_keywords)
        
        # Healthcare-specific test types that should ONLY appear in healthcare contexts
        healthcare_only_types = ["Interoperability Testing", "Accessibility Compliance"]
        
        # Suppress healthcare-specific tests in non-healthcare contexts
        if test_type in healthcare_only_types and not is_healthcare:
            logger.debug(f"  ⬇ Domain suppression: {test_type} suppressed (not healthcare context)")
            return 0.0
        
        # Boost healthcare types in healthcare context
        healthcare_boost_types = ["Role-Based Access Testing", "Accessibility Compliance", "Interoperability Testing"]
        if test_type in healthcare_boost_types and is_healthcare:
            for keyword in healthcare_keywords:
                if keyword in text_lower:
                    boosted = min(1.0, confidence * 1.15)  # +15% boost, max 1.0
                    logger.debug(f"  ⬆ Healthcare boost: {test_type} {confidence:.3f} → {boosted:.3f}")
                    return boosted
        
        # Boost e-commerce types in e-commerce context
        ecommerce_boost_types = ["Functional Testing", "Error Handling Testing", "UI Regression Testing"]
        if test_type in ecommerce_boost_types and is_ecommerce:
            boosted = min(1.0, confidence * 1.10)  # +10% boost, max 1.0
            logger.debug(f"  ⬆ E-commerce boost: {test_type} {confidence:.3f} → {boosted:.3f}")
            return boosted
        
        # Boost fintech types in fintech context
        fintech_boost_types = ["Payment Workflow Testing", "Payment Security Testing", "API Functional Testing"]
        if test_type in fintech_boost_types and is_fintech:
            boosted = min(1.0, confidence * 1.10)  # +10% boost, max 1.0
            logger.debug(f"  ⬆ Fintech boost: {test_type} {confidence:.3f} → {boosted:.3f}")
            return boosted
        
        return confidence
    
    def _layer1_deterministic_keywords(
        self,
        text: str,
        user_stories: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, List[Tuple[str, List[str]]]]:
        """
        LAYER 1: DETERMINISTIC KEYWORD MATCHING
        
        High-precision pattern matching against testing type keywords.
        
        Args:
            text: Cleaned document text (BRD)
            user_stories: Optional list of user stories
        Returns:
            Dict mapping test_type -> [(match, keywords_matched), ...]
        """
        logger.info("")
        logger.info("LAYER 1: Deterministic Keyword Matching")
        logger.info("-" * 80)
        
        matches = defaultdict(list)
        text_lower = text.lower()
        
        for test_type, config in self.taxonomy.items():
            keywords = config.get("keywords", [])
            matched_keywords = []
            # BRD keyword matching
            for keyword in keywords:
                pattern = rf'\b{re.escape(keyword)}\b'
                if re.search(pattern, text_lower):
                    matched_keywords.append(keyword)
                    logger.info(f"Layer 1: Matched keyword '{keyword}' in BRD section.")
            # User story keyword matching
            if user_stories:
                for story in user_stories:
                    story_id = story.get('id', 'N/A')
                    story_text = (story.get('title', '') + ' ' + story.get('description', '')).lower()
                    for keyword in keywords:
                        pattern = rf'\b{re.escape(keyword)}\b'
                        if re.search(pattern, story_text):
                            if keyword not in matched_keywords:
                                matched_keywords.append(keyword)
                            logger.info(f"Layer 1: Matched keyword '{keyword}' in user story: '{story_id}'")
            if matched_keywords:
                # Determine minimum keywords based on test category
                # Standard tests (critical): 1 keyword sufficient
                # Recommended tests (advanced): 2 keywords to avoid false positives
                min_keywords = 1 if config.get('category') == 'standard' else 2
                
                if len(matched_keywords) >= min_keywords:
                    matches[test_type].append((text, matched_keywords))
                    logger.debug(f"  ✓ {test_type}: {len(matched_keywords)} keyword(s) matched")
                else:
                    logger.debug(f"  ⚠ {test_type}: Only {len(matched_keywords)} keyword(s) matched, need ≥{min_keywords}")
        logger.info(f"Deterministic matches: {len(matches)} testing types triggered (minimum 1 keyword required for standard tests, 2 for recommended)")
        return dict(matches)
    
    def _layer2_semantic_sections(
        self,
        text: str,
        top_k: int = 5
    ) -> Dict[str, Tuple[float, List[str]]]:
        """
        LAYER 2: SEMANTIC SECTION-LEVEL EMBEDDINGS
        
        Compute paragraph embeddings and compare against testing type descriptions.
        
        Args:
            text: Cleaned document text
            top_k: Number of top matches to return per section
            
        Returns:
            Dict mapping test_type -> (similarity_score, [matching_paragraphs])
        """
        logger.info("")
        logger.info("LAYER 2: Semantic Section-Level Embeddings")
        logger.info("-" * 80)
        
        # Split into paragraphs (non-empty lines separated by blank lines)
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip() and len(p.strip()) > 50]
        
        if not paragraphs:
            logger.warning("⚠ No substantial paragraphs found for semantic analysis")
            return {}
        
        logger.info(f"Analyzing {len(paragraphs)} paragraph(s)")
        
        # Encode paragraphs
        try:
            paragraph_embeddings = self.model.encode(
                paragraphs,
                convert_to_tensor=True,
                show_progress_bar=False
            )
        except Exception as e:
            logger.error(f"✗ Failed to encode paragraphs: {e}")
            return {}
        
        # Compute similarities
        similarities = util.cos_sim(paragraph_embeddings, self.test_type_embeddings)
        
        # Aggregate scores per test type
        results = {}
        
        for i, test_type in enumerate(self.test_type_names):
            # Get top-k paragraph matches for this test type
            test_type_sims = similarities[:, i].cpu().numpy()
            top_indices = np.argsort(test_type_sims)[-top_k:][::-1]
            
            avg_similarity = float(np.mean(test_type_sims[top_indices]))
            matching_paragraphs = [paragraphs[idx][:200] + "..." for idx in top_indices if test_type_sims[idx] > 0.28]
            
            if avg_similarity > 0.28:  # Lowered from 0.30 for better recall - matches QA intuition
                results[test_type] = (avg_similarity, matching_paragraphs)
                logger.debug(f"  ✓ {test_type}: {avg_similarity:.3f} similarity")
        
        logger.info(f"Semantic matches: {len(results)} testing types above threshold (0.28)")
        return results
    
    def _layer3_granular_user_stories(
        self,
        user_stories: List[Dict[str, str]],
        top_k: int = 3
    ) -> Dict[str, List[Tuple[str, float, str]]]:
        """
        LAYER 3: GRANULAR USER STORY-LEVEL EMBEDDINGS
        
        Compare individual user story descriptions against testing types.
        
        Args:
            user_stories: List of dicts with 'id', 'title', 'description'
            top_k: Number of top matches per story
            
        Returns:
            Dict mapping test_type -> [(story_id, similarity, story_text), ...]
        """
        logger.info("")
        logger.info("LAYER 3: Granular User Story-Level Embeddings")
        logger.info("-" * 80)
        
        if not user_stories:
            logger.warning("⚠ No user stories provided for granular analysis")
            return {}
        
        logger.info(f"Analyzing {len(user_stories)} user story/stories")
        logger.info("(Layer 3 weight: 35% - INCREASED for stronger user story influence)")
        
        # Extract story texts
        story_texts = []
        story_ids = []
        
        for story in user_stories:
            story_id = story.get('id', 'UNKNOWN')
            title = story.get('title', '')
            description = story.get('description', '')
            
            combined_text = f"{title}. {description}".strip()
            if combined_text and combined_text != '.':
                story_texts.append(combined_text)
                story_ids.append(story_id)
                logger.debug(f"  ✓ Story {story_id}: {len(combined_text)} chars")
            else:
                logger.warning(f"  ⚠ Story {story_id}: SKIPPED - empty title and description")
        
        if not story_texts:
            logger.warning("⚠ No valid story texts found")
            return {}
        
        # Encode stories
        try:
            story_embeddings = self.model.encode(
                story_texts,
                convert_to_tensor=True,
                show_progress_bar=False
            )
        except Exception as e:
            logger.error(f"✗ Failed to encode user stories: {e}")
            return {}
        
        # Compute similarities
        similarities = util.cos_sim(story_embeddings, self.test_type_embeddings)
        
        # Log top similarities for debugging
        logger.info("")
        logger.info("Layer 3 User Story Similarity Analysis:")
        for j, story_id in enumerate(story_ids):
            top_test_types = []
            story_sims = similarities[j, :].cpu().numpy()
            top_indices = np.argsort(story_sims)[-5:][::-1]  # Top 5 test types for this story
            for idx in top_indices:
                if story_sims[idx] > 0.15:  # Log if > 15%
                    top_test_types.append(f"{self.test_type_names[idx]} ({story_sims[idx]:.3f})")
            if top_test_types:
                logger.info(f"  Story {story_id}: {', '.join(top_test_types)}")
        
        # Aggregate per test type
        results = defaultdict(list)
        
        for i, test_type in enumerate(self.test_type_names):
            test_type_sims = similarities[:, i].cpu().numpy()
            
            # Get stories with similarity > 0.25 (lowered threshold for better recall)
            for j, sim_score in enumerate(test_type_sims):
                if sim_score > 0.25:
                    results[test_type].append((
                        story_ids[j],
                        float(sim_score),
                        story_texts[j][:150] + "..."
                    ))
                    logger.debug(f"  ✓ Layer3 Match: {test_type} ← Story {story_ids[j]} (similarity: {sim_score:.3f})")
            
            if results[test_type]:
                # Sort by similarity descending
                results[test_type].sort(key=lambda x: x[1], reverse=True)
                results[test_type] = results[test_type][:top_k]
                logger.info(f"  ✓ {test_type}: {len(results[test_type])} user story match(es) - Stories: {', '.join([s[0] for s in results[test_type]])}")
        
        logger.info(f"User story matches: {len(results)} testing types matched")
        return dict(results)
   
    def _build_sources_list(self, l3_stories: List[Tuple[str, float, str]], l2_paragraphs: List[str] = None) -> List[str]:
        """Build sources list from BRD sections and matched user stories"""
        sources = []
        
        # Add BRD with section evidence if available
        if l2_paragraphs:
            # Show BRD with top matching section as evidence
            top_section = l2_paragraphs[0][:150] + "..." if len(l2_paragraphs[0]) > 150 else l2_paragraphs[0]
            sources.append(f"BRD (Section: '{top_section}')")
        else:
            # Fallback to generic BRD
            sources.append("BRD")
        
        # Add user story IDs
        if l3_stories:
            for story_id, _, _ in l3_stories:
                if story_id not in sources:
                    sources.append(story_id)
        return sources
    
    def _weighted_fusion_scoring(
        self,
        layer1_matches: Dict[str, List[Tuple[str, List[str]]]],
        layer2_matches: Dict[str, Tuple[float, List[str]]],
        layer3_matches: Dict[str, List[Tuple[str, float, str]]],
        text: str,
        user_stories: List[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        PHASE 3: WEIGHTED FUSION SCORING
        
        Combine all three layers with configurable weights:
        - Layer 1 (Keywords): 30% weight (reduced for user story influence)
        - Layer 2 (Semantic): 35% weight
        - Layer 3 (User Stories): 35% weight (increased for stronger user story influence)
        
        Args:
            layer1_matches: Deterministic keyword matches
            layer2_matches: Semantic section matches
            layer3_matches: User story matches
            text: Full document text for negation/boosting
            
        Returns:
            List of recommendation dicts with confidence scores
        """
        logger.info("")
        logger.info("=" * 80)
        logger.info("PHASE 3: WEIGHTED FUSION SCORING")
        logger.info("=" * 80)
        
        # Weights
        W_LAYER1 = 0.30  # Reduced from 0.40 to give user stories more influence
        W_LAYER2 = 0.35
        W_LAYER3 = 0.35  # Increased from 0.25 to make user stories have stronger impact
        
        logger.info(f"Fusion weights: Layer1={W_LAYER1}, Layer2={W_LAYER2}, Layer3={W_LAYER3}")
        
        all_test_types = set(layer1_matches.keys()) | set(layer2_matches.keys()) | set(layer3_matches.keys())
        recommendations = []
        
        for test_type in all_test_types:
            # Layer 1 score
            l1_score = 0.0
            l1_keywords = []
            if test_type in layer1_matches:
                l1_keywords = layer1_matches[test_type][0][1]
                # Gradual scoring: 0.20 baseline + 0.25 per keyword, max 1.0
                if len(l1_keywords) >= 2:
                    l1_score = min(1.0, 0.20 + (len(l1_keywords) * 0.25))
                else:
                    l1_score = 0.0  # Shouldn't happen due to filter, but safety check
            
            # Layer 2 score
            l2_score = 0.0
            l2_paragraphs = []
            if test_type in layer2_matches:
                l2_score, l2_paragraphs = layer2_matches[test_type]
                l2_score = float(l2_score)  # Convert to native Python float
            
            # Layer 3 score
            l3_score = 0.0
            l3_stories = []
            if test_type in layer3_matches:
                l3_stories = layer3_matches[test_type]
                l3_score = float(np.mean([s[1] for s in l3_stories])) if l3_stories else 0.0
            
            # Weighted fusion
            base_confidence = (
                W_LAYER1 * l1_score +
                W_LAYER2 * l2_score +
                W_LAYER3 * l3_score
            )
            
            # USER STORY PRESENCE BONUS/PENALTY:
            # Only penalize tests with NO evidence from any layer (pure semantic drift)
            # If test has strong keyword matches, don't penalize for missing user stories
            if user_stories and len(user_stories) > 0:
                if l3_stories and len(l3_stories) > 0:
                    # Boost tests that match user stories by 30%
                    base_confidence = min(1.0, base_confidence * 1.30)
                    logger.info(f"  ✓ {test_type}: +30% user story presence bonus")
                elif len(l1_keywords) >= 1:  # Changed from >= 2 to >= 1
                    # Has keyword evidence (even 1 keyword), no penalty
                    logger.debug(f"  → {test_type}: No penalty (has keyword evidence)")
                elif l2_score >= 0.35:  # Changed from 0.40 to 0.35 (less strict)
                    # Has strong semantic match, only light penalty
                    base_confidence = base_confidence * 0.85  # Changed from 0.80 to 0.85 (-15% instead of -20%)
                    logger.info(f"  ⚠ {test_type}: -15% weak user story alignment (semantic only)")
                else:
                    # Weak evidence from all layers - moderate penalty (reduced from -50% to -30%)
                    base_confidence = base_confidence * 0.70  # Changed from 0.50 to 0.70
                    logger.info(f"  ⚠ {test_type}: -30% no explicit evidence (semantic drift)")
            
            # Check negation (override if detected)
            if self._detect_negation(text, test_type):
                logger.info(f"  ✗ {test_type}: SUPPRESSED due to negation")
                continue
            
            # Apply domain boosting
            final_confidence = self._apply_domain_boosting(text, base_confidence, test_type)
            
            # Skip if confidence is 0.000 (no evidence at all)
            if final_confidence == 0.0:
                continue
            
            # Build recommendation
            config = self.taxonomy[test_type]
            
            # Build triggering requirements list
            triggering_requirements = []
            if l1_keywords:
                for kw in l1_keywords[:5]:
                    triggering_requirements.append({
                        "type": "Keyword Match",
                        "artifact": f"Keyword: '{kw}'"
                    })
            if l2_paragraphs:
                for para in l2_paragraphs[:2]:
                    triggering_requirements.append({
                        "type": "BRD Section",
                        "artifact": para[:120] + "..." if len(para) > 120 else para
                    })
            if l3_stories:
                for story_id, sim, story_text in l3_stories[:3]:
                    triggering_requirements.append({
                        "type": "User Story",
                        "artifact": f"{story_id}: {story_text[:80]}..." if len(story_text) > 80 else f"{story_id}: {story_text}"
                    })
            
            # Build BRD sections list (from Layer 2)
            brd_sections = []
            if l2_paragraphs:
                for para in l2_paragraphs[:3]:  # Top 3 matching paragraphs
                    brd_sections.append(para[:300] + "..." if len(para) > 300 else para)
            
            # Build user stories list (from Layer 3)
            user_stories_matched = []
            if l3_stories:
                for story_id, sim, story_text in l3_stories[:3]:  # Top 3 matching stories
                    user_stories_matched.append({
                        "id": story_id,
                        "similarity": round(float(sim), 3),
                        "text": story_text[:200] + "..." if len(story_text) > 200 else story_text
                    })
            
            recommendation = {
                "test_type": test_type,
                "category": config["category"],
                "confidence": round(final_confidence, 3),
                
                # NEW: Short one-line description for UI display
                "display_description": config.get("display_description", config["description"][:100]),
                
                # Section 2: Overview (full static definition from taxonomy)
                "overview": config["description"],
                
                # NEW: BRD sections that triggered this recommendation
                "brd_sections": brd_sections,
                
                # NEW: User stories that matched this recommendation
                "user_stories": user_stories_matched,
                
                # Section 3: Why This Test Is Recommended (feature-specific, will be populated by LLM)
                "why_recommended": "",
                
                # Section 4: Requirements & Artifacts Triggering This Test (bullet list)
                "triggering_requirements": triggering_requirements,
                
                # Section 5: LLM Assessment (explainable AI summary, will be populated by LLM)
                "llm_assessment": "",
                
                # Section 7: Sources (with BRD section evidence when available)
                "sources": self._build_sources_list(l3_stories, l2_paragraphs),
                
                # Metadata for internal tracking
                "_detection_metadata": {
                    "layer1_keyword_score": round(l1_score, 3),
                    "layer2_semantic_score": round(l2_score, 3),
                    "layer3_story_score": round(l3_score, 3),
                    "base_confidence": round(base_confidence, 3),
                    "domain_boosted": bool(final_confidence != base_confidence),
                    "keywords_matched": l1_keywords[:5],
                    "user_stories_matched": [s[0] for s in l3_stories[:3]]
                },
                
                "risk_factor": config.get("risk_factor", "N/A"),
                "requirement_type": config.get("requirement_type", "N/A")
            }
            
            # EVIDENCE VALIDATION: Reject recommendations without explicit BRD triggers
            has_explicit_evidence = (
                len(l1_keywords) >= 2 or  # At least 2 keyword matches
                l2_score >= 0.35 or       # Strong semantic match
                len(l3_stories) >= 1      # At least 1 user story match
            )
            
            if not has_explicit_evidence:
                logger.info(f"  ⚠ {test_type}: REJECTED - insufficient explicit evidence (weak inference)")
                continue
            
            # SPECIAL VALIDATION: Payment Workflow Testing requires explicit payment keywords
            if test_type == "Payment Workflow Testing":
                # Must have at least one core payment keyword
                core_payment_keywords = [
                    "payment", "billing", "checkout", "transaction", "refund",
                    "subscription", "stripe", "paypal", "payment gateway",
                    "credit card", "debit card", "invoice", "payment processing"
                ]
                has_payment_keyword = any(
                    kw in l1_keywords for kw in core_payment_keywords
                )
                if not has_payment_keyword:
                    logger.info(f"  ⚠ {test_type}: REJECTED - no explicit payment keywords (false positive from generic terms)")
                    continue
            
            # SPECIAL VALIDATION: Payment Security Testing requires explicit security keywords
            if test_type == "Payment Security Testing":
                security_payment_keywords = [
                    "pci", "pci-dss", "payment security", "encryption", "fraud",
                    "cvv", "tokenization", "secure payment", "compliance"
                ]
                has_security_keyword = any(
                    kw in l1_keywords for kw in security_payment_keywords
                )
                if not has_security_keyword:
                    logger.info(f"  ⚠ {test_type}: REJECTED - no explicit payment security keywords")
                    continue
            
            # Log user story attribution
            story_ids_list = [s[0] for s in l3_stories[:3]]
            if story_ids_list:
                logger.info(f"  📝 {test_type}: Attributed to stories: {', '.join(story_ids_list)}")
            else:
                logger.debug(f"  📝 {test_type}: No user story attribution (keywords/BRD only)")
            
            recommendations.append(recommendation)
            logger.debug(f"  ✓ {test_type}: {final_confidence:.3f} (L1={l1_score:.2f}, L2={l2_score:.2f}, L3={l3_score:.2f})")
        
        # Sort by confidence descending
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        
        # DEBUG: Log top 5 scores even if below threshold
        logger.info("")
        logger.info("Top 5 confidence scores (before threshold filter):")
        for i, rec in enumerate(recommendations[:5]):
            logger.info(f"  {i+1}. {rec['test_type']}: {rec['confidence']:.3f}")
        
        logger.info("")
        logger.info(f"Final recommendations: {len(recommendations)} testing types")
        logger.info("=" * 80)
        
        return recommendations
    
    async def generate_recommendations(
        self,
        brd_text: str,
        user_stories: Optional[List[Dict[str, str]]] = None,
        confidence_threshold: float = 0.08
    ) -> Dict[str, Any]:
        """
        Main method to generate testing recommendations.
        
        Args:
            brd_text: Raw BRD document text
            user_stories: Optional list of user stories with 'id', 'title', 'description'
            confidence_threshold: Minimum confidence to include (default: 0.08)
            
        Returns:
            Audit-ready JSON response with recommendations and metadata
        
        Note:
            LLM is used ONLY for out-of-scope content filtering.
            Justifications are rule-based for speed and reliability.
        """
        logger.info("")
        logger.info("#" * 80)
        logger.info("STARTING RECOMMENDATION GENERATION")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("#" * 80)
        logger.info("")
        logger.info("INPUT ANALYSIS:")
        logger.info(f"  • BRD Length: {len(brd_text)} characters, {len(brd_text.split())} words")
        logger.info(f"  • User Stories: {len(user_stories or [])} provided")
        if user_stories:
            for story in user_stories[:3]:
                logger.info(f"    - {story.get('id', 'N/A')}: {story.get('title', 'N/A')[:60]}...")
            if len(user_stories) > 3:
                logger.info(f"    - ... and {len(user_stories) - 3} more")
        logger.info(f"  • Confidence Threshold: {confidence_threshold}")
        logger.info("")
        logger.info("ANALYSIS PIPELINE:")
        logger.info("  1. Remove Out-of-Scope sections from BRD (LLM + Regex)")
        logger.info("  2. Layer 1: Keyword matching (deterministic, QA-focused)")
        logger.info("  3. Layer 2: Semantic section analysis (BRD paragraphs)")
        logger.info("  4. Layer 3: User story semantic analysis")
        logger.info("  5. Weighted fusion scoring (30% + 35% + 35%)")
        logger.info("  6. Domain boosting & confidence adjustment")
        logger.info("  7. Rule-based justification generation")
        logger.info("")
        
        # PHASE 1: Text Sanitization
        cleaned_text, filtering_metadata = await self._preprocess_filter_out_of_scope(brd_text)
        
        # PHASE 2: Multi-layer scoring
        logger.info("")
        logger.info("=" * 80)
        logger.info("PHASE 2: VECTOR ENCODING & MULTI-LAYER ANALYSIS")
        logger.info("=" * 80)
        
        logger.info("ANALYZING BRD DOCUMENT:")
        logger.info(f"  • Document after filtering: {len(cleaned_text)} characters")
        logger.info("  • Running Layer 1 (Keyword Matching)...")
        layer1_matches = self._layer1_deterministic_keywords(cleaned_text)
        logger.info(f"  ✓ Layer 1 Complete: {len(layer1_matches)} testing types triggered")
        
        logger.info("  • Running Layer 2 (Semantic Section Analysis)...")
        layer2_matches = self._layer2_semantic_sections(cleaned_text, top_k=5)
        logger.info(f"  ✓ Layer 2 Complete: {len(layer2_matches)} testing types matched")
        
        logger.info("")
        logger.info("ANALYZING USER STORIES:")
        if user_stories:
            logger.info(f"  • Processing {len(user_stories)} user stories...")
        layer3_matches = self._layer3_granular_user_stories(user_stories or [], top_k=3)
        if user_stories:
            logger.info(f"  ✓ Layer 3 Complete: {len(layer3_matches)} testing types matched")
        
        # PHASE 3: Weighted Fusion
        recommendations = self._weighted_fusion_scoring(
            layer1_matches,
            layer2_matches,
            layer3_matches,
            cleaned_text,
            user_stories  # Pass user stories for presence bonus/penalty
        )
        
        # Filter by confidence threshold
        filtered_recommendations = [
            rec for rec in recommendations
            if rec["confidence"] >= confidence_threshold
        ]
        
        logger.info("")
        logger.info(f"Applied confidence threshold: {confidence_threshold}")
        logger.info(f"Recommendations above threshold: {len(filtered_recommendations)}/{len(recommendations)}")
        
        # Diagnose if no recommendations found
        if len(filtered_recommendations) == 0:
            logger.warning("")
            logger.warning("⚠" * 40)
            logger.warning("NO TESTING TYPES DETECTED")
            logger.warning("⚠" * 40)
            logger.warning("")
            logger.warning("Possible reasons:")
            logger.warning("  1. BRD text is too short or lacks technical details")
            logger.warning(f"     → Current BRD length: {len(cleaned_text)} characters")
            logger.warning("")
            logger.warning("  2. No keywords matched from testing taxonomy")
            logger.warning(f"     → Layer 1 matches: {len(layer1_matches)} testing types")
            logger.warning("")
            logger.warning("  3. Semantic similarity scores too low")
            logger.warning(f"     → Layer 2 matches: {len(layer2_matches)} testing types")
            logger.warning("")
            logger.warning("  4. User stories not provided or too vague")
            logger.warning(f"     → User stories provided: {len(user_stories or [])}")
            logger.warning(f"     → Layer 3 matches: {len(layer3_matches)} testing types")
            logger.warning("")
            logger.warning("  5. All recommendations filtered out by confidence threshold")
            if recommendations:
                top_filtered = recommendations[0]
                logger.warning(f"     → Highest confidence: {top_filtered['confidence']:.3f} ({top_filtered['test_type']})")
                logger.warning(f"     → Threshold: {confidence_threshold}")
                logger.warning(f"     → Try lowering threshold to {top_filtered['confidence'] - 0.01:.2f} or below")
            logger.warning("")
            logger.warning("Recommendations:")
            logger.warning("  • Add more specific technical requirements to the BRD")
            logger.warning("  • Include keywords like: test, validate, security, performance, UI, API")
            logger.warning("  • Provide detailed user stories with acceptance criteria")
            logger.warning("  • Describe system components, workflows, and integrations")
            logger.warning("")
            logger.warning("⚠" * 40)
        
        # PHASE 4: Build justifications (LLM justification layer completely removed)
        # Note: LLM is ONLY used for out-of-scope filtering, NOT for generating explanations
        # Using rule-based justifications for speed and reliability
        for rec in filtered_recommendations:
            metadata = rec["_detection_metadata"]
            keywords = metadata["keywords_matched"]
            rec["why_recommended"] = f"This test is recommended based on {len(keywords)} requirement matches with {rec['confidence']:.0%} confidence."
            rec["llm_assessment"] = f"Detected via keyword and semantic analysis with {rec['confidence']:.0%} confidence."
        # Build final response with exact API format
        response = {
            "timestamp": datetime.now().isoformat(),
            "model_used": self.model_name,
            "confidence_threshold": confidence_threshold,
            "filtered_content": {
                "sections_removed": filtering_metadata["sections_removed"],
                "examples": filtering_metadata["examples"]
            },
            "recommendations": filtered_recommendations,
            "summary": {
                "total_recommendations": len(filtered_recommendations),
                "standard_tests": len([r for r in filtered_recommendations if r["category"] == "standard"]),
                "recommended_tests": len([r for r in filtered_recommendations if r["category"] == "recommended"]),
                "average_confidence": round(
                    np.mean([r["confidence"] for r in filtered_recommendations]),
                    3
                ) if filtered_recommendations else 0.0
            }
        }
        
        logger.info("")
        logger.info("#" * 80)
        logger.info("RECOMMENDATION GENERATION COMPLETE")
        logger.info(f"Total: {response['summary']['total_recommendations']} recommendations")
        logger.info(f"Standard: {response['summary']['standard_tests']}, Recommended: {response['summary']['recommended_tests']}")
        logger.info(f"Average Confidence: {response['summary']['average_confidence']}")
        logger.info("#" * 80)
        
        return response


# ============================================================================
# Helper Functions
# ============================================================================

def format_recommendations_for_report(
    recommendations: List[Dict[str, Any]],
    format_type: str = "markdown"
) -> str:
    """
    Format recommendations for human-readable report.
    
    Args:
        recommendations: List of recommendation dicts
        format_type: Output format ('markdown', 'html', 'text')
        
    Returns:
        Formatted report string
    """
    if format_type == "markdown":
        lines = ["# Testing Recommendations Report", ""]
        
        # Standard Tests
        standard = [r for r in recommendations if r["category"] == "standard"]
        if standard:
            lines.append("## Standard Tests (Critical/MVP)")
            lines.append("")
            for rec in standard:
                lines.append(f"### {rec['test_type']} (Confidence: {rec['confidence']:.1%})")
                lines.append(f"**Risk Factor:** {rec['risk_factor']}")
                lines.append(f"**Description:** {rec['description']}")
                lines.append(f"**Justification:** {rec.get('why_recommended', 'N/A')}")
                lines.append("")
        
        # Recommended Tests
        recommended = [r for r in recommendations if r["category"] == "recommended"]
        if recommended:
            lines.append("## Recommended Tests (Advanced/Post-MVP)")
            lines.append("")
            for rec in recommended:
                lines.append(f"### {rec['test_type']} (Confidence: {rec['confidence']:.1%})")
                lines.append(f"**Risk Factor:** {rec['risk_factor']}")
                lines.append(f"**Description:** {rec['description']}")
                lines.append("")
        
        return "\n".join(lines)
    
    elif format_type == "text":
        lines = ["TESTING RECOMMENDATIONS REPORT", "=" * 60, ""]
        
        for rec in recommendations:
            lines.append(f"{rec['test_type']} [{rec['category'].upper()}] - {rec['confidence']:.1%}")
            lines.append(f"  {rec['description']}")
            lines.append("")
        
        return "\n".join(lines)
    
    else:
        raise ValueError(f"Unsupported format type: {format_type}")


# For backwards compatibility - export old template name
TEST_TEMPLATES = TESTING_TYPES_TAXONOMY


if __name__ == "__main__":
    # Example usage
    logger.info("Testing Recommendation Engine - Example Run")
    
    sample_brd = """
    # Business Requirements Document
    
    ## User Authentication
    Users must be able to login using email and password.
    Session should expire after 30 minutes of inactivity.
    
    ## Patient Dashboard
    Healthcare practitioners can view patient records and medical history.
    The dashboard must comply with HIPAA regulations.
    
    ## Payment Processing
    Users can purchase subscriptions using credit cards.
    All payment data must be PCI-DSS compliant.
    
    ## Out of Scope
    - Mobile app development
    - Integration with legacy systems
    """
    
    sample_stories = [
        {
            "id": "US-001",
            "title": "User Login",
            "description": "As a user, I want to login securely so I can access my dashboard"
        },
        {
            "id": "US-002",
            "title": "View Patient Records",
            "description": "As a practitioner, I want to view patient medical history in the dashboard"
        }
    ]
    
    engine = TestingRecommendationEngine()
    results = engine.generate_recommendations(sample_brd, sample_stories)
    
    print("\n" + "=" * 80)
    print("SAMPLE RESULTS (JSON)")
    print("=" * 80)
    print(json.dumps(results, indent=2))
