from __future__ import annotations

import hashlib
import secrets

from app.core.config import settings


#Eto otdelnyy shag generate_verification_token, chtoby ne kopipastit odno i to zhe.
def generate_verification_token() -> str:
    return secrets.token_urlsafe(48)


#Funkciya hash_verification_token zakryvaet konkretnuyu zadachu v etom meste.
def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


#Eto otdelnyy shag build_verification_link, chtoby ne kopipastit odno i to zhe.
def build_verification_link(token: str) -> str:
    return f"{settings.frontend_base_url.rstrip('/')}/verify-email?token={token}"
