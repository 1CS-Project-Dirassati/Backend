# madrassati/auth/utils.py
from typing import Optional, Dict, Any # Added Dict, Any for type hinting
import json
import hashlib
import random
from datetime import datetime, timezone, timedelta
import jwt
import secrets
from madrassati.config import Config
from madrassati.extensions import redis_client
from typing import Optional # Added for type hinting


# --- JWT Functions ---
def generate_access_token(user_id: int) -> str:
    """Generate a JWT access token."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=Config.JWT_EXPIRATION),
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)

def generate_refresh_token() -> str:
    """Generate a secure random refresh token."""
    return secrets.token_urlsafe(32)

# --- Token Utility Functions ---
def generate_token_hash(token: str) -> str:
    """Create a searchable SHA-256 hash of a token."""
    # Ensure token is encoded to bytes before hashing
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

# Removed encrypt_token and decrypt_token functions as they are no longer needed

def store_token(user_id: int, refresh_token: str, expires_at: datetime) -> str:
    """
    Store refresh token hash details in Redis with a TTL.
    Associates the token hash (key) with the user and a verification hash (value).
    """
    # This hash is used as the Redis key for quick lookup/revocation
    token_key_hash = generate_token_hash(refresh_token)
    # This hash is stored *inside* the value for verification later
    token_verification_hash = generate_token_hash(refresh_token) # Using same hash for simplicity

    token_data = {
        'user_id': user_id,
        # Store the hash for verification instead of the encrypted token
        'token_verification_hash': token_verification_hash,
        'expires_at': expires_at.isoformat() # Store expiration time
    }

    # Ensure expires_at is timezone-aware (UTC recommended)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # Calculate TTL in seconds
    ttl_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    # Add a buffer, ensure TTL is positive
    ttl_with_buffer = max(ttl_seconds, 0) + 3600 # 1 hour buffer, minimum 1 hour TTL

    redis_key = f"refresh_token:{token_key_hash}"

    # Store the main token data with TTL
    redis_client.setex(
        redis_key,
        ttl_with_buffer,
        json.dumps(token_data)
    )

    # Also store the token hash (the key) in a set associated with the user_id
    redis_client.sadd(f"user_tokens:{user_id}", token_key_hash)

    return token_key_hash # Return the key hash for reference
def retrieve_token(provided_refresh_token: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves and validates refresh token data from Redis.

    Checks if the token exists, if the stored verification hash matches the
    provided token's hash, and if the token has not expired.

    Args:
        provided_refresh_token: The raw refresh token string from the user.

    Returns:
        A dictionary containing 'user_id' and 'expires_at' (datetime object)
        if the token is valid, otherwise None.
    """
    if not provided_refresh_token:
        return None # Cannot retrieve without a token

    token_key_hash = generate_token_hash(provided_refresh_token)
    redis_key = f"refresh_token:{token_key_hash}"

    try:
        token_data_bytes = redis_client.get(redis_key)
        if not token_data_bytes:
            # print(f"Debug: Token not found in Redis for key: {redis_key}")
            return None # Token not found

        # Decode bytes and parse JSON
        token_data_str = token_data_bytes.decode('utf-8') if isinstance (token_data_bytes,bytes) else str(token_data_bytes)
        token_data = json.loads(token_data_str)

        user_id = token_data.get('user_id')
        stored_verification_hash = token_data.get('token_verification_hash')
        expires_at_iso = token_data.get('expires_at')

        # Validate data structure
        if not all([user_id, stored_verification_hash, expires_at_iso]):
             print(f"Warning: Stored token data is incomplete for key: {redis_key}")
             return None # Malformed data

        # 1. Verify the token hash itself
        # Calculate the hash of the token the user provided
        provided_verification_hash = generate_token_hash(provided_refresh_token)
        if provided_verification_hash != stored_verification_hash:
            print(f"Warning: Refresh token hash mismatch for key: {redis_key}")
            # Potentially log this as a possible token theft attempt?
            return None # Token doesn't match stored hash

        # 2. Verify expiration
        expires_at = datetime.fromisoformat(expires_at_iso)
        # Ensure comparison is timezone-aware
        if datetime.now(timezone.utc) > expires_at:
            print(f"Debug: Refresh token expired for key: {redis_key}")
            # Optional: Clean up expired token here explicitly, though TTL handles it eventually
            # revoke_token(token_key_hash) # Be cautious if calling revoke from retrieve
            return None # Token expired

        # If all checks pass, the token is valid
        return {
            'user_id': user_id,
            'expires_at': expires_at # Return the expiry datetime object
            }

    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError, TypeError) as e:
        print(f"Error retrieving or validating refresh token (key: {redis_key}): {e}")
        # Consider logging the specific error and token_key_hash
        return None # Error during processing
    except Exception as e: # Catch potential Redis errors
        print(f"Redis error retrieving token (key: {redis_key}): {e}")
        return None

