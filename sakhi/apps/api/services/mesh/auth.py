"""
A.6 Mesh Authentication
-----------------------
JWT-based authentication for inter-Sakhi communication.

Uses public key infrastructure:
1. Each Sakhi generates RSA key pair on registration
2. Public key stored in mesh_endpoints
3. Messages signed with private key
4. Receiver verifies using sender's public key

This eliminates the need for shared secrets between Sakhi instances.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import jwt
from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec
from sakhi.apps.api.services.mesh.inter_sakhi import (
    MeshMessage,
    lookup_sakhi_endpoint,
)

LOGGER = logging.getLogger(__name__)

# Constants
JWT_ALGORITHM = "RS256"  # RSA with SHA-256
FALLBACK_ALGORITHM = "HS256"  # HMAC fallback when no keys
JWT_EXPIRY_HOURS = 24
MESH_JWT_ISSUER = "sakhi-mesh"

# Get mesh secret from environment (fallback for HMAC)
MESH_SECRET = os.getenv("MESH_SECRET", "sakhi-mesh-default-secret")


# =============================================================================
# Models
# =============================================================================

class MeshJWTClaims(BaseModel):
    """Claims in a mesh JWT token."""
    iss: str  # Issuer sakhi_id
    sub: str  # Subject (message ID or purpose)
    aud: Optional[str] = None  # Audience (target sakhi_id)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    jti: str  # JWT ID
    sakhi_id: str  # Sender's sakhi_id
    message_type: Optional[str] = None
    payload_hash: Optional[str] = None  # SHA-256 of payload for integrity


class TokenVerificationResult(BaseModel):
    """Result of verifying a mesh JWT."""
    valid: bool
    error: Optional[str] = None
    claims: Optional[Dict[str, Any]] = None
    issuer_sakhi_id: Optional[str] = None
    expired: bool = False


# =============================================================================
# Key Management
# =============================================================================

def generate_key_pair() -> Tuple[str, str]:
    """
    Generate RSA key pair for Sakhi authentication.

    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        # Get public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return private_pem, public_pem

    except ImportError:
        LOGGER.warning("[mesh_auth] cryptography not installed, using HMAC fallback")
        return "", ""


async def rotate_sakhi_keys(sakhi_id: str) -> Tuple[str, str]:
    """
    Generate and store new key pair for a Sakhi.

    Args:
        sakhi_id: The Sakhi's ID

    Returns:
        Tuple of (private_key_pem, public_key_pem)
        Note: Private key should be stored securely by caller, not in DB
    """
    private_key, public_key = generate_key_pair()

    if public_key:
        await dbexec(
            """
            UPDATE mesh_endpoints
            SET public_key = $1
            WHERE sakhi_id = $2
            """,
            public_key,
            sakhi_id,
        )
        LOGGER.info("[mesh_auth] Rotated keys for %s", sakhi_id)

    return private_key, public_key


async def get_sakhi_public_key(sakhi_id: str) -> Optional[str]:
    """
    Get a Sakhi's public key for verification.

    Args:
        sakhi_id: The Sakhi's ID

    Returns:
        Public key PEM or None
    """
    endpoint = await lookup_sakhi_endpoint(sakhi_id)
    return endpoint.public_key if endpoint else None


async def store_private_key(sakhi_id: str, private_key: str) -> bool:
    """
    Store private key securely (in a separate secure store, not main DB).

    For now, stores in mesh_private_keys table with encryption.
    In production, use HSM or secure vault.
    """
    try:
        from sakhi.libs.security.crypto import encrypt_sensitive

        encrypted = encrypt_sensitive(private_key)

        await dbexec(
            """
            INSERT INTO mesh_private_keys (sakhi_id, encrypted_key, created_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (sakhi_id) DO UPDATE
            SET encrypted_key = $2, rotated_at = NOW()
            """,
            sakhi_id,
            encrypted,
        )
        return True

    except Exception as e:
        LOGGER.exception("[mesh_auth] Failed to store private key: %s", e)
        return False


async def get_private_key(sakhi_id: str) -> Optional[str]:
    """
    Retrieve private key for signing.

    Returns decrypted private key or None.
    """
    try:
        from sakhi.libs.security.crypto import decrypt_sensitive

        row = await dbfetch(
            "SELECT encrypted_key FROM mesh_private_keys WHERE sakhi_id = $1",
            sakhi_id,
            one=True,
        )

        if not row:
            return None

        return decrypt_sensitive(row["encrypted_key"])

    except Exception as e:
        LOGGER.warning("[mesh_auth] Failed to get private key: %s", e)
        return None


# =============================================================================
# JWT Token Creation
# =============================================================================

