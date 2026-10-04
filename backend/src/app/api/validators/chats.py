from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ChatCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class FeedbackRequest(BaseModel):
    rating: Literal["up", "down"]
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_downvote_comment(self):
        if self.rating == "down" and not (self.comment and self.comment.strip()):
            raise ValueError("Please add a short comment explaining your feedback.")
        return self
