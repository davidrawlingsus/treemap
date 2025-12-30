# Refactor Phase 2 - Implementation Plan

**Status**: Planning  
**Branch**: `refactor`  
**Created**: December 29, 2025  
**Current Codebase Health**: 8.5/10

---

## 🎯 Overview

Phase 1 successfully reorganized the codebase into routers, services, and models. Phase 2 focuses on:
1. Further modularization of large files
2. Eliminating code duplication
3. Adding comprehensive test coverage
4. Improving documentation

**Goal**: Achieve 9.5/10 codebase health score

---

## 📋 Priority 1 Tasks (High Impact)

### 1.1 Split `founder_admin.py` (1,249 lines) 🔴

**Current Problem**: Single file is 4x larger than recommended 300-line guideline

**Solution**: Split into logical domain modules

```
backend/app/routers/founder_admin/
├── __init__.py              # Export all routers
├── users.py                 # User management (~120 lines)
├── domains.py               # Authorized domains (~175 lines)
├── voc_editor.py            # VOC data editing (~350 lines)
└── database.py              # Database admin (~600 lines)
```

**Files to Create**:
- `backend/app/routers/founder_admin/__init__.py`
- `backend/app/routers/founder_admin/users.py`
- `backend/app/routers/founder_admin/domains.py`
- `backend/app/routers/founder_admin/voc_editor.py`
- `backend/app/routers/founder_admin/database.py`

**Files to Modify**:
- `backend/app/main.py` (update import statement)

**Estimated Time**: 2-3 hours  
**Risk**: Low (well-defined separation)

---

### 1.2 Create Authorization Module 🟡

**Current Problem**: Client access verification duplicated across routers

**Locations of Duplication**:
- `backend/app/routers/clients.py:29` - `verify_client_access()` function
- `backend/app/routers/voc.py:354` - Inline membership check
- `backend/app/routers/auth.py:431` - Similar membership query

**Solution**: Create centralized authorization module

```python
# backend/app/authorization.py

def verify_client_access(client_id: UUID, user: User, db: Session) -> Client:
    """Verify user has access to client via membership or founder status"""
    ...

def verify_membership(user_id: UUID, client_id: UUID, db: Session) -> Membership:
    """Get active membership or raise HTTPException"""
    ...

def get_user_clients(user: User, db: Session) -> List[Client]:
    """Get all clients accessible to user"""
    ...
```

**Files to Create**:
- `backend/app/authorization.py` (~100 lines)

**Files to Modify**:
- `backend/app/routers/clients.py` (replace inline logic)
- `backend/app/routers/voc.py` (replace inline logic)
- `backend/app/routers/auth.py` (use new helpers)

**Estimated Time**: 1-2 hours  
**Risk**: Low (simple refactor)

---

### 1.3 Add Core Test Coverage 🟡

**Current Problem**: Test files exist but contain no test functions

**Solution**: Implement tests for critical paths

**Test Categories**:

```
backend/tests/
├── test_auth.py              # NEW: Auth endpoints (login, magic link)
├── test_authorization.py     # NEW: Access control logic
├── test_config.py            # EXISTS: Add actual tests
├── test_routes_integration.py # EXISTS: Add actual tests
├── test_utils.py             # EXISTS: Add actual tests
├── test_voc_queries.py       # NEW: VOC data queries
└── test_insights.py          # NEW: Insights CRUD
```

**Priority Test Cases**:
1. **Authentication**:
   - Login with valid credentials
   - Magic link generation and verification
   - Token expiration handling
   - Impersonation (founder only)

2. **Authorization**:
   - Client access via membership
   - Founder access to all clients
   - Denied access returns 403

3. **VOC Queries**:
   - Get VOC data with filters
   - Get questions for dimension
   - Get clients with data

4. **Insights**:
   - Create insight
   - Update insight
   - List insights with filters

**Files to Create**:
- `backend/tests/test_auth.py` (~200 lines)
- `backend/tests/test_authorization.py` (~150 lines)
- `backend/tests/test_voc_queries.py` (~200 lines)
- `backend/tests/test_insights.py` (~200 lines)

**Files to Modify**:
- `backend/tests/test_config.py` (add real tests)
- `backend/tests/test_routes_integration.py` (add real tests)
- `backend/tests/test_utils.py` (add real tests)

**Estimated Time**: 6-8 hours  
**Risk**: Medium (requires understanding business logic)

---

## 📋 Priority 2 Tasks (Code Quality)

### 2.1 Split `schemas.py` (549 lines) 🟡

**Current Problem**: Approaching threshold, better organized by domain

**Solution**: Split by domain into submodule

```
backend/app/schemas/
├── __init__.py              # Export all schemas
├── auth.py                  # Auth schemas (~80 lines)
├── client.py                # Client schemas (~60 lines)
├── data_source.py           # Data source schemas (~120 lines)
├── voc.py                   # VOC schemas (~150 lines)
├── insight.py               # Insight schemas (~90 lines)
└── admin.py                 # Admin/database schemas (~50 lines)
```

**Files to Create**:
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/client.py`
- `backend/app/schemas/data_source.py`
- `backend/app/schemas/voc.py`
- `backend/app/schemas/insight.py`
- `backend/app/schemas/admin.py`

**Files to Modify**:
- All routers that import from `app.schemas`

**Estimated Time**: 2-3 hours  
**Risk**: Low (straightforward reorganization)

---

### 2.2 Create Environment Documentation 🟢

**Current Problem**: No `.env.example` file for new developers

**Solution**: Document all environment variables

**Files to Create**:
- `.env.example` (comprehensive template)
- `docs/ENVIRONMENT_VARIABLES.md` (detailed documentation)

**Content Structure**:

```bash
# .env.example

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/vizualizd
DATABASE_PUBLIC_URL=  # Optional: For local dev with Railway

