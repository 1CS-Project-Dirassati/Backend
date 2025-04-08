# madrassati/auth/utils.py
import random
from datetime import datetime, timezone, timedelta
import jwt

from madrassati.config import Config
from madrassati.extensions import redis_client

# --- Constants ---
OTP_EXPIRATION_MINUTES = 10

# --- JWT Functions ---
def generate_token(user_id):
    """Generate a JWT token."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=Config.JWT_EXPIRATION),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)

# --- OTP Functions ---
def generate_and_store_otp(phone_number: str) -> int:
    """Generates a 5-digit OTP, stores it in Redis, and returns the OTP."""
    otp_code = random.randint(10000, 99999)
    expiration_time = timedelta(minutes=OTP_EXPIRATION_MINUTES)
    redis_key = f"otp:{phone_number}"

    redis_client.setex(redis_key, expiration_time, otp_code)

    # !!! Important: Remove this print in production !!!
    # This should be replaced by an actual SMS sending mechanism.
    print(f"Generated OTP for {phone_number}: {otp_code} (Stored in Redis key: {redis_key})")

    return otp_code # Returning for potential use/logging, though original only printed


def verify_stored_otp(phone_number: str, submitted_otp: str) -> bool:
    """Verifies the submitted OTP against the one stored in Redis."""
    redis_key = f"otp:{phone_number}"
    stored_otp_bytes = redis_client.get(redis_key)

    if not stored_otp_bytes:
        return False # OTP not found or expired

    stored_otp_awaitable = redis_client.get(f"otp:{phone_number}")
    stored_otp = stored_otp_awaitable.decode() if isinstance(stored_otp_awaitable, bytes) else str(stored_otp_awaitable)

    if stored_otp == submitted_otp:
        # OTP is correct, remove it from Redis
        redis_client.delete(redis_key)
        return True
    else:
        return False # OTP is incorrect
