"""
Database administration schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ColumnInfo(BaseModel):
    """Information about a database column"""
    name: str
    type: str
    nullable: bool
    primary_key: bool = False
    foreign_key: Optional[str] = None
    default: Optional[Any] = None


class TableInfo(BaseModel):
    """Information about a database table"""
    name: str
    row_count: Optional[int] = None
    columns: List[ColumnInfo] = Field(default_factory=list)


class TableDataResponse(BaseModel):
    """Paginated response for table data"""
    table_name: str
    columns: List[ColumnInfo]
    rows: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


class RowCreateRequest(BaseModel):
    """Request to create a new row"""
    data: Dict[str, Any]


class RowUpdateRequest(BaseModel):
    """Request to update a row"""
    data: Dict[str, Any]


class TableCreateRequest(BaseModel):
    """Request to create a new table"""
    table_name: str
    columns: List[Dict[str, Any]]  # name, type, nullable, etc.


class ColumnAddRequest(BaseModel):
    """Request to add a column to a table"""
    column_name: str
    column_type: str
    nullable: bool = True
    default: Optional[Any] = None