# Application
ENVIRONMENT=development  # development | production
JWT_SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7 days

# Magic Link Authentication
MAGIC_LINK_TOKEN_EXPIRE_MINUTES=60
MAGIC_LINK_RATE_LIMIT_SECONDS=120
FRONTEND_BASE_URL=http://localhost:8000
MAGIC_LINK_REDIRECT_PATH=/magic-login

# Email Service (Resend)
RESEND_API_KEY=
RESEND_FROM_EMAIL=noreply@yourdomain.com
RESEND_REPLY_TO_EMAIL=support@yourdomain.com

# OpenAI Integration
OPENAI_API_KEY=sk-...

# OAuth (Optional)
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=

# CORS (Optional)
ADDITIONAL_CORS_ORIGINS=["http://localhost:3000"]
```

**Files to Create**:
- `.env.example`
- `docs/ENVIRONMENT_VARIABLES.md`

**Estimated Time**: 1 hour  
**Risk**: None

---

### 2.3 Add Integration Tests 🟢

**Current Problem**: No end-to-end API tests

**Solution**: Add API integration tests with test database

**Files to Create**:
- `backend/tests/integration/test_auth_flow.py`
- `backend/tests/integration/test_voc_workflow.py`
- `backend/tests/integration/test_insights_workflow.py`

**Test Scenarios**:
1. **Auth Flow**: Request magic link → Verify → Access protected route
2. **VOC Workflow**: Upload CSV → Map columns → Query data
3. **Insights Workflow**: Create insight → Add origins → Update → Delete

**Estimated Time**: 4-5 hours  
**Risk**: Medium (requires test database setup)

---

## 📋 Priority 3 Tasks (Nice to Have)

### 3.1 Add Response Caching 🟢

**Problem**: Expensive queries (VOC data, insights) called repeatedly

**Solution**: Add caching middleware for read endpoints

**Candidates for Caching**:
- `/api/voc/data` (5 second cache)
- `/api/voc/questions` (30 second cache)
- `/api/clients/{id}/insights` (10 second cache)
- `/api/dimensions/{uuid}/{source}/{ref}/summary` (1 hour cache)

**Implementation**: Use `functools.lru_cache` or Redis

**Estimated Time**: 2-3 hours  
**Risk**: Low

---

### 3.2 Create Pagination Helpers 🟢

**Problem**: Pagination logic duplicated across multiple endpoints

**Solution**: Create reusable pagination utilities

```python
# backend/app/pagination.py

def paginate(query, page: int, page_size: int) -> PaginatedResponse:
    """Apply pagination and return structured response"""
    ...

def get_pagination_params(page: int = 1, page_size: int = 50) -> dict:
    """Validate and return pagination parameters"""
    ...
```

**Estimated Time**: 1 hour  
**Risk**: None

---

### 3.3 Add Request/Response Logging 🟢

**Problem**: No structured logging for API requests

**Solution**: Add middleware for request/response logging

```python
# backend/app/middleware/logging.py

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing and response status"""
    ...
```

**Estimated Time**: 1 hour  
**Risk**: Low

---

## 📅 Implementation Timeline

### Week 1: Core Improvements
- **Day 1-2**: Split `founder_admin.py` (Task 1.1)
- **Day 3**: Create authorization module (Task 1.2)
- **Day 4-5**: Add core tests (Task 1.3 - partial)

### Week 2: Quality & Documentation
- **Day 1-2**: Complete core tests (Task 1.3)
- **Day 3**: Split `schemas.py` (Task 2.1)
- **Day 4**: Environment documentation (Task 2.2)
- **Day 5**: Integration tests (Task 2.3)

### Week 3: Polish (Optional)
- **Day 1**: Response caching (Task 3.1)
- **Day 2**: Pagination helpers (Task 3.2)
- **Day 3**: Request logging (Task 3.3)
- **Day 4-5**: Buffer/refinement

---

## ✅ Success Criteria

**Phase 2 Complete When**:
1. ✅ No files exceed 500 lines (target: 300 lines)
2. ✅ Test coverage > 70% for critical paths
3. ✅ Zero code duplication in authorization logic
4. ✅ All environment variables documented
5. ✅ Integration tests pass for major workflows

**Expected Codebase Health**: 9.5/10

---

## 🚀 Getting Started

**To begin Phase 2**:

```bash
# Ensure you're on refactor branch
git checkout refactor

# Pull latest changes
git pull origin refactor

# Start with Task 1.1
mkdir -p backend/app/routers/founder_admin
# Begin splitting founder_admin.py...
```

---

## 📊 Progress Tracking

- [ ] Task 1.1: Split founder_admin.py
- [ ] Task 1.2: Create authorization module
- [ ] Task 1.3: Add core test coverage
- [ ] Task 2.1: Split schemas.py
- [ ] Task 2.2: Environment documentation
- [ ] Task 2.3: Integration tests
- [ ] Task 3.1: Response caching (optional)
- [ ] Task 3.2: Pagination helpers (optional)
- [ ] Task 3.3: Request logging (optional)

---

**Next Command**: Review this plan and approve to proceed with Task 1.1