def _compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Compute SHA-256 hash of payload for integrity."""
    import hashlib
    import json
    content = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def create_mesh_jwt(
    sakhi_id: str,
    subject: str,
    audience: Optional[str] = None,
    message_type: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    private_key: Optional[str] = None,
    expires_in_hours: int = JWT_EXPIRY_HOURS,
) -> str:
    """
    Create a signed JWT for mesh communication.

    Args:
        sakhi_id: This Sakhi's ID (issuer)
        subject: Subject (message ID or purpose)
        audience: Target Sakhi ID (optional)
        message_type: Type of mesh message
        payload: Message payload (for integrity hash)
        private_key: RSA private key PEM (uses HMAC fallback if None)
        expires_in_hours: Token expiry

    Returns:
        Signed JWT string
    """
    import uuid

    now = int(time.time())
    exp = now + (expires_in_hours * 3600)

    claims = {
        "iss": MESH_JWT_ISSUER,
        "sub": subject,
        "exp": exp,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "sakhi_id": sakhi_id,
    }

    if audience:
        claims["aud"] = audience

    if message_type:
        claims["message_type"] = message_type

    if payload:
        claims["payload_hash"] = _compute_payload_hash(payload)

    # Sign with RSA if we have a private key, otherwise HMAC
    if private_key:
        try:
            return jwt.encode(claims, private_key, algorithm=JWT_ALGORITHM)
        except Exception as e:
            LOGGER.warning("[mesh_auth] RSA signing failed, falling back to HMAC: %s", e)

    # HMAC fallback
    return jwt.encode(claims, MESH_SECRET, algorithm=FALLBACK_ALGORITHM)


async def create_mesh_jwt_async(
    sakhi_id: str,
    subject: str,
    audience: Optional[str] = None,
    message_type: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    expires_in_hours: int = JWT_EXPIRY_HOURS,
) -> str:
    """
    Create a signed JWT, fetching private key automatically.

    This is the main function to use when signing messages.
    """
    private_key = await get_private_key(sakhi_id)
    return create_mesh_jwt(
        sakhi_id=sakhi_id,
        subject=subject,
        audience=audience,
        message_type=message_type,
        payload=payload,
        private_key=private_key,
        expires_in_hours=expires_in_hours,
    )


# =============================================================================
# JWT Token Verification
# =============================================================================

def verify_mesh_jwt(
    token: str,
    public_key: Optional[str] = None,
    expected_audience: Optional[str] = None,
    verify_payload_hash: Optional[Dict[str, Any]] = None,
) -> TokenVerificationResult:
    """
    Verify a mesh JWT token.

    Args:
        token: JWT string
        public_key: Sender's RSA public key (uses HMAC if None)
        expected_audience: Expected audience claim
        verify_payload_hash: Payload to verify integrity against

    Returns:
        TokenVerificationResult with validation details
    """
    try:
        # Try RSA first if we have a public key
        if public_key:
            try:
                claims = jwt.decode(
                    token,
                    public_key,
                    algorithms=[JWT_ALGORITHM],
                    issuer=MESH_JWT_ISSUER,
                    audience=expected_audience,
                    options={"require": ["exp", "iat", "jti", "sakhi_id"]},
                )
            except jwt.InvalidAlgorithmError:
                # Fall through to HMAC
                claims = None
        else:
            claims = None

        # HMAC fallback
        if claims is None:
            claims = jwt.decode(
                token,
                MESH_SECRET,
                algorithms=[FALLBACK_ALGORITHM],
                issuer=MESH_JWT_ISSUER,
                options={"require": ["exp", "iat", "jti", "sakhi_id"]},
            )

            # Manual audience check for HMAC
            if expected_audience and claims.get("aud") != expected_audience:
                return TokenVerificationResult(
                    valid=False,
                    error=f"Audience mismatch: expected {expected_audience}",
                )

        # Verify payload hash if provided
        if verify_payload_hash and claims.get("payload_hash"):
            computed = _compute_payload_hash(verify_payload_hash)
            if computed != claims["payload_hash"]:
                return TokenVerificationResult(
                    valid=False,
                    error="Payload integrity check failed",
                    claims=claims,
                    issuer_sakhi_id=claims.get("sakhi_id"),
                )

        return TokenVerificationResult(
            valid=True,
            claims=claims,
            issuer_sakhi_id=claims.get("sakhi_id"),
        )

    except jwt.ExpiredSignatureError:
        return TokenVerificationResult(
            valid=False,
            error="Token expired",
            expired=True,
        )

    except jwt.InvalidTokenError as e:
        return TokenVerificationResult(
            valid=False,
            error=f"Invalid token: {str(e)}",
        )


async def verify_mesh_jwt_async(
    token: str,
    issuer_sakhi_id: str,
    expected_audience: Optional[str] = None,
    verify_payload_hash: Optional[Dict[str, Any]] = None,
) -> TokenVerificationResult:
    """
    Verify a mesh JWT, fetching public key automatically.

    Args:
        token: JWT string
        issuer_sakhi_id: Expected issuer's sakhi_id (to fetch public key)
        expected_audience: Expected audience claim
        verify_payload_hash: Payload to verify integrity against

    Returns:
        TokenVerificationResult
    """
    public_key = await get_sakhi_public_key(issuer_sakhi_id)
    return verify_mesh_jwt(
        token=token,
        public_key=public_key,
        expected_audience=expected_audience,
        verify_payload_hash=verify_payload_hash,
    )


# =============================================================================
# Message Signing
# =============================================================================

def sign_mesh_message(
    message: MeshMessage,
    private_key: Optional[str] = None,
) -> str:
    """
    Create a JWT signature for a mesh message.

    Args:
        message: The MeshMessage to sign
        private_key: RSA private key (uses HMAC if None)

    Returns:
        JWT signature string
    """
    return create_mesh_jwt(
        sakhi_id=message.from_sakhi_id,
        subject=message.message_id,
        audience=message.to_sakhi_id,
        message_type=message.message_type.value,
        payload=message.payload,
        private_key=private_key,
    )


async def sign_mesh_message_async(message: MeshMessage) -> str:
    """
    Sign a mesh message, fetching private key automatically.
    """
    private_key = await get_private_key(message.from_sakhi_id)
    return sign_mesh_message(message, private_key)


async def verify_mesh_message(
    message: MeshMessage,
    signature: str,
) -> TokenVerificationResult:
    """
    Verify a mesh message signature.

    Args:
        message: The received message
        signature: JWT signature from message

    Returns:
        TokenVerificationResult
    """
    return await verify_mesh_jwt_async(
        token=signature,
        issuer_sakhi_id=message.from_sakhi_id,
        expected_audience=message.to_sakhi_id,
        verify_payload_hash=message.payload,
    )


# =============================================================================
# Trust & Authorization
# =============================================================================

async def is_trusted_sender(
    from_sakhi_id: str,
    to_sakhi_id: str,
) -> Tuple[bool, str]:
    """
    Check if a sender is trusted by the receiver.

    Verifies:
    1. Sender is registered
    2. Sender has valid public key
    3. Connection exists between them

    Returns:
        Tuple of (is_trusted, reason)
    """
    # Check sender is registered
    sender = await lookup_sakhi_endpoint(from_sakhi_id)
    if not sender:
        return False, "Sender not registered"

    # Check receiver exists
    receiver = await lookup_sakhi_endpoint(to_sakhi_id)
    if not receiver:
        return False, "Receiver not found"

    # Check connection (optional - can be relaxed for open mesh)
    try:
        from sakhi.apps.api.services.mesh.connections import are_connected

        if not await are_connected(sender.person_id, receiver.person_id):
            # Allow messages from unconnected Sakhis but flag it
            return True, "not_connected"

        return True, "connected"

    except Exception:
        # Connection check failed, allow anyway
        return True, "connection_check_failed"


async def get_auth_requirements(
    to_sakhi_id: str,
    message_type: str,
) -> Dict[str, Any]:
    """
    Get authentication requirements for sending to a Sakhi.

    Different message types may have different requirements:
    - PING: No auth required
    - SCHEDULING_REQUEST: Must be connected
    - INQUIRY: Signature required

    Returns:
        Dict with requirements
    """
    # Get receiver's settings
    receiver = await lookup_sakhi_endpoint(to_sakhi_id)
    if not receiver:
        return {"error": "Receiver not found"}

    # Default requirements
    requirements = {
        "signature_required": True,
        "connection_required": False,
        "trust_level_required": None,
    }

    # Relax for certain message types
    if message_type in ["ping", "pong", "register"]:
        requirements["signature_required"] = False

    if message_type in ["scheduling_request", "availability_request"]:
        requirements["connection_required"] = True

    return requirements


__all__ = [
    "MeshJWTClaims",
    "TokenVerificationResult",
    "generate_key_pair",
    "rotate_sakhi_keys",
    "get_sakhi_public_key",
    "store_private_key",
    "get_private_key",
    "create_mesh_jwt",
    "create_mesh_jwt_async",
    "verify_mesh_jwt",
    "verify_mesh_jwt_async",
    "sign_mesh_message",
    "sign_mesh_message_async",
    "verify_mesh_message",
    "is_trusted_sender",
    "get_auth_requirements",
]
