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
    AuthorizedEmailBase,
    AuthorizedEmailCreate,
    AuthorizedEmailUpdate,
    AuthorizedEmailResponse,
    ClientCreate,
    ClientResponse,
    ClientLogoUpdate,
    ClientSettingsUpdate,
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

from .prompt import (
    PromptCreate,
    PromptUpdate,
    PromptResponse,
    PromptMenuItem,
    ClientPromptExecuteRequest,
    PromptHelperPromptResponse,
)

from .action import (
    ActionCreate,
    ActionResponse,
    ClientActionResponse,
)

from .facebook_ad import (
    FacebookAdCreate,
    FacebookAdUpdate,
    FacebookAdResponse,
    FacebookAdListResponse,
)

from .ad_image import (
    AdImageCreate,
    AdImageResponse,
    AdImageListResponse,
)

# Resolve forward references after all schemas are imported
# This is necessary for Pydantic v2 when using forward references
FounderUserMembership.model_rebuild()
UserWithClients.model_rebuild()
FounderUserSummary.model_rebuild()

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
    "AuthorizedEmailBase",
    "AuthorizedEmailCreate",
    "AuthorizedEmailUpdate",
    "AuthorizedEmailResponse",
    "ClientCreate",
    "ClientResponse",
    "ClientLogoUpdate",
    "ClientSettingsUpdate",
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
    # Prompts
    "PromptCreate",
    "PromptUpdate",
    "PromptResponse",
    "PromptMenuItem",
    "ClientPromptExecuteRequest",
    "PromptHelperPromptResponse",
    # Actions
    "ActionCreate",
    "ActionResponse",
    "ClientActionResponse",
    # Facebook Ads
    "FacebookAdCreate",
    "FacebookAdUpdate",
    "FacebookAdResponse",
    "FacebookAdListResponse",
    # Ad Images
    "AdImageCreate",
    "AdImageResponse",
    "AdImageListResponse",
]

