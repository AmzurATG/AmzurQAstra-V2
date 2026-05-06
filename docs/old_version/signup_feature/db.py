from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE, JWT_SECRET
from typing import Optional, List, Dict, Any
import bcrypt
import logging
import jwt
import uuid
import datetime
from models import UserCreate, User, SecurityQuestion
from utils.supabase_resilient import (
    execute_with_retry_and_fallback,
    fetch_users_via_rest,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        # Use service role key for full database access
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)
        self.login_attempts = {}
        self.lockout_duration_minutes = 5

    def email_exists(self, email: str) -> bool:
        try:
            def _supabase_call():
                return self.supabase.table('users').select('email').eq('email', email).execute()

            def _rest_fallback():
                return fetch_users_via_rest(SUPABASE_URL, SUPABASE_SERVICE_ROLE, email=email)

            result = execute_with_retry_and_fallback(_supabase_call, _rest_fallback)
            return len(result) > 0 if result else False
        except Exception as e:
            logger.error(f"Error checking if email exists: {str(e)}")
            # Default to false on error to avoid revealing user information
            return False

    def create_user(self, user_data: UserCreate) -> User:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user_data.password.encode(), salt).decode()
        new_user = {
            "first_name": user_data.first_name or None,
            "last_name": user_data.last_name or None,
            "company_name": user_data.company_name or None,
            "email": user_data.email,
            "country_code": user_data.country_code,  # Add country_code field
            "phone_no": user_data.phone_number if user_data.phone_number else None,  # Changed to phone_no to match schema
            "password_hash": hashed_password,  # Changed to password_hash to match schema
            "is_verified": False  # User starts as not verified
        }
        try:
            user_response = self.supabase.table('users').insert(new_user).execute()
            if not user_response.data:
                raise Exception("Failed to create user")
            created_user = user_response.data[0]
            user_id = created_user['id']
            # Store security questions with hashed answers
            for sq in user_data.security_questions:
                # Hash the security answer for security
                answer_hash = bcrypt.hashpw(sq.answer.lower().encode(), bcrypt.gensalt()).decode()
                self.supabase.table('security_questions').insert({
                    "user_id": user_id,
                    "question_text": sq.question,  # Changed to question_text to match schema
                    "answer_hash": answer_hash  # Store hashed answer
                }).execute()
            return User(**created_user)
        except Exception as e:
            logger.error(f"Error in create_user transaction: {str(e)}")
            raise

    def verify_user(self, email: str) -> bool:
        """Mark user as verified in database after OTP verification"""
        logger.info(f"Marking user verified: {email}")
        response = self.supabase.table('users').update({"is_verified": True}).eq('email', email).execute()
        success = len(response.data) > 0
        if success:
            logger.info(f"Successfully verified user: {email}")
        else:
            logger.warning(f"Failed to verify user: {email}")
        return success

    def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            def _supabase_call():
                return self.supabase.table('users').select('*').eq('email', email).execute()

            def _rest_fallback():
                return fetch_users_via_rest(SUPABASE_URL, SUPABASE_SERVICE_ROLE, email=email)

            data_list = execute_with_retry_and_fallback(_supabase_call, _rest_fallback)
            if data_list:
                user_data = data_list[0]
                user_data['phone_number'] = user_data.get('phone_no', '')
                return User(**user_data)
        except Exception as e:
            logger.error(f"Error retrieving user by email: {e}")
        return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            try:
                uid_int = int(user_id)
            except (ValueError, TypeError):
                uid_int = None

            def _supabase_call():
                return self.supabase.table('users').select('*').eq('id', user_id).execute()

            def _rest_fallback():
                if uid_int is None:
                    return []
                return fetch_users_via_rest(SUPABASE_URL, SUPABASE_SERVICE_ROLE, user_id=uid_int)

            data_list = execute_with_retry_and_fallback(_supabase_call, _rest_fallback)
            if data_list:
                user_data = data_list[0]
                user_data['phone_number'] = user_data.get('phone_no', '')
                return User(**user_data)
            return None
        except Exception as e:
            logger.error(f"Error retrieving user by ID: {str(e)}")
            return None

    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        logger.info(f"🔐 Authentication attempt for email: {email}")

        lockout_info = self.check_account_lockout(email)
        if lockout_info["locked"]:
            logger.warning(f"🔒 Account locked for {email}")
            return {"error": "account_locked", "message": f"Locked. Try in {lockout_info['minutes']} min"}

        def _supabase_call():
            return self.supabase.table('users').select('*').eq('email', email).execute()

        def _rest_fallback():
            return fetch_users_via_rest(SUPABASE_URL, SUPABASE_SERVICE_ROLE, email=email)

        try:
            data_list = execute_with_retry_and_fallback(_supabase_call, _rest_fallback)
        except Exception as e:
            logger.error(f"Database unavailable during login: {e}")
            return {
                "error": "service_unavailable",
                "message": "Authentication service is temporarily unavailable. Please try again or use a different network.",
            }

        if not data_list:
            logger.warning(f"[ERROR] No user found for email: {email}")
            self.record_login_attempt(email, False)
            return None

        user_data = data_list[0]
        logger.info(f"[SUCCESS] User found - ID: {user_data['id']}, is_verified: {user_data.get('is_verified')}")

        if not user_data.get('is_verified'):
            logger.warning(f"[WARNING] User not verified: {email}")
            return {"error": "user_not_verified"}

        # Check password
        password_hash = user_data.get('password_hash')
        if not password_hash:
            logger.error(f"[ERROR] No password_hash found for user: {email}")
            self.record_login_attempt(email, False)
            return {"error": "invalid_credentials"}

        logger.info(f"[AUTH] Checking password for {email}")
        pw_hash_bytes = password_hash.encode() if isinstance(password_hash, str) else password_hash
        try:
            password_match = bcrypt.checkpw(password.encode(), pw_hash_bytes)
        except Exception as e:
            logger.error(f"Password check error: {e}")
            return {"error": "invalid_credentials"}
        logger.info(f"[AUTH] Password match result: {password_match}")
        
        if not password_match:
            logger.warning(f"[ERROR] Invalid password for {email}")
            self.record_login_attempt(email, False)
            return {"error": "invalid_credentials"}
        
        logger.info(f"[SUCCESS] Authentication successful for {email}")
        self.record_login_attempt(email, True)
        payload = {"user_id": user_data['id'], "email": user_data['email'], "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)}
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        return {
            "id": user_data['id'],
            "first_name": user_data['first_name'],
            "last_name": user_data['last_name'],
            "email": user_data['email'],
            "company_name": user_data['company_name'],
            "token": token,
            "detail": "Login successful"
        }

    def get_security_questions(self, email: str) -> List[SecurityQuestion]:
        try:
            # First check if the email exists
            if not self.email_exists(email):
                logger.warning(f"Attempted to get security questions for non-existent email: {email}")
                # Return default questions for non-existent emails
                return [
                    {"question": "What is your favorite color?", "answer": ""},
                    {"question": "What is your pet's name?", "answer": ""}
                ]
               
            user_response = self.supabase.table('users').select('id').eq('email', email).execute()
            if not user_response.data:
                logger.warning(f"No user found with email: {email}")
                return []
               
            user_id = user_response.data[0]['id']
            questions = self.supabase.table('security_questions').select('question_text').eq('user_id', user_id).execute().data
            return [{"question": q['question_text'], "answer": ""} for q in questions]
        except Exception as e:
            logger.error(f"Error getting security questions: {str(e)}")
            return []

    def verify_security_answers(self, email: str, answers: List[SecurityQuestion]) -> bool:
        try:
            # First check if the email exists
            if not self.email_exists(email):
                logger.warning(f"Attempted to verify security answers for non-existent email: {email}")
                return False
               
            user_response = self.supabase.table('users').select('id').eq('email', email).execute()
            if not user_response.data:
                logger.warning(f"No user found with email: {email}")
                return False
               
            user_id = user_response.data[0]['id']
            for a in answers:
                response = self.supabase.table('security_questions').select('answer_hash').eq('user_id', user_id).eq('question_text', a.question).execute()
                if not response.data:
                    return False
                # Verify hashed answer
                stored_hash = response.data[0]['answer_hash']
                if not bcrypt.checkpw(a.answer.lower().encode(), stored_hash.encode()):
                    return False
            return True
        except Exception as e:
            logger.error(f"Error verifying security answers: {str(e)}")
            return False

    def verify_security_answers_detailed(self, email: str, answers: List[SecurityQuestion]) -> Dict[str, Any]:
        """
        Verify security answers and return detailed results for each answer
        Returns: dict with verification results for each answer
        """
        try:
            # First check if the email exists
            if not self.email_exists(email):
                logger.warning(f"Attempted to verify security answers for non-existent email: {email}")
                return {
                    "all_correct": False,
                    "answers": {},
                    "error": "Email not found"
                }
               
            user_response = self.supabase.table('users').select('id').eq('email', email).execute()
            if not user_response.data:
                logger.warning(f"No user found with email: {email}")
                return {
                    "all_correct": False,
                    "answers": {},
                    "error": "User not found"
                }
               
            user_id = user_response.data[0]['id']
            results = {}
            all_correct = True
            
            for idx, a in enumerate(answers):
                answer_id = a.id if a.id else f"question{idx+1}"
                response = self.supabase.table('security_questions').select('answer_hash').eq('user_id', user_id).eq('question_text', a.question).execute()
                
                if not response.data:
                    results[answer_id] = {
                        "correct": False,
                        "error": "Question not found"
                    }
                    all_correct = False
                    continue
                
                # Verify hashed answer
                stored_hash = response.data[0]['answer_hash']
                is_correct = bcrypt.checkpw(a.answer.lower().encode(), stored_hash.encode())
                
                results[answer_id] = {
                    "correct": is_correct,
                    "error": None if is_correct else "Incorrect answer"
                }
                
                if not is_correct:
                    all_correct = False
            
            return {
                "all_correct": all_correct,
                "answers": results,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error verifying security answers: {str(e)}")
            return {
                "all_correct": False,
                "answers": {},
                "error": str(e)
            }

    def get_pending_reset_token(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Check if there's a valid pending reset token for this email
        Returns: dict with token and expiry info, or None
        """
        try:
            # Check if email exists
            if not self.email_exists(email):
                return None
            
            # Get user ID
            user_response = self.supabase.table('users').select('id').eq('email', email).execute()
            if not user_response.data:
                return None
            
            user_id = user_response.data[0]['id']
            
            # Check for valid pending tokens (not used and not expired)
            now = datetime.datetime.now().isoformat()
            response = self.supabase.table('password_reset_tokens').select('*').eq('user_id', user_id).eq('used', False).gt('expires_at', now).order('expires_at', desc=True).limit(1).execute()
            
            if not response.data:
                return None
            
            token_data = response.data[0]
            
            return {
                "token": token_data['token_hash'],
                "expiry": token_data['expires_at'],
                "is_valid": True
            }
        except Exception as e:
            logger.error(f"Error checking for pending reset token: {str(e)}")
            return None

    def create_reset_token(self, email: str) -> str:
        """
        Create a new reset token with 10-minute expiry
        Invalidates any previous unused tokens for this user
        """
        user_id = self.supabase.table('users').select('id').eq('email', email).execute().data[0]['id']
        
        # Invalidate any previous unused tokens for this user
        self.supabase.table('password_reset_tokens').update({"used": True}).eq('user_id', user_id).eq('used', False).execute()
        
        token = str(uuid.uuid4())
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=10)  # 10-minute expiry
        self.supabase.table('password_reset_tokens').insert({"user_id": user_id, "token_hash": token, "expires_at": expires_at.isoformat(), "used": False}).execute()
        return token

    def cleanup_expired_tokens(self) -> int:
        """
        Remove all expired reset tokens from the database
        Returns: number of tokens cleaned up
        """
        try:
            now = datetime.datetime.now().isoformat()
            # Mark expired tokens as used
            response = self.supabase.table('password_reset_tokens').update({"used": True}).eq('used', False).lte('expires_at', now).execute()
            count = len(response.data) if response.data else 0
            logger.info(f"Cleaned up {count} expired reset tokens")
            return count
        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {str(e)}")
            return 0

    def verify_reset_token(self, email: str, token: str) -> bool:
        try:
            logger.info(f"Verifying reset token for email: {email}, token: {token}")
           
            # Check if email exists first
            if not self.email_exists(email):
                logger.warning(f"Attempted to verify token for non-existent email: {email}")
                return False
               
            # Get user ID
            user_response = self.supabase.table('users').select('id').eq('email', email).execute()
            if not user_response.data:
                logger.warning(f"No user found with email: {email}")
                return False
               
            user_id = user_response.data[0]['id']
            logger.info(f"Found user ID: {user_id}")
           
            now = datetime.datetime.now().isoformat()
           
            # First, try a simple check to see if the token exists at all
            token_exists = self.supabase.table('password_reset_tokens').select('reset_token_id').eq('token_hash', token).execute()
            if not token_exists.data:
                logger.warning(f"No token found matching: {token}")
                return False
           
            logger.info(f"Token exists in database: {token}")
               
            # Check for a valid token (not expired and not used)
            response = self.supabase.table('password_reset_tokens').select('*').eq('user_id', user_id).eq('token_hash', token).eq('used', False).gt('expires_at', now).execute()
           
            result = bool(response.data)
            if result:
                logger.info("Token verification successful")
            else:
                logger.warning(f"Token verification failed: User ID mismatch or token expired/used")
                # Check why it failed specifically
                used_check = self.supabase.table('password_reset_tokens').select('*').eq('user_id', user_id).eq('token_hash', token).eq('used', True).execute()
                if used_check.data:
                    logger.warning("Token has already been used")
               
                expired_check = self.supabase.table('password_reset_tokens').select('*').eq('user_id', user_id).eq('token_hash', token).lte('expires_at', now).execute()
                if expired_check.data:
                    logger.warning("Token has expired")
           
            return result
        except Exception as e:
            logger.error(f"Error verifying reset token: {str(e)}")
            return False

    def reset_password(self, email: str, token: str, new_password: str) -> bool:
        try:
            # Verify email exists
            if not self.email_exists(email):
                logger.warning(f"Attempted to reset password for non-existent email: {email}")
                return False
               
            # Get user ID
            user_response = self.supabase.table('users').select('id').eq('email', email).execute()
            if not user_response.data:
                logger.warning(f"No user found with email: {email}")
                return False
               
            user_id = user_response.data[0]['id']
           
            # Find the token
            token_response = self.supabase.table('password_reset_tokens').select('reset_token_id').eq('user_id', user_id).eq('token_hash', token).eq('used', False).execute()
            if not token_response.data:
                logger.warning(f"No valid reset token found for user: {email}")
                return False
               
            token_id = token_response.data[0]['reset_token_id']
           
            # Update password and mark token as used
            hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            self.supabase.table('users').update({"password_hash": hashed}).eq('id', user_id).execute()
            self.supabase.table('password_reset_tokens').update({"used": True}).eq('reset_token_id', token_id).execute()
           
            return True
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            return False

    def record_login_attempt(self, email: str, success: bool):
        now = datetime.datetime.now()
        if success:
            self.login_attempts.pop(email, None)
            return
        record = self.login_attempts.setdefault(email, {"count": 0, "last_attempt": now, "locked_until": None})
        record["count"] += 1
        record["last_attempt"] = now
        if record["count"] >= 3:
            record["locked_until"] = now + datetime.timedelta(minutes=self.lockout_duration_minutes)

    def check_account_lockout(self, email: str) -> dict:
        record = self.login_attempts.get(email)
        if not record:
            return {"locked": False}
        if record.get("locked_until") and datetime.datetime.now() < record["locked_until"]:
            seconds_left = int((record["locked_until"] - datetime.datetime.now()).total_seconds())
            return {"locked": True, "minutes": seconds_left // 60, "seconds": seconds_left}
        self.login_attempts.pop(email, None)
        return {"locked": False}

    async def get_stripe_customer_id(self, user_id: str) -> Optional[str]:
        """
        Get the Stripe customer ID for a user
        """
        try:
            response = self.supabase.table('user_subscriptions').select('stripe_customer_id').eq('user_id', user_id).execute()
            if response.data:
                return response.data[0].get('stripe_customer_id')
            return None
        except Exception as e:
            logger.error(f"Error getting Stripe customer ID: {str(e)}")
            return None
   
    async def save_stripe_customer_id(self, user_id: str, customer_id: str) -> bool:
        """
        Save a Stripe customer ID for a user
        """
        try:
            # Check if user subscription record exists
            response = self.supabase.table('user_subscriptions').select('id').eq('user_id', user_id).execute()
           
            if response.data:
                # Update existing record
                self.supabase.table('user_subscriptions').update(
                    {"stripe_customer_id": customer_id}
                ).eq('user_id', user_id).execute()
            else:
                # Create new record
                self.supabase.table('user_subscriptions').insert({
                    "user_id": user_id,
                    "stripe_customer_id": customer_id,
                    "status": "created"
                }).execute()
           
            return True
        except Exception as e:
            logger.error(f"Error saving Stripe customer ID: {str(e)}")
            return False

    async def update_user_profile(
        self,
        user_id: str,
        first_name: Optional[str],
        last_name: Optional[str],
        company_name: Optional[str],
        country_code: Optional[str],  # Add country_code parameter
        phone_number: Optional[str],
        password: Optional[str] = None,
        email: Optional[str] = None,
        is_verified: Optional[bool] = None
    ) -> Optional[User]:
        """Update user profile information, including password and email if provided. Insert if not exists."""
        try:
            # Check if user exists
            response = self.supabase.table('users').select('id').eq('id', user_id).execute()
            user_exists = bool(response.data)

            update_data = {}
            if first_name is not None:
                update_data["first_name"] = first_name
            if last_name is not None:
                update_data["last_name"] = last_name
            if company_name is not None:
                update_data["company_name"] = company_name
            if country_code is not None:  # Add country_code handling
                update_data["country_code"] = country_code
            if phone_number is not None:
                update_data["phone_no"] = phone_number  # Changed to phone_no to match schema
            if password:
                update_data["password_hash"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()  # Changed to password_hash
            if email:
                update_data["email"] = email
            if is_verified is not None:
                update_data["is_verified"] = is_verified

            if not update_data:
                return None

            if user_exists:
                # Update existing user
                response = self.supabase.table('users').update(update_data).eq('id', user_id).execute()
                if not response.data:
                    return None
                updated_user = response.data[0]
                # Map phone_no to phone_number for User model compatibility
                updated_user['phone_number'] = updated_user.get('phone_no', '')
                return User(**updated_user)
            else:
                # Insert new user with all required fields
                # Fill missing required fields with empty string or default
                required_fields = {
                    "id": user_id,
                    "first_name": first_name or "",
                    "last_name": last_name or "",
                    "company_name": company_name or "",
                    "email": email or "",
                    "phone_no": phone_number or "",  # Changed to phone_no
                    "password_hash": update_data.get("password_hash", bcrypt.hashpw("TempPass123!".encode(), bcrypt.gensalt()).decode()),  # Changed to password_hash
                    "is_verified": is_verified if is_verified is not None else False,
                }
                # Merge any additional fields
                required_fields.update(update_data)
                response = self.supabase.table('users').insert(required_fields).execute()

                if not response.data:
                    return None
                updated_user = response.data[0]
                # Map phone_no to phone_number for User model compatibility
                updated_user['phone_number'] = updated_user.get('phone_no', '')
                return User(**updated_user)
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            raise

    # ============================================================================
    # DIFF CHECKER DATABASE METHODS
    # Methods for user story and test case diff checking and retrieval
    # ============================================================================
    
    def get_user_stories_by_hashes(
        self,
        session_id: str,
        content_hashes: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve user stories matching given content hashes.
        
        Args:
            session_id: Session identifier to scope the search
            content_hashes: List of SHA-256 content hashes to search for
        
        Returns:
            List of user story dictionaries matching the hashes
        
        Example:
            >>> stories = db.get_user_stories_by_hashes(
            ...     session_id='123',
            ...     content_hashes=['abc123...', 'def456...']
            ... )
        """
        try:
            if not content_hashes:
                logger.debug("No content hashes provided")
                return []
            
            logger.info(f"Retrieving user stories by {len(content_hashes)} hashes for identifier {session_id}")
            
            response = self.supabase.table('user_stories').select('*').in_(
                'content_hash', content_hashes
            ).eq('identifier_id', session_id).execute()
            
            if not response.data:
                logger.info("No matching user stories found")
                return []
            
            logger.info(f"Found {len(response.data)} user stories")
            return response.data
            
        except Exception as e:
            logger.error(f"Error retrieving user stories by hashes: {str(e)}")
            return []
    
    def get_user_stories_by_ids(
        self,
        session_id: str,
        story_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Retrieve user stories by their IDs.
        
        Args:
            session_id: Session identifier to scope the search
            story_ids: List of user story IDs (can be UUIDs or string IDs like 'US001')
        
        Returns:
            List of user story dictionaries
        """
        try:
            if not story_ids:
                logger.debug("No story IDs provided")
                return []
            
            logger.info(f"Retrieving {len(story_ids)} user stories by ID for identifier {session_id}")
            
            # Try matching by UUID first (database ID)
            response = self.supabase.table('user_stories').select('*').in_(
                'id', story_ids
            ).eq('identifier_id', session_id).execute()
            
            stories = response.data if response.data else []
            
            # If no results, try matching by original_id (story ID like 'US001')
            if not stories:
                response = self.supabase.table('user_stories').select('*').in_(
                    'original_id', story_ids
                ).eq('identifier_id', session_id).execute()
                stories = response.data if response.data else []
            
            logger.info(f"Found {len(stories)} user stories")
            return stories
            
        except Exception as e:
            logger.error(f"Error retrieving user stories by IDs: {str(e)}")
            return []
    
    def get_test_cases_by_user_story_ids(
        self,
        session_id: str,
        user_story_ids: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve test cases grouped by user story ID.
        
        Args:
            session_id: Session identifier
            user_story_ids: List of user story IDs
        
        Returns:
            Dictionary mapping user_story_id -> list of test cases
            Example: {'US001': [tc1, tc2], 'US002': [tc3]}
        """
        try:
            if not user_story_ids:
                logger.debug("No user story IDs provided")
                return {}
            
            logger.info(f"Retrieving test cases for {len(user_story_ids)} user stories")
            
            # Query test cases, excluding deprecated and deleted ones
            response = self.supabase.table('test_cases').select('*').in_(
                'user_story_id', user_story_ids
            ).eq('identifier_id', session_id).neq('status', 'deprecated').or_("is_deleted.is.null,is_deleted.eq.false").execute()
            
            if not response.data:
                logger.info("No test cases found")
                return {}
            
            # Group test cases by user_story_id
            test_cases_by_story = {}
            for test_case in response.data:
                story_id = test_case.get('user_story_id')
                if story_id:
                    if story_id not in test_cases_by_story:
                        test_cases_by_story[story_id] = []
                    test_cases_by_story[story_id].append(test_case)
            
            total_test_cases = sum(len(tcs) for tcs in test_cases_by_story.values())
            logger.info(f"Found {total_test_cases} test cases across {len(test_cases_by_story)} stories")
            
            return test_cases_by_story
            
        except Exception as e:
            logger.error(f"Error retrieving test cases by user story IDs: {str(e)}")
            return {}

    def get_user_story_test_case_counts(
        self,
        session_id: str,
        user_story_ids: List[str]
    ) -> Dict[str, int]:
        """
        Get test case counts for each user story across the ENTIRE test_cases table.
        Checks if test cases were EVER generated for these user stories, regardless of session.
        
        Args:
            session_id: Session identifier (not used in query, kept for compatibility)
            user_story_ids: List of user story IDs
        
        Returns:
            Dictionary mapping user_story_id -> count of test cases
            Example: {'story_1': 3, 'story_2': 0, 'story_3': 5}
        """
        try:
            if not user_story_ids:
                logger.debug("No user story IDs provided")
                return {}
            
            logger.info(f"[GET TEST CASE COUNTS] Getting test case counts for {len(user_story_ids)} user stories")
            logger.info(f"[GET TEST CASE COUNTS] Session ID (not used): {session_id}")
            logger.info(f"[GET TEST CASE COUNTS] Story IDs: {user_story_ids}")
            
            # Query test cases across ENTIRE table by user_story_id only (not filtering by session)
            # This checks if test cases were EVER generated for these stories
            # Exclude deleted test cases
            logger.info(f"[GET TEST CASE COUNTS] Querying ENTIRE test_cases table for user_story_id matches")
            response = self.supabase.table('test_cases').select('user_story_id').in_(
                'user_story_id', user_story_ids
            ).neq('status', 'deprecated').or_("is_deleted.is.null,is_deleted.eq.false").execute()
            
            logger.info(f"[GET TEST CASE COUNTS] Query response: {response}")
            logger.info(f"[GET TEST CASE COUNTS] Found {len(response.data) if response.data else 0} test cases across all sessions")
            
            if not response.data:
                logger.info("[GET TEST CASE COUNTS] No test cases found anywhere, returning zero counts")
                # Return zero counts for all stories
                return {story_id: 0 for story_id in user_story_ids}
            
            # Count test cases per story
            test_case_counts = {}
            for story_id in user_story_ids:
                test_case_counts[story_id] = 0
            
            for test_case in response.data:
                story_id = test_case.get('user_story_id')
                if story_id and story_id in test_case_counts:
                    test_case_counts[story_id] += 1
            
            logger.info(f"[GET TEST CASE COUNTS] Final counts: {test_case_counts}")
            logger.info(f"[GET TEST CASE COUNTS] Stories with test cases: {sum(1 for count in test_case_counts.values() if count > 0)}")
            logger.info(f"[GET TEST CASE COUNTS] Stories without test cases: {sum(1 for count in test_case_counts.values() if count == 0)}")
            
            return test_case_counts
            
        except Exception as e:
            logger.error(f"[GET TEST CASE COUNTS] Error getting test case counts: {str(e)}")
            logger.error(f"[GET TEST CASE COUNTS] Error type: {type(e)}")
            # Return zero counts for all stories on error
            return {story_id: 0 for story_id in user_story_ids} if user_story_ids else {}
    
    def bulk_insert_user_stories(
        self,
        user_stories: List[Dict[str, Any]],
        identifier_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Insert multiple user stories with computed hashes.
        
        Args:
            user_stories: List of user story dictionaries to insert
            identifier_id: Optional identifier for grouping/filtering
            user_id: Optional user identifier
        
        Returns:
            List of inserted user story records with database IDs
        
        Note:
            Each story should have a 'content_hash' field computed before insertion.
            If not present, it should be computed by the caller using diff_checker.
        """
        try:
            if not user_stories:
                logger.debug("No user stories to insert")
                return []
            
            logger.info(f"Bulk inserting {len(user_stories)} user stories")
            
            # Prepare stories for insertion
            stories_to_insert = []
            for story in user_stories:
                story_data = {
                    'identifier_id': identifier_id,
                    'user_id': user_id,
                    'story_title': story.get('story_title') or story.get('title', ''),
                    'story_description': story.get('story_description') or story.get('description', ''),
                    'acceptance_criteria': story.get('acceptance_criteria', []),
                    'raw_json': story,  # Store complete original data
                    'content_hash': story.get('content_hash') or story.get('_computed_hash'),
                    'status': story.get('status', 'generated'),
                    'version': story.get('version', 1),
                    'original_id': story.get('original_id') or story.get('id')
                }
                stories_to_insert.append(story_data)
            
            # Bulk insert
            response = self.supabase.table('user_stories').insert(stories_to_insert).execute()
            
            if not response.data:
                logger.error("Bulk insert returned no data")
                return []
            
            logger.info(f"Successfully inserted {len(response.data)} user stories")
            return response.data
            
        except Exception as e:
            logger.error(f"Error bulk inserting user stories: {str(e)}")
            return []
    
    def bulk_insert_test_cases(
        self,
        test_cases: List[Dict[str, Any]],
        identifier_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Insert multiple test cases with computed hashes.
        
        Args:
            test_cases: List of test case dictionaries to insert
            identifier_id: Optional identifier for grouping/filtering
        
        Returns:
            List of inserted test case records with database IDs
        """
        try:
            if not test_cases:
                logger.debug("No test cases to insert")
                return []
            
            logger.info(f"Bulk inserting {len(test_cases)} test cases")
            
            # Prepare test cases for insertion
            cases_to_insert = []
            for test_case in test_cases:
                case_data = {
                    'identifier_id': identifier_id,
                    'user_story_id': test_case.get('user_story_id'),
                    'name': test_case.get('name') or test_case.get('title', ''),
                    'description': test_case.get('description', ''),
                    'steps': test_case.get('steps', []),
                    'expected_result': test_case.get('expected_result', ''),
                    'status': test_case.get('status', 'draft'),
                    'priority': test_case.get('priority', 'medium'),
                    'content_hash': test_case.get('content_hash') or test_case.get('_computed_hash'),
                    'version': test_case.get('version', 1),
                    'original_story_id': test_case.get('original_story_id') or test_case.get('user_story_id'),
                    'client_id': test_case.get('id')  # Store original ID
                }
                cases_to_insert.append(case_data)
            
            # Bulk insert
            response = self.supabase.table('test_cases').insert(cases_to_insert).execute()
            
            if not response.data:
                logger.error("Bulk insert returned no data")
                return []
            
            logger.info(f"Successfully inserted {len(response.data)} test cases")
            return response.data
            
        except Exception as e:
            logger.error(f"Error bulk inserting test cases: {str(e)}")
            return []
    
    def update_user_story_hash(
        self,
        story_id: str,
        content_hash: str
    ) -> bool:
        """
        Update content hash for existing user story.
        
        Args:
            story_id: UUID of the user story
            content_hash: New SHA-256 content hash
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            logger.info(f"Updating content hash for user story {story_id}")
            
            response = self.supabase.table('user_stories').update({
                'content_hash': content_hash,
                'updated_at': datetime.datetime.utcnow().isoformat()
            }).eq('id', story_id).execute()
            
            success = bool(response.data)
            if success:
                logger.info(f"Successfully updated content hash for story {story_id}")
            else:
                logger.warning(f"Failed to update content hash for story {story_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating user story hash: {str(e)}")
            return False
    
    def update_test_case_hash(
        self,
        test_case_id: str,
        content_hash: str
    ) -> bool:
        """
        Update content hash for existing test case.
        
        Args:
            test_case_id: UUID of the test case
            content_hash: New SHA-256 content hash
        
        Returns:
            True if update successful, False otherwise
        """
        try:
            logger.info(f"Updating content hash for test case {test_case_id}")
            
            response = self.supabase.table('test_cases').update({
                'content_hash': content_hash,
                'updated_at': datetime.datetime.utcnow().isoformat()
            }).eq('id', test_case_id).execute()
            
            success = bool(response.data)
            if success:
                logger.info(f"Successfully updated content hash for test case {test_case_id}")
            else:
                logger.warning(f"Failed to update content hash for test case {test_case_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating test case hash: {str(e)}")
            return False
    
    def get_version_history(
        self,
        entity_type: str,
        original_id: str,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a user story or test case.
        
        Args:
            entity_type: 'user_story' or 'test_case'
            original_id: Original ID to get history for
            session_id: Optional session filter
        
        Returns:
            List of versions ordered by version number descending
        """
        try:
            table_name = 'user_stories' if entity_type == 'user_story' else 'test_cases'
            
            logger.info(f"Retrieving version history for {entity_type}: {original_id}")
            
            query = self.supabase.table(table_name).select('*').eq('original_id', original_id)
            
            if session_id:
                query = query.eq('identifier_id', session_id)
            
            response = query.order('version', desc=True).execute()
            
            if not response.data:
                logger.info(f"No version history found for {original_id}")
                return []
            
            logger.info(f"Found {len(response.data)} versions")
            return response.data
            
        except Exception as e:
            logger.error(f"Error retrieving version history: {str(e)}")
            return []
    
    def deprecate_test_case(
        self,
        test_case_id: str,
        replaced_by_id: Optional[str] = None
    ) -> bool:
        """
        Mark a test case as deprecated.
        
        Args:
            test_case_id: UUID of test case to deprecate
            replaced_by_id: Optional UUID of replacement test case
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Deprecating test case {test_case_id}")
            
            update_data = {
                'status': 'deprecated',
                'deprecated_at': datetime.datetime.utcnow().isoformat(),
                'updated_at': datetime.datetime.utcnow().isoformat()
            }
            
            if replaced_by_id:
                update_data['replaced_by'] = replaced_by_id
            
            response = self.supabase.table('test_cases').update(update_data).eq('id', test_case_id).execute()
            
            success = bool(response.data)
            if success:
                logger.info(f"Successfully deprecated test case {test_case_id}")
            else:
                logger.warning(f"Failed to deprecate test case {test_case_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deprecating test case: {str(e)}")
            return False

    # ============================================================================
    # END DIFF CHECKER DATABASE METHODS
    # ============================================================================

    def save_binary_to_supabase(self, table_name, data):
        """
        Save binary data (like images) to Supabase
       
        Args:
            table_name (str): Name of the table
            data (dict): Data to save, can include binary fields
           
        Returns:
            dict: Response data or None on failure
        """
        try:
            response = self.supabase.table(table_name).insert(data).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error saving binary data to Supabase: {str(e)}")
            return None

    def get_binary_from_supabase(self, table_name, column, value):
        """
        Get binary data from Supabase
       
        Args:
            table_name (str): Name of the table
            column (str): Column to filter by
            value (Any): Value to match
           
        Returns:
            dict: Record with binary data or None
        """
        try:
            response = self.supabase.table(table_name).select('*').eq(column, value).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error retrieving binary data from Supabase: {str(e)}")
            return None

def get_user_by_id(user_id):
    """
    Get user by ID - directly query the database
    """
    try:
        logger.info(f"Retrieving user with ID: {user_id}")
        response = supabase.table('users').select('*').eq('id', user_id).limit(1).execute()
       
        if response and hasattr(response, 'data') and len(response.data) > 0:
            user_data = response.data[0]
            logger.info(f"User found: {user_data.get('email')}")
           
            # Create a User object from the data
            from models import User  # Import here to avoid circular imports
            return User(
                id=user_data.get('id'),
                email=user_data.get('email', ''),
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                company_name=user_data.get('company_name', ''),
                phone_number=user_data.get('phone_no', ''),  # Map phone_no to phone_number
                country_code=user_data.get('country_code', ''),
                is_verified=user_data.get('is_verified', False),
                role=user_data.get('role', 'user')
            )
       
        logger.warning(f"No user found with ID: {user_id}")
        return None
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None

# Create a global database instance
db = Database()

# FastAPI dependency for database access
def get_db() -> Database:
    """
    Dependency function to get the database instance.
    Used with FastAPI's Depends() for dependency injection.
    """
    return db

    def save_test_case(self, test_case_data: dict) -> str:
        """
        Save a test case to the database.
        
        Args:
            test_case_data: Dictionary containing test case information
        
        Returns:
            The ID of the saved test case
        """
        try:
            logger.info(f"[SAVE TEST CASE] ========================================")
            logger.info(f"[SAVE TEST CASE] Saving test case: {test_case_data.get('name', 'Unnamed')}")
            logger.info(f"[SAVE TEST CASE] Session ID: {test_case_data.get('session_id')}")
            logger.info(f"[SAVE TEST CASE] User Story ID: {test_case_data.get('user_story_id')}")
            
            # Prepare data for insertion
            insert_data = {
                "identifier_id": test_case_data["session_id"],  # Use identifier_id consistently
                "user_story_id": test_case_data.get("user_story_id"),
                "name": test_case_data["name"],  # Column is 'name' not 'test_case_name'
                "description": test_case_data.get("description", ""),
                "steps": test_case_data.get("steps", []),
                "expected_result": test_case_data.get("expected_results", test_case_data.get("expected_result", "")),
                "priority": test_case_data.get("priority", "Medium"),
                "status": test_case_data.get("status", "Ready")
            }
            
            logger.info(f"[SAVE TEST CASE] Insert data prepared")
            
            response = self.supabase.table('test_cases').insert(insert_data).execute()
            
            if not response.data:
                logger.error(f"[SAVE TEST CASE] [ERROR] No data returned from insert")
                raise Exception("Failed to save test case - no data returned")
            
            test_case_id = response.data[0]["id"]
            logger.info(f"[SAVE TEST CASE] [SUCCESS] Test case saved with ID: {test_case_id}")
            logger.info(f"[SAVE TEST CASE] ========================================")
            
            return test_case_id
            
        except Exception as e:
            logger.error(f"[SAVE TEST CASE] [ERROR] Error saving test case: {str(e)}")
            logger.error(f"[SAVE TEST CASE] Error type: {type(e)}")
            logger.error(f"[SAVE TEST CASE] ========================================")
            raise