def revoke_token(token_key_hash: str) -> bool: # Renamed arg for clarity
    """
    Remove a specific refresh token reference from Redis based on its key hash.

    Args:
        token_key_hash: The SHA-256 hash (used as Redis key) of the refresh token.

    Returns:
        True if the token reference was found and successfully revoked, False otherwise.
    """
    redis_key = f"refresh_token:{token_key_hash}"
    # Get token data first to find user_id (needed for removing from user's set)
    token_data_bytes = redis_client.get(redis_key)

    user_id_to_clean = None
    if token_data_bytes:
        try:
            # Attempt to find user_id even if we are just deleting
            token_data_str = token_data_bytes.decode('utf-8') if isinstance(token_data_bytes,bytes) else str(token_data_bytes   )
            token_data = json.loads(token_data_str)
            user_id_to_clean = token_data.get('user_id')
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
            print(f"Warning: Could not parse user_id while revoking token (hash: {token_key_hash}): {e}")
            # Proceed with deletion of main key anyway

    # Delete the main token entry from Redis
    # redis-py's delete returns an integer (number of keys deleted)
    deleted_count = redis_client.delete(redis_key)

    # If we found a user_id, remove the token hash from the user's set
    if user_id_to_clean:
        redis_client.srem(f"user_tokens:{user_id_to_clean}", token_key_hash)

    # Return True if deletion from the main store was successful (key existed)

    result = deleted_count.decode("utf-8") if isinstance(deleted_count,bytes) else str(deleted_count )
    return int(result )> 0


# --- OTP Functions ---
def generate_and_store_otp(phone_number: str) -> int:
    """Generates a 5-digit OTP, stores it in Redis, and returns the OTP."""
    otp_code = random.randint(10000, 99999)
    expiration_time = timedelta(minutes=Config.OTP_EXPIRATION_MINUTES)
    redis_key = f"otp:{phone_number}"

    # Store OTP as string
    redis_client.setex(redis_key, int(expiration_time.total_seconds()), str(otp_code)) # Use integer seconds for TTL

    print(f"Generated OTP for {phone_number}: {otp_code} (Stored in Redis key: {redis_key})") # Dev only

    return otp_code

def verify_stored_otp(phone_number: str, submitted_otp: str) -> bool:
    """Verifies the submitted OTP against the one stored in Redis."""
    redis_key = f"otp:{phone_number}"
    # Get stored OTP (returns bytes or None)
    stored_otp_bytes = redis_client.get(redis_key)

    if not stored_otp_bytes:
        return False # OTP not found or expired

    # Decode the bytes to string for comparison
    try:
        stored_otp = stored_otp_bytes.decode('utf-8') if isinstance(stored_otp_bytes,bytes) else str(stored_otp_bytes)
    except UnicodeDecodeError:
        return False # Should not happen if stored correctly, but handle defensively

    if stored_otp == submitted_otp:
        # OTP is correct, remove it from Redis to prevent reuse
        redis_client.delete(redis_key)
        return True
    else:
        return False # OTP is incorrect

# --- User Functions ---
def find_user_by_email(email: str): # Consider adding return type hint e.g. -> Optional[User]
    """Finds a user by email."""
    # Assuming you have a User model with an email field
    from madrassati.models import User # Keep import local to avoid circular dependencies
    return User.query.filter_by(email=email).first()

# --- Example: How to verify a refresh token (in your auth endpoint) ---
# This function would NOT live in utils.py, it's just for illustration
# def verify_refresh_token(provided_refresh_token: str) -> Optional[int]:
#     """Verifies a refresh token and returns user_id if valid, else None."""
#     token_key_hash = generate_token_hash(provided_refresh_token)
#     redis_key = f"refresh_token:{token_key_hash}"
#
#     token_data_bytes = redis_client.get(redis_key)
#     if not token_data_bytes:
#         print("Refresh token not found in Redis.")
#         return None # Token not found
#
#     try:
#         token_data_str = token_data_bytes.decode('utf-8')
#         token_data = json.loads(token_data_str)
#
#         user_id = token_data.get('user_id')
#         stored_verification_hash = token_data.get('token_verification_hash')
#         expires_at_iso = token_data.get('expires_at')
#
#         if not all([user_id, stored_verification_hash, expires_at_iso]):
#              print("Stored token data is incomplete.")
#              return None # Malformed data
#
#         # 1. Verify the token hash itself
#         provided_verification_hash = generate_token_hash(provided_refresh_token)
#         if provided_verification_hash != stored_verification_hash:
#             print("Refresh token hash mismatch.")
#             return None # Token doesn't match stored hash
#
#         # 2. Verify expiration
#         expires_at = datetime.fromisoformat(expires_at_iso)
#         if datetime.now(timezone.utc) > expires_at:
#             print("Refresh token expired.")
#             # Optional: Clean up expired token here or rely on TTL
#             # revoke_token(token_key_hash)
#             return None # Token expired
#
#         # If all checks pass, the token is valid
#         return user_id
#
#     except (json.JSONDecodeError, UnicodeDecodeError, KeyError, ValueError) as e:
#         print(f"Error verifying refresh token: {e}")
#         return None # Error during processing
