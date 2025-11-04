# Database Schema Refactoring Plan

## Overview
The Railway database has a new schema structure that differs significantly from the current application models. This document outlines the differences and the refactoring plan.

## Schema Comparison

### Current Schema (app/models/)
- **clients** - 6 columns, no user relationships
- **data_sources** - Stores raw and normalized JSONB data
- **dimension_names** - Maps ref_keys to custom names per data source

### New Railway Schema

#### 1. **clients** table
**Changes:**
- ✅ Same: id, name, slug, is_active, settings, created_at, updated_at
- ➕ **NEW:** `founder_user_id` (UUID, FK to users.id)
- ⚠️ **Note:** Unique constraints are on `name` and `slug` (via indexes, not column-level)

**Migration needed:**
- Add `founder_user_id` column (nullable initially)
- Update relationships to include founder user

#### 2. **users** table (NEW)
**Purpose:** User authentication and management

**Columns:**
- `id` (UUID, PK, default: gen_random_uuid())
- `email` (VARCHAR(255), unique, not null)
- `name` (VARCHAR(255), nullable)
- `is_founder` (BOOLEAN, default: false)
- `is_active` (BOOLEAN, default: true)
- `email_verified_at` (TIMESTAMP, nullable)
- `last_login_at` (TIMESTAMP, nullable)
- `metadata` (JSONB, nullable)
- `created_at` (TIMESTAMP, not null, default: CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, not null, default: CURRENT_TIMESTAMP)

**Indexes:**
- idx_users_email (non-unique)
- idx_users_is_active (non-unique)
- idx_users_is_founder (non-unique)
- users_email_key (unique)

**Action:** Create new `User` model

#### 3. **memberships** table (NEW)
**Purpose:** Many-to-many relationship between users and clients with roles

**Columns:**
- `id` (UUID, PK, default: gen_random_uuid())
- `user_id` (UUID, FK to users.id, not null)
- `client_id` (UUID, FK to clients.id, not null)
- `role` (VARCHAR(50), default: 'viewer')
- `status` (VARCHAR(50), default: 'active')
- `invited_by` (UUID, FK to users.id, nullable)
- `invited_at` (TIMESTAMP, nullable)
- `joined_at` (TIMESTAMP, nullable)
- `metadata` (JSONB, nullable)
- `created_at` (TIMESTAMP, not null, default: CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, not null, default: CURRENT_TIMESTAMP)

**Constraints:**
- Unique constraint on (user_id, client_id) - ensures one membership per user-client pair
- Foreign keys to users (user_id, invited_by) and clients (client_id)

**Indexes:**
- idx_memberships_client_id
- idx_memberships_role
- idx_memberships_status
- idx_memberships_user_id
- idx_memberships_user_status (composite: user_id, status)

**Action:** Create new `Membership` model

#### 4. **process_voc** table (REPLACES data_sources)
**Purpose:** Stores processed/normalized VOC data in a relational format instead of JSONB

**Key Differences from data_sources:**
- ❌ **REMOVED:** `raw_data` (JSONB) - no longer stored
- ❌ **REMOVED:** `normalized_data` (JSONB) - replaced with relational columns
- ❌ **REMOVED:** `name`, `source_format`, `is_normalized`
- ➕ **NEW:** Individual columns for each data point
- ➕ **NEW:** `client_uuid` (FK to clients.id) - links to clients table
- ➕ **NEW:** `dimension_name` stored directly (not in separate table)
- ➕ **NEW:** `topics` (JSONB) - stores extracted topics
- ➕ **NEW:** `overall_sentiment` (VARCHAR) - sentiment analysis result

**Columns:**
- `id` (INTEGER, PK, auto-increment)
- `respondent_id` (VARCHAR(50), not null)
- `created`, `last_modified` (TIMESTAMP, nullable)
- `client_id` (VARCHAR(50), nullable) - legacy client ID
- `client_name` (VARCHAR(255), nullable)
- `project_id`, `project_name` (VARCHAR, nullable)
- `total_rows` (INTEGER, nullable)
- `data_source` (VARCHAR(255), nullable) - e.g., "email_survey"
- `region`, `response_type`, `user_type` (VARCHAR(50), nullable)
- `start_date`, `submit_date` (TIMESTAMP, nullable)
- `dimension_ref` (VARCHAR(50), not null) - e.g., "ref_ljwfv"
- `dimension_name` (TEXT, nullable) - e.g., "Positive Results Experienced"
- `value` (TEXT, nullable) - the actual response text
- `overall_sentiment` (VARCHAR(50), nullable)
- `topics` (JSONB, nullable) - array of topic objects
- `created_at`, `updated_at` (TIMESTAMP, default: CURRENT_TIMESTAMP)
- `client_uuid` (UUID, FK to clients.id, nullable)

