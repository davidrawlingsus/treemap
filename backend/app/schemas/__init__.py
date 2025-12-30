"""
Pydantic schemas organized by domain.
Exports all schemas for backward compatibility.
"""

# Import all schemas from domain modules
from .auth import (
    Token,
    TokenData,
    UserLogin,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    ImpersonateRequest,
    FounderUserMembership,
    UserResponse,
    UserWithClients,
    FounderUserSummary,
)

from .client import (
    AuthorizedDomainBase,
    AuthorizedDomainCreate,
    AuthorizedDomainUpdate,
    AuthorizedDomainResponse,
    ClientCreate,
    ClientResponse,
)

from .data_source import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceDetail,
    QuestionInfo,
    DataSourceWithQuestions,
    DimensionNameCreate,
    DimensionNameBatchUpdate,
    DimensionNameResponse,
)

from .voc import (
    ProcessVocResponse,
    ProcessVocListResponse,
    DimensionQuestionInfo,
    VocSourceInfo,
    VocClientInfo,
    VocProjectInfo,
    ProcessVocBulkUpdateItem,
    ProcessVocBulkUpdateRequest,
    ProcessVocBulkUpdateResponse,
    ProcessVocAdminListResponse,
    FieldMetadata,
    FieldMetadataResponse,
    DynamicBulkUpdateRequest,
)

from .csv_upload import (
    CsvColumnMapping,
    CsvUploadResponse,
    CsvColumnMappingRequest,
    CsvSaveResponse,
)

from .admin import (
    ColumnInfo,
    TableInfo,
    TableDataResponse,
    RowCreateRequest,
    RowUpdateRequest,
    TableCreateRequest,
    ColumnAddRequest,
)

from .insight import (
    InsightOrigin,
    InsightCreate,
    InsightUpdate,
    InsightResponse,
    InsightListResponse,
)

# Export all for backward compatibility
__all__ = [
    # Auth
    "Token",
    "TokenData",
    "UserLogin",
    "MagicLinkRequest",
    "MagicLinkVerifyRequest",
    "ImpersonateRequest",
    "FounderUserMembership",
    "UserResponse",
    "UserWithClients",
    "FounderUserSummary",
    # Client
    "AuthorizedDomainBase",
    "AuthorizedDomainCreate",
    "AuthorizedDomainUpdate",
    "AuthorizedDomainResponse",
    "ClientCreate",
    "ClientResponse",
    # Data Source
    "DataSourceCreate",
    "DataSourceResponse",
    "DataSourceDetail",
    "QuestionInfo",
    "DataSourceWithQuestions",
    "DimensionNameCreate",
    "DimensionNameBatchUpdate",
    "DimensionNameResponse",
    # VOC
    "ProcessVocResponse",
    "ProcessVocListResponse",
    "DimensionQuestionInfo",
    "VocSourceInfo",
    "VocClientInfo",
    "VocProjectInfo",
    "ProcessVocBulkUpdateItem",
    "ProcessVocBulkUpdateRequest",
    "ProcessVocBulkUpdateResponse",
    "ProcessVocAdminListResponse",
    "FieldMetadata",
    "FieldMetadataResponse",
    "DynamicBulkUpdateRequest",
    # CSV
    "CsvColumnMapping",
    "CsvUploadResponse",
    "CsvColumnMappingRequest",
    "CsvSaveResponse",
    # Admin
    "ColumnInfo",
    "TableInfo",
    "TableDataResponse",
    "RowCreateRequest",
    "RowUpdateRequest",
    "TableCreateRequest",
    "ColumnAddRequest",
    # Insights
    "InsightOrigin",
    "InsightCreate",
    "InsightUpdate",
    "InsightResponse",
    "InsightListResponse",
]

