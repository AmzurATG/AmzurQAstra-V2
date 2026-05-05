import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging
import os
import shutil

from fastapi import UploadFile
from config import EMAIL_HOST, EMAIL_PORT, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_FROM, OTP_EXPIRY_MINUTES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory OTP storage (in production, use Redis or another persistent store)
otp_store: Dict[str, Dict] = {}


def generate_otp(length=6):
    """Generate a random OTP of specified length."""
    otp = ''.join(random.choice(string.digits) for _ in range(length))
    logger.info(f"Generated OTP: {otp}")
    return otp


def store_otp(email: str, otp: str):
    """Store OTP with expiry time."""
    expiry_time = datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    
    # Always convert to string to ensure consistent comparisons later
    if not isinstance(otp, str):
        otp = str(otp)
        
    otp_store[email] = {"otp": otp, "expiry": expiry_time}
    logger.info(f"Stored OTP for {email}, expires at {expiry_time}")


def verify_otp(email: str, otp: str):
    """Verify if OTP is valid and not expired."""
    logger.info(f"Verifying OTP for email: {email}")
    
    if email not in otp_store:
        logger.warning(f"No OTP found for email: {email}")
        return "invalid"
    
    stored_data = otp_store[email]
    current_time = datetime.now()
    
    # Ensure comparison is done with strings
    stored_otp = str(stored_data["otp"]).strip()
    provided_otp = str(otp).strip()
    
    logger.info(f"Checking OTP for {email}: Stored={stored_otp}, Provided={provided_otp}, Expiry={stored_data['expiry']}, Current={current_time}")
    
    if current_time > stored_data["expiry"]:
        # OTP expired
        logger.warning(f"OTP expired for {email}. Expired at {stored_data['expiry']}, current time: {current_time}")
        del otp_store[email]
        return "expired"
    
    if provided_otp != stored_otp:
        logger.warning(f"OTP mismatch for {email}. Expected: {stored_otp}, Got: {provided_otp}")
        return "invalid"
    
    # OTP verified successfully, remove it
    logger.info(f"OTP verified successfully for {email}")
    del otp_store[email]
    return True


def send_otp_email(to_email: str, otp: str):
    """Send OTP via email."""
    subject = "Your QAstra Verification Code"
    message = f"""
    <html>
    <body>
        <h2>Welcome to QAstra!</h2>
        <p>Thank you for signing up. Please use the verification code below to complete your registration:</p>
        <h1 style="background-color: #f0f0f0; padding: 10px; text-align: center; font-family: monospace;">{otp}</h1>
        <p>This code will expire in {OTP_EXPIRY_MINUTES} minutes.</p>
        <p>If you didn't request this code, please ignore this email.</p>
    </body>
    </html>
    """
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    
    msg.attach(MIMEText(message, 'html'))
    
    try:
        logger.info(f"Attempting to send OTP email to {to_email}")
        if not EMAIL_HOST or not EMAIL_USERNAME or not EMAIL_PASSWORD:
            logger.warning("Email credentials not configured properly. Check your .env file.")
            return False
            
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"OTP email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def send_password_reset_email(to_email: str, reset_token: str):
    """Send password reset email."""
    subject = "QAstra Password Reset"
    message = f"""
    <html>
    <body>
        <h2>Password Reset Request</h2>
        <p>You've requested to reset your password for your QAstra account.</p>
        <p>Use the following token to complete the password reset process:</p>
        <h1 style="background-color: #f0f0f0; padding: 10px; text-align: center; font-family: monospace;">{reset_token}</h1>
        <p>This token will expire in 10 minutes.</p>
        <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
    </body>
    </html>
    """
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    
    msg.attach(MIMEText(message, 'html'))
    
    try:
        logger.info(f"Attempting to send password reset email to {to_email}")
        if not EMAIL_HOST or not EMAIL_USERNAME or not EMAIL_PASSWORD:
            logger.warning("Email credentials not configured properly. Check your .env file.")
            return False
            
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Password reset email sent successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return False


