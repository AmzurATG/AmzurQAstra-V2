"""
Quick test script to verify domain classification is working
Run with: python test_domain_classification.py
"""

import sys
import json
from services.domain_test_orchestrator import get_orchestrator

# Sample Healthcare BRD
healthcare_brd = """
Patient Management System Requirements

The system must manage patient records including personal information, medical history, 
diagnoses, prescriptions, and treatment plans. All data must comply with HIPAA regulations.

Key features:
- Electronic Health Records (EHR) management
- Doctor-patient appointment scheduling
- Prescription management and pharmacy integration
- Lab test results tracking
- Insurance claim processing
- Patient portal for accessing medical records

Security Requirements:
- HIPAA compliance mandatory
- Role-based access control (doctors, nurses, administrators)
- Audit logging for all patient data access
- Encrypted data storage and transmission
"""

healthcare_stories = [
    {
        "id": "US-001",
        "title": "Patient Registration",
        "description": "As a receptionist, I want to register new patients with their personal and insurance information"
    },
    {
        "id": "US-002", 
        "title": "View Medical History",
        "description": "As a doctor, I want to view patient's complete medical history and previous diagnoses"
    }
]

# Sample E-commerce BRD
ecommerce_brd = """
Online Shopping Platform Requirements

Build a modern e-commerce platform for retail clothing sales.

Key Features:
- Product catalog with categories, filters, search
- Shopping cart and wishlist
- Secure payment processing (credit card, PayPal, etc.)
- Order management and tracking
- Customer reviews and ratings
- Inventory management
- Promotional codes and discounts

Security:
- PCI-DSS compliance for payment data
- SSL encryption
- Fraud detection
"""

ecommerce_stories = [
    {
        "id": "US-003",
        "title": "Browse Products",
        "description": "As a customer, I want to browse products by category and filter by price"
    },
    {
        "id": "US-004",
        "title": "Checkout Process",
        "description": "As a customer, I want to complete checkout with multiple payment options"
    }
]


def test_classification(name: str, brd: str, stories: list):
    """Test domain classification with sample data"""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print('='*80)
    
    orchestrator = get_orchestrator()
    result = orchestrator.analyze_requirements(brd, stories)
    
    # Extract key info
    classification = result.get('domain_classification', {})
    test_recommendations = result.get('test_recommendations', {})
    metadata = result.get('metadata', {})
    
    # Check if low confidence response
    if result.get('status') == 'LOW_CONFIDENCE':
        print(f"\n[!] LOW CONFIDENCE RESULT")
        print(f"   Message: {result.get('message')}")
        print(f"\nTOP CANDIDATES:")
        for i, candidate in enumerate(classification.get('top_candidates', []), 1):
            print(f"   {i}. {candidate.get('domain')}: {candidate.get('confidence', 0):.1%}")
        return result
    
    print(f"\nCLASSIFICATION RESULTS:")
    print(f"   Domain: {classification.get('domain', 'unknown')}")
    print(f"   Confidence: {classification.get('confidence_score', 0.0):.1%}")
    print(f"   Level: {metadata.get('confidence_level', 'unknown')}")
    
    # Show evidence
    evidence = classification.get('evidence', [])
    if evidence:
        print(f"\nEVIDENCE (matched keywords):")
        print(f"   {', '.join(evidence[:10])}")  # Show first 10
        if len(evidence) > 10:
            print(f"   ... and {len(evidence) - 10} more")
    
    # Show scores breakdown
    all_scores = classification.get('all_scores', {})
    if all_scores:
        print(f"\nSCORING BREAKDOWN:")
        for domain, score_data in all_scores.items():
            if score_data.get('final', 0) > 0.1:  # Only show significant scores
                print(f"   {domain}: {score_data.get('final', 0):.1%} "
                      f"(keywords: {score_data.get('keyword', 0):.1%}, "
                      f"context: {score_data.get('context', 0):.1%})")
    
    # Show recommendations
    standard = test_recommendations.get('standard_tests', [])
    recommended = test_recommendations.get('recommended_tests', [])
    
    print(f"\nRECOMMENDATIONS:")
    print(f"   Standard Tests: {len(standard)}")
    if standard:
        for test in standard[:3]:  # Show first 3
            print(f"      - {test.get('type')} [{test.get('priority')}]")
        if len(standard) > 3:
            print(f"      ... and {len(standard) - 3} more")
    
    print(f"\n   Recommended Tests: {len(recommended)}")
    if recommended:
        for test in recommended[:3]:  # Show first 3
            print(f"      - {test.get('type')} [{test.get('priority')}]")
        if len(recommended) > 3:
            print(f"      ... and {len(recommended) - 3} more")
    
    # Show processing time
    processing_time = result.get('processing_time_ms', 0)
    print(f"\nProcessing Time: {processing_time:.0f}ms")
    
    return result


if __name__ == "__main__":
    print("\n" + "="*80)
    print("DOMAIN CLASSIFICATION TEST SUITE")
    print("="*80)
    
    try:
        # Test 1: Healthcare
        result1 = test_classification(
            "Healthcare - Patient Management System",
            healthcare_brd,
            healthcare_stories
        )
        
        # Test 2: E-commerce
        result2 = test_classification(
            "E-commerce - Online Shopping Platform",
            ecommerce_brd,
            ecommerce_stories
        )
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nSummary:")
        print(f"  Test 1 Domain: {result1.get('domain_classification', {}).get('domain')}")
        print(f"  Test 2 Domain: {result2.get('domain_classification', {}).get('domain')}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
