from __future__ import annotations

from pydantic import BaseModel, field_validator


class LocalEmailModel(BaseModel):
    #Funkciya validate_local_email zakryvaet konkretnuyu zadachu v etom meste.
    @field_validator("email", check_fields=False)
    @classmethod
    def validate_local_email(cls, value: str) -> str:
        email = value.strip().lower()
        if email.count("@") != 1:
            raise ValueError("Email must contain a single @ symbol")

        local_part, domain = email.split("@", 1)
        if not local_part or not domain:
            raise ValueError("Email must include local and domain parts")
        if "." not in domain and domain != "localhost":
            raise ValueError("Email domain must contain a dot or be localhost")
        if domain.startswith(".") or domain.endswith("."):
            raise ValueError("Email domain is invalid")

        return email
