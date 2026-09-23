"""Issue payload entering phase 1 (workflow event shaped for the seam)."""

from pydantic import BaseModel, Field


class IssuePayload(BaseModel):
    """The opened-issue payload phase 1 triages (seam A input)."""

    number: int
    title: str
    body: str
    author_login: str
    comments: list[str] = Field(default_factory=list)
