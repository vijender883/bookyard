import os
import json
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx

# These should be in environment variables
CLERK_FRONTEND_API = os.getenv("CLERK_FRONTEND_API")
CLERK_JWT_PUBLIC_KEY = os.getenv("CLERK_JWT_PUBLIC_KEY")
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL") or (
    f"https://{CLERK_FRONTEND_API}/.well-known/jwks.json" if CLERK_FRONTEND_API else None
)

security = HTTPBearer()

# Cache for JWKS
_jwks_cache: Optional[Dict[str, Any]] = None

async def get_jwks() -> Dict[str, Any]:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    
    if not CLERK_JWKS_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk JWKS URL or Frontend API not configured."
        )
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(CLERK_JWKS_URL)
            response.raise_for_status()
            _jwks_cache = response.json()
            return _jwks_cache
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch JWKS from Clerk: {str(e)}"
            )

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify the Clerk JWT token and return the user information.
    """
    # Prefer local public key if provided
    if CLERK_JWT_PUBLIC_KEY:
        try:
            payload = jwt.decode(
                token.credentials, 
                CLERK_JWT_PUBLIC_KEY, 
                algorithms=["RS256"],
                options={"verify_aud": False}
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Could not validate credentials with public key: {str(e)}",
            )

    # Fallback to JWKS
    jwks = await get_jwks()
    try:
        # jwt.decode can handle JWKS if you pass it correctly, 
        # but jose needs the specific key. We'll let it find it.
        payload = jwt.decode(
            token.credentials,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials with JWKS: {str(e)}",
        )
