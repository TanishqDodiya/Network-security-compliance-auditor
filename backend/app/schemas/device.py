"""Pydantic schemas = shape of data going in/out of the API.

Beginner idea: models.py describes the DATABASE tables.
schemas.py describes the JSON the frontend sends/receives.
We keep them separate so DB changes don't break the API.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128, examples=["Cisco-Router-01"])
    vendor: str = Field(default="unknown", max_length=32, examples=["cisco"])


class DeviceOut(BaseModel):
    id: int
    name: str
    vendor: str
    created_at: datetime

    model_config = {"from_attributes": True}
