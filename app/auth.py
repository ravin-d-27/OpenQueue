import hashlib
import hmac
import os
from typing import Optional, TypedDict

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.exceptions import HTTPException

from .database import db


class CurrentUser(TypedDict):
    id: str
    email: Optional[str]
    is_active: bool


security = HTTPBearer(auto_error=True)


def hash_api_token(token: str) -> str:
    """
    Derive a stable token hash for lookup in the database.

    Default: SHA-256(token) as hex.

    If `OPENQUEUE_TOKEN_HMAC_SECRET` is set:
      hash = HMAC-SHA256(secret, token) as hex

    Why HMAC?
    - Prevents offline token-guessing attacks if the DB leaks (attacker can't verify guesses
      without the server secret).
    - Allows rotating the secret (with care) as part of operational security.

    Important:
    - Do NOT change this in production without a migration plan, because all stored
      api_token_hash values depend on this derivation.
    """
    secret = os.getenv("OPENQUEUE_TOKEN_HMAC_SECRET")
    if secret:
        digest = hmac.new(
            key=secret.encode("utf-8"),
            msg=token.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return digest

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    token = (credentials.credentials or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    token_hash = hash_api_token(token)

    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, is_active
                FROM users
                WHERE api_token_hash = $1
                """,
                token_hash,
            )

            if not row:
                raise HTTPException(status_code=401, detail="Invalid API token")
            if not row["is_active"]:
                raise HTTPException(status_code=403, detail="User is inactive")

            await conn.execute(
                "UPDATE users SET last_seen_at = NOW() WHERE id = $1",
                row["id"],
            )

            return {
                "id": str(row["id"]),
                "email": row["email"],
                "is_active": row["is_active"],
            }