def send_build_integrity_email(recipient_email, build_id, build_url, status, quality_score, test_results=None):
    """
    Send an email notification about build integrity check results with dynamic test data.
    
    Args:
        recipient_email: Email address to send to
        build_id: Build identifier
        build_url: URL of the build
        status: 'pass' or 'fail' (will be recalculated from test_results if available)
        quality_score: Quality score percentage (0-100) (will be recalculated from test_results if available)
        test_results: List of test result dictionaries with 'test_name'/'name', 'status', 'duration', etc.
    """
    import os
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime
    
    # Get email configuration from environment variables - add logging for debugging
    email_username = os.getenv("EMAIL_USERNAME")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    email_port = int(os.getenv("EMAIL_PORT", 587))
    email_from = os.getenv("EMAIL_FROM", email_username)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Log the email configuration (without password)
    logging.info(f"Email config: username={email_username}, host={email_host}, port={email_port}, from={email_from}")
    logging.info(f"Frontend URL for link: {frontend_url}")
    
    # Check if email configuration exists
    if not all([email_username, email_password, email_host, email_port, email_from]):
        missing = []
        if not email_username: missing.append("EMAIL_USERNAME")
        if not email_password: missing.append("EMAIL_PASSWORD")
        if not email_host: missing.append("EMAIL_HOST")
        if not email_port: missing.append("EMAIL_PORT")
        if not email_from: missing.append("EMAIL_FROM")
        logger.warning(f"Email configuration missing: {', '.join(missing)}, skipping build integrity result email")
        return False
    
    if not recipient_email:
        logger.warning("No recipient email provided, skipping build integrity result email")
        return False
    
    # Calculate test statistics from test_results for the email summary table
    # Use the status and quality_score directly as provided (already correct from BIC results)
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skipped_tests = 0
    
    if test_results and isinstance(test_results, list):
        total_tests = len(test_results)
        for test in test_results:
            test_status = test.get('status', '').lower()
            if test_status in ['pass', 'passed']:
                passed_tests += 1
            elif test_status in ['fail', 'failed', 'error']:
                failed_tests += 1
            elif test_status in ['skip', 'skipped']:
                skipped_tests += 1
        
        logging.info(f"Email Summary - Total: {total_tests}, Passed: {passed_tests}, Failed: {failed_tests}, Skipped: {skipped_tests}")
        logging.info(f"Using BIC values - Status: {status}, Quality Score: {quality_score}%")
    else:
        logging.warning(f"No test results provided for email")
    
    # Create the email message
    message = MIMEMultipart()
    message["Subject"] = f"Build Integrity Check Results: {status.upper()} - Build {build_id}"
    message["From"] = email_from
    message["To"] = recipient_email
    
    # Email content
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate test results table HTML
    test_results_html = ""
    if test_results and len(test_results) > 0:
        test_results_html = """
        <div class="results-section">
            <h3 class="results-title">Test Results Details</h3>
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th style="width: 100px; text-align: center;">Status</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for idx, test in enumerate(test_results[:20]):  # Show first 20 tests
            # Try multiple field names for test name (test_name, name, title)
            test_name = test.get('test_name') or test.get('name') or test.get('title') or f'Test {idx + 1}'
            test_status = test.get('status', 'unknown').upper()
            
            # Map status to display format
            if test_status in ['PASS', 'PASSED']:
                status_display = 'PASSED'
                status_color = '#28a745'
            elif test_status in ['FAIL', 'FAILED', 'ERROR']:
                status_display = 'FAILED'
                status_color = '#dc3545'
            elif test_status in ['SKIP', 'SKIPPED']:
                status_display = 'SKIPPED'
                status_color = '#ffc107'
            else:
                status_display = test_status
                status_color = '#6c757d'
            
            test_results_html += f"""
                    <tr>
                        <td>{test_name}</td>
                        <td style="text-align: center; color: {status_color}; font-weight: bold;">{status_display}</td>
                    </tr>
            """
        
        if len(test_results) > 20:
            remaining = len(test_results) - 20
            test_results_html += f"""
                    <tr>
                        <td colspan="2" style="text-align: center; font-style: italic; color: #6c757d; background-color: #e9ecef;">
                            ... and {remaining} more test(s)
                        </td>
                    </tr>
            """
        
        test_results_html += """
                </tbody>
            </table>
        </div>
        """
    else:
        # No test results available - show message
        test_results_html = """
        <div class="results-section">
            <p style="text-align: center; color: #6c757d; font-style: italic;">
                Detailed test results are available in the full report.
            </p>
        </div>
        """
    
    # HTML email body with better styling and dynamic test results
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f4f4f4; }}
            .email-container {{ max-width: 750px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            .header {{ background-color: {'#28a745' if status.lower() == 'pass' else '#dc3545'}; color: white; padding: 25px 30px; text-align: center; }}
            .header h2 {{ margin: 0; font-size: 24px; }}
            .content {{ padding: 30px; }}
            .details-section {{ background-color: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0; }}
            .detail-item {{ margin-bottom: 15px; }}
            .detail-label {{ font-weight: 600; color: #495057; font-size: 14px; }}
            .detail-value {{ color: #212529; margin-top: 5px; font-size: 15px; }}
            .quality-score {{ font-size: 28px; font-weight: bold; color: {'#28a745' if quality_score >= 80 else '#ffc107' if quality_score >= 60 else '#dc3545'}; }}
            .summary-box {{ background: #f8f9fa; padding: 25px; border-radius: 6px; margin: 25px 0; }}
            .summary-title {{ text-align: center; color: #333; font-size: 20px; margin: 0 0 20px 0; font-weight: 600; }}
            .stats-grid {{ display: table; width: 100%; margin-top: 15px; }}
            .stats-row {{ display: table-row; }}
            .stat-cell {{ display: table-cell; padding: 15px 10px; text-align: center; background: #ffffff; border: 2px solid #dee2e6; vertical-align: middle; }}
            .stat-number {{ font-size: 28px; font-weight: bold; display: block; margin-bottom: 5px; }}
            .stat-label {{ font-size: 13px; color: #6c757d; font-weight: 500; }}
            .results-section {{ margin: 25px 0; }}
            .results-title {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-bottom: 15px; font-size: 18px; font-weight: 600; }}
            .results-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .results-table th {{ background-color: #f8f9fa; padding: 12px 15px; text-align: left; border: 1px solid #dee2e6; font-weight: 600; font-size: 14px; }}
            .results-table td {{ padding: 10px 15px; border: 1px solid #dee2e6; }}
            .results-table tr:nth-child(even) {{ background-color: #f8f9fa; }}
            .button-container {{ text-align: center; margin: 30px 0 20px 0; }}
            .view-button {{ 
                display: inline-block; 
                padding: 14px 35px; 
                background-color: #007bff; 
                color: #ffffff !important; 
                text-decoration: none !important; 
                border-radius: 6px; 
                font-weight: 600; 
                font-size: 16px;
                box-shadow: 0 2px 4px rgba(0,123,255,0.3);
                transition: background-color 0.3s ease;
            }}
            .view-button:hover {{ 
                background-color: #0056b3; 
                box-shadow: 0 4px 8px rgba(0,123,255,0.4);
            }}
            .footer {{ text-align: center; padding: 20px; background-color: #f8f9fa; color: #6c757d; font-size: 12px; border-top: 1px solid #dee2e6; }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h2>Build Integrity Check {status.upper()}</h2>
            </div>
            
            <div class="content">
                <p style="margin-top: 0;">Hello,</p>
                <p>Your build integrity check has completed with the following results:</p>
                
                <div class="details-section">
                    <div class="detail-item">
                        <div class="detail-label">Build ID:</div>
                        <div class="detail-value">{build_id}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Build URL:</div>
                        <div class="detail-value"><a href="{build_url}" style="color: #007bff; text-decoration: none; word-break: break-word;">{build_url}</a></div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Status:</div>
                        <div class="detail-value" style="color: {'#28a745' if status.lower() == 'pass' else '#dc3545'}; font-weight: bold; font-size: 18px;">
                            {status.upper()}
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Quality Score:</div>
                        <div class="quality-score">{quality_score}%</div>
                    </div>
                    <div class="detail-item" style="margin-bottom: 0;">
                        <div class="detail-label">Date/Time:</div>
                        <div class="detail-value">{current_time}</div>
                    </div>
                </div>
                
                <div class="summary-box">
                    <h3 class="summary-title">Test Execution Summary</h3>
                    <div class="stats-grid">
                        <div class="stats-row">
                            <div class="stat-cell" style="border-radius: 6px 0 0 6px;">
                                <span class="stat-number" style="color: #007bff;">{total_tests}</span>
                                <span class="stat-label">Total Tests</span>
                            </div>
                            <div class="stat-cell">
                                <span class="stat-number" style="color: #28a745;">{passed_tests}</span>
                                <span class="stat-label">Passed</span>
                            </div>
                            <div class="stat-cell">
                                <span class="stat-number" style="color: #dc3545;">{failed_tests}</span>
                                <span class="stat-label">Failed</span>
                            </div>
                            <div class="stat-cell" style="border-radius: 0 6px 6px 0;">
                                <span class="stat-number" style="color: #ffc107;">{skipped_tests}</span>
                                <span class="stat-label">Skipped</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                {test_results_html}
                
                <!-- Hidden: View Detailed Results section as per requirement -->
                <!--
                <p style="margin-top: 25px; margin-bottom: 10px; text-align: center; color: #495057; font-size: 15px;">
                    You can access your full test results, detailed reports, and screenshots by logging in to your account.
                </p>
                
                <div class="button-container">
                    <a href="{frontend_url}/#/bic-output?buildId={build_id}" 
                       class="view-button" 
                       style="display: inline-block; padding: 14px 35px; background-color: #007bff; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; box-shadow: 0 2px 4px rgba(0,123,255,0.3);">
                        View Detailed Results
                    </a>
                </div>
                -->
            </div>
            
            <div class="footer">
                <p style="margin: 0;">This is an automated message from the AI-Powered Test Automation platform.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Attach HTML content
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    try:
        # Connect to the SMTP server
        logger.info(f"Attempting to connect to SMTP server {email_host}:{email_port}")
        with smtplib.SMTP(email_host, email_port) as server:
            server.starttls()
            server.login(email_username, email_password)
            server.send_message(message)
        
        logger.info(f"Build integrity check email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send build integrity email: {str(e)}")
        return False


def ensure_dir_exists(directory: str) -> None:
    """Ensure that a directory exists, creating it if necessary."""
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


async def save_upload_file(
    upload_file: UploadFile, 
    directory: str, 
    filename: Optional[str] = None
) -> str:
    """
    Save an uploaded file to the specified directory.
    
    Args:
        upload_file: The uploaded file
        directory: Directory to save the file to
        filename: Optional custom filename, if None, original filename is used
        
    Returns:
        The path where the file was saved
    """
    # Create directory if it doesn't exist
    ensure_dir_exists(directory)
    
    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{upload_file.filename}"
    
    # Create the complete file path
    file_path = os.path.join(directory, filename)
    
    try:
        # Write file content
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)
        
        return file_path
    except Exception as e:
        # Re-raise with more context
        raise IOError(f"Failed to save upload file: {str(e)}")