from typing import Optional, Dict, Any
from fernet import Fernet
import json
import hashlib
import random
from datetime import datetime, timezone, timedelta
import jwt
import secrets

from werkzeug.security import check_password_hash, generate_password_hash
from madrassati.config import Config
from madrassati.extensions import redis_client

ENCRYPTION_KEY = Config.SECRET_KEY
cipher_suite = Fernet(Config.FERNET_KEY.encode("utf-8"))  # Ensure the key is bytes


# --- JWT Functions ---
def generate_access_token(user_id: int, refresh_token_hash) -> str:
    """Generate a JWT access token."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=Config.JWT_EXPIRATION),
        "iat": datetime.now(timezone.utc),
        "type": "access",
        "refresh_hash": refresh_token_hash,
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def generate_refresh_token() -> str:
    """Generate a secure random refresh token."""
    return secrets.token_urlsafe(32)


# --- Token Utility Functions ---
def generate_token_hash(token: str) -> str:
    """Create a searchable SHA-256 hash of a token."""
    # Ensure token is encoded to bytes before hashing
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def store_refresh_token(user_id: int, refresh_token: str, expires_at: datetime) -> str:
    """
    Store refresh token hash details in Redis with a TTL.
    Associates the token hash (key) with the user and a verification hash (value).
    """
    token_key_hash = generate_token_hash(refresh_token)
    encrypted_token = generate_password_hash(refresh_token)

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    refresh_token_data = {
        "user_id": user_id,
        "token": encrypted_token,  # Store as string
        "expires_at": expires_at.isoformat(),
    }

    ttl_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    ttl_with_buffer = max(ttl_seconds, 0) + 3600  # 1 hour buffer, minimum 1 hour TTL

    redis_key = f"refresh_token:{token_key_hash}"

    redis_client.setex(redis_key, ttl_with_buffer, json.dumps(refresh_token_data))
    redis_client.sadd(f"user_tokens:{user_id}", token_key_hash)
    return token_key_hash  # Return the key hash for reference


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
        return None  # Cannot retrieve without a token

    token_key_hash = generate_token_hash(provided_refresh_token)
    redis_key = f"refresh_token:{token_key_hash}"

    try:
        token_data_bytes = redis_client.get(redis_key)
        if not token_data_bytes:
            return None  # Token not found

        token_data_str = token_data_bytes.decode("utf-8") if isinstance(token_data_bytes, bytes) else str(token_data_bytes)
        token_data = json.loads(token_data_str)

        user_id = token_data.get("user_id")
        stored_verification_hash = token_data.get("token")
        expires_at_iso = token_data.get("expires_at")

        if not all([user_id, stored_verification_hash, expires_at_iso]):
            return None  # Malformed data

        provided_verification_hash = generate_password_hash(
            provided_refresh_token
        )
        if not check_password_hash(provided_verification_hash, stored_verification_hash):
            return None  # Token doesn't match stored hash

        expires_at = datetime.fromisoformat(expires_at_iso)
        if datetime.now(timezone.utc) > expires_at:
            return None  # Token expired

        return {
            "user_id": user_id,
            "expires_at": expires_at,  # Return the expiry datetime object
        }

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        ValueError,
        KeyError,
        TypeError,
    ) as e:
        return None  # Error during processing
    except Exception as e:  # Catch potential Redis errors
        return None


def revoke_all_tokens(user_id: int) -> bool:
    """
    Remove all refresh token references for a user from Redis.

    Args:
        user_id: The ID of the user whose tokens are to be revoked.

    Returns:
        True if tokens were found and successfully revoked, False otherwise.
    """
    redis_key = f"user_tokens:{user_id}"
    token_hashes = redis_client.smembers(redis_key)
    token_hashes = (
        token_hashes.decode("utf-8")
        if isinstance(token_hashes, bytes)
        else str(token_hashes)
    )

    if not token_hashes:
        return False  # No tokens to revoke

    for token_key_hash_bytes in token_hashes:
        token_key_hash = token_key_hash_bytes
        redis_client.delete(f"refresh_token:{token_key_hash}")

    redis_client.delete(redis_key)
    return True  # Tokens revoked successfully
def revoke_token(token_key_hash: str) -> bool:
    """
    Remove a specific refresh token reference from Redis based on its key hash.

    Args:
        token_key_hash: The SHA-256 hash (used as Redis key) of the refresh token.

    Returns:
        True if the token reference was found and successfully revoked, False otherwise.
    """
    redis_key = f"refresh_token:{token_key_hash}"
    token_data_bytes = redis_client.get(redis_key)

    user_id_to_clean = None
    if token_data_bytes:
        try:
            token_data_str = token_data_bytes.decode("utf-8") if isinstance(token_data_bytes, bytes) else str(token_data_bytes)
            token_data = json.loads(token_data_str)
            user_id_to_clean = token_data.get("user_id")
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
            pass

    deleted_count = redis_client.delete(redis_key)

    if user_id_to_clean:
        redis_client.srem(f"user_tokens:{user_id_to_clean}", token_key_hash)
    result = (
        deleted_count.decode("utf-8")
        if isinstance(deleted_count, bytes)
        else str(deleted_count)
    )

    return int(result ) > 0


# --- OTP Functions ---
def generate_and_store_otp(phone_number: str, ) -> int:
    """Generates a 5-digit OTP, stores it in Redis, and returns the OTP."""
    otp_code = random.randint(10000, 99999)
    expiration_time = timedelta(minutes=Config.OTP_EXPIRATION_MINUTES)
    redis_key = f"otp:{phone_number}"

    redis_client.setex(
        redis_key, int(expiration_time.total_seconds()), str(otp_code)
    )  # Use integer seconds for TTL

    return otp_code


def verify_stored_otp(phone_number: str, submitted_otp: str) -> bool:
    """Verifies the submitted OTP against the one stored in Redis."""
    redis_key = f"otp:{phone_number}"
    stored_otp_bytes = redis_client.get(redis_key)

    if not stored_otp_bytes:
        return False  # OTP not found or expired

    try:
        stored_otp = stored_otp_bytes.decode("utf-8") if isinstance(stored_otp_bytes, bytes) else str(stored_otp_bytes)
    except UnicodeDecodeError:
        return False  # Should not happen if stored correctly, but handle defensively

    if stored_otp == submitted_otp:
        # OTP is correct, remove it from Redis to prevent reuse
        redis_client.delete(redis_key)
        return True
    else:
        return False  # OTP is incorrect


# --- Parent Functions ---
def find_parent_by_email(
    email: str,
):  # Consider adding return type hint e.g. -> Optional[Parent]
    """Finds a user by email."""
    # Assuming you have a Parent model with an email field
    from madrassati.models import (
        Parent,
    )  # Keep import local to avoid circular dependencies

    return Parent.query.filter_by(email=email).first()