**Constraints:**
- Unique constraint on (respondent_id, dimension_ref)
- Foreign key: client_uuid → clients.id

**Indexes:**
- fk_respondent_dimension (unique: respondent_id, dimension_ref)
- idx_process_voc_client_uuid

**Action:** 
- Create new `ProcessVoc` model
- Remove or deprecate `DataSource` model
- Remove or deprecate `DimensionName` model (dimension_name now in process_voc)

## Refactoring Plan

### Phase 1: Model Updates

1. **Update Client model**
   - Add `founder_user_id` field
   - Add relationship to `User` (founder)
   - Add relationship to `Membership` (members)

2. **Create User model**
   - Implement all columns from schema
   - Add relationships to `Client` (as founder) and `Membership`

3. **Create Membership model**
   - Implement all columns from schema
   - Add relationships to `User` and `Client`
   - Add unique constraint on (user_id, client_id)

4. **Create ProcessVoc model**
   - Implement all columns from schema
   - Replace `DataSource` usage throughout codebase
   - Add relationship to `Client` via `client_uuid`

### Phase 2: Data Migration

1. **Migrate existing data_sources to process_voc**
   - Extract normalized_data from JSONB
   - Flatten into process_voc rows
   - Map client_id to client_uuid
   - Extract dimension_ref and dimension_name

2. **Migrate dimension_names**
   - If dimension_names table exists, merge into process_voc.dimension_name
   - Or keep as lookup table for historical data

3. **Create default users and memberships**
   - Create founder users for existing clients
   - Create memberships linking users to clients

### Phase 3: API Updates

1. **Update endpoints to use new models**
   - Replace `/api/data-sources` endpoints with `/api/voc` or `/api/process-voc`
   - Update data upload/processing to write to process_voc
   - Update queries to use relational columns instead of JSONB

2. **Update transformers**
   - Modify `DataTransformer` to write to process_voc format
   - Extract topics and sentiment during transformation
   - Map dimension_ref correctly

3. **Update frontend integration**
   - Update API calls to new endpoints
   - Update data structures expected by frontend

### Phase 4: Cleanup

1. **Remove deprecated models**
   - Remove `DataSource` model (or keep for migration purposes)
   - Remove `DimensionName` model (or keep as lookup table)

2. **Update migrations**
   - Create Alembic migrations for new schema
   - Ensure backward compatibility during transition

## Key Design Decisions

### Why process_voc instead of data_sources?
- **Performance:** Relational queries are faster than JSONB queries
- **Queryability:** Can filter/index on specific columns
- **Normalization:** Data is already processed and normalized
- **Scalability:** Better for large datasets

### User Management
- Multi-tenant support with roles (owner, viewer, etc.)
- Founder users can create clients
- Memberships manage access to clients

### Data Structure
- Each row in process_voc represents one response to one dimension
- Unique constraint ensures no duplicate responses
- Topics stored as JSONB for flexibility
- Sentiment analysis pre-computed

## Files to Create/Modify

### New Files:
- `app/models/user.py` - User model
- `app/models/membership.py` - Membership model  
- `app/models/process_voc.py` - ProcessVoc model (replaces DataSource)

### Files to Modify:
- `app/models/client.py` - Add founder_user_id, update relationships
- `app/models/__init__.py` - Export new models
- `app/schemas.py` - Update/create schemas for new models
- `app/main.py` - Update endpoints to use new models
- `app/transformers/__init__.py` - Update transformers for process_voc

### Files to Deprecate:
- `app/models/data_source.py` - Eventually remove
- `app/models/dimension_name.py` - Eventually remove (or keep as lookup)

## Next Steps

1. ✅ Schema introspection complete
2. ⏳ Create new model files
3. ⏳ Update existing models
4. ⏳ Create migration scripts
5. ⏳ Update API endpoints
6. ⏳ Test data migration
7. ⏳ Update frontend integration

