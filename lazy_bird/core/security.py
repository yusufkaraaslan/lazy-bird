"""Security utilities for authentication and authorization.

This module provides utilities for:
- API key generation and verification
- JWT token creation and verification
- Password hashing and verification
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from lazy_bird.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT algorithm
ALGORITHM = "HS256"


def generate_api_key(prefix: str = "lb", length: int = 32) -> str:
    """Generate a secure random API key.

    Args:
        prefix: Key prefix for identification (default: "lb")
        length: Length of random portion in bytes (default: 32)

    Returns:
        str: API key in format "prefix_randomstring"

    Example:
        >>> key = generate_api_key()
        >>> key.startswith("lb_")
        True
        >>> len(key)
        67  # "lb_" (3) + 64 hex chars (32 bytes * 2)
    """
    random_bytes = secrets.token_bytes(length)
    random_string = random_bytes.hex()
    return f"{prefix}_{random_string}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256.

    Args:
        api_key: Raw API key to hash

    Returns:
        str: Hexadecimal hash of the API key

    Example:
        >>> key = "lb_abc123"
        >>> hashed = hash_api_key(key)
        >>> len(hashed)
        64  # SHA-256 produces 64 hex characters
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash.

    Args:
        raw_key: Raw API key to verify
        hashed_key: Stored hash to compare against

    Returns:
        bool: True if key matches hash, False otherwise

    Example:
        >>> key = "lb_abc123"
        >>> hashed = hash_api_key(key)
        >>> verify_api_key(key, hashed)
        True
        >>> verify_api_key("wrong_key", hashed)
        False
    """
    return hash_api_key(raw_key) == hashed_key


def get_api_key_prefix(api_key: str) -> str:
    """Extract the prefix from an API key (first 8 characters).

    Args:
        api_key: Full API key

    Returns:
        str: First 8 characters for display/identification

    Example:
        >>> key = "lb_abc123def456"
        >>> get_api_key_prefix(key)
        'lb_abc12'
    """
    return api_key[:8] if len(api_key) >= 8 else api_key


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Bcrypt hash of the password

    Example:
        >>> hashed = hash_password("mypassword")
        >>> hashed.startswith("$2b$")
        True
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored bcrypt hash

    Returns:
        bool: True if password matches hash, False otherwise

    Example:
        >>> hashed = hash_password("mypassword")
        >>> verify_password("mypassword", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Token expiration time (default: from settings)

    Returns:
        str: Encoded JWT token

    Example:
        >>> token = create_access_token({"sub": "user123"})
        >>> len(token) > 0
        True
        >>> "." in token  # JWT has 3 parts separated by dots
        True
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Optional[Dict[str, Any]]: Decoded token payload if valid, None otherwise

    Example:
        >>> token = create_access_token({"sub": "user123", "email": "user@example.com"})
        >>> payload = verify_token(token)
        >>> payload is not None
        True
        >>> payload["sub"]
        'user123'
        >>> verify_token("invalid_token") is None
        True
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token with longer expiration.

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Token expiration time (default: from settings)

    Returns:
        str: Encoded JWT refresh token

    Example:
        >>> token = create_refresh_token({"sub": "user123"})
        >>> len(token) > 0
        True
    """
    to_encode = data.copy()

    # Set expiration time (longer than access token)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "refresh"})

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT refresh token.

    Args:
        token: JWT refresh token string

    Returns:
        Optional[Dict[str, Any]]: Decoded token payload if valid and is refresh token, None otherwise

    Example:
        >>> token = create_refresh_token({"sub": "user123"})
        >>> payload = verify_refresh_token(token)
        >>> payload is not None
        True
        >>> payload["type"]
        'refresh'
    """
    payload = verify_token(token)

    # Verify it's a refresh token
    if payload and payload.get("type") == "refresh":
        return payload

    return None


def generate_secure_random_string(length: int = 32) -> str:
    """Generate a cryptographically secure random string.

    Args:
        length: Length of the string in characters (default: 32)

    Returns:
        str: URL-safe random string

    Example:
        >>> random_str = generate_secure_random_string()
        >>> len(random_str)
        32
        >>> random_str.isalnum() or '_' in random_str or '-' in random_str
        True
    """
    return secrets.token_urlsafe(length)


def constant_time_compare(val1: str, val2: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks.

    Args:
        val1: First string
        val2: Second string

    Returns:
        bool: True if strings are equal, False otherwise

    Example:
        >>> constant_time_compare("secret", "secret")
        True
        >>> constant_time_compare("secret", "wrong")
        False
    """
    return secrets.compare_digest(val1.encode(), val2.encode())
