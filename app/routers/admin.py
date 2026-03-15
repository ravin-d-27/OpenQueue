from __future__ import annotations

import secrets
import string
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, EmailStr

from ..auth import hash_api_token
from ..database import db
from ..settings import get_settings

router = APIRouter(prefix="/admin", tags=["Admin"])


class ProvisionRequest(BaseModel):
    email: EmailStr


class ProvisionResponse(BaseModel):
    token: str
    email: str
    created: bool


def _generate_token() -> str:
    """Generate a new oq_live_... API token (40 random URL-safe characters)."""
    alphabet = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(40))
    return f"oq_live_{random_part}"


@router.post(
    "/provision",
    summary="Provision a user",
    description=(
        "Creates or updates a user record, generating a fresh API token. "
        "Protected by the X-Admin-Secret header."
    ),
    response_model=ProvisionResponse,
    status_code=status.HTTP_200_OK,
)
async def provision_user(
    body: ProvisionRequest,
    x_admin_secret: Optional[str] = Header(default=None),
) -> ProvisionResponse:
    settings = get_settings()

    # Guard: admin secret must be configured and must match.
    if not settings.admin_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin provisioning is not configured on this server.",
        )
    if x_admin_secret != settings.admin_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-Secret header.",
        )

    token = _generate_token()
    token_hash = hash_api_token(token)

    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            # Upsert: create user if not exists, update token hash if exists.
            row = await conn.fetchrow(
                """
                INSERT INTO users (email, api_token_hash, is_active)
                VALUES ($1, $2, true)
                ON CONFLICT (email) DO UPDATE
                    SET api_token_hash = EXCLUDED.api_token_hash,
                        is_active      = true
                RETURNING id,
                          (xmax = 0) AS created
                """,
                body.email,
                token_hash,
            )

    return ProvisionResponse(
        token=token,
        email=body.email,
        created=bool(row["created"]),
    )
