from datetime import datetime

from pydantic import BaseModel, field_validator


class RepositorySubmit(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith("https://github.com/"):
            raise ValueError("Only public GitHub URLs are supported (https://github.com/...)")
        parts = v.replace("https://github.com/", "").split("/")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError("URL must be in format https://github.com/owner/repo")
        return v


class RepositoryResponse(BaseModel):
    id: str
    url: str
    owner: str
    name: str
    default_branch: str | None
    description: str | None
    stars: int | None
    languages: list[str] | None
    frameworks: list[str] | None
    clone_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryListResponse(BaseModel):
    items: list[RepositoryResponse]
    total: int
