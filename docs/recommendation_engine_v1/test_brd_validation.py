"""Test BRD validation logic"""

def validate_user_stories_coverage(brd_content: str, user_stories: list) -> list:
    """Validate if user stories are covered in the BRD content."""
    if not user_stories:
        return []
    
    brd_lower = brd_content.lower()
    unmatched_stories = []
    
    for story in user_stories:
        # Extract key terms from user story
        story_text = f"{story.get('title', '')} {story.get('description', '')} {story.get('acceptance_criteria', '')}".lower()
        
        # Extract meaningful words
        story_words = set([
            word.strip() for word in story_text.split() 
            if len(word.strip()) > 3 and word.strip() not in {
                'user', 'want', 'need', 'should', 'must', 'will', 'can', 'able',
                'given', 'when', 'then', 'and', 'the', 'for', 'with', 'that', 'this',
                'from', 'have', 'been', 'has', 'are', 'was', 'were', 'been'
            }
        ])
        
        # Check if at least 30% of meaningful words appear in BRD
        if story_words:
            matched_words = sum(1 for word in story_words if word in brd_lower)
            match_percentage = matched_words / len(story_words)
            
            if match_percentage < 0.3:
                unmatched_stories.append({
                    "id": story.get('id', 'N/A'),
                    "title": story.get('title', 'Untitled'),
                    "match_percentage": round(match_percentage * 100, 1)
                })
                print(f"❌ '{story.get('title')}' - {match_percentage:.1%} matched")
            else:
                print(f"✅ '{story.get('title')}' - {match_percentage:.1%} matched")
    
    return unmatched_stories


# Test Case 1: Matching stories
print("=== TEST 1: Matching Stories ===")
brd1 = """
Healthcare Management System
Patient records, medical history, doctor appointments, prescription tracking,
HIPAA compliance, electronic health records.
"""

stories1 = [
    {"id": "US-1", "title": "Patient Registration", "description": "Register new patient with medical history"},
    {"id": "US-2", "title": "Doctor Appointment", "description": "Schedule appointment with doctor"}
]

result1 = validate_user_stories_coverage(brd1, stories1)
print(f"Unmatched: {len(result1)}\n")


# Test Case 2: Non-matching stories
print("=== TEST 2: Non-Matching Stories ===")
brd2 = """
E-commerce Platform
Shopping cart, product catalog, payment gateway, order tracking
"""

stories2 = [
    {"id": "US-3", "title": "Flight Booking", "description": "Book international flight tickets"},
    {"id": "US-4", "title": "Hotel Reservation", "description": "Reserve hotel rooms"}
]

result2 = validate_user_stories_coverage(brd2, stories2)
print(f"Unmatched: {len(result2)}")
for story in result2:
    print(f"  - {story['title']} ({story['match_percentage']}% match)")
