import hashlib
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
    # store and compare only hashes
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
