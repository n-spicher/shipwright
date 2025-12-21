import os
import logging
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models.user import User

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK (done once at startup)
_firebase_initialized = False

def initialize_firebase():
    """Initialize Firebase Admin SDK if not already initialized."""
    global _firebase_initialized
    
    if _firebase_initialized:
        return
    
    try:
        # Check if Firebase app is already initialized
        firebase_admin.get_app()
        _firebase_initialized = True
        logger.info("Firebase Admin SDK already initialized")
        return
    except ValueError:
        # App not initialized yet, proceed with initialization
        pass
    
    try:
        # Try to get service account path from environment
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        
        if service_account_path and os.path.exists(service_account_path):
            # Use explicit service account file
            logger.info(f"Initializing Firebase Admin SDK with service account: {service_account_path}")
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            # Use default credentials or project ID
            project_id = os.getenv("FIREBASE_PROJECT_ID")
            if project_id:
                logger.info(f"Initializing Firebase Admin SDK with project ID: {project_id}")
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id
                })
            else:
                logger.warning("No Firebase credentials configured. Using default Application Default Credentials.")
                firebase_admin.initialize_app()
        
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
        raise


def verify_firebase_token(token: str) -> dict:
    """
    Verify Firebase ID token and return decoded token.
    
    Args:
        token: Firebase ID token string
        
    Returns:
        dict: Decoded token with uid, email, etc.
        
    Raises:
        HTTPException: If token is invalid
    """
    if not token:
        logger.error("[firebase_auth] No token provided")
        raise HTTPException(status_code=401, detail="No authentication token provided")
    
    try:
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get('uid')
        uid_prefix = uid[:8] if uid else None
        logger.info(f"[firebase_auth] Token verified successfully uidPrefix={uid_prefix}")
        return decoded_token
        
    except auth.InvalidIdTokenError as e:
        logger.error(f"[firebase_auth] Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except auth.ExpiredIdTokenError as e:
        logger.error(f"[firebase_auth] Expired token: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication token has expired")
    except Exception as e:
        logger.error(f"[firebase_auth] Token verification error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")


def get_current_user_from_token(token: str, db: Session) -> User:
    """
    Verify token and get or create backend user.
    
    Args:
        token: Firebase ID token
        db: Database session
        
    Returns:
        User: Backend user object
        
    Raises:
        HTTPException: If authentication fails
    """
    # Verify token and get Firebase user info
    decoded_token = verify_firebase_token(token)
    firebase_uid = decoded_token.get('uid')
    email = decoded_token.get('email')
    uid_prefix = firebase_uid[:8] if firebase_uid else None
    email_domain = email.split('@')[-1] if isinstance(email, str) and '@' in email else None
    
    if not firebase_uid:
        logger.error("[firebase_auth] No uid in decoded token")
        raise HTTPException(status_code=401, detail="Invalid token: missing uid")
    
    logger.info(f"[firebase_auth] User lookup uidPrefix={uid_prefix} emailDomain={email_domain}")
    
    # Try to find existing user by firebase_uid
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    
    if user:
        logger.info(f"[firebase_auth] Found existing user user_id={user.id} uidPrefix={uid_prefix}")
        return user
    
    # If not found by firebase_uid, try by email
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Update existing user with firebase_uid
            logger.info(f"[firebase_auth] Found user by email, updating firebase_uid user_id={user.id} uidPrefix={uid_prefix}")
            user.firebase_uid = firebase_uid
            db.commit()
            db.refresh(user)
            return user
    
    # Create new user if doesn't exist
    logger.info(f"[firebase_auth] Creating new user uidPrefix={uid_prefix} emailDomain={email_domain}")
    
    # Generate username from email or firebase_uid
    if email:
        username = email.split('@')[0]
    else:
        username = f"user_{firebase_uid[:8]}"
    
    # Ensure username is unique
    base_username = username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1
    
    # Create new user
    new_user = User(
        email=email or f"{firebase_uid}@firebase.user",
        username=username,
        firebase_uid=firebase_uid,
        hashed_password="",  # No password needed for Firebase users
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"[firebase_auth] Created new user user_id={new_user.id} uidPrefix={uid_prefix}")
    return new_user
