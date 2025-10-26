from pydantic import BaseModel
from typing import Any, Union
from datetime import datetime
from uuid import UUID


class DataSourceCreate(BaseModel):
    name: str
    source_type: str = "intercom"
    raw_data: Union[dict[str, Any], list[Any]]  # Can be dict or list


class DataSourceResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class DataSourceDetail(DataSourceResponse):
    raw_data: Union[dict[str, Any], list[Any]]  # Can be dict or list

    class Config:
        from_attributes = True

