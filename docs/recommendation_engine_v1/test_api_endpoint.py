"""
Test the domain-based recommendations API endpoint
Run backend server first: uvicorn main:app --reload --port 8000
Then run: python test_api_endpoint.py
"""

import requests
import json

# Test data
healthcare_request = {
    "brd_content": """
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
    """,
    "user_stories": [
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
}

ecommerce_request = {
    "brd_content": """
    Online Shopping Platform Requirements
    
    Build a modern e-commerce platform for retail clothing sales.
    
    Key Features:
    - Product catalog with categories, filters, search
    - Shopping cart and wishlist
    - Secure payment processing (credit card, PayPal, Stripe)
    - Order management and tracking
    - Customer reviews and ratings
    - Inventory management
    - Promotional codes and discounts
    
    Security:
    - PCI-DSS compliance for payment data
    - SSL encryption
    - Fraud detection
    """,
    "user_stories": [
        {
            "id": "US-003",
            "title": "Browse Products",
            "description": "As a customer, I want to browse products by category and filter by price"
        }
    ]
}

def test_endpoint(name: str, payload: dict):
    """Test the API endpoint"""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print('='*80)
    
    url = "http://localhost:8000/api/test-recommendations/domain-based-recommendations"
    
    try:
        print(f"Sending POST request to: {url}")
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                result = data.get('data', {})
                classification = result.get('domain_classification', {})
                recommendations = result.get('recommendations', {})
                
                print(f"\n✅ SUCCESS")
                print(f"\n📊 Domain: {classification.get('domain')}")
                print(f"   Confidence: {classification.get('confidence_score', 0):.1%}")
                print(f"   Level: {classification.get('confidence_level')}")
                
                evidence = classification.get('evidence', [])
                if evidence:
                    print(f"\n🔍 Evidence: {', '.join(evidence[:8])}")
                
                standard = recommendations.get('standard', [])
                recommended = recommendations.get('recommended', [])
                
                print(f"\n✅ Recommendations:")
                print(f"   Standard: {len(standard)} tests")
                print(f"   Recommended: {len(recommended)} tests")
                
                if standard:
                    print(f"\n   Top Standard Tests:")
                    for test in standard[:3]:
                        print(f"      - {test.get('type')} [{test.get('priority')}]")
                
                metadata = result.get('metadata', {})
                print(f"\n⏱️  Processing Time: {metadata.get('processing_time_ms', 0):.0f}ms")
                
            else:
                print(f"❌ FAILED: {data.get('message', 'Unknown error')}")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR")
        print("Make sure the backend server is running:")
        print("   cd backend")
        print("   uvicorn main:app --reload --port 8000")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔬 API ENDPOINT TEST")
    print("="*80)
    print("\nEndpoint: POST /api/test-recommendations/domain-based-recommendations")
    print("Server: http://localhost:8000")
    
    # Test 1: Healthcare
    test_endpoint("Healthcare - Patient Management", healthcare_request)
    
    # Test 2: E-commerce
    test_endpoint("E-commerce - Online Shopping", ecommerce_request)
    
    print("\n" + "="*80)
    print("✅ API TESTS COMPLETED")
    print("="*80)
