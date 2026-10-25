from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    base_url: str
    model: str
    max_retries: int = Field(ge=0)
    request_timeout_seconds: int = Field(gt=0)
