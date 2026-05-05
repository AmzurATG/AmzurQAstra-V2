from fastapi import APIRouter, HTTPException, Body
from datetime import datetime, timedelta
import logging

from services.authentication import (
    generate_otp,
    store_otp,
    verify_otp,
    send_otp_email,
    send_password_reset_email,
)
from models import (
    UserCreate, OTPVerify, OTPResponse, LoginRequest, LoginResponse,
    PasswordResetRequest, SecurityAnswerVerify, PasswordReset,
)
from db import db


# Initialize router
router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Add login attempt tracking for account lockout
login_attempts = {}
MAX_LOGIN_ATTEMPTS = 3
LOCKOUT_DURATION = 5  

# Add OTP attempt tracking for account lockout
otp_attempts = {}
MAX_OTP_ATTEMPTS = 3
OTP_LOCKOUT_DURATION = 5  # minutes (reduced for testing)

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token
    """
    email = request.email
    
    # Check if user is locked out
    if email in login_attempts and login_attempts[email]["locked_until"]:
        locked_until = login_attempts[email]["locked_until"]
        if datetime.now() < locked_until:
            remaining_minutes = int((locked_until - datetime.now()).total_seconds() / 60) + 1
            raise HTTPException(
                status_code=403,
                detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {remaining_minutes} minutes."
            )
        else:
            # Reset lockout if time has passed
            login_attempts[email] = {"count": 0, "locked_until": None}
    
    # Authenticate user
    result = db.authenticate_user(request.email, request.password)
    
    if not result:
        # Track failed login attempt
        if email not in login_attempts:
            login_attempts[email] = {"count": 1, "locked_until": None}
        else:
            login_attempts[email]["count"] += 1
            
        # Check if account should be locked
        if login_attempts[email]["count"] >= MAX_LOGIN_ATTEMPTS:
            locked_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION)
            login_attempts[email]["locked_until"] = locked_until
            raise HTTPException(
                status_code=403,
                detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {LOCKOUT_DURATION} minutes."
            )
            
        raise HTTPException(status_code=401, detail="Invalid Email or Password")
    
    if "error" in result:
        if result["error"] == "user_not_verified":
            raise HTTPException(status_code=403, detail="Email not verified. Please check your email for verification code.")
        elif result["error"] == "account_locked":
            raise HTTPException(status_code=403, detail=result["message"])
        elif result["error"] == "service_unavailable":
            raise HTTPException(status_code=503, detail=result.get("message", "Service temporarily unavailable. Please try again."))
        else:
            # Track failed login attempt
            if email not in login_attempts:
                login_attempts[email] = {"count": 1, "locked_until": None}
            else:
                login_attempts[email]["count"] += 1
                
            # Check if account should be locked
            if login_attempts[email]["count"] >= MAX_LOGIN_ATTEMPTS:
                locked_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION)
                login_attempts[email]["locked_until"] = locked_until
                raise HTTPException(
                    status_code=403,
                    detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {LOCKOUT_DURATION} minutes."
                )
                
            raise HTTPException(status_code=401, detail="Invalid Email or Password")
    
    # Reset login attempts on successful login
    if email in login_attempts:
        login_attempts[email] = {"count": 0, "locked_until": None}
    
    return result

# In-memory storage for temporary user data awaiting verification
pending_user_registrations = {}

@router.post("/signup")
async def signup(user_data: UserCreate):
    """
    Register a new user
    """
    email = user_data.email
    now = datetime.now()

    # Check for OTP lockout before allowing signup
    if email in otp_attempts and otp_attempts[email].get("locked_until"):
        locked_until = otp_attempts[email]["locked_until"]
        if now < locked_until:
            remaining_seconds = int((locked_until - now).total_seconds())
            remaining_minutes = int(remaining_seconds // 60) + 1
            raise HTTPException(
                status_code=403,
                detail=f"Account is temporarily locked due to multiple incorrect verification attempts. Try again after {remaining_minutes} minutes.",
                headers={"X-Lockout-Seconds": str(remaining_seconds)}
            )
        else:
            # Reset after lockout
            otp_attempts[email] = {"count": 0, "locked_until": None}

    # Check if email is already registered
    if db.email_exists(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Store user data temporarily instead of creating immediately
    try:
        # Ensure phone_number is None if empty string
        if user_data.phone_number == "":
            user_data.phone_number = None
            
        # Ensure security_questions is at least an empty list if not provided
        if user_data.security_questions is None:
            user_data.security_questions = []
            
        # Store the user data in memory until OTP verification
        pending_user_registrations[user_data.email] = user_data
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing user data: {error_message}")
        raise HTTPException(status_code=500, detail=f"Failed to process user data: {error_message}")
    
    # Generate OTP for email verification
    otp = generate_otp()
    store_otp(user_data.email, otp)
    
    # Send OTP email
    email_sent = send_otp_email(user_data.email, otp)
    if not email_sent:
        logger.warning(f"Failed to send OTP email to {user_data.email}")
    
    return {
        "message": "Verification code sent. Please verify your email to complete registration.",
        "email": user_data.email
    }

@router.post("/verify-otp", response_model=OTPResponse)
async def verify_email(verification_data: OTPVerify):
    """
    Verify email using OTP and complete user registration
    """
    email = verification_data.email
    now = datetime.now()

    # Check for lockout due to multiple incorrect OTP attempts
    if email in otp_attempts and otp_attempts[email].get("locked_until"):
        locked_until = otp_attempts[email]["locked_until"]
        if now < locked_until:
            remaining_seconds = int((locked_until - now).total_seconds())
            remaining_minutes = int(remaining_seconds // 60) + 1
            raise HTTPException(
                status_code=403,
                detail=f"Too many incorrect attempts. Try again after {remaining_minutes} minutes.",
                headers={"X-Lockout-Seconds": str(remaining_seconds)}
            )
        else:
            # Reset after lockout
            otp_attempts[email] = {"count": 0, "locked_until": None}

    logger.info(f"Verifying OTP for email: {verification_data.email}, OTP: {verification_data.otp}")
    
    result = verify_otp(verification_data.email, verification_data.otp)
    
    if result == "expired":
        logger.warning(f"OTP expired for email: {verification_data.email}")
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    elif result == "invalid":
        # Track failed attempts
        if email not in otp_attempts:
            otp_attempts[email] = {"count": 1, "locked_until": None}
        else:
            otp_attempts[email]["count"] += 1

        if otp_attempts[email]["count"] >= MAX_OTP_ATTEMPTS:
            locked_until = now + timedelta(minutes=OTP_LOCKOUT_DURATION)
            otp_attempts[email]["locked_until"] = locked_until
            remaining_seconds = int((locked_until - now).total_seconds())
            raise HTTPException(
                status_code=403,
                detail=f"Too many incorrect attempts. Try again after {OTP_LOCKOUT_DURATION} minutes.",
                headers={"X-Lockout-Seconds": str(remaining_seconds)}
            )
        else:
            remaining = MAX_OTP_ATTEMPTS - otp_attempts[email]["count"]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid OTP. {remaining} attempt(s) left."
            )
    elif result is True:
        # Reset attempts on successful verification
        if email in otp_attempts:
            otp_attempts[email] = {"count": 0, "locked_until": None}
        
        # Get the pending user data
        user_data = pending_user_registrations.get(email)
        if not user_data:
            logger.error(f"No pending registration data found for email: {verification_data.email}")
            raise HTTPException(status_code=400, detail="User registration data not found. Please sign up again.")
        
        try:
            # Create the user in the database now that OTP is verified
            user = db.create_user(user_data)
            logger.info(f"User created successfully for email: {email}")
            
            # Clean up the pending registration data
            del pending_user_registrations[email]
            
            # Mark user as verified
            db.verify_user(email)
            logger.info(f"User verified successfully for email: {email}")
            return {"detail": "Email verified successfully", "success": True}
        except Exception as e:
            logger.error(f"Error creating user after OTP verification: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to complete registration: {str(e)}")
    else:
        logger.error(f"Unexpected OTP verification result for email: {email}")
        raise HTTPException(status_code=400, detail="Invalid OTP verification request")

@router.post("/resend-otp")
async def resend_otp(data: dict):
    """
    Resend OTP for email verification
    """
    logger.info(f"Resend OTP request received with data: {data}")
    
    if "email" not in data:
        raise HTTPException(status_code=400, detail="Email is required")
    
    email = data["email"]
    logger.info(f"Resending OTP for email: {email}")
    
    # Prevent OTP resend if locked out
    now = datetime.now()
    if email in otp_attempts and otp_attempts[email].get("locked_until"):
        locked_until = otp_attempts[email]["locked_until"]
        if locked_until and now < locked_until:
            remaining_seconds = int((locked_until - now).total_seconds())
            remaining_minutes = int(remaining_seconds // 60) + 1
            raise HTTPException(
                status_code=403,
                detail=f"Too many incorrect attempts. Try again after {remaining_minutes} minutes.",
                headers={"X-Lockout-Seconds": str(remaining_seconds)}
            )
    
    # Reset OTP attempts when a new OTP is requested (only if not locked out)
    if email in otp_attempts:
        otp_attempts[email] = {"count": 0, "locked_until": None}
    
    # Check if there's a pending registration for this email
    pending_registration = email in pending_user_registrations
    user_exists = db.email_exists(email)
    
    if not pending_registration and not user_exists:
        logger.warning(f"No pending registration or existing user found for email: {email}")
        raise HTTPException(status_code=404, detail="Email not found. Please sign up first.")
    
    # Generate new OTP
    otp = generate_otp()
    store_otp(email, otp)
    logger.info(f"New OTP generated for {email}: {otp}")
    
    # Send OTP email
    email_sent = send_otp_email(email, otp)
    if not email_sent:
        logger.error(f"Failed to send OTP email to {email}")
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
    
    logger.info(f"OTP email sent successfully to {email}")
    return {"message": "OTP sent successfully"}

@router.post("/forgot-password/initiate")
async def initiate_password_reset(request: dict = Body(...)):
    """
    Initiate password reset process
    Checks for pending tokens and returns appropriate response
    """
    email = request.get('email')
    request_new = request.get('request_new', False)
    
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Check if email exists in the database
    if not db.email_exists(email):
        # Return an error for non-existent email, but don't explicitly state it doesn't exist
        # Use a generic message for security reasons
        raise HTTPException(status_code=404, detail="We couldn't find an account matching that email address. Please verify your email or sign up for a new account.")
    
    # Clean up any expired tokens first
    db.cleanup_expired_tokens()
    
    # Check for existing pending reset token
    pending_token = db.get_pending_reset_token(email)
    
    if pending_token and not request_new:
        logger.info(f"Found pending reset token for {email}, expiry: {pending_token['expiry']}")
        
        # Return information about the pending token
        return {
            "email": email,
            "has_pending_reset": True,
            "token_expiry": pending_token["expiry"],
            "message": "You have an incomplete password reset. You can use the existing token or request a new one."
        }
    
    # No pending token or requesting new - proceed with security questions
    try:
        security_questions = db.get_security_questions(email)
        
        # Don't generate or send token yet - we'll do that after security questions are answered
        
        return {
            "email": email,
            "has_pending_reset": False,
            "security_questions": security_questions
        }
    except Exception as e:
        logger.error(f"Error initiating password reset: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate password reset")

@router.post("/forgot-password/verify-security")
async def verify_security_answers(request: SecurityAnswerVerify):
    """
    Verify security questions answers
    """
    try:
        email = request.email
        security_answers = request.security_answers
        
        # Check if email exists
        if not db.email_exists(email):
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Verify security answers with detailed results
        verification_result = db.verify_security_answers_detailed(email, security_answers)
        
        # If there's a general error (not answer-specific)
        if verification_result.get("error"):
            raise HTTPException(status_code=400, detail=verification_result["error"])
        
        # If not all answers are correct, return field-specific errors
        if not verification_result["all_correct"]:
            field_errors = {}
            for answer_id, result in verification_result["answers"].items():
                if not result["correct"]:
                    field_errors[answer_id] = result.get("error", "Incorrect answer")
            
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": "Some security answers are incorrect",
                    "field_errors": field_errors
                }
            )
        
        # Generate and send reset token
        reset_token = db.create_reset_token(email)
        
        # Send reset token via email
        email_sent = send_password_reset_email(email, reset_token)
        if not email_sent:
            logger.warning(f"Failed to send password reset email to {email}")
            raise HTTPException(status_code=500, detail="Failed to send password reset email")
        
        # Return token in the response for development environments
        # In production, you would typically only send via email
        return {
            "message": "Security answers verified. Password reset email sent.",
            "reset_token": reset_token  # Include the token in the response
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying security answers: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify security answers")

@router.post("/forgot-password/reset")
async def reset_password(request: PasswordReset):
    """
    Reset password using token
    """
    try:
        # Validate passwords match
        if request.new_password != request.confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        email = request.email
        token = request.reset_token
        new_password = request.new_password
        
        # Check if email exists
        if not db.email_exists(email):
            raise HTTPException(status_code=404, detail="Account not found")
            
        # Check if token is valid
        if not db.verify_reset_token(email, token):
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
        # Reset password
        db.reset_password(email, token, new_password)
        
        return {"message": "Password reset successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password")

@router.post("/forgot-password/verify-token")
async def verify_reset_token(request: dict = Body(...)):
    """
    Verify if a reset token is valid for a given email
    """
    try:
        logger.info(f"Verifying reset token: {request}")
        
        if not "email" in request or not "token" in request:
            raise HTTPException(status_code=400, detail="Email and token are required")
            
        email = request["email"]
        token = request["token"]
        
        logger.info(f"Verifying token for email: {email}, token: {token}")
        
        # Check if email exists
        if not db.email_exists(email):
            logger.warning(f"Account not found for email: {email}")
            raise HTTPException(status_code=404, detail="Account not found")
            
        # Check if token is valid
        is_valid = db.verify_reset_token(email, token)
        logger.info(f"Token verification result: {is_valid}")
        
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid reset token. Please check the token in your email")
        
        return {"valid": True, "message": "Token verified successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying reset token: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify token")

@router.post("/check-email")
async def check_email(data: dict = Body(...)):
    """
    Check if email exists in the database
    """
    logger.info(f"check_email endpoint called with data: {data}")
    
    if "email" not in data:
        raise HTTPException(status_code=400, detail="Email is required")
    
    email = data["email"]
    exists = db.email_exists(email)
    
    logger.info(f"Check email endpoint called for: {email}, exists: {exists}")
    
    return {
        "exists": exists,
        "email": email
    }